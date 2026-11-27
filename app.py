
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import sqlite3
import hashlib
import secrets
import json
import os
import io
import base64
import urllib.parse
import requests
import PyPDF2
from datetime import datetime

# ==================================================
# 1. PAGE CONFIG
# ==================================================

st.set_page_config(
    page_title="Vardast | ور دست",
    page_icon="⚡",
    layout="wide"
)

DB_PATH = "vardast.db"

PERSIPOLIS_IMAGE = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/"
    "6/6f/Persepolis_24.jpg/1200px-Persepolis_24.jpg"
)

# ==================================================
# 2. DATABASE
# ==================================================

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                chats_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
        """)

def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        310000
    ).hex()

def register_user(username, display_name, password):
    username = username.strip().lower()
    display_name = display_name.strip()

    if len(username) < 3:
        return False, "نام کاربری باید حداقل ۳ حرف باشد."

    if not username.replace("_", "").isalnum():
        return False, "نام کاربری فقط می‌تواند شامل حروف، عدد و _ باشد."

    if not display_name:
        return False, "نام نمایشی را وارد کنید."

    if len(password) < 8:
        return False, "رمز عبور باید حداقل ۸ کاراکتر باشد."

    salt = secrets.token_hex(16)
    password_hash = hash_password(password, salt)

    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO users (
                    username,
                    display_name,
                    salt,
                    password_hash,
                    chats_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                username,
                display_name,
                salt,
                password_hash,
                json.dumps({
                    "chats": {"Chat 1": []},
                    "current_chat": "Chat 1",
                    "chat_counter": 1
                }),
                datetime.now().isoformat()
            ))

        return True, "حساب شما با موفقیت ساخته شد."

    except sqlite3.IntegrityError:
        return False, "این نام کاربری قبلاً ثبت شده است."

def authenticate_user(username, password):
    with get_db() as conn:
        user = conn.execute("""
            SELECT id, username, display_name,
                   salt, password_hash, chats_json
            FROM users
            WHERE username = ?
        """, (username.strip().lower(),)).fetchone()

    if not user:
        return None

    calculated = hash_password(password, user[3])

    if not secrets.compare_digest(calculated, user[4]):
        return None

    try:
        chat_data = json.loads(user[5])
    except (ValueError, TypeError):
        chat_data = {}

    return {
        "id": user[0],
        "username": user[1],
        "display_name": user[2],
        "chat_data": chat_data
    }

def save_user_data():
    if not st.session_state.get("authenticated"):
        return

    data = {
        "chats": st.session_state.chats,
        "current_chat": st.session_state.current_chat,
        "chat_counter": st.session_state.chat_counter
    }

    with get_db() as conn:
        conn.execute("""
            UPDATE users
            SET chats_json = ?
            WHERE id = ?
        """, (
            json.dumps(data, ensure_ascii=False),
            st.session_state.user_id
        ))

def restore_user_data(user):
    data = user["chat_data"]

    chats = data.get("chats", {"Chat 1": []})

    if not isinstance(chats, dict) or not chats:
        chats = {"Chat 1": []}

    st.session_state.chats = chats

    current = data.get("current_chat", next(iter(chats)))

    if current not in chats:
        current = next(iter(chats))

    st.session_state.current_chat = current
    st.session_state.chat_counter = data.get("chat_counter", 1)

init_db()

# ==================================================
# 3. SESSION STATE
# ==================================================

defaults = {
    "authenticated": False,
    "chats": {"Chat 1": []},
    "current_chat": "Chat 1",
    "chat_counter": 1,
    "feedback": {},
    "input_counter": 0
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==================================================
# 4. API CONFIG
# ==================================================

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

# ==================================================
# 5. DESIGN
# ==================================================

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
}}

.rtl {{
    direction: rtl;
    text-align: right;
    line-height: 2;
}}

.brand {{
    text-align: center;
    color: #888;
    font-size: 13px;
}}

</style>
""", unsafe_allow_html=True)

# ==================================================
# 6. AUTHENTICATION PAGE
# ==================================================

