import hashlib
import io
import json
import re

import streamlit as st
from google import genai
from PIL import Image, UnidentifiedImageError

try:
    from gtts import gTTS
except ImportError:
    gTTS = None


st.set_page_config(
    page_title="Stratifyxglobal | ওষুধ সহায়ক",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Bengali:wght@400;500;600;700&display=swap');

:root {
  --navy: #12304a;
  --teal: #087f7b;
  --mint: #eaf8f5;
  --line: #d9e8e6;
  --danger: #b42318;
  --danger-bg: #fff1f0;
}

html, body, [class*="css"], .stApp {
  font-family: "Noto Sans Bengali", sans-serif;
}

.stApp {
  background: #f7fbfb;
  color: var(--navy);
}

[data-testid="stHeader"] {
  background: rgba(247, 251, 251, 0.88);
}

.block-container {
  max-width: 1180px;
  padding-top: 1.5rem;
  padding-bottom: 4rem;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: .8rem 0 1.25rem;
  border-bottom: 1px solid var(--line);
  margin-bottom: 1.7rem;
}

.brand-name {
  color: var(--navy);
  font-size: 1.35rem;
  font-weight: 700;
}

.brand-name span {
  color: var(--teal);
}

.brand-badge {
  color: #416476;
  font-size: .86rem;
  font-weight: 600;
}

.hero {
  background: #ffffff;
  border: 1px solid var(--line);
  border-left: 5px solid var(--teal);
  padding: 1.5rem 1.7rem;
  margin-bottom: 1.3rem;
  box-shadow: 0 10px 30px rgba(18, 48, 74, .06);
}

.hero h1 {
  color: var(--navy);
  font-size: clamp(1.75rem, 4vw, 2.7rem);
  line-height: 1.25;
  margin: 0 0 .45rem;
}

.hero p {
  color: #557180;
  font-size: 1rem;
  margin: 0;
}

.step {
  color: var(--teal);
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: .25rem;
}

.section-title {
  color: var(--navy);
  font-size: 1.28rem;
  font-weight: 700;
  margin: 1rem 0 .65rem;
}

.medicine-card {
  background: #fff;
  border: 1px solid var(--line);
  border-left: 4px solid var(--teal);
  padding: 1.05rem 1.15rem;
  margin: .65rem 0;
}

.medicine-card h3 {
  color: var(--navy);
  margin: 0 0 .55rem;
  font-size: 1.18rem;
}

.medicine-card p {
  color: #3f5e6c;
  margin: .3rem 0;
}

.danger-card {
  background: var(--danger-bg);
  border: 1px solid #f4b7b2;
  border-left: 5px solid var(--danger);
  color: #7a271a;
  padding: .9rem 1rem;
  margin: .55rem 0;
}

.safe-card {
  background: var(--mint);
  border: 1px solid #b8e0d9;
  color: #185b59;
  padding: .9rem 1rem;
  margin: .55rem 0;
}

.trust-note {
  color: #506f7c;
  background: #fff;
  border: 1px solid var(--line);
  padding: .85rem 1rem;
  margin-top: 1rem;
  font-size: .9rem;
}

div.stButton > button {
  min-height: 3rem;
  border-radius: 6px;
  font-weight: 700;
}

div.stButton > button[kind="primary"] {
  background: var(--teal);
  border-color: var(--teal);
}

[data-testid="stFileUploaderDropzone"] {
  background: #fff;
  border: 1.5px dashed #80bdb8;
  border-radius: 6px;
}

[data-testid="stDataFrame"], [data-testid="stAudio"] {
  border: 1px solid var(--line);
  background: #fff;
}

@media (max-width: 700px) {
  .block-container {
    padding: .8rem .8rem 3rem;
  }
  .brand {
    align-items: flex-start;
    flex-direction: column;
    gap: .15rem;
  }
  .hero {
    padding: 1.15rem;
  }
  .hero h1 {
    font-size: 1.8rem;
  }
  .medicine-card {
    padding: .9rem;
  }
}
</style>
""",
    unsafe_allow_html=True,
)


ANALYSIS_PROMPT = """
তুমি বাংলাদেশের সাধারণ মানুষের জন্য তৈরি একটি অত্যন্ত সতর্ক স্বাস্থ্য-তথ্য সহকারী।
প্রেসক্রিপশন বা ওষুধের প্যাকেটের ছবিটি পড়ে নিচের JSON structure-এ শুধু JSON উত্তর দাও।

{
  "image_quality": "clear অথবা unclear",
  "image_message": "ছবির কোন অংশ অস্পষ্ট হলে সহজ বাংলায় বলো, নইলে খালি string",
  "summary": "খুব সহজ বাংলায় ২-৪ বাক্যে ছবিটির সারাংশ",
  "medicines": [
    {
      "name": "ছবিতে যেমন দেখা যায়",
      "purpose": "সহজ বাংলায় কী কাজে লাগে; নিশ্চিত না হলে ছবিতে স্পষ্ট নয়",
      "dose": "শুধু ছবিতে স্পষ্ট ডোজ; না হলে ছবিতে স্পষ্ট নয়",
      "timing": "শুধু ছবিতে স্পষ্ট সময়/খাবারের সম্পর্ক; না হলে ছবিতে স্পষ্ট নয়",
      "duration": "শুধু ছবিতে স্পষ্ট থাকলে; না হলে ছবিতে স্পষ্ট নয়",
      "note": "সহজ সতর্কতা বা খালি string"
    }
  ],
  "schedule": [
    {
      "time": "সকাল/দুপুর/রাত/অন্যান্য",
      "medicine": "ওষুধের নাম",
      "instruction": "কতটি ও কখন; শুধু ছবিতে স্পষ্ট তথ্য"
    }
  ],
  "danger_signals": [
    {
      "title": "সংক্ষিপ্ত সতর্কতার নাম",
      "message": "সহজ বাংলায় ব্যাখ্যা",
      "action": "ডাক্তার বা ফার্মাসিস্টকে কী জিজ্ঞেস করবে"
    }
  ],
  "voice_text": "নিরক্ষর বা কম পড়তে জানা মানুষের জন্য খুব সহজ কথ্য বাংলায় সর্বোচ্চ ১৪০ শব্দের সারাংশ"
}

অবশ্যই মানবে:
- কোনো লেখা, ওষুধের নাম, ডোজ বা সময় অনুমান করবে না।
- অস্পষ্ট হলে সরাসরি "ছবিতে স্পষ্ট নয়" বলবে।
- danger_signals-এ কেবল সম্ভাব্য ঝুঁকি লিখবে এবং যাচাই করতে বলবে; নিশ্চিত রোগনির্ণয় করবে না।
- ছবিতে স্পষ্ট তথ্য না থাকলে schedule খালি রাখবে।
- নিজে থেকে ডোজ বা চিকিৎসা দেবে না।
- voice_text-এর শেষে বলবে: নিশ্চিত হতে ডাক্তার বা ফার্মাসিস্টের সাথে কথা বলুন।
"""

TEST_ANALYSIS_PROMPT = """
তুমি বাংলাদেশের সাধারণ মানুষের জন্য তৈরি একটি অত্যন্ত সতর্ক স্বাস্থ্য-তথ্য সহকারী।
ব্যবহারকারীর দেওয়া diagnostic test prescription বা test list পড়ে নিচের JSON structure-এ শুধু JSON উত্তর দাও।

{
  "image_quality": "clear অথবা unclear",
  "image_message": "ছবির কোন অংশ অস্পষ্ট হলে সহজ বাংলায় বলো, নইলে খালি string",
  "summary": "খুব সহজ বাংলায় ২-৪ বাক্যে test list-এর সারাংশ",
  "counts": {
    "total": 0,
    "routine": 0,
    "special": 0,
    "possible_overlap_groups": 0,
    "questions_for_doctor": 0
  },
  "tests": [
    {
      "name": "ছবিতে যেমন দেখা যায়",
      "category": "রক্ত/প্রস্রাব/ইমেজিং/অন্যান্য/ছবিতে স্পষ্ট নয়",
      "purpose": "সাধারণত এই test কেন করা হয়, সহজ বাংলায়",
      "preparation": "খালি পেট বা অন্য প্রস্তুতি; নিশ্চিত না হলে ল্যাব বা ডাক্তারকে জিজ্ঞেস করুন",
      "priority_note": "ছবিতে জরুরি লেখা থাকলে বলো; না থাকলে জরুরিতা ছবিতে স্পষ্ট নয়",
      "question": "এই test নিয়ে ডাক্তারকে করার একটি দরকারি প্রশ্ন"
    }
  ],
  "possible_overlaps": [
    {
      "tests": "সম্ভাব্য কাছাকাছি তথ্য দেওয়া test-গুলোর নাম",
      "explanation": "কেন কাছাকাছি মনে হতে পারে, কিন্তু কেন দুটোই লাগতে পারে সেটিও বলো",
      "ask_doctor": "ডাক্তারের কাছে কীভাবে জানতে হবে"
    }
  ],
  "preparation_checklist": ["সহজ প্রস্তুতির নির্দেশনা"],
  "doctor_questions": ["ডাক্তারের কাছে করার গুরুত্বপূর্ণ প্রশ্ন"],
  "danger_signals": [
    {
      "title": "জরুরি বা গুরুত্বপূর্ণ বিষয়",
      "message": "সহজ বাংলায় ব্যাখ্যা",
      "action": "কী করতে হবে"
    }
  ],
  "voice_text": "নিরক্ষর বা কম পড়তে জানা মানুষের জন্য সর্বোচ্চ ১৪০ শব্দের কথ্য বাংলা সারাংশ"
}

অবশ্যই মানবে:
- কখনো বলবে না যে কোনো test অপ্রয়োজনীয়, বাদ দিতে হবে বা না করলেও চলবে।
- test list, রোগীর ইতিহাস ও চিকিৎসকের কারণ না জেনে প্রয়োজনীয়তা সম্পর্কে চূড়ান্ত সিদ্ধান্ত দেবে না।
- সম্ভাব্য overlap থাকলে শুধু ডাক্তারকে জিজ্ঞেস করতে বলবে।
- ছবিতে যা নেই, তা অনুমান করবে না।
- অস্পষ্ট লেখা হলে "ছবিতে স্পষ্ট নয়" বলবে।
- প্রস্তুতির নিয়ম নিশ্চিত না হলে সংশ্লিষ্ট lab বা ডাক্তারকে জিজ্ঞেস করতে বলবে।
- জরুরি স্বাস্থ্য সমস্যা মনে হলে দ্রুত চিকিৎসা নিতে বলবে।
- voice_text-এর শেষে বলবে: কোনো test বাদ দেওয়ার আগে অবশ্যই চিকিৎসকের সাথে কথা বলুন।
"""

REVIEW_ANALYSIS_PROMPT = """
তুমি একটি অত্যন্ত সতর্ক medication-review সহায়ক। ব্যবহারকারী একাধিক স্বাস্থ্য-নথির ছবি দিয়েছেন:
এক বা একাধিক test report এবং ডাক্তার দেওয়া prescription। সব report ও prescription একসাথে দেখে শুধু JSON উত্তর দাও।

{
  "image_quality": "clear অথবা unclear",
  "image_message": "কোন ছবি বা অংশ অস্পষ্ট তা বলো, নইলে খালি string",
  "summary": "report ও prescription-এর সম্পর্ক খুব সহজ বাংলায় ২-৪ বাক্যে",
  "report_findings": [
    {
      "finding": "report-এ দেখা গুরুত্বপূর্ণ ফলাফল",
      "status": "স্বাভাবিক/বেশি/কম/ছবিতে স্পষ্ট নয়",
      "meaning": "সহজ বাংলায় অর্থ",
      "action": "ডাক্তারকে কী জিজ্ঞেস করবে"
    }
  ],
  "medicine_reviews": [
    {
      "name": "ওষুধের নাম",
      "status": "reason_clear অথবা ask_doctor অথবা verify_soon",
      "status_label": "কারণ বোঝা যাচ্ছে অথবা কারণ পরিষ্কার নয় অথবা দ্রুত যাচাই প্রয়োজন",
      "usual_purpose": "ওষুধটি সাধারণত কেন ব্যবহার হয়",
      "connection": "দেওয়া report-এর সাথে সম্ভাব্য সম্পর্ক; নিশ্চিত না হলে পরিষ্কার নয় বলো",
      "concern": "সম্ভাব্য সমস্যা বা খালি string",
      "doctor_question": "ডাক্তারকে করার নির্দিষ্ট প্রশ্ন"
    }
  ],
  "possible_interactions": [
    {
      "items": "সম্ভাব্য interaction থাকা ওষুধ/বিষয়",
      "message": "এটি শুধু সম্ভাবনা—সহজ ব্যাখ্যা",
      "action": "নিজে বন্ধ না করে কাকে দ্রুত দেখাতে হবে"
    }
  ],
  "doctor_questions": ["ডাক্তারের কাছে করার অগ্রাধিকারভিত্তিক প্রশ্ন"],
  "danger_signals": [
    {
      "title": "গুরুত্বপূর্ণ সতর্কতা",
      "message": "সহজ ব্যাখ্যা",
      "action": "কী করতে হবে"
    }
  ],
  "voice_text": "সর্বোচ্চ ১৪০ শব্দে খুব সহজ কথ্য বাংলা সারাংশ"
}

অবশ্যই মানবে:
- কখনো বলবে না ডাক্তার ভুল করেছেন, ওষুধ অপ্রয়োজনীয়, অথবা ওষুধ বন্ধ করতে হবে।
- শুধু report দেখে diagnosis বা prescription সঠিক/ভুলের চূড়ান্ত সিদ্ধান্ত দেবে না।
- ওষুধের কারণ report থেকে পরিষ্কার না হলে status হবে ask_doctor।
- dose অস্বাভাবিক মনে হলে বা সম্ভাব্য interaction থাকলে status হবে verify_soon এবং দ্রুত ডাক্তার/ফার্মাসিস্টকে যাচাই করতে বলবে।
- কোনো ওষুধ নিজে থেকে শুরু, বন্ধ বা dose পরিবর্তন করতে বলবে না।
- অস্পষ্ট লেখা অনুমান করবে না।
- voice_text-এর শেষে বলবে: কোনো ওষুধ পরিবর্তনের আগে অবশ্যই ডাক্তার বা ফার্মাসিস্টের সাথে কথা বলুন।
"""


def get_api_key() -> str:
    try:
        return str(st.secrets.get("GEMINI_API_KEY", "")).strip()
    except Exception:
        return ""


def clean_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def analyze_image(api_key: str, image: Image.Image, mode: str) -> dict:
    client = genai.Client(api_key=api_key)
    prompt = ANALYSIS_PROMPT if mode == "ওষুধ বুঝুন" else TEST_ANALYSIS_PROMPT
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt, image],
        config={"response_mime_type": "application/json"},
    )
    if not response.text:
        raise ValueError("AI কোনো উত্তর দেয়নি।")
    return clean_json(response.text)


def analyze_review(
    api_key: str, report_images: list[Image.Image], prescription_image: Image.Image
) -> dict:
    client = genai.Client(api_key=api_key)
    contents = [REVIEW_ANALYSIS_PROMPT]
    for index, report_image in enumerate(report_images, start=1):
        contents.extend([f"Test report পৃষ্ঠা {index}", report_image])
    contents.extend(["Doctor prescription", prescription_image])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config={"response_mime_type": "application/json"},
    )
    if not response.text:
        raise ValueError("AI কোনো উত্তর দেয়নি।")
    return clean_json(response.text)


def make_voice(text: str) -> bytes:
    if gTTS is None:
        raise RuntimeError("Voice package পাওয়া যায়নি।")
    audio = io.BytesIO()
    gTTS(text=text, lang="bn", slow=False).write_to_fp(audio)
    return audio.getvalue()


def esc(value) -> str:
    import html

    return html.escape(str(value or "ছবিতে স্পষ্ট নয়"))


def medicine_card(medicine: dict) -> None:
    st.markdown(
        f"""
        <div class="medicine-card">
          <h3>💊 {esc(medicine.get("name"))}</h3>
          <p><strong>কী কাজে লাগে:</strong> {esc(medicine.get("purpose"))}</p>
          <p><strong>ডোজ:</strong> {esc(medicine.get("dose"))}</p>
          <p><strong>কখন খাবেন:</strong> {esc(medicine.get("timing"))}</p>
          <p><strong>কতদিন:</strong> {esc(medicine.get("duration"))}</p>
          {f'<p><strong>খেয়াল রাখুন:</strong> {esc(medicine.get("note"))}</p>' if medicine.get("note") else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def test_card(test: dict) -> None:
    st.markdown(
        f"""
        <div class="medicine-card">
          <h3>🧪 {esc(test.get("name"))}</h3>
          <p><strong>ধরন:</strong> {esc(test.get("category"))}</p>
          <p><strong>সাধারণত কেন করা হয়:</strong> {esc(test.get("purpose"))}</p>
          <p><strong>প্রস্তুতি:</strong> {esc(test.get("preparation"))}</p>
          <p><strong>জরুরিতা:</strong> {esc(test.get("priority_note"))}</p>
          <p><strong>ডাক্তারকে জিজ্ঞেস করুন:</strong> {esc(test.get("question"))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def review_card(item: dict) -> None:
    status = item.get("status", "ask_doctor")
    icons = {"reason_clear": "✅", "ask_doctor": "❓", "verify_soon": "⚠️"}
    css_class = "danger-card" if status == "verify_soon" else "medicine-card"
    st.markdown(
        f"""
        <div class="{css_class}">
          <h3>{icons.get(status, "❓")} {esc(item.get("name"))}</h3>
          <p><strong>অবস্থা:</strong> {esc(item.get("status_label"))}</p>
          <p><strong>সাধারণত কী কাজে লাগে:</strong> {esc(item.get("usual_purpose"))}</p>
          <p><strong>Report-এর সাথে সম্পর্ক:</strong> {esc(item.get("connection"))}</p>
          {f'<p><strong>যা যাচাই করা দরকার:</strong> {esc(item.get("concern"))}</p>' if item.get("concern") else ''}
          <p><strong>ডাক্তারকে জিজ্ঞেস করুন:</strong> {esc(item.get("doctor_question"))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ask_follow_up(api_key: str, analysis: dict, question: str, mode: str) -> str:
    client = genai.Client(api_key=api_key)
    context = json.dumps(analysis, ensure_ascii=False)
    prompt = f"""
এই {mode} বিশ্লেষণের প্রসঙ্গে ব্যবহারকারীর প্রশ্নের উত্তর খুব সহজ বাংলায় দাও।
তথ্য অস্পষ্ট হলে অনুমান না করে ডাক্তার বা ফার্মাসিস্টকে জিজ্ঞেস করতে বলো।
কোনো নতুন ডোজ বা চিকিৎসা দেবে না।
Test mode হলে কখনো কোনো test বাদ দিতে বা অপ্রয়োজনীয় বলতে পারবে না।
Report review mode হলে ডাক্তার ভুল বলেছেন বা ওষুধ বন্ধ করতে হবে—এমন সিদ্ধান্ত দেবে না।

বিশ্লেষণ: {context}
প্রশ্ন: {question}
"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text or "উত্তর পাওয়া যায়নি।"


def simplify_answer(api_key: str, analysis: dict, mode: str) -> str:
    client = genai.Client(api_key=api_key)
    context = json.dumps(analysis, ensure_ascii=False)
    prompt = f"""
নিচের {mode} বিশ্লেষণটি খুব সহজ, কথ্য, গ্রামের সাধারণ মানুষের বোঝার মতো বাংলায়
সর্বোচ্চ ১০০ শব্দে বলো। কোনো তথ্য যোগ বা অনুমান করবে না। শেষে ডাক্তার বা ফার্মাসিস্টের
সাথে কথা বলতে বলো।
Test mode হলে কোনো test বাদ দেওয়ার পরামর্শ দেবে না।
Report review mode হলে কোনো ওষুধ বন্ধ বা dose পরিবর্তনের পরামর্শ দেবে না।

{context}
"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text or "সহজ ব্যাখ্যা পাওয়া যায়নি।"


for key, default in {
    "analysis": None,
    "image_id": None,
    "active_mode": None,
    "voice_audio": None,
    "simple_answer": None,
    "follow_up_answer": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


st.markdown(
    """
<div class="brand">
  <div class="brand-name">Stratifyx<span>global</span></div>
  <div class="brand-badge">বিশ্বস্ত ডিজিটাল স্বাস্থ্য সহায়ক</div>
</div>
<div class="hero">
  <div class="step">Prescription Intelligence</div>
  <h1>স্বাস্থ্য নির্দেশনা বুঝুন, নিরাপদ থাকুন</h1>
  <p>ওষুধের prescription, test list অথবা report ও prescription দিন। সহজ বাংলা ব্যাখ্যা ও গুরুত্বপূর্ণ সতর্কতা পান।</p>
</div>
""",
    unsafe_allow_html=True,
)

api_key = get_api_key()
if not api_key:
    with st.sidebar:
        st.markdown("### গোপন সেটিংস")
        api_key = st.text_input("Google AI Studio API Key", type="password")

mode = st.segmented_control(
    "সেবা বেছে নিন",
    options=["ওষুধ বুঝুন", "টেস্ট বুঝুন", "রিপোর্ট ও প্রেসক্রিপশন যাচাই"],
    default="ওষুধ বুঝুন",
    selection_mode="single",
    label_visibility="collapsed",
)

is_medicine_mode = mode == "ওষুধ বুঝুন"
is_test_mode = mode == "টেস্ট বুঝুন"
is_review_mode = mode == "রিপোর্ট ও প্রেসক্রিপশন যাচাই"
if st.session_state.active_mode != mode:
    st.session_state.active_mode = mode
    st.session_state.analysis = None
    st.session_state.image_id = None
    st.session_state.voice_audio = None
    st.session_state.simple_answer = None
    st.session_state.follow_up_answer = None

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    if is_medicine_mode:
        upload_title = "ওষুধের প্রেসক্রিপশনের ছবি দিন"
    elif is_test_mode:
        upload_title = "Test prescription বা test list-এর ছবি দিন"
    else:
        upload_title = "Test report ও doctor prescription দিন"
    st.markdown(f'<div class="step">ধাপ ১</div><div class="section-title">{upload_title}</div>', unsafe_allow_html=True)
    if is_review_mode:
        report_files = st.file_uploader(
            "১. Test report-এর সব ছবি দিন (সর্বোচ্চ ২০টি)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="report_file",
        )
        prescription_file = st.file_uploader(
            "২. Doctor prescription-এর ছবি",
            type=["jpg", "jpeg", "png", "webp"],
            key="prescription_file",
        )
        uploaded_file = None
    else:
        uploaded_file = st.file_uploader(
            "পরিষ্কার JPG, PNG বা WEBP ছবি আপলোড করুন",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed",
        )
        report_files = None
        prescription_file = None
    st.caption("ভালো আলোতে সোজা করে ছবি তুলুন। রোগীর ব্যক্তিগত তথ্য ঢেকে দিতে পারেন।")

with right:
    if is_medicine_mode:
        st.markdown('<div class="step">কী পাবেন</div><div class="section-title">ওষুধ নিয়ে চারটি সহায়তা</div>', unsafe_allow_html=True)
        st.markdown(
            """
        <div class="safe-card">🔊 <strong>বাংলায় শুনুন</strong> — পড়তে না পারলেও সহজে বোঝা যাবে</div>
        <div class="safe-card">📋 <strong>সময়সূচি</strong> — সকাল, দুপুর ও রাতের ওষুধ গুছানো থাকবে</div>
        <div class="safe-card">🛡️ <strong>বিপদ-সংকেত</strong> — সম্ভাব্য ঝুঁকি আলাদা করে চোখে পড়বে</div>
        <div class="safe-card">🔎 <strong>সৎ বিশ্লেষণ</strong> — অস্পষ্ট লেখা নিয়ে AI অনুমান করবে না</div>
        """,
            unsafe_allow_html=True,
        )
    elif is_test_mode:
        st.markdown('<div class="step">কী পাবেন</div><div class="section-title">Test নিয়ে নিরাপদ সহায়তা</div>', unsafe_allow_html=True)
        st.markdown(
            """
        <div class="safe-card">🧪 <strong>Test-এর সহজ অর্থ</strong> — কোন test সাধারণত কেন করা হয়</div>
        <div class="safe-card">🥛 <strong>প্রস্তুতি</strong> — খালি পেট বা অন্য প্রস্তুতির তথ্য</div>
        <div class="safe-card">🔄 <strong>সম্ভাব্য মিল</strong> — কাছাকাছি test থাকলে ডাক্তারকে কী জিজ্ঞেস করবেন</div>
        <div class="safe-card">🛡️ <strong>নিরাপদ সিদ্ধান্ত</strong> — AI কখনো নিজে থেকে test বাদ দিতে বলবে না</div>
        """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="step">কী পাবেন</div><div class="section-title">Report ও ওষুধের সম্পর্ক</div>', unsafe_allow_html=True)
        st.markdown(
            """
        <div class="safe-card">✅ <strong>কারণ বোঝা যাচ্ছে</strong> — report-এর সাথে সম্ভাব্য সম্পর্ক দেখাবে</div>
        <div class="safe-card">❓ <strong>কারণ পরিষ্কার নয়</strong> — ডাক্তারকে সঠিক প্রশ্ন করতে সাহায্য করবে</div>
        <div class="safe-card">⚠️ <strong>দ্রুত যাচাই প্রয়োজন</strong> — সম্ভাব্য interaction বা চিন্তার বিষয় দেখাবে</div>
        <div class="safe-card">🛡️ <strong>নিরাপদ সহায়তা</strong> — নিজে থেকে কোনো ওষুধ বন্ধ করতে বলবে না</div>
        """,
            unsafe_allow_html=True,
        )

if is_review_mode and report_files and prescription_file is not None:
    if len(report_files) > 20:
        st.error("একবারে সর্বোচ্চ ২০টি test report ছবি দিন।")
        st.stop()

    combined_bytes = b"".join(report.getvalue() for report in report_files) + prescription_file.getvalue()
    review_id = f"{mode}:{hashlib.sha256(combined_bytes).hexdigest()}"
    if review_id != st.session_state.image_id:
        st.session_state.image_id = review_id
        st.session_state.analysis = None
        st.session_state.voice_audio = None
        st.session_state.simple_answer = None
        st.session_state.follow_up_answer = None
    try:
        report_images = []
        for report_file in report_files:
            report_image = Image.open(io.BytesIO(report_file.getvalue()))
            report_image.load()
            if report_image.mode != "RGB":
                report_image = report_image.convert("RGB")
            report_images.append(report_image)
        prescription_image = Image.open(io.BytesIO(prescription_file.getvalue()))
        prescription_image.load()
        if prescription_image.mode != "RGB":
            prescription_image = prescription_image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        st.error("একটি বা দুটি ছবি পড়া যাচ্ছে না। পরিষ্কার JPG, PNG বা WEBP ছবি দিন।")
        st.stop()

    st.success(f"{len(report_images)}টি test report পৃষ্ঠা এবং ১টি prescription প্রস্তুত আছে।")
    with st.expander("আপলোড করা ছবিগুলো দেখুন"):
        st.markdown("#### Test report")
        st.image(
            report_images,
            caption=[f"Report পৃষ্ঠা {index}" for index in range(1, len(report_images) + 1)],
            width=220,
        )
        st.markdown("#### Doctor prescription")
        st.image(prescription_image, use_container_width=True)

    if st.button("Report ও prescription যাচাই করুন", type="primary", use_container_width=True):
        if not api_key:
            st.error("অ্যাপটি চালু করতে API Key প্রয়োজন।")
            st.stop()
        try:
            with st.spinner("Report ও prescription মিলিয়ে দেখা হচ্ছে..."):
                st.session_state.analysis = analyze_review(api_key, report_images, prescription_image)
                st.session_state.voice_audio = None
                st.session_state.simple_answer = None
                st.session_state.follow_up_answer = None
        except Exception as error:
            st.error("যাচাই করা যায়নি। ছবি, ইন্টারনেট অথবা API ব্যবহারের সীমা পরীক্ষা করুন।")
            with st.expander("কারিগরি তথ্য"):
                st.code(str(error), language="text")

elif uploaded_file is not None:
    current_image_id = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
    image_state_id = f"{mode}:{current_image_id}"
    if image_state_id != st.session_state.image_id:
        st.session_state.image_id = image_state_id
        st.session_state.analysis = None
        st.session_state.voice_audio = None
        st.session_state.simple_answer = None
        st.session_state.follow_up_answer = None

    try:
        image = Image.open(io.BytesIO(uploaded_file.getvalue()))
        image.load()
        if image.mode != "RGB":
            image = image.convert("RGB")
    except (UnidentifiedImageError, OSError):
        st.error("ছবিটি পড়া যাচ্ছে না। অন্য একটি পরিষ্কার JPG, PNG বা WEBP ছবি দিন।")
        st.stop()

    with st.expander("আপলোড করা ছবি দেখুন"):
        st.image(image, use_container_width=True)

    button_label = "ওষুধের প্রেসক্রিপশন বিশ্লেষণ করুন" if is_medicine_mode else "Test list বিশ্লেষণ করুন"
    if st.button(button_label, type="primary", use_container_width=True):
        if not api_key:
            st.error("অ্যাপটি চালু করতে API Key প্রয়োজন।")
            st.stop()
        try:
            with st.spinner("প্রেসক্রিপশন মনোযোগ দিয়ে পড়া হচ্ছে..."):
                st.session_state.analysis = analyze_image(api_key, image, mode)
                st.session_state.voice_audio = None
                st.session_state.simple_answer = None
                st.session_state.follow_up_answer = None
        except Exception as error:
            st.error("বিশ্লেষণ করা যায়নি। ছবি, ইন্টারনেট অথবা API ব্যবহারের সীমা পরীক্ষা করুন।")
            with st.expander("কারিগরি তথ্য"):
                st.code(str(error), language="text")

analysis = st.session_state.analysis
if analysis:
    st.divider()
    if analysis.get("image_quality") == "unclear" or analysis.get("image_message"):
        st.warning(f"ছবি সম্পর্কে: {analysis.get('image_message') or 'কিছু লেখা স্পষ্ট নয়। আরও পরিষ্কার ছবি দিন।'}")

    st.markdown('<div class="step">ধাপ ২</div><div class="section-title">সহজ বাংলা ব্যাখ্যা</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="safe-card">{esc(analysis.get("summary"))}</div>', unsafe_allow_html=True)

    action_one, action_two = st.columns(2)
    with action_one:
        if st.button("🔊 বাংলায় শুনুন", use_container_width=True):
            try:
                with st.spinner("বাংলা কণ্ঠ তৈরি হচ্ছে..."):
                    st.session_state.voice_audio = make_voice(
                        analysis.get("voice_text") or analysis.get("summary") or ""
                    )
            except Exception as error:
                st.error(f"এখন কণ্ঠ তৈরি করা যায়নি: {error}")
    with action_two:
        if st.button("সহজ করে বলো", use_container_width=True):
            try:
                with st.spinner("আরও সহজ করে বলা হচ্ছে..."):
                    st.session_state.simple_answer = simplify_answer(api_key, analysis, mode)
            except Exception:
                st.error("এখন সহজ ব্যাখ্যা তৈরি করা যায়নি।")

    if st.session_state.voice_audio:
        st.audio(st.session_state.voice_audio, format="audio/mp3")
    if st.session_state.simple_answer:
        st.info(st.session_state.simple_answer)

    if is_medicine_mode:
        medicines = analysis.get("medicines") or []
        if medicines:
            st.markdown('<div class="section-title">ওষুধের বিস্তারিত</div>', unsafe_allow_html=True)
            for medicine in medicines:
                medicine_card(medicine)

        st.markdown('<div class="step">ধাপ ৩</div><div class="section-title">খাওয়ার সময়সূচি</div>', unsafe_allow_html=True)
        schedule = analysis.get("schedule") or []
        if schedule:
            rows = [
                {
                    "সময়": item.get("time", "ছবিতে স্পষ্ট নয়"),
                    "ওষুধ": item.get("medicine", "ছবিতে স্পষ্ট নয়"),
                    "নির্দেশনা": item.get("instruction", "ছবিতে স্পষ্ট নয়"),
                }
                for item in schedule
            ]
            st.dataframe(rows, use_container_width=True, hide_index=True)
            st.caption("এই সময়সূচি শুধু ছবিতে স্পষ্টভাবে দেখা তথ্য দিয়ে তৈরি।")
        else:
            st.info("ছবিতে পরিষ্কার সময়সূচি পাওয়া যায়নি। অনুমান করে কোনো সময় যোগ করা হয়নি।")
    elif is_test_mode:
        counts = analysis.get("counts") or {}
        st.markdown('<div class="step">ধাপ ৩</div><div class="section-title">Test list-এর সারাংশ</div>', unsafe_allow_html=True)
        metric_cols = st.columns(5)
        metric_cols[0].metric("মোট Test", counts.get("total", 0))
        metric_cols[1].metric("সাধারণ", counts.get("routine", 0))
        metric_cols[2].metric("বিশেষ", counts.get("special", 0))
        metric_cols[3].metric("সম্ভাব্য মিল", counts.get("possible_overlap_groups", 0))
        metric_cols[4].metric("ডাক্তারকে প্রশ্ন", counts.get("questions_for_doctor", 0))

        tests = analysis.get("tests") or []
        if tests:
            st.markdown('<div class="section-title">প্রতিটি Test সহজভাবে বুঝুন</div>', unsafe_allow_html=True)
            for test in tests:
                test_card(test)

        overlaps = analysis.get("possible_overlaps") or []
        st.markdown('<div class="section-title">সম্ভাব্য কাছাকাছি Test</div>', unsafe_allow_html=True)
        if overlaps:
            for overlap in overlaps:
                st.markdown(
                    f"""
                    <div class="safe-card">
                      <strong>🔄 {esc(overlap.get("tests"))}</strong><br>
                      {esc(overlap.get("explanation"))}<br>
                      <strong>ডাক্তারকে জিজ্ঞেস করুন:</strong> {esc(overlap.get("ask_doctor"))}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.info("ছবির তথ্য থেকে কাছাকাছি ধরনের test চিহ্নিত হয়নি।")

        prep = analysis.get("preparation_checklist") or []
        questions = analysis.get("doctor_questions") or []
        prep_col, question_col = st.columns(2)
        with prep_col:
            st.markdown("#### Test-এর আগে প্রস্তুতি")
            for item in prep:
                st.markdown(f"- {item}")
        with question_col:
            st.markdown("#### ডাক্তারকে জিজ্ঞেস করুন")
            for item in questions:
                st.markdown(f"- {item}")
    else:
        st.markdown('<div class="step">ধাপ ৩</div><div class="section-title">Report-এর গুরুত্বপূর্ণ ফলাফল</div>', unsafe_allow_html=True)
        findings = analysis.get("report_findings") or []
        if findings:
            finding_rows = [
                {
                    "ফলাফল": item.get("finding", "ছবিতে স্পষ্ট নয়"),
                    "অবস্থা": item.get("status", "ছবিতে স্পষ্ট নয়"),
                    "সহজ অর্থ": item.get("meaning", "ছবিতে স্পষ্ট নয়"),
                    "করণীয় প্রশ্ন": item.get("action", "ডাক্তারকে জিজ্ঞেস করুন"),
                }
                for item in findings
            ]
            st.dataframe(finding_rows, use_container_width=True, hide_index=True)
        else:
            st.info("Report থেকে পরিষ্কার গুরুত্বপূর্ণ ফলাফল পাওয়া যায়নি।")

        st.markdown('<div class="section-title">প্রতিটি ওষুধ কেন দেওয়া হতে পারে</div>', unsafe_allow_html=True)
        reviews = analysis.get("medicine_reviews") or []
        if reviews:
            for item in reviews:
                review_card(item)
        else:
            st.info("Prescription থেকে ওষুধের তথ্য পরিষ্কারভাবে পাওয়া যায়নি।")

        st.markdown('<div class="section-title">সম্ভাব্য interaction যাচাই</div>', unsafe_allow_html=True)
        interactions = analysis.get("possible_interactions") or []
        if interactions:
            for item in interactions:
                st.markdown(
                    f"""
                    <div class="danger-card">
                      <strong>⚠️ {esc(item.get("items"))}</strong><br>
                      {esc(item.get("message"))}<br>
                      <strong>করণীয়:</strong> {esc(item.get("action"))}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="safe-card">দেওয়া ছবিগুলো থেকে আলাদা কোনো সম্ভাব্য interaction চিহ্নিত হয়নি। তবুও ডাক্তার বা ফার্মাসিস্টকে সব ওষুধের তালিকা দেখান।</div>',
                unsafe_allow_html=True,
            )

        doctor_questions = analysis.get("doctor_questions") or []
        if doctor_questions:
            st.markdown("#### ডাক্তারকে অগ্রাধিকার দিয়ে জিজ্ঞেস করুন")
            for item in doctor_questions:
                st.markdown(f"- {item}")

    st.markdown('<div class="step">ধাপ ৪</div><div class="section-title">বিপদ-সংকেত ও সতর্কতা</div>', unsafe_allow_html=True)
    danger_signals = analysis.get("danger_signals") or []
    if danger_signals:
        for signal in danger_signals:
            st.markdown(
                f"""
                <div class="danger-card">
                  <strong>⚠️ {esc(signal.get("title"))}</strong><br>
                  {esc(signal.get("message"))}<br>
                  <strong>করণীয়:</strong> {esc(signal.get("action"))}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="safe-card">ছবির তথ্য থেকে আলাদা কোনো বিপদ-সংকেত পাওয়া যায়নি। তবুও ওষুধ শুরুর আগে চিকিৎসকের পরামর্শ নিন।</div>',
            unsafe_allow_html=True,
        )

    if is_medicine_mode:
        question_title = "এই প্রেসক্রিপশন নিয়ে প্রশ্ন করুন"
        question_placeholder = "যেমন: কোন ওষুধটি খাবারের পরে লেখা আছে?"
    elif is_test_mode:
        question_title = "এই Test list নিয়ে প্রশ্ন করুন"
        question_placeholder = "যেমন: কোন test-এর আগে খালি পেটে থাকতে হবে?"
    else:
        question_title = "Report ও ওষুধ নিয়ে প্রশ্ন করুন"
        question_placeholder = "যেমন: এই ওষুধটি কোন report ফলাফলের জন্য দেওয়া হতে পারে?"
    st.markdown(f'<div class="section-title">{question_title}</div>', unsafe_allow_html=True)
    with st.form("follow_up_form"):
        question = st.text_input(
            "আপনার প্রশ্ন",
            placeholder=question_placeholder,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("প্রশ্ন করুন", use_container_width=True)
    if submitted and question.strip():
        try:
            with st.spinner("উত্তর তৈরি হচ্ছে..."):
                st.session_state.follow_up_answer = ask_follow_up(api_key, analysis, question.strip(), mode)
        except Exception:
            st.error("এই মুহূর্তে প্রশ্নের উত্তর দেওয়া যায়নি।")
    if st.session_state.follow_up_answer:
        st.info(st.session_state.follow_up_answer)

    if is_medicine_mode:
        trust_message = "কোনো ওষুধ শুরু, বন্ধ বা ডোজ পরিবর্তনের আগে রেজিস্টার্ড ডাক্তার বা ফার্মাসিস্টের সাথে কথা বলুন।"
    elif is_test_mode:
        trust_message = "কোনো test বাদ দেওয়া, পরিবর্তন করা বা দেরি করার আগে অবশ্যই চিকিৎসকের সাথে কথা বলুন।"
    else:
        trust_message = "কোনো ওষুধ শুরু, বন্ধ বা dose পরিবর্তনের আগে অবশ্যই ডাক্তার বা ফার্মাসিস্টের সাথে কথা বলুন।"
    st.markdown(
        f"""
        <div class="trust-note">
          <strong>গুরুত্বপূর্ণ:</strong> এই অ্যাপ সহায়ক তথ্য দেয়, চিকিৎসকের বিকল্প নয়।
          {trust_message}
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="trust-note">
          Stratifyxglobal কোনো অস্পষ্ট লেখা অনুমান করে না। পরিষ্কার তথ্য না পেলে আপনাকে আবার ছবি তুলতে বলবে।
        </div>
        """,
        unsafe_allow_html=True,
    )
