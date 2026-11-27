
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import os
import io
import json
import base64
import urllib.parse
import requests
import PyPDF2
from datetime import datetime

# =====================================================
# 1. PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Vardast | ور دست",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

PERSIPOLIS_IMAGE = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/"
    "6/6f/Persepolis_24.jpg/1200px-Persepolis_24.jpg"
)

# =====================================================
# 2. PWA
# =====================================================

pwa_html = """
<link rel="manifest" href="data:application/manifest+json,
%7B%22name%22%3A%22Vardast%22%2C%22short_name%22%3A%22Vardast%22%2C
%22start_url%22%3A%22.%22%2C%22display%22%3A%22standalone%22%2C
%22background_color%22%3A%22%230e1117%22%2C
%22theme_color%22%3A%22%230e1117%22%7D">
"""
components.html(pwa_html, height=0)

# =====================================================
# 3. SESSION STATE
# =====================================================

defaults = {
    "chats": {"Chat 1": []},
    "current_chat": "Chat 1",
    "chat_counter": 1,
    "pending_text": None,
    "pending_files": [],
    "regen_requested": False,
    "feedback": {},
    "input_counter": 0,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =====================================================
# 4. LANGUAGE
# =====================================================

LANGUAGES = {
    "فارسی": {
        "title": "ور دست ⚡",
        "caption": "دستیار هوشمند، رایگان و در دسترس همه",
        "new": "چت جدید",
        "history": "تاریخچه گفتگوها",
        "clear": "پاک کردن گفتگو",
        "search": "جستجو در گفتگوها...",
        "language": "زبان",
        "theme": "پوسته",
        "tone": "لحن پاسخ",
        "placeholder": "پیام خود را بنویسید...",
        "send": "ارسال پیام",
        "upload": "پیوست فایل",
        "download": "دانلود گفتگو",
        "welcome": "سلام! من ور دست هستم. چطور می‌توانم کمکت کنم؟",
        "quick1": "ترجمه متن",
        "quick2": "آموزش برنامه‌نویسی",
        "quick3": "ایده‌پردازی خلاقانه",
        "creator": "ساخته شده توسط سید محمد پارسا حسینی",
        "rename": "تغییر نام گفتگو",
        "delete": "حذف گفتگو",
        "temperature": "میزان خلاقیت",
        "friendly": "دوستانه",
        "professional": "حرفه‌ای",
        "creative": "خلاقانه",
        "direct": "مستقیم"
    },
    "English": {
        "title": "Vardast ⚡",
        "caption": "Your smart assistant.",
        "new": "New Chat",
        "history": "Chat History",
        "clear": "Clear Chat",
        "search": "Search chats...",
        "language": "Language",
        "theme": "Theme",
        "tone": "Response Tone",
        "placeholder": "Type your message...",
        "send": "Send Message",
        "upload": "Attach Files",
        "download": "Download Chat",
        "welcome": "Hello! I am Vardast. How can I help you?",
        "quick1": "Translate text",
        "quick2": "Learn programming",
        "quick3": "Creative ideas",
        "creator": "Made by Seyed Mohammad Parsa Hosseini",
        "rename": "Rename Chat",
        "delete": "Delete Chat",
        "temperature": "Creativity",
        "friendly": "Friendly",
        "professional": "Professional",
        "creative": "Creative",
        "direct": "Direct"
    }
}

# =====================================================
# 5. API CONFIGURATION
# =====================================================

try:
    API_KEY = st.secrets.get("GROQ_API_KEY", "")
except Exception:
    API_KEY = os.environ.get("GROQ_API_KEY", "")

MODEL = os.environ.get(
    "GROQ_MODEL",
    "qwen/qwen3.8-27b"
)

client = None

if API_KEY:
    client = OpenAI(
        api_key=API_KEY,
        base_url="https://api.groq.com/openai/v1"
    )

# =====================================================
# 6. CUSTOM CSS
# =====================================================

st.markdown(f"""
<style>

@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Vazirmatn:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Poppins', 'Vazirmatn', sans-serif;
}}

.stApp {{
    background-image:
    linear-gradient(rgba(14,17,23,.86), rgba(14,17,23,.96)),
    url("{PERSIPOLIS_IMAGE}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

.header-style {{
    background: rgba(30,35,47,.72);
    backdrop-filter: blur(18px);
    padding: 25px;
    border-radius: 22px;
    margin-bottom: 25px;
    border: 1px solid rgba(255,255,255,.1);
    box-shadow: 0 8px 32px rgba(0,0,0,.3);
}}

[data-testid="stChatMessage"] {{
    background: rgba(30,35,47,.65) !important;
    backdrop-filter: blur(18px);
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 14px;
    border: 1px solid rgba(255,255,255,.08);
}}

[data-testid="stSidebar"] {{
    background: rgba(15,18,26,.96);
}}

[data-testid="stSidebar"] button {{
    border-radius: 12px !important;
}}

.stTextArea textarea {{
    border-radius: 16px !important;
    background: rgba(0,0,0,.35) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,.15) !important;
    font-size: 16px !important;
}}

div.stButton > button[kind="primary"] {{
    border-radius: 40px !important;
    background: linear-gradient(90deg,#4A90E2,#8E44AD) !important;
    color: white !important;
    border: none !important;
    font-weight: 600 !important;
    transition: .25s;
}}

div.stButton > button[kind="primary"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 5px 20px rgba(74,144,226,.4);
}}

/* Response toolbar */

[data-testid="stHorizontalBlock"] button {{
    transition: .2s ease;
}}

[data-testid="stHorizontalBlock"] button:hover {{
    color: #ffffff !important;
    transform: scale(1.06);
}}

.rtl {{
    direction: rtl;
    text-align: right;
    line-height: 2;
}}

.brand {{
    font-size: 13px;
    color: #888;
    text-align: center;
}}

</style>
""", unsafe_allow_html=True)

# =====================================================
# 7. HELPER FUNCTIONS
# =====================================================

def get_current_messages():
    return st.session_state.chats[
        st.session_state.current_chat
    ]


def new_chat():
    st.session_state.chat_counter += 1
    name = f"Chat {st.session_state.chat_counter}"

    st.session_state.chats[name] = []
    st.session_state.current_chat = name
    st.rerun()


def export_chat(messages):
    output = []

    for msg in messages:
        role = "شما" if msg["role"] == "user" else "ور دست"
        output.append(
            f"{role}:\n{msg['content']}\n"
        )

    return "\n--------------------\n".join(output)


def safe_copy(text):
    # Clipboard runs inside the browser.
    payload = json.dumps(text, ensure_ascii=False)

    html = f"""
    <script>
    const text = {payload};
    navigator.clipboard.writeText(text)
        .then(() => console.log("Copied"))
        .catch(() => console.log("Clipboard unavailable"));
    </script>
    """

    components.html(html, height=0)


def read_pdf(file):
    reader = PyPDF2.PdfReader(
        io.BytesIO(file.getvalue())
    )

    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages)


def speak_text(text, language):
    try:
        short_text = text[:200]
        lang = "fa" if language == "فارسی" else "en"

        url = (
            "https://translate.google.com/translate_tts?"
            f"ie=UTF-8&q={urllib.parse.quote(short_text)}"
            f"&tl={lang}&client=tw-ob"
        )

        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )

        response.raise_for_status()

        st.audio(
            io.BytesIO(response.content),
            format="audio/mp3",
            autoplay=True
        )

    except Exception:
        st.warning("سرویس صوتی در دسترس نیست.")


def generate_response(messages, tone, temperature, user_text, files):
    if not client:
        st.error("ابتدا GROQ_API_KEY را تنظیم کن.")
        return None

    system_prompt = f"""
تو ور دست هستی؛ یک دستیار هوش مصنوعی دقیق و کاربردی.

قوانین:
- پاسخ‌ها دقیق، مفید و قابل فهم باشند.
- از Markdown برای مرتب‌سازی پاسخ استفاده کن.
- اگر کاربر فارسی صحبت کرد، فارسی روان پاسخ بده.
- از توضیحات غیرضروری پرهیز کن.
- در صورت نیاز مثال و مراحل عملی ارائه بده.
- لحن پاسخ: {tone}
- اگر کاربر درخواست ساخت تصویر کرد، در یک خط جداگانه بنویس:
IMAGE_GEN: [English image prompt]
"""

    if not user_text.strip():
        user_text = "لطفاً فایل پیوست شده را بررسی کن."

    api_content = [
        {"type": "text", "text": user_text}
    ]

    for file in files:
        try:
            if file.type.startswith("image/"):
                encoded = base64.b64encode(
                    file.getvalue()
                ).decode("utf-8")

                api_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{file.type};base64,{encoded}"
                    }
                })

            elif file.type == "application/pdf":
                pdf_text = read_pdf(file)

                api_content.append({
                    "type": "text",
                    "text": (
                        "محتوای PDF:\n" +
                        pdf_text[:12000]
                    )
                })

        except Exception as error:
            st.warning(f"خطا در پردازش {file.name}: {error}")

    api_messages = [
        {"role": "system", "content": system_prompt}
    ]

    for msg in messages[:-1]:
        api_messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })

    api_messages.append({
        "role": "user",
        "content": api_content
    })

    try:
        stream = client.chat.completions.create(
            model=MODEL,
            messages=api_messages,
            temperature=temperature,
            max_tokens=2000,
            stream=True
        )

        return st.write_stream(stream)

    except Exception as error:
        st.error(f"خطا در ارتباط با هوش مصنوعی: {error}")
        return None


