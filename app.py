import streamlit as st
from openai import OpenAI
import os

# ==========================================
# ۱. تنظیمات ظاهری و فونت‌ها
# ==========================================
st.set_page_config(page_title="Vardast | ور دست", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&family=Vazirmatn:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', 'Vazirmatn', sans-serif; }
    .rtl { direction: rtl; text-align: right; }
    [data-testid="stChatMessage"] { border-radius: 15px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ۲. ساختار چندزبانه (i18n)
# ==========================================
LANGUAGES = {
    "English": {
        "title": "Vardast 👁️", "caption": "A smart assistant for you, free and accessible.",
        "language": "App Language", "theme": "Theme Mode", "tone": "Response Tone",
        "tone_opts": {"Friendly": "Friendly and casual", "Professional": "Formal and professional", "Creative": "Creative and poetic", "Direct": "Short and direct"},
        "new_chat": "➕ New Chat", "chat_list": "Chat History", "clear_chat": "🗑️ Clear this chat",
        "force_fa": "Force Persian Input (فارسی بنویس)", "placeholder": "Type your message here...",
        "system_prompt": "You are a smart assistant named 'Vardast'. Your answers must be accurate, helpful, and of high quality. Your tone should be {tone}."
    },
    "فارسی": {
        "title": "ور دست 👁️", "caption": "دستیار هوشمند، رایگان و در دسترس همه",
        "language": "زبان برنامه", "theme": "تم رنگی", "tone": "لحن پاسخ‌دهی",
        "tone_opts": {"دوستانه": "دوستانه و صمیمی", "حرفه‌ای": "رسمی و حرفه‌ای", "خلاقانه": "خلاقانه و شاعرانه", "مستقیم": "کوتاه و مستقیم"},
        "new_chat": "➕ چت جدید", "chat_list": "تاریخچه چت‌ها", "clear_chat": "🗑️ پاک کردن این چت",
        "force_fa": "ورودی انگلیسی (English input)", "placeholder": "پیام خود را به فارسی بنویسید...",
        "system_prompt": "تو یک دستیار هوشمند به نام 'ور دست' هستی. پاسخ‌هایت باید دقیق، مفید و با کیفیت بالا باشد. لحن تو باید {tone} باشد."
    }
}

# ==========================================
# ۳. تنظیمات کلید API (خواندن از Secrets یا Render)
# ==========================================
try:
    api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    api_key = os.environ.get("GROQ_API_KEY")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=api_key
)

# ==========================================
# ۴. مدیریت حافظه
# ==========================================
if "chats" not in st.session_state: st.session_state.chats = {"Chat 1": []}
if "current_chat" not in st.session_state: st.session_state.current_chat = "Chat 1"

# ==========================================
# ۵. منوی کناری (Sidebar)
# ==========================================
with st.sidebar:
    selected_lang = st.selectbox("Language / زبان", list(LANGUAGES.keys()))
    t = LANGUAGES[selected_lang]
    
    st.divider()
    
    if st.button(t["new_chat"], use_container_width=True):
        chat_name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[chat_name] = []
        st.session_state.current_chat = chat_name
        st.rerun()

    st.write(f"**{t['chat_list']}**")
    for chat_name in st.session_state.chats.keys():
        if st.button(chat_name, use_container_width=True):
            st.session_state.current_chat = chat_name
            st.rerun()

    st.divider()
    
    theme_choice = st.radio(t["theme"], ["Dark", "Light"], horizontal=True)
    
    st.write(f"**{t['tone']}**")
    tone_labels = list(t["tone_opts"].keys())
    tone_choice = st.radio("", tone_labels, horizontal=True, label_visibility="collapsed")
    tone_value = t["tone_opts"][tone_choice]
    
    if st.button(t["clear_chat"], use_container_width=True):
        st.session_state.chats[st.session_state.current_chat] = []
        st.rerun()

# ==========================================
# ۶. اعمال تم دارک/لایت
# ==========================================
if theme_choice == "Dark":
    st.markdown("<style>.stApp { background-color: #0E1117; color: white; } [data-testid='stChatMessage'] { background-color: #1E232F; }</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.stApp { background-color: #F8F9FA; color: #333; } [data-testid='stChatMessage'] { background-color: #FFFFFF; }</style>", unsafe_allow_html=True)

# ==========================================
# ۷. هدر و تنظیم ورودی
# ==========================================
st.title(t["title"])
st.caption(t["caption"])

if selected_lang == "English":
    force_persian = st.checkbox(t["force_fa"], value=False)
    direction = "rtl" if force_persian else "ltr"
else:
    force_english = st.checkbox(t["force_fa"], value=False)
    direction = "ltr" if force_english else "rtl"

# ==========================================
# ۸. نمایش چت و ارتباط با هوش مصنوعی
# ==========================================
current_messages = st.session_state.chats[st.session_state.current_chat]

for message in current_messages:
    with st.chat_message(message["role"]):
        if direction == "rtl": st.markdown(f"<div class='rtl'>{message['content']}</div>", unsafe_allow_html=True)
        else: st.markdown(message["content"])

if prompt := st.chat_input(t["placeholder"]):
    current_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        if direction == "rtl": st.markdown(f"<div class='rtl'>{prompt}</div>", unsafe_allow_html=True)
        else: st.markdown(prompt)

    sys_prompt = t["system_prompt"].format(tone=tone_value)
    if direction == "rtl": sys_prompt += " کاربر به زبان فارسی صحبت می‌کند، لطفاً به فارسی روان پاسخ بده."
    
    api_messages = [{"role": "system", "content": sys_prompt}] + [{"role": m["role"], "content": m["content"]} for m in current_messages]

    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=api_messages, temperature=1.0, stream=True,
            )
            response = st.write_stream(stream)
            current_messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Connection error: {e}")