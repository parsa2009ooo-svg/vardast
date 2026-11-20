import streamlit as st
from openai import OpenAI
import os
import urllib.parse

# ==========================================
# ۱. تنظیمات ظاهری
# ==========================================
st.set_page_config(page_title="Vardast | ور دست", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&family=Vazirmatn:wght@300;400;700&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', 'Vazirmatn', sans-serif; }
    .rtl { direction: rtl; text-align: right; }
    [data-testid="stChatMessage"] { border-radius: 15px; padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .stChatInput { border-radius: 20px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ۲. ساختار چندزبانه
# ==========================================
LANGUAGES = {
    "English": {
        "title": "Vardast ✨", "caption": "A smart assistant for you, free and accessible.",
        "language": "App Language", "theme": "Theme Mode", "tone": "Response Tone",
        "tone_opts": {"Friendly": "Friendly and casual", "Professional": "Formal and professional", "Creative": "Creative and poetic", "Direct": "Short and direct"},
        "new_chat": "➕ New Chat", "chat_list": "Chat History", "clear_chat": "🗑️ Clear this chat",
        "force_fa": "Force Persian Input (فارسی بنویس)", "placeholder": "Type your message or ask for an image...",
        "system_prompt": "You are a smart assistant named 'Vardast'. You have access to the web. If the user asks for current information, use your browser_search tool. If the user asks you to generate an image, reply EXACTLY with 'IMAGE_GEN: [English prompt]'. Your tone should be {tone}.",
        "creator": "Made with ❤️ by Parsa"
    },
    "فارسی": {
        "title": "ور دست ✨", "caption": "دستیار هوشمند، رایگان و در دسترس همه",
        "language": "زبان برنامه", "theme": "تم رنگی", "tone": "لحن پاسخ‌دهی",
        "tone_opts": {"دوستانه": "دوستانه و صمیمی", "حرفه‌ای": "رسمی و حرفه‌ای", "خلاقانه": "خلاقانه و شاعرانه", "مستقیم": "کوتاه و مستقیم"},
        "new_chat": "➕ چت جدید", "chat_list": "تاریخچه چت‌ها", "clear_chat": "🗑️ پاک کردن این چت",
        "force_fa": "ورودی انگلیسی (English input)", "placeholder": "پیامت رو بنویس یا بخواه عکس بسازه...",
        "system_prompt": "تو یک دستیار هوشمند به نام 'ور دست' هستی. تو به وب دسترسی داری. اگر کاربر اطلاعات به‌روز خواست، از ابزار browser_search استفاده کن. اگر کاربر ازت خواست عکس بسازی، دقیقاً بنویس 'IMAGE_GEN: [توضیح انگلیسی]'. لحن تو باید {tone} باشد.",
        "creator": "ساخته شده با ❤️ توسط پارسا"
    }
}

# ==========================================
# ۳. تنظیمات کلید API
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
# ۵. منوی کناری
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

    st.divider()
    st.markdown(f"<div style='text-align: center; color: gray; font-size: 14px;'>{t['creator']}</div>", unsafe_allow_html=True)

# ==========================================
# ۶. اعمال تم
# ==========================================
if theme_choice == "Dark":
    st.markdown("<style>.stApp { background-color: #0E1117; color: white; } [data-testid='stChatMessage'] { background-color: #1E232F; }</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.stApp { background-color: #F8F9FA; color: #333; } [data-testid='stChatMessage'] { background-color: #FFFFFF; }</style>", unsafe_allow_html=True)

# ==========================================
# ۷. هدر
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
# ۸. نمایش چت
# ==========================================
current_messages = st.session_state.chats[st.session_state.current_chat]

for message in current_messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and message["content"].startswith("IMAGE_GEN:"):
            img_prompt = message["content"].replace("IMAGE_GEN:", "").strip()
            encoded_prompt = urllib.parse.quote(img_prompt)
            img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            st.image(img_url, caption=f"Prompt: {img_prompt}")
            if direction == "rtl": st.markdown(f"<div class='rtl'>تصویر ساخته شد!</div>", unsafe_allow_html=True)
            else: st.markdown("Image generated!")
        else:
            if direction == "rtl": st.markdown(f"<div class='rtl'>{message['content']}</div>", unsafe_allow_html=True)
            else: st.markdown(message["content"])

# ==========================================
# ۹. دریافت ورودی (با قابلیت آپلود فایل)
# ==========================================
prompt = st.chat_input(t["placeholder"], accept_file=True, file_type=["jpg", "jpeg", "png", "pdf"])

if prompt:
    user_text = prompt.text if prompt.text else ""
    user_files = prompt.files if prompt.files else []
    
    # اگر فایل آپلود شده بود، نامش را به متن اضافه می‌کنیم تا مدل بداند
    if user_files:
        file_names = [f.name for f in user_files]
        user_text += f"\n[Files attached: {', '.join(file_names)}]"
    
    current_messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        if direction == "rtl": st.markdown(f"<div class='rtl'>{user_text}</div>", unsafe_allow_html=True)
        else: st.markdown(user_text)
        for file in user_files:
            if file.type.startswith("image"):
                st.image(file)

    sys_prompt = t["system_prompt"].format(tone=tone_value)
    if direction == "rtl": sys_prompt += " کاربر به زبان فارسی صحبت می‌کند، لطفاً به فارسی روان پاسخ بده."
    
    api_messages = [{"role": "system", "content": sys_prompt}] + [
        {"role": m["role"], "content": m["content"]} for m in current_messages
    ]

    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=api_messages, 
                temperature=1.0, 
                stream=True,
                tools=[{"type": "browser_search"}], # فعال‌سازی جستجوی وب
            )
            response = st.write_stream(stream)
            current_messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Connection error: {e}")