if not st.session_state.authenticated:

    st.markdown(
        "<h1 style='text-align:center'>ور دست ⚡</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center'>"
        "دستیار هوشمند شما"
        "</p>",
        unsafe_allow_html=True
    )

    tab1, tab2 = st.tabs(["ورود به حساب", "ثبت نام"])

    with tab1:

        with st.form("login_form"):

            username = st.text_input("نام کاربری")

            password = st.text_input(
                "رمز عبور",
                type="password"
            )

            login = st.form_submit_button(
                "ورود",
                type="primary",
                use_container_width=True
            )

            if login:

                user = authenticate_user(username, password)

                if user:

                    st.session_state.authenticated = True
                    st.session_state.user_id = user["id"]
                    st.session_state.username = user["username"]
                    st.session_state.display_name = user["display_name"]

                    restore_user_data(user)

                    st.rerun()

                else:
                    st.error("نام کاربری یا رمز عبور اشتباه است.")

    with tab2:

        with st.form("register_form"):

            display_name = st.text_input("نام شما")

            new_username = st.text_input("نام کاربری")

            new_password = st.text_input(
                "رمز عبور",
                type="password"
            )

            confirm_password = st.text_input(
                "تکرار رمز عبور",
                type="password"
            )

            register = st.form_submit_button(
                "ساخت حساب",
                type="primary",
                use_container_width=True
            )

            if register:

                if new_password != confirm_password:

                    st.error("رمزهای عبور یکسان نیستند.")

                else:

                    success, message = register_user(
                        new_username,
                        display_name,
                        new_password
                    )

                    if success:
                        st.success(message)
                        st.info("حالا از قسمت ورود وارد حساب خود شوید.")
                    else:
                        st.error(message)

    st.stop()

# ==================================================
# 7. CHAT FUNCTIONS
# ==================================================

def current_messages():
    return st.session_state.chats[
        st.session_state.current_chat
    ]

def new_chat():

    st.session_state.chat_counter += 1

    name = f"Chat {st.session_state.chat_counter}"

    st.session_state.chats[name] = []

    st.session_state.current_chat = name

    save_user_data()

    st.rerun()

def export_chat(messages):

    result = []

    for message in messages:

        role = "شما" if message["role"] == "user" else "ور دست"

        result.append(
            f"{role}:\n{message['content']}"
        )

    return "\n\n--------------------\n\n".join(result)

def read_pdf(file):

    reader = PyPDF2.PdfReader(
        io.BytesIO(file.getvalue())
    )

    pages = []

    for page in reader.pages:
        pages.append(page.extract_text() or "")

    return "\n".join(pages)

def safe_copy(text):

    payload = json.dumps(text, ensure_ascii=False)

    html = f"""
    <script>
    navigator.clipboard.writeText({payload})
        .then(() => console.log("Copied"))
        .catch(() => console.log("Copy failed"));
    </script>
    """

    components.html(html, height=0)

