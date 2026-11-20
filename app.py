import streamlit as st
from openai import OpenAI
import os
import urllib.parse
import base64
import PyPDF2
import io

# ==========================================
# ۱. تنظیمات ظاهری (طراحی مدرن)
# ==========================================
st.set_page_config(page_title="Vardast | ور دست", page_icon="✨", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&family=Vazirmatn:wght@300;400;700&display=swap');
    
    /* فونت و جهت‌دهی */
    html, body, [class*="css"] { font-family: 'Poppins', 'Vazirmatn', sans-serif; }
    .rtl { direction: rtl; text-align: right; }
    
    /* هدر گرادیانتی */
    .header-style {
        background: linear-gradient(90deg, #1E232F 0%, #0E1117 100%);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        border: 1px solid #2C333F;
    }
    
    /* حباب‌های چت */
    [data-testid="stChatMessage"] {
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.05);
    }
    
    /* دکمه‌های شیشه‌ای منوی کناری */
    [data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255,255,255,0.05);
        color: white;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: rgba(255,255,255,0.1);
        border-color: #4A90E2;
    }
    
    /* کادر ورودی */
    .stChatInput {
        border-radius: 20px;
        box-shadow: 0 0 15px rgba(74, 144, 226, 0.2);
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ۲. ساختار چندزبانه
# ==========================================
LANGUAGES = {
    "English": {
        "title": "Vardast ✨", "caption": "Your smart, free assistant.",
        "language": "Language", "theme": "Theme", "tone": "Tone",
        "tone_opts": {"Friendly": "Friendly", "Professional": "Professional", "Creative": "Creative", "Direct": "Direct"},
        "new_chat": "➕ New Chat", "chat_list": "History", "clear_chat": "🗑️ Clear Chat",
        "force_fa": "Force Persian Input", "placeholder": "Type here...",
        "system_prompt": "You are 'Vardast'. Be concise. If asked to generate an image, reply EXACTLY with 'IMAGE_GEN: [English prompt]'. Tone: {tone}.",
        "creator": "Made with ❤️ by Parsa"
    },
    "فارسی": {
        "title": "ور دست ✨", "caption": "دستیار هوشمند، رایگان و در دسترس همه",
        "language": "زبان", "theme": "تم", "tone": "لحن",
        "tone_opts": {"دوستانه": "دوستانه", "حرفه‌ای": "حرفه‌ای", "خلاقانه": "خلاقانه", "مستقیم": "مستقیم"},
        "new_chat": "➕ چت جدید", "chat_list": "تاریخچه", "clear_chat": "🗑️ پاک کردن",
        "force_fa": "ورودی انگلیسی", "placeholder": "اینجا بنویس...",
        "system_prompt": "تو 'ور دست' هستی. مختصر جواب بده. اگر خواست عکس بسازی دقیقاً بنویس 'IMAGE_GEN: [توضیح انگلیسی]'. لحن: {tone}.",
        "creator": "ساخته شده با ❤️ توسط پارسا"
    }
}

# ==========================================
# ۳. تنظیمات API
# ==========================================
try:
    api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    api_key = os.environ.get("GROQ_API_KEY")

client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)

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
    st.markdown(f"<div style='text-align: center; color: gray; font-size: 13px;'>{t['creator']}</div>", unsafe_allow_html=True)

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
st.markdown('<div class="header-style">', unsafe_allow_html=True)
st.title(t["title"])
st.caption(t["caption"])
st.markdown('</div>', unsafe_allow_html=True)

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
# ۹. دریافت ورودی (با قابلیت آپلود فایل و PDF)
# ==========================================
prompt = st.chat_input(t["placeholder"], accept_file=True, file_type=["jpg", "jpeg", "png", "pdf"])

if prompt:
    user_text = prompt.text if prompt.text else ""
    user_files = prompt.files if prompt.files else []
    
    display_content = user_text
    if user_files:
        display_content += f"\n[فایل پیوست شد]"
    
    api_content = [{"type": "text", "text": user_text if user_text else "این فایل را تحلیل کن."}]
    
    for file in user_files:
        # پردازش تصویر
        if file.type.startswith("image"):
            image_bytes = file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            api_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{file.type};base64,{base64_image}"}
            })
        # پردازش PDF
        elif file.type == "application/pdf":
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.getvalue()))
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
                
                api_content.append({
                    "type": "text",
                    "text": f"متن استخراج شده از فایل PDF:\n{pdf_text[:2000]}..."  # محدود کردن به ۲۰۰۰ کاراکتر اول
                })
            except Exception as e:
                st.error(f"خطا در خواندن PDF: {e}")
    
    current_messages.append({"role": "user", "content": display_content})
    with st.chat_message("user"):
        if direction == "rtl": st.markdown(f"<div class='rtl'>{display_content}</div>", unsafe_allow_html=True)
        else: st.markdown(display_content)
        for file in user_files:
            if file.type.startswith("image"):
                st.image(file)

    sys_prompt = t["system_prompt"].format(tone=tone_value)
    if direction == "rtl": 
        sys_prompt += " کاربر به زبان فارسی صحبت می‌کند، لطفاً به فارسی روان پاسخ بده."

    api_messages = [{"role": "system", "content": sys_prompt}]
    for m in current_messages[:-1]:
        api_messages.append({"role": m["role"], "content": m["content"]})
    api_messages.append({"role": "user", "content": api_content})

    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=api_messages, 
                temperature=1.0, 
                stream=True,
                max_tokens=600
            )
            response = st.write_stream(stream)
            current_messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.error(f"Connection error: {e}")