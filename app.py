
import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from gtts import gTTS
import os
import io
import json
import base64
import sqlite3
import hashlib
import secrets
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

APP_NAME = "ور دست"
CREATOR = "سید محمد پارسا حسینی"

# =====================================================
# 2. DATABASE - PERMANENT USER DATA
# =====================================================

if os.path.isdir("/var/data"):
    DB_PATH = os.getenv("DB_PATH", "/var/data/vardast.db")
else:
    DB_PATH = os.getenv("DB_PATH", "vardast.db")


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
                ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(chat_id) REFERENCES chats(id)
                ON DELETE CASCADE
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                reaction TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(message_id) REFERENCES messages(id)
            )
        """)


init_db()


def now():
    return datetime.now().isoformat(timespec="seconds")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        200000
    ).hex()
    return salt + "$" + hashed


def verify_password(password, stored):
    try:
        salt, old_hash = stored.split("$")
        return secrets.compare_digest(
            hash_password(password, salt).split("$")[1],
            old_hash
        )
    except Exception:
        return False


def create_user(username, password):
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO users(username,password,created_at) VALUES(?,?,?)",
                (username, hash_password(password), now())
            )
        return True
    except sqlite3.IntegrityError:
        return False


def login_user(username, password):
    with db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()

    if user and verify_password(password, user["password"]):
        return user["id"]

    return None


def get_chats(user_id):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM chats WHERE user_id=? ORDER BY id DESC",
            (user_id,)
        ).fetchall()


def create_chat(user_id, title="گفتگوی جدید"):
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO chats(user_id,title,created_at) VALUES(?,?,?)",
            (user_id, title, now())
        )
        return cur.lastrowid


def rename_chat(chat_id, user_id, title):
    with db() as conn:
        conn.execute(
            "UPDATE chats SET title=? WHERE id=? AND user_id=?",
            (title, chat_id, user_id)
        )


def delete_chat(chat_id, user_id):
    with db() as conn:
        conn.execute(
            "DELETE FROM chats WHERE id=? AND user_id=?",
            (chat_id, user_id)
        )


def get_messages(chat_id):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM messages WHERE chat_id=? ORDER BY id",
            (chat_id,)
        ).fetchall()


def save_message(chat_id, role, content):
    with db() as conn:
        cur = conn.execute(
            """INSERT INTO messages(chat_id,role,content,created_at)
               VALUES(?,?,?,?)""",
            (chat_id, role, content, now())
        )
        return cur.lastrowid


def save_feedback(user_id, message_id, reaction):
    with db() as conn:
        conn.execute(
            """INSERT INTO feedback(user_id,message_id,reaction)
               VALUES(?,?,?)""",
            (user_id, message_id, reaction)
        )


# =====================================================
# 3. API CONFIGURATION
# =====================================================

try:
    API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    API_KEY = os.getenv("GROQ_API_KEY")

client = None

if API_KEY:
    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=API_KEY
    )

CHAT_MODEL = os.getenv(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

VISION_MODEL = os.getenv(
    "GROQ_VISION_MODEL",
    "meta-llama/llama-4-scout-17b-16e-instruct"
)

# =====================================================
# 4. SESSION STATE
# =====================================================

defaults = {
    "user_id": None,
    "username": None,
    "chat_id": None,
    "theme": "Dark",
    "language": "فارسی",
    "tone": "دوستانه",
    "creativity": 1.5,
    "pending_prompt": "",
    "show_register": False
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =====================================================
# 5. CSS / DESIGN
# =====================================================

PERSIPOLIS_IMAGE = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/"
    "6/6f/Persepolis_24.jpg/1200px-Persepolis_24.jpg"
)

st.markdown(f"""
<style>

@import url('https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {{
    font-family: 'Vazirmatn', sans-serif;
}}

.stApp {{
    background:
    linear-gradient(rgba(10,12,19,.91),rgba(10,12,19,.97)),
    url("{PERSIPOLIS_IMAGE}");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}}

[data-testid="stSidebar"] {{
    background: rgba(13,16,25,.96);
    border-right: 1px solid rgba(255,255,255,.08);
}}

[data-testid="stChatMessage"] {{
    background: rgba(28,32,45,.83);
    border: 1px solid rgba(255,255,255,.09);
    border-radius: 20px;
    padding: 18px;
    margin-bottom: 15px;
}}

.stTextArea textarea, .stTextInput input {{
    border-radius: 15px !important;
    background: rgba(25,25,29,.9) !important;
    color: white !important;
}}

.stButton button, .stDownloadButton button {{
    border-radius: 13px;
    transition: .2s;
}}

.stButton button:hover {{
    border-color: #8e44ad;
    transform: translateY(-2px);
}}

div.stButton > button[kind="primary"] {{
    background: linear-gradient(90deg,#4A90E2,#8E44AD);
    color: white;
    border: none;
    border-radius: 30px;
    font-weight: bold;
}}

.header-box {{
    background: rgba(35,39,55,.78);
    border: 1px solid rgba(255,255,255,.12);
    padding: 22px;
    border-radius: 22px;
    text-align: center;
    margin-bottom: 25px;
}}

.brand {{
    font-size: 38px;
    font-weight: 700;
}}

.muted {{
    color: #aaa;
    font-size: 13px;
}}

.rtl {{
    direction: rtl;
    text-align: right;
}}

</style>
""", unsafe_allow_html=True)


# =====================================================
# 6. AUTHENTICATION
# =====================================================

if st.session_state.user_id is None:

    st.markdown("""
    <div class="header-box">
        <div class="brand">ور دست ⚡</div>
        <p>دستیار هوشمند، خلاق و همیشه در دسترس</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["ورود", "ثبت نام"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("نام کاربری")
            password = st.text_input("رمز عبور", type="password")
            login = st.form_submit_button("ورود به حساب", use_container_width=True)

        if login:
            uid = login_user(username.strip(), password)
            if uid:
                st.session_state.user_id = uid
                st.session_state.username = username.strip()

                chats = get_chats(uid)
                if chats:
                    st.session_state.chat_id = chats[0]["id"]
                else:
                    st.session_state.chat_id = create_chat(uid)

                st.rerun()
            else:
                st.error("نام کاربری یا رمز عبور اشتباه است.")

    with tab_register:
        with st.form("register_form"):
            new_username = st.text_input("نام کاربری جدید")
            new_password = st.text_input("رمز عبور جدید", type="password")
            confirm_password = st.text_input("تکرار رمز عبور", type="password")
            register = st.form_submit_button("ساخت حساب", use_container_width=True)

        if register:
            if len(new_username.strip()) < 3:
                st.error("نام کاربری باید حداقل ۳ حرف باشد.")
            elif len(new_password) < 8:
                st.error("رمز عبور باید حداقل ۸ کاراکتر باشد.")
            elif new_password != confirm_password:
                st.error("رمزهای عبور یکسان نیستند.")
            elif create_user(new_username.strip(), new_password):
                st.success("حساب ساخته شد. حالا وارد شوید.")
            else:
                st.error("این نام کاربری قبلاً استفاده شده است.")

    st.stop()


# =====================================================
# 7. SIDEBAR
# =====================================================

with st.sidebar:

    st.markdown("## ⚡ ور دست")

    st.caption("خوش آمدی، " + st.session_state.username)

    st.divider()

    st.session_state.language = st.selectbox(
        "زبان",
        ["فارسی", "English"],
        index=0 if st.session_state.language == "فارسی" else 1
    )

    st.session_state.theme = st.radio(
        "تم",
        ["Dark", "Light"],
        horizontal=True
    )

    st.session_state.tone = st.selectbox(
        "لحن پاسخ",
        ["دوستانه", "حرفه‌ای", "خلاقانه", "مستقیم"]
    )

    st.markdown("### میزان خلاقیت")

    st.session_state.creativity = st.slider(
        "خلاقیت",
        min_value=0.0,
        max_value=1.5,
        value=float(st.session_state.creativity),
        step=0.1
    )

    st.divider()

    st.markdown("### مدیریت گفتگو")

    if st.button("➕ گفتگوی جدید", use_container_width=True):
        st.session_state.chat_id = create_chat(
            st.session_state.user_id
        )
        st.rerun()

    chats = get_chats(st.session_state.user_id)

    if chats:
        chat_options = {c["title"] + f"  #{c['id']}": c["id"] for c in chats}

        selected_chat = st.selectbox(
            "تاریخچه گفتگوها",
            list(chat_options.keys()),
            index=next(
                (i for i, c in enumerate(chats)
                 if c["id"] == st.session_state.chat_id),
                0
            )
        )

        new_chat_id = chat_options[selected_chat]

        if new_chat_id != st.session_state.chat_id:
            st.session_state.chat_id = new_chat_id
            st.rerun()

    with st.expander("تغییر نام گفتگو"):
        rename_value = st.text_input("نام جدید", key="rename_input")

        if st.button("ذخیره نام"):
            if rename_value.strip():
                rename_chat(
                    st.session_state.chat_id,
                    st.session_state.user_id,
                    rename_value.strip()
                )
                st.rerun()

    if st.button("🗑️ پاک کردن گفتگو", use_container_width=True):
        delete_chat(
            st.session_state.chat_id,
            st.session_state.user_id
        )
        st.session_state.chat_id = create_chat(
            st.session_state.user_id
        )
        st.rerun()

    st.divider()

    if st.button("خروج از حساب", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.chat_id = None
        st.rerun()

    st.divider()

    st.markdown(
        f"<div style='text-align:center;color:#999;font-size:12px'>"
        f"ساخته شده با ❤️ توسط<br><b>{CREATOR}</b></div>",
        unsafe_allow_html=True
    )


# =====================================================
# 8. THEME
# =====================================================

if st.session_state.theme == "Light":
    st.markdown("""
    <style>
    .stApp {
        background: #f1f3f8 !important;
        color: #222 !important;
    }
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,.95) !important;
        color: #222 !important;
    }
    </style>
    """, unsafe_allow_html=True)


# =====================================================
# 9. SYSTEM PROMPT
# =====================================================

if st.session_state.language == "فارسی":
    language_instruction = "همیشه به فارسی روان پاسخ بده، مگر اینکه کاربر زبان دیگری بخواهد."
else:
    language_instruction = "Answer in English unless the user requests another language."


SYSTEM_PROMPT = f"""
تو ور دست (Vardast) هستی.

یک دستیار هوش مصنوعی دقیق، خلاق، مودب و توانمند هستی.

سازنده تو {CREATOR} است.

قوانین:
- پاسخ دقیق و کاربردی بده.
- از Markdown استفاده کن.
- پاسخ را متناسب با سطح کاربر تنظیم کن.
- اگر کد خواست، کد کامل و قابل اجرا بده.
- اگر درخواست تصویر کرد، در انتهای پاسخ یک خط با قالب زیر بنویس:
IMAGE_GEN: English image prompt
- برای تولید تصویر، پرامپت دقیق و توصیفی بنویس.
- اطلاعات ساختگی را به عنوان واقعیت معرفی نکن.
- به فایل‌های ارسالی با دقت توجه کن.

لحن: {st.session_state.tone}
{language_instruction}
"""


# =====================================================
# 10. IMAGE GENERATION
# =====================================================

def generate_image(prompt):
    encoded = urllib.parse.quote(prompt)

    return (
        "https://image.pollinations.ai/prompt/"
        + encoded
        + "?width=1024&height=1024&nologo=true"
    )


def show_image(prompt):
    url = generate_image(prompt)

    try:
        response = requests.get(
            url,
            timeout=90,
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if response.status_code == 200 and response.content:
            st.image(
                response.content,
                caption="ساخته شده توسط ور دست ⚡",
                use_container_width=True
            )
            return url

        st.error("سرویس تولید تصویر پاسخ نداد.")
        return None

    except Exception:
        st.error("ارتباط با سرویس تصویرسازی برقرار نشد.")
        return None


# =====================================================
# 11. MAIN HEADER
# =====================================================

st.markdown("""
<div class="header-box">
    <div class="brand">ور دست ⚡</div>
    <p>دستیار هوشمند، رایگان و در دسترس همه</p>
</div>
""", unsafe_allow_html=True)


# =====================================================
# 12. QUICK TOOLS
# =====================================================

st.markdown("### ابزارهای سریع")

q1, q2, q3 = st.columns(3)

with q1:
    if st.button("🌐 ترجمه", use_container_width=True):
        st.session_state.pending_prompt = "لطفاً متن زیر را ترجمه کن: "

with q2:
    if st.button("💻 برنامه نویسی", use_container_width=True):
        st.session_state.pending_prompt = "در برنامه نویسی به من کمک کن."

with q3:
    if st.button("💡 ایده خلاقانه", use_container_width=True):
        st.session_state.pending_prompt = "یک ایده خلاقانه و کاربردی پیشنهاد بده."


# =====================================================
# 13. IMAGE GENERATOR PANEL
# =====================================================

with st.expander("🎨 استودیوی تولید تصویر", expanded=False):

    image_prompt = st.text_area(
        "چه تصویری می‌خواهی بسازم؟",
        placeholder="مثلاً: یک شهر آینده نگر در شب..."
    )

    if st.button("ساخت تصویر", type="primary"):
        if image_prompt.strip():
            with st.spinner("در حال ساخت تصویر..."):
                url = show_image(image_prompt)

                if url:
                    save_message(
                        st.session_state.chat_id,
                        "assistant",
                        "IMAGE_RESULT::" + url + "\n" + image_prompt
                    )
        else:
            st.warning("ابتدا توضیح تصویر را بنویس.")


# =====================================================
# 14. VOICE INPUT
# =====================================================

st.markdown("### 🎙️ ورودی صوتی")

audio_value = st.audio_input("ویس خود را ضبط کن")

if audio_value is not None:

    st.audio(audio_value)

    if st.button("تبدیل ویس به متن"):

        if not client:
            st.error("کلید API تنظیم نشده است.")
        else:
            try:
                with st.spinner("در حال تبدیل صدا به متن..."):

                    audio_bytes = audio_value.getvalue()

                    transcript = client.audio.transcriptions.create(
                        model="whisper-large-v3-turbo",
                        file=(
                            "voice.wav",
                            audio_bytes,
                            "audio/wav"
                        )
                    )

                    recognized_text = transcript.text

                    st.success("متن شناسایی شده:")
                    st.write(recognized_text)

                    st.session_state.pending_prompt = recognized_text

            except Exception as e:
                st.error(f"خطا در تبدیل صدا: {e}")


# =====================================================
# 15. LOAD CHAT HISTORY
# =====================================================

messages = get_messages(st.session_state.chat_id)

for msg in messages:

    role = msg["role"]
    content = msg["content"]

    avatar = "👤" if role == "user" else "⚡"

    with st.chat_message(role, avatar=avatar):

        if content.startswith("IMAGE_RESULT::"):
            parts = content.split("\n", 1)
            url = parts[0].replace("IMAGE_RESULT::", "")
            prompt = parts[1] if len(parts) > 1 else ""

            st.caption("تصویر تولید شده")
            st.image(url, use_container_width=True)
            st.caption(prompt)

        else:
            st.markdown(content)

            if role == "assistant":
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.button(
                        "📋",
                        key=f"copy_{msg['id']}",
                        help="کپی پاسخ"
                    )

                with col2:
                    if st.button(
                        "👍",
                        key=f"like_{msg['id']}",
                        help="پسندیدم"
                    ):
                        save_feedback(
                            st.session_state.user_id,
                            msg["id"],
                            "like"
                        )
                        st.toast("ممنون از بازخوردت!")

                with col3:
                    if st.button(
                        "👎",
                        key=f"dislike_{msg['id']}",
                        help="نپسندیدم"
                    ):
                        save_feedback(
                            st.session_state.user_id,
                            msg["id"],
                            "dislike"
                        )
                        st.toast("بازخوردت ثبت شد.")

                with col4:
                    if st.button(
                        "🔊",
                        key=f"voice_{msg['id']}",
                        help="خواندن پاسخ"
                    ):
                        try:
                            lang = (
                                "fa" if st.session_state.language == "فارسی"
                                else "en"
                            )

                            speech = gTTS(
                                text=content[:4000],
                                lang=lang
                            )

                            audio_buffer = io.BytesIO()
                            speech.write_to_fp(audio_buffer)
                            audio_buffer.seek(0)

                            st.audio(
                                audio_buffer,
                                format="audio/mp3"
                            )

                        except Exception as e:
                            st.warning(f"خطا در ساخت صدا: {e}")


# =====================================================
# 16. FILE UPLOAD
# =====================================================

st.divider()

uploaded_files = st.file_uploader(
    "📎 پیوست فایل (اختیاری)",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True
)


# =====================================================
# 17. CHAT INPUT
# =====================================================

default_prompt = st.session_state.pending_prompt
st.session_state.pending_prompt = ""

user_text = st.text_area(
    "پیام خود را بنویسید",
    value=default_prompt,
    height=110,
    placeholder="پیام خود را اینجا بنویسید..."
)

send_button = st.button(
    "ارسال پیام 🚀",
    type="primary",
    use_container_width=True
)


# =====================================================
# 18. PROCESS USER MESSAGE
# =====================================================

if send_button:

    if not user_text.strip() and not uploaded_files:
        st.warning("لطفاً پیام یا فایل ارسال کن.")

    elif not client:
        st.error("کلید GROQ_API_KEY تنظیم نشده است.")

    else:

        api_content = [
            {
                "type": "text",
                "text": user_text.strip() or "فایل ارسالی را تحلیل کن."
            }
        ]

        file_notes = []

        for file in uploaded_files or []:

            if file.type.startswith("image/"):

                image_bytes = file.getvalue()

                encoded_image = base64.b64encode(
                    image_bytes
                ).decode("utf-8")

                api_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{file.type};base64,{encoded_image}"
                        )
                    }
                })

            elif file.type == "application/pdf":

                try:
                    reader = PyPDF2.PdfReader(
                        io.BytesIO(file.getvalue())
                    )

                    extracted = "\n".join(
                        page.extract_text() or ""
                        for page in reader.pages
                    )

                    file_notes.append(
                        "محتوای PDF:\n" + extracted[:12000]
                    )

                except Exception as e:
                    file_notes.append(
                        f"خطا در خواندن PDF: {e}"
                    )

        if file_notes:
            api_content.append({
                "type": "text",
                "text": "\n\n".join(file_notes)
            })

        display_text = user_text.strip()

        if uploaded_files:
            display_text += (
                f"\n\n[{len(uploaded_files)} فایل پیوست شد]"
            )

        save_message(
            st.session_state.chat_id,
            "user",
            display_text
        )

        history = get_messages(st.session_state.chat_id)

        api_messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

        # محدود کردن تاریخچه ارسالی برای کنترل حجم درخواست
        for old_msg in history[:-1][-20:]:

            if old_msg["content"].startswith("IMAGE_RESULT::"):
                continue

            api_messages.append({
                "role": old_msg["role"],
                "content": old_msg["content"]
            })

        api_messages.append({
            "role": "user",
            "content": api_content
        })

        selected_model = (
            VISION_MODEL
            if any(f.type.startswith("image/") for f in uploaded_files or [])
            else CHAT_MODEL
        )

        try:

            with st.spinner("ور دست در حال فکر کردن است..."):

                result = client.chat.completions.create(
                    model=selected_model,
                    messages=api_messages,
                    temperature=float(
                        st.session_state.creativity
                    ),
                    max_tokens=2000
                )

                answer = result.choices[0].message.content or ""

                if "IMAGE_GEN:" in answer:

                    parts = answer.split("IMAGE_GEN:", 1)

                    text_part = parts[0].strip()
                    prompt = parts[1].strip()

                    if text_part:
                        save_message(
                            st.session_state.chat_id,
                            "assistant",
                            text_part
                        )

                    with st.chat_message(
                        "assistant",
                        avatar="⚡"
                    ):

                        if text_part:
                            st.markdown(text_part)

                        with st.spinner("در حال تولید تصویر..."):

                            url = show_image(prompt)

                            if url:
                                save_message(
                                    st.session_state.chat_id,
                                    "assistant",
                                    "IMAGE_RESULT::" + url + "\n" + prompt
                                )

                else:

                    save_message(
                        st.session_state.chat_id,
                        "assistant",
                        answer
                    )

                    with st.chat_message(
                        "assistant",
                        avatar="⚡"
                    ):
                        st.markdown(answer)

            st.rerun()

        except Exception as e:

            st.error(f"خطا در ارتباط با هوش مصنوعی: {e}")


# =====================================================
# 19. DOWNLOAD CHAT
# =====================================================

all_messages = get_messages(st.session_state.chat_id)

if all_messages:

    export_text = ""

    for m in all_messages:
        role = "شما" if m["role"] == "user" else "ور دست"

        if m["content"].startswith("IMAGE_RESULT::"):
            export_text += role + ":\n[تصویر تولید شده]\n\n"
        else:
            export_text += (
                role + ":\n" + m["content"] + "\n\n"
            )

    st.divider()

    st.download_button(
        "📥 دانلود تاریخچه گفتگو",
        data=export_text,
        file_name="vardast_chat.txt",
        mime="text/plain",
        use_container_width=True
    )


# =====================================================
# 20. FOOTER
# =====================================================

st.markdown(
    f"""
    <div style="
        text-align:center;
        color:#888;
        padding:25px;
        font-size:12px;
    ">
        Vardast ⚡ | ساخته شده توسط {CREATOR}
        <br>
        Your Smart AI Assistant
    </div>
    """,
    unsafe_allow_html=True
)