def speak_text(text, language):

    try:

        lang = "fa" if language == "فارسی" else "en"

        url = (
            "https://translate.google.com/translate_tts?"
            f"ie=UTF-8&q={urllib.parse.quote(text[:200])}"
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

# ==================================================
# 8. AI RESPONSE
# ==================================================

def ask_ai(messages, text, files, tone, temperature):

    if not client:
        st.error("کلید GROQ_API_KEY تنظیم نشده است.")
        return None

    system_prompt = f"""
تو ور دست هستی، یک دستیار هوش مصنوعی دقیق و کاربردی.

قوانین:
- پاسخ‌ها دقیق و قابل فهم باشند.
- از Markdown استفاده کن.
- اگر کاربر فارسی صحبت کرد فارسی پاسخ بده.
- مثال‌های مفید ارائه بده.
- لحن پاسخ: {tone}
- از اطلاعات ساختگی به عنوان واقعیت استفاده نکن.
"""

    if not text.strip():
        text = "لطفاً فایل پیوست شده را بررسی کن."

    api_content = [
        {"type": "text", "text": text}
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
                    "text": "متن PDF:\n" + pdf_text[:12000]
                })

        except Exception as error:
            st.warning(f"خطا در فایل {file.name}: {error}")

    api_messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    for message in messages[:-1]:

        api_messages.append({
            "role": message["role"],
            "content": message["content"]
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

        st.error(f"خطای اتصال به هوش مصنوعی: {error}")

        return None

# ==================================================
# 9. SIDEBAR
# ==================================================

with st.sidebar:

    st.success(
        f"خوش آمدی {st.session_state.display_name}"
    )

    st.caption(
        f"حساب: {st.session_state.username}"
    )

    st.divider()

    if st.button(
        "چت جدید",
        icon=":material/add_circle:",
        use_container_width=True
    ):
        new_chat()

    st.subheader("تاریخچه")

    search_query = st.text_input(
        "جستجوی گفتگو",
        placeholder="نام یا متن گفتگو..."
    )

    for name, messages in list(st.session_state.chats.items()):

        searchable = name + " " + " ".join(
            m["content"] for m in messages
        )

        if search_query.lower() in searchable.lower():

            if st.button(
                name,
                key=f"select_{name}",
                type=(
                    "primary"
                    if name == st.session_state.current_chat
                    else "secondary"
                ),
                use_container_width=True
            ):

                st.session_state.current_chat = name
                st.rerun()

    st.divider()

    language = st.selectbox(
        "زبان",
        ["فارسی", "English"]
    )

    theme = st.radio(
        "تم",
        ["Dark", "Light"],
        horizontal=True
    )

    tone = st.selectbox(
        "لحن پاسخ",
        ["دوستانه", "حرفه‌ای", "خلاقانه", "مستقیم"]
    )

    temperature = st.slider(
        "میزان خلاقیت",
        0.0,
        1.5,
        0.7,
        0.1
    )

    st.divider()

    st.subheader("مدیریت گفتگو")

    rename = st.text_input(
        "نام جدید گفتگو"
    )

    if st.button(
        "تغییر نام",
        icon=":material/edit:"
    ):

        if rename.strip():

            old = st.session_state.current_chat
            new = rename.strip()

            if new not in st.session_state.chats:

                st.session_state.chats[new] = (
                    st.session_state.chats.pop(old)
                )

                st.session_state.current_chat = new

                save_user_data()
                st.rerun()

            else:
                st.warning("این نام قبلاً وجود دارد.")

    if st.button(
        "پاک کردن گفتگو",
        icon=":material/delete_sweep:",
        use_container_width=True
    ):

        st.session_state.chats[
            st.session_state.current_chat
        ] = []

        save_user_data()
        st.rerun()

    if len(st.session_state.chats) > 1:

        if st.button(
            "حذف کامل این گفتگو",
            icon=":material/delete:",
            use_container_width=True
        ):

            del st.session_state.chats[
                st.session_state.current_chat
            ]

            st.session_state.current_chat = next(
                iter(st.session_state.chats)
            )

            save_user_data()
            st.rerun()

    messages = current_messages()

    if messages:

        st.download_button(
            "دانلود تاریخچه",
            data=export_chat(messages),
            file_name="vardast_chat.txt",
            mime="text/plain",
            icon=":material/download:",
            use_container_width=True
        )

    st.divider()

    if st.button(
        "خروج از حساب",
        icon=":material/logout:",
        use_container_width=True
    ):

        save_user_data()

        for key in [
            "authenticated",
            "user_id",
            "username",
            "display_name",
            "chats",
            "current_chat",
            "chat_counter"
        ]:
            st.session_state.pop(key, None)

        st.rerun()

# ==================================================
# 10. THEME
# ==================================================

if theme == "Light":

    st.markdown("""
    <style>
    .stApp {
        background-image:
        linear-gradient(
            rgba(248,249,250,.92),
            rgba(248,249,250,.97)
        ) !important;
        color: #222 !important;
    }

    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,.9) !important;
        color: #222 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==================================================
# 11. HEADER
# ==================================================

st.markdown(
    '<div class="header-style">',
    unsafe_allow_html=True
)

st.title("ور دست ⚡")
st.caption("دستیار هوشمند، رایگان و در دسترس همه")

st.markdown(
    '</div>',
    unsafe_allow_html=True
)

# ==================================================
# 12. QUICK PROMPTS
# ==================================================

messages = current_messages()

if not messages:

    with st.chat_message("assistant", avatar="⚡"):

        st.markdown(
            "سلام! من ور دست هستم. چطور می‌توانم کمکت کنم؟"
        )

    q1, q2, q3 = st.columns(3)

    if q1.button(
        "ترجمه",
        icon=":material/translate:",
        use_container_width=True
    ):
        st.session_state.quick_prompt = "این متن را به انگلیسی ترجمه کن:"

    if q2.button(
        "برنامه‌نویسی",
        icon=":material/code:",
        use_container_width=True
    ):
        st.session_state.quick_prompt = "به من برنامه‌نویسی آموزش بده."

    if q3.button(
        "ایده خلاقانه",
        icon=":material/lightbulb:",
        use_container_width=True
    ):
        st.session_state.quick_prompt = "چند ایده خلاقانه پیشنهاد بده."

# ==================================================
# 13. DISPLAY CHAT
# ==================================================

for i, message in enumerate(messages):

    avatar = "👤" if message["role"] == "user" else "⚡"

    with st.chat_message(
        message["role"],
        avatar=avatar
    ):

        content = message["content"]

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

            st.image(
                image_url,
                caption="Vardast Image Generator"
            )

        else:
            st.markdown(content)

        if message["role"] == "assistant":

            c1, c2, c3, c4, c5, c6 = st.columns(6)

            with c1:

                if st.button(
                    " ",
                    icon=":material/content_copy:",
                    key=f"copy_{i}",
                    help="کپی"
                ):
                    safe_copy(content)
                    st.toast("درخواست کپی ارسال شد.")

            with c2:

                if st.button(
                    " ",
                    icon=":material/thumb_up:",
                    key=f"like_{i}",
                    help="پسندیدن"
                ):
                    st.session_state.feedback[
                        f"{st.session_state.current_chat}_{i}"
                    ] = "like"

                    st.toast("ممنون از بازخوردت!")

            with c3:

                if st.button(
                    " ",
                    icon=":material/thumb_down:",
                    key=f"dislike_{i}",
                    help="نپسندیدن"
                ):
                    st.session_state.feedback[
                        f"{st.session_state.current_chat}_{i}"
                    ] = "dislike"

                    st.toast("بازخورد ثبت شد.")

            with c4:

                if st.button(
                    " ",
                    icon=":material/volume_up:",
                    key=f"audio_{i}",
                    help="خواندن صوتی"
                ):
                    speak_text(content, language)

            with c5:

                if st.button(
                    " ",
                    icon=":material/share:",
                    key=f"share_{i}",
                    help="اشتراک گذاری"
                ):
                    safe_copy(content)
                    st.toast("متن برای اشتراک‌گذاری کپی شد.")

            with c6:

                with st.popover(
                    " ",
                    icon=":material/more_vert:"
                ):

                    st.download_button(
                        "دانلود پاسخ",
                        data=content,
                        file_name=f"vardast_answer_{i}.txt",
                        mime="text/plain"
                    )

                    if i == len(messages) - 1:

                        if st.button(
                            "تولید مجدد پاسخ",
                            icon=":material/refresh:"
                        ):

                            last_user = next(
                                (
                                    m["content"]
                                    for m in reversed(messages[:i])
                                    if m["role"] == "user"
                                ),
                                None
                            )

                            if last_user:

                                messages.pop()
                                save_user_data()

                                st.session_state.quick_prompt = last_user
                                st.rerun()

# ==================================================
# 14. FILE UPLOAD
# ==================================================

st.divider()

with st.expander(
    "پیوست فایل",
    icon=":material/attach_file:"
):

    uploaded_files = st.file_uploader(
        "تصویر یا PDF انتخاب کن",
        type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True
    )

    if uploaded_files:

        st.success(
            f"{len(uploaded_files)} فایل انتخاب شد."
        )

        for file in uploaded_files:
            st.caption(file.name)

# ==================================================
# 15. MESSAGE INPUT
# ==================================================

quick_text = st.session_state.pop(
    "quick_prompt",
    ""
)

input_key = f"input_{st.session_state.input_counter}"

user_text = st.text_area(
    "پیام",
    value=quick_text,
    height=100,
    placeholder="پیام خود را بنویسید...",
    key=input_key,
    label_visibility="collapsed"
)

send = st.button(
    "ارسال پیام",
    icon=":material/send:",
    type="primary",
    use_container_width=True
)

if send:

    if user_text.strip() or uploaded_files:

        # Save user message first

        display_text = user_text.strip()

        if uploaded_files:
            display_text += (
                f"\n[{len(uploaded_files)} فایل پیوست شد]"
            )

        messages = current_messages()

        messages.append({
            "role": "user",
            "content": display_text
        })

        save_user_data()

        st.session_state.input_counter += 1

        # Show user message

        with st.chat_message("user", avatar="👤"):
            st.markdown(display_text)

        # Generate AI response

        with st.chat_message("assistant", avatar="⚡"):

            with st.spinner("ور دست در حال فکر کردن است..."):

                answer = ask_ai(
                    messages,
                    user_text,
                    uploaded_files if uploaded_files else [],
                    tone,
                    temperature
                )

            if answer:

                messages.append({
                    "role": "assistant",
                    "content": answer
                })

                # Save assistant answer immediately

                save_user_data()

        st.rerun()

# ==================================================
# 16. FOOTER
# ==================================================

st.divider()

st.markdown(
    """
    <div class="brand">
    Vardast AI ⚡ | Your intelligent companion
    </div>
    """,
    unsafe_allow_html=True
)
