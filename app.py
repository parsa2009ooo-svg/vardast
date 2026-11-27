import os
import io
import base64
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
from openai import OpenAI
from supabase import create_client, Client
from gtts import gTTS
from PyPDF2 import PdfReader
import requests

# ------------------------------------------------------------
# Vardast v2 - Streamlit + Groq + Supabase + Pollinations
# Secrets are read from environment variables (Render).
# ------------------------------------------------------------

st.set_page_config(
    page_title="Vardast | ور دست",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "ور دست"
CREATOR = "سید محمد پارسا حسینی"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "").strip()
IMAGE_MODEL = os.getenv("POLLINATIONS_IMAGE_MODEL", "black-forest-labs/flux.1-schnell").strip()

SYSTEM_PROMPT = """
تو «ور دست» هستی؛ یک دستیار هوشمند دقیق، خوش‌برخورد و کاربردی.
به زبان کاربر پاسخ بده. اگر کاربر فارسی نوشت، فارسی روان و قابل فهم بنویس.
اگر پاسخ را نمی‌دانی، صادقانه بگو و اطلاعات ساختگی نساز.
برای آموزش برنامه‌نویسی، مرحله‌به‌مرحله و با مثال توضیح بده.
"""

# ---- Styling ----
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Vazirmatn', sans-serif; }
.block-container { padding-top: 1.4rem; max-width: 1200px; }
.hero {
  padding: 1.25rem 1.4rem; border-radius: 20px;
  background: linear-gradient(125deg, #171b3b, #263d73 60%, #345c91);
  color: white; margin-bottom: 1rem;
}
.hero h1 { margin: 0; font-size: 2rem; }
.hero p { margin: .45rem 0 0 0; opacity: .9; }
.small-muted { color: #8a8f9c; font-size: .85rem; }
.stButton>button { border-radius: 12px; min-height: 2.6rem; }
[data-testid="stChatMessage"] { border-radius: 15px; }
</style>
""", unsafe_allow_html=True)

# ---- Clients ----
@st.cache_resource
def get_groq_client():
    if not GROQ_API_KEY:
        return None
    return OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

@st.cache_resource
def get_supabase_client():
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

groq = get_groq_client()
supabase = get_supabase_client()

# ---- Session state ----
defaults = {
    "user": None,
    "access_token": None,
    "active_chat": None,
    "messages": [],
    "chats": [],
    "tone": "دوستانه و روشن",
    "language": "خودکار",
    "pending_prompt": "",
    "last_image": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

def user_id():
    u = st.session_state.user
    if not u:
        return None
    return getattr(u, "id", None) or (u.get("id") if isinstance(u, dict) else None)

def db_ready():
    return supabase is not None and st.session_state.user is not None

def show_error(title, err):
    st.error(f"{title}: {str(err)[:500]}")

# ---- Auth ----
def auth_screen():
    st.markdown(f"""
    <div class="hero">
      <h1>✨ ور دست</h1>
      <p>دستیار هوشمند تو برای یادگیری، ایده‌پردازی و ساختن</p>
    </div>
    """, unsafe_allow_html=True)

    if supabase is None:
        st.warning("اتصال Supabase هنوز تنظیم نشده است. ابتدا SUPABASE_URL و SUPABASE_ANON_KEY را در Render اضافه کن.")
        st.code("SUPABASE_URL\nSUPABASE_ANON_KEY")
        st.info("برای امنیت، کلیدها را در Render وارد کن؛ آن‌ها را در کد یا چت عمومی قرار نده.")
        return

    tab_login, tab_signup = st.tabs(["ورود", "ساخت حساب"])
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("ایمیل", key="login_email")
            password = st.text_input("رمز عبور", type="password", key="login_password")
            submit = st.form_submit_button("ورود", use_container_width=True)
        if submit:
            try:
                result = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
                st.session_state.user = result.user
                st.session_state.access_token = result.session.access_token if result.session else None
                st.session_state.active_chat = None
                st.session_state.messages = []
                st.rerun()
            except Exception as e:
                show_error("ورود انجام نشد. ایمیل و رمز را بررسی کن", e)

    with tab_signup:
        with st.form("signup_form"):
            email2 = st.text_input("ایمیل", key="signup_email")
            password2 = st.text_input("رمز عبور (حداقل ۸ کاراکتر)", type="password", key="signup_password")
            password3 = st.text_input("تکرار رمز عبور", type="password")
            submit2 = st.form_submit_button("ساخت حساب", use_container_width=True)
        if submit2:
            if password2 != password3:
                st.error("رمزها یکسان نیستند.")
            elif len(password2) < 8:
                st.error("رمز عبور باید حداقل ۸ کاراکتر باشد.")
            else:
                try:
                    result = supabase.auth.sign_up({"email": email2.strip(), "password": password2})
                    if result.session:
                        st.session_state.user = result.user
                        st.session_state.access_token = result.session.access_token
                        st.rerun()
                    else:
                        st.success("حساب ساخته شد. اگر تأیید ایمیل فعال است، ایمیلت را تأیید کن و سپس وارد شو.")
                except Exception as e:
                    show_error("ساخت حساب انجام نشد", e)

def load_chats():
    try:
        res = (supabase.table("conversations")
               .select("id,title,created_at,updated_at")
               .eq("user_id", user_id())
               .order("updated_at", desc=True)
               .execute())
        st.session_state.chats = res.data or []
    except Exception as e:
        show_error("خواندن فهرست گفتگوها ناموفق بود", e)
        st.session_state.chats = []

def load_messages(chat_id):
    try:
        res = (supabase.table("messages")
               .select("id,role,content,created_at")
               .eq("conversation_id", chat_id)
               .order("created_at")
               .execute())
        st.session_state.messages = [
            {"role": r["role"], "content": r["content"]}
            for r in (res.data or [])
        ]
    except Exception as e:
        show_error("خواندن پیام‌ها ناموفق بود", e)
        st.session_state.messages = []

def new_chat():
    title = "گفتگوی تازه"
    try:
        res = supabase.table("conversations").insert({
            "user_id": user_id(), "title": title
        }).execute()
        row = res.data[0]
        st.session_state.active_chat = row["id"]
        st.session_state.messages = []
        load_chats()
    except Exception as e:
        show_error("ساخت گفتگوی تازه ناموفق بود", e)

def save_message(role, content):
    if not db_ready() or not st.session_state.active_chat:
        return
    try:
        supabase.table("messages").insert({
            "conversation_id": st.session_state.active_chat,
            "user_id": user_id(),
            "role": role,
            "content": content,
        }).execute()
        supabase.table("conversations").update({
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", st.session_state.active_chat).eq("user_id", user_id()).execute()
    except Exception as e:
        show_error("ذخیره پیام ناموفق بود", e)

def delete_chat(chat_id):
    try:
        supabase.table("messages").delete().eq("conversation_id", chat_id).eq("user_id", user_id()).execute()
        supabase.table("conversations").delete().eq("id", chat_id).eq("user_id", user_id()).execute()
        if st.session_state.active_chat == chat_id:
            st.session_state.active_chat = None
            st.session_state.messages = []
        load_chats()
        st.rerun()
    except Exception as e:
        show_error("حذف گفتگو ناموفق بود", e)

def rename_chat(chat_id, title):
    try:
        supabase.table("conversations").update({"title": title}).eq("id", chat_id).eq("user_id", user_id()).execute()
        load_chats()
    except Exception as e:
        show_error("تغییر نام گفتگو ناموفق بود", e)

# ---- AI helpers ----
def build_context(extra_text=""):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT + f" لحن پاسخ: {st.session_state.tone}. زبان: {st.session_state.language}."}]
    for m in st.session_state.messages[-18:]:
        msgs.append({"role": m["role"], "content": m["content"]})
    if extra_text:
        msgs.append({"role": "system", "content": "محتوای فایل کاربر برای استفاده در پاسخ:\n" + extra_text[:18000]})
    return msgs

def ask_ai(prompt, uploaded_image=None, extra_text=""):
    if groq is None:
        raise RuntimeError("کلید GROQ_API_KEY در Render تنظیم نشده است.")
    model = GROQ_VISION_MODEL if uploaded_image else GROQ_MODEL
    messages = build_context(extra_text)
    if uploaded_image:
        b64 = base64.b64encode(uploaded_image.getvalue()).decode("utf-8")
        mime = uploaded_image.type or "image/png"
        user_content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
        ]
        messages.append({"role": "user", "content": user_content})
    else:
        messages.append({"role": "user", "content": prompt})

    response = groq.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
        max_tokens=1800,
    )
    return response.choices[0].message.content or "پاسخی دریافت نشد."

def generate_image(prompt):
    if not POLLINATIONS_API_KEY:
        raise RuntimeError("برای ساخت تصویر، متغیر POLLINATIONS_API_KEY هنوز در Render تنظیم نشده است.")
    # OpenAI-compatible image generation endpoint
    client = OpenAI(
        api_key=POLLINATIONS_API_KEY,
        base_url="https://gen.pollinations.ai/v1"
    )
    result = client.images.generate(
        model=IMAGE_MODEL,
        prompt=prompt,
        size="1024x1024",
        response_format="b64_json",
    )
    b64 = result.data[0].b64_json
    if not b64:
        raise RuntimeError("سرویس تصویر، فایل تصویری برنگرداند.")
    return base64.b64decode(b64)

def transcribe_audio(audio_file):
    if groq is None:
        raise RuntimeError("کلید GROQ_API_KEY تنظیم نشده است.")
    raw = audio_file.getvalue()
    file_tuple = (audio_file.name or "voice.wav", raw)
    result = groq.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=file_tuple,
        response_format="text",
    )
    return str(result).strip()

def make_tts(text, lang):
    language = "fa" if lang == "فارسی" else "en"
    audio = io.BytesIO()
    gTTS(text=text[:3500], lang=language).write_to_fp(audio)
    audio.seek(0)
    return audio

# ---- Main layout ----
if not st.session_state.user:
    auth_screen()
    st.stop()

st.markdown(f"""
<div class="hero">
  <h1>✨ ور دست</h1>
  <p>همراه هوشمند تو؛ از پرسش و یادگیری تا ایده‌پردازی و تصویرسازی</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 🧭 منوی ور دست")
    st.caption(f"حساب: {getattr(st.session_state.user, 'email', 'کاربر')}")
    if st.button("＋ گفتگوی جدید", use_container_width=True):
        new_chat()
        st.rerun()

    st.markdown("### گفتگوهای قبلی")
    if not st.session_state.chats:
        load_chats()
    for chat in st.session_state.chats:
        c1, c2 = st.columns([5, 1])
        with c1:
            label = (chat.get("title") or "گفتگو")[:26]
            if st.button(label, key=f"open_{chat['id']}", use_container_width=True):
                st.session_state.active_chat = chat["id"]
                load_messages(chat["id"])
                st.rerun()
        with c2:
            if st.button("🗑", key=f"del_{chat['id']}"):
                st.session_state.confirm_delete = chat["id"]
    if st.session_state.get("confirm_delete"):
        st.warning("این گفتگو حذف شود؟")
        yes, no = st.columns(2)
        with yes:
            if st.button("بله، حذف", key="yes_delete"):
                delete_chat(st.session_state.confirm_delete)
                st.session_state.confirm_delete = None
        with no:
            if st.button("لغو", key="no_delete"):
                st.session_state.confirm_delete = None
                st.rerun()

    st.divider()
    st.markdown("### تنظیمات پاسخ")
    st.session_state.tone = st.selectbox(
        "لحن پاسخ", ["دوستانه و روشن", "رسمی", "آموزشی و مرحله‌به‌مرحله", "خلاصه و مستقیم"],
        index=["دوستانه و روشن", "رسمی", "آموزشی و مرحله‌به‌مرحله", "خلاصه و مستقیم"].index(st.session_state.tone)
    )
    st.session_state.language = st.selectbox("زبان", ["خودکار", "فارسی", "English"])
    st.divider()
    if st.button("خروج از حساب", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        for k in ["user", "access_token", "active_chat", "messages", "chats"]:
            st.session_state[k] = None if k in ["user", "access_token", "active_chat"] else []
        st.rerun()
    st.caption(f"سازنده: {CREATOR}")

if not st.session_state.active_chat:
    if st.session_state.chats:
        st.info("از ستون کناری یک گفتگو را انتخاب کن یا گفتگوی تازه بساز.")
    else:
        st.info("برای شروع، روی «گفتگوی جدید» در ستون کناری بزن.")
    st.stop()

# Load conversation on first entry if needed
if st.session_state.active_chat and not st.session_state.messages:
    load_messages(st.session_state.active_chat)

# Header tools
left, right = st.columns([3, 1])
with left:
    st.subheader("گفتگو با ور دست")
with right:
    if st.button("⬇️ دانلود گفتگو", use_container_width=True):
        transcript = "\n\n".join(
            [("شما: " if m["role"] == "user" else "ور دست: ") + m["content"] for m in st.session_state.messages]
        )
        st.download_button("دریافت فایل متنی", transcript, file_name="vardast_chat.txt", mime="text/plain")

# Display chat
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            with st.expander("🔊 شنیدن پاسخ"):
                tts_lang = st.selectbox("زبان صدا", ["فارسی", "English"], key=f"tts_lang_{i}")
                if st.button("ساخت صدا", key=f"tts_{i}"):
                    try:
                        audio = make_tts(msg["content"], tts_lang)
                        st.audio(audio, format="audio/mp3")
                    except Exception as e:
                        show_error("تبدیل متن به صدا انجام نشد", e)

# File input and voice
with st.expander("📎 افزودن فایل یا تصویر"):
    uploaded = st.file_uploader("تصویر یا PDF انتخاب کن", type=["png", "jpg", "jpeg", "webp", "pdf"])
    if uploaded:
        st.caption(f"فایل انتخاب‌شده: {uploaded.name}")
        if uploaded.type.startswith("image/"):
            st.image(uploaded, caption="تصویر ارسالی", use_container_width=True)
    audio_input = st.audio_input("🎙️ پیام صوتی ضبط کن")

if audio_input:
    if st.button("تبدیل صدا به متن"):
        try:
            text_result = transcribe_audio(audio_input)
            st.session_state.pending_prompt = text_result
            st.success("متن صدا آماده شد؛ می‌توانی آن را ویرایش کنی و بفرستی.")
            st.text_area("متن تشخیص‌داده‌شده", key="recognized_text", value=text_result)
        except Exception as e:
            show_error("تبدیل صدا ناموفق بود", e)

# Image creation panel
with st.expander("🎨 ساخت تصویر با هوش مصنوعی"):
    image_prompt = st.text_area("چه تصویری بسازم؟", placeholder="مثلاً: یک شهر آینده‌نگر در غروب، سبک سینمایی...")
    if st.button("ساخت تصویر", use_container_width=True):
        if not image_prompt.strip():
            st.warning("ابتدا توضیح تصویر را بنویس.")
        else:
            with st.spinner("در حال ساخت تصویر..."):
                try:
                    image_bytes = generate_image(image_prompt.strip())
                    st.session_state.last_image = image_bytes
                    st.image(image_bytes, caption="تصویر ساخته‌شده", use_container_width=True)
                    st.download_button("دانلود تصویر", image_bytes, file_name="vardast_image.png", mime="image/png")
                except Exception as e:
                    show_error("ساخت تصویر انجام نشد", e)

if st.session_state.last_image:
    st.image(st.session_state.last_image, caption="آخرین تصویر ساخته‌شده", use_container_width=True)

# Chat input
prompt = st.chat_input("پیامت را برای ور دست بنویس...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    save_message("user", prompt)
    with st.chat_message("user"):
        st.markdown(prompt)

    image_for_ai = uploaded if uploaded and uploaded.type.startswith("image/") else None
    extra_text = ""
    if uploaded and uploaded.type == "application/pdf":
        try:
            reader = PdfReader(uploaded)
            extra_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:
            st.warning(f"خواندن PDF ناموفق بود: {e}")

    with st.chat_message("assistant"):
        with st.spinner("ور دست در حال فکر کردن است..."):
            try:
                answer = ask_ai(prompt, uploaded_image=image_for_ai, extra_text=extra_text)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_message("assistant", answer)
            except Exception as e:
                err = str(e)
                if "model" in err.lower() and ("not found" in err.lower() or "does not exist" in err.lower()):
                    st.error("مدل انتخاب‌شده در Groq در دسترس نیست. مقدار GROQ_MODEL و GROQ_VISION_MODEL را در Render بررسی کن.")
                else:
                    show_error("پاسخ‌گویی هوش مصنوعی ناموفق بود", e)
    st.rerun()

st.markdown("---")
st.markdown(
    f"<div class='small-muted' style='text-align:center'>ور دست · ساخته‌شده توسط {CREATOR}</div>",
    unsafe_allow_html=True
)