# =====================================================
# 8. SIDEBAR
# =====================================================

with st.sidebar:

    selected_lang = st.selectbox(
        "Language / زبان",
        ["فارسی", "English"]
    )

    t = LANGUAGES[selected_lang]

    st.divider()

    if st.button(
        t["new"],
        icon=":material/add_circle:",
        width="stretch"
    ):
        new_chat()

    st.subheader(t["history"])

    search_query = st.text_input(
        "Search",
        placeholder=t["search"],
        label_visibility="collapsed"
    )

    # Chat search

    for chat_name, chat_messages in list(
        st.session_state.chats.items()
    ):

        searchable = chat_name + " " + " ".join(
            m["content"] for m in chat_messages
        )

        if search_query.lower() in searchable.lower():

            if st.button(
                chat_name,
                key=f"chat_{chat_name}",
                width="stretch",
                type=(
                    "primary"
                    if chat_name == st.session_state.current_chat
                    else "secondary"
                )
            ):
                st.session_state.current_chat = chat_name
                st.rerun()

    st.divider()

    st.subheader("تنظیمات")

    theme = st.radio(
        t["theme"],
        ["Dark", "Light"],
        horizontal=True
    )

    tone_labels = [
        t["friendly"],
        t["professional"],
        t["creative"],
        t["direct"]
    ]

    tone = st.selectbox(
        t["tone"],
        tone_labels
    )

    temperature = st.slider(
        t["temperature"],
        min_value=0.0,
        max_value=1.5,
        value=0.7,
        step=0.1
    )

    # Chat management

    st.divider()

    st.subheader("مدیریت گفتگو")

    rename_value = st.text_input(
        t["rename"],
        placeholder="نام جدید..."
    )

    if st.button("ذخیره نام", icon=":material/edit:"):
        if rename_value.strip():
            old_name = st.session_state.current_chat
            new_name = rename_value.strip()

            if new_name not in st.session_state.chats:
                st.session_state.chats[new_name] = (
                    st.session_state.chats.pop(old_name)
                )
                st.session_state.current_chat = new_name
                st.rerun()
            else:
                st.warning("این نام قبلاً استفاده شده است.")

    if st.button(
        t["clear"],
        icon=":material/delete_sweep:",
        width="stretch"
    ):
        st.session_state.chats[
            st.session_state.current_chat
        ] = []
        st.rerun()

    if len(st.session_state.chats) > 1:
        if st.button(
            t["delete"],
            icon=":material/delete:",
            width="stretch"
        ):
            del st.session_state.chats[
                st.session_state.current_chat
            ]

            st.session_state.current_chat = next(
                iter(st.session_state.chats)
            )
            st.rerun()

    # Export

    messages = get_current_messages()

    if messages:
        st.download_button(
            t["download"],
            data=export_chat(messages),
            file_name="vardast_chat.txt",
            mime="text/plain",
            icon=":material/download:",
            width="stretch"
        )

        st.download_button(
            "دانلود Markdown",
            data=export_chat(messages),
            file_name="vardast_chat.md",
            mime="text/markdown",
            icon=":material/description:",
            width="stretch"
        )

    st.divider()

    st.markdown(
        f"<div class='brand'>{t['creator']}</div>",
        unsafe_allow_html=True
    )

# =====================================================
# 9. THEME
# =====================================================

if theme == "Light":
    st.markdown("""
    <style>
    .stApp {
        background-image:
        linear-gradient(
            rgba(248,249,250,.91),
            rgba(248,249,250,.97)
        ) !important;
        color: #222 !important;
    }

    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,.88) !important;
        color: #222 !important;
    }

    </style>
    """, unsafe_allow_html=True)

# =====================================================
# 10. HEADER
# =====================================================

st.markdown(
    '<div class="header-style">',
    unsafe_allow_html=True
)

st.title(t["title"])
st.caption(t["caption"])

st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# 11. QUICK PROMPTS
# =====================================================

messages = get_current_messages()

if not messages:

    with st.chat_message("assistant", avatar="⚡"):
        st.markdown(t["welcome"])

    q1, q2, q3 = st.columns(3)

    if q1.button(
        t["quick1"],
        icon=":material/translate:",
        width="stretch"
    ):
        st.session_state.quick_prompt = (
            "این متن را به انگلیسی ترجمه کن: "
        )
        st.rerun()

    if q2.button(
        t["quick2"],
        icon=":material/code:",
        width="stretch"
    ):
        st.session_state.quick_prompt = (
            "به من برنامه‌نویسی را آموزش بده."
        )
        st.rerun()

    if q3.button(
        t["quick3"],
        icon=":material/lightbulb:",
        width="stretch"
    ):
        st.session_state.quick_prompt = (
            "چند ایده خلاقانه و کاربردی پیشنهاد بده."
        )
        st.rerun()

# =====================================================
# 12. CHAT DISPLAY
# =====================================================

for i, message in enumerate(messages):

    avatar = (
        "👤" if message["role"] == "user"
        else "⚡"
    )

    with st.chat_message(
        message["role"],
        avatar=avatar
    ):

        content = message["content"]

        # Image generation

        if (
            message["role"] == "assistant"
            and "IMAGE_GEN:" in content
        ):

            parts = content.split("IMAGE_GEN:", 1)

            text_part = parts[0].strip()
            prompt = parts[1].strip()

            if text_part:
                st.markdown(text_part)

            image_url = (
                "https://image.pollinations.ai/prompt/"
                + urllib.parse.quote(prompt)
                + "?width=1024&height=1024&nologo=true"
            )

            try:
                st.image(
                    image_url,
                    caption="Vardast Image Generator"
                )
            except Exception:
                st.warning("تصویر در دسترس نیست.")

        else:

            st.markdown(content)

        # User feedback toolbar

        if message["role"] == "assistant":

            st.caption(" ")

            c1, c2, c3, c4, c5, c6 = st.columns(
                [1, 1, 1, 1, 1, 1]
            )

            with c1:
                if st.button(
                    "کپی",
                    icon=":material/content_copy:",
                    key=f"copy_{i}",
                    help="کپی پاسخ",
                    type="tertiary"
                ):
                    safe_copy(content)
                    st.toast("درخواست کپی ارسال شد.")

            with c2:
                if st.button(
                    "پسندیدم",
                    icon=":material/thumb_up:",
                    key=f"like_{i}",
                    help="پسندیدن پاسخ",
                    type="tertiary"
                ):
                    st.session_state.feedback[i] = "like"
                    st.toast("ممنون از بازخوردت!")

            with c3:
                if st.button(
                    "نپسندیدم",
                    icon=":material/thumb_down:",
                    key=f"dislike_{i}",
                    help="نپسندیدن پاسخ",
                    type="tertiary"
                ):
                    st.session_state.feedback[i] = "dislike"
                    st.toast("بازخورد ثبت شد.")

            with c4:
                if st.button(
                    "صوت",
                    icon=":material/volume_up:",
                    key=f"audio_{i}",
                    help="خواندن پاسخ",
                    type="tertiary"
                ):
                    speak_text(content, selected_lang)

            with c5:
                if st.button(
                    "اشتراک",
                    icon=":material/share:",
                    key=f"share_{i}",
                    help="کپی برای اشتراک‌گذاری",
                    type="tertiary"
                ):
                    safe_copy(content)
                    st.toast("متن برای اشتراک‌گذاری آماده شد.")

            with c6:
                with st.popover(
                    "بیشتر",
                    icon=":material/more_vert:"
                ):
                    st.download_button(
                        "دانلود این پاسخ",
                        data=content,
                        file_name=f"vardast_answer_{i}.txt",
                        mime="text/plain",
                        width="stretch"
                    )

                    if st.button(
                        "تولید مجدد پاسخ",
                        icon=":material/refresh:",
                        key=f"regen_{i}",
                        width="stretch"
                    ):
                        if i == len(messages) - 1:
                            last_user = next(
                                (
                                    m["content"]
                                    for m in reversed(messages[:i])
                                    if m["role"] == "user"
                                ),
                                None
                            )

                            if last_user:
                                st.session_state.chats[
                                    st.session_state.current_chat
                                ].pop()

                                st.session_state.pending_text = last_user
                                st.session_state.pending_files = []
                                st.rerun()
                        else:
                            st.warning(
                                "برای تولید مجدد، آخرین پاسخ را انتخاب کن."
                            )

            if i in st.session_state.feedback:
                st.caption(
                    "بازخورد شما ثبت شده است."
                )

# =====================================================
# 13. FILE UPLOAD
# =====================================================

st.divider()

with st.expander(
    t["upload"],
    icon=":material/attach_file:"
):

    uploaded_files = st.file_uploader(
        "انتخاب فایل",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.success(
            f"{len(uploaded_files)} فایل انتخاب شده است."
        )

        for file in uploaded_files:
            st.caption(
                f"{file.name} - {file.size / 1024:.1f} KB"
            )

# =====================================================
# 14. INPUT
# =====================================================

default_value = st.session_state.pop(
    "quick_prompt",
    ""
)

input_key = f"message_{st.session_state.input_counter}"

user_text = st.text_area(
    t["placeholder"],
    value=default_value,
    height=100,
    key=input_key,
    label_visibility="collapsed"
)

send_clicked = st.button(
    t["send"],
    type="primary",
    icon=":material/send:",
    width="stretch"
)

if send_clicked:

    if user_text.strip() or uploaded_files:

        st.session_state.pending_text = user_text
        st.session_state.pending_files = (
            uploaded_files if uploaded_files else []
        )

        st.session_state.input_counter += 1
        st.rerun()

# =====================================================
# 15. PROCESS MESSAGE
# =====================================================

if st.session_state.pending_text is not None:

    text_to_process = st.session_state.pending_text

    files_to_process = st.session_state.pending_files

    st.session_state.pending_text = None
    st.session_state.pending_files = []

    current_messages = get_current_messages()

    display_text = text_to_process

    if files_to_process:
        display_text += (
            f"\n\n[{len(files_to_process)} فایل پیوست شده]"
        )

    current_messages.append({
        "role": "user",
        "content": display_text
    })

    with st.chat_message("user", avatar="👤"):
        st.markdown(display_text)

    tone_map = {
        t["friendly"]: "دوستانه",
        t["professional"]: "حرفه‌ای",
        t["creative"]: "خلاقانه",
        t["direct"]: "مستقیم"
    }

    selected_tone = tone_map[tone]

    with st.chat_message("assistant", avatar="⚡"):

        with st.spinner("ور دست در حال فکر کردن است..."):

            answer = generate_response(
                current_messages,
                selected_tone,
                temperature,
                text_to_process,
                files_to_process
            )

        if answer:
            current_messages.append({
                "role": "assistant",
                "content": answer
            })

    st.rerun()

# =====================================================
# 16. FOOTER
# =====================================================

st.divider()

st.markdown(
    """
    <div class="brand">
    Vardast AI ⚡ | Your intelligent companion
    </div>
    """,
    unsafe_allow_html=True
)
