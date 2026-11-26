import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import os
import urllib.parse
import base64
import PyPDF2
import io
from gtts import gTTS

# ==========================================
# ۰. تنظیمات PWA
# ==========================================
pwa_html = """
<link rel="manifest" href="data:application/manifest+json,{%22name%22:%22Vardast%22,%22short_name%22:%22Vardast%22,%22description%22:%22A smart assistant for you.%22,%22start_url%22:%22/%22,%22display%22:%22standalone%22,%22background_color%22:%22%230e1117%22,%22theme_color%22:%22%230e1117%22}">
"""
components.html(pwa_html, height=0, width=0)

# ==========================================
# ۱. تنظیمات ظاهری پیشرفته (CSS)
# ==========================================
st.set_page_config(page_title="Vardast | ور دست", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&family=Vazirmatn:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Poppins', 'Vazirmatn', sans-serif; }
    .rtl { direction: rtl; text-align: right; }
    
    /* هدر گرادیانتی */
    .header-style {
        background: linear-gradient(135deg, #1E232F 0%, #0E1117 100%);
        padding: 25px; border-radius: 20px; margin-bottom: 25px;
        border: 1px solid rgba(255,255,255,0.05);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }
    
    /* حباب‌های چت */
    [data-testid="stChatMessage"] {
        border-radius: 20px; padding: 20px; margin-bottom: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.03);
        backdrop-filter: blur(10px);
    }
    
    /* دکمه‌های منوی کناری */
    [data-testid="stSidebar"] .stButton > button {
        background: rgba(255, 255, 255, 0.03); color: #e0e0e0;
        border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px;
        transition: all 0.3s ease; backdrop-filter: blur(5px);
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: rgba(255, 255, 255, 0.1); border-color: #4A90E2;
        color: white; transform: translateY(-2px);
    }
    
    /* کادر متن */
    .stTextArea textarea {
        border-radius: 15px !important; padding: 15px !important;
        background-color: rgba(0,0,0,0.2) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: white !important; font-size: 16px !important;
    }
    
    /* دکمه ارسال */
    div.stButton > button[kind="primary"] {
        border-radius: 50px !important;
        background: linear-gradient(90deg, #4A90E2, #8E44AD) !important;
        color: white !important; border: none !important;
        padding: 10px 30px !important; font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(74, 144, 226, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 6px 20px rgba(74, 144, 226, 0.6) !important;
    }
    
    /* دکمه‌های شیشه‌ای آیکونی */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] button {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 50% !important;
        width: 38px !important;
        height: 38px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 16px !important;
        color: #ccc !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] button:hover {
        background: rgba(255, 255, 255, 0.15) !important;
        color: white !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
    }
    
    /* انیمیشن سه نقطه */
    .typing-indicator { display: inline-block; position: relative; width: 40px; height: 20px; }
    .typing-indicator::before, .typing-indicator::after, .typing-indicator span {
        content: ''; position: absolute; top: 50%; width: 6px; height: 6px;
        background-color: #888; border-radius: 50%; transform: translateY(-50%);
        animation: typing 1.4s infinite ease-in-out both;
    }
    .typing-indicator::before { left: 0; animation-delay: -0.32s; }
    .typing-indicator span { left: 12px; animation-delay: -0.16s; }
    .typing-indicator::after { left: 24px; }
    @keyframes typing {
        0%, 80%, 100% { transform: translateY(-50%) scale(0); }
        40% { transform: translateY(-50%) scale(1); }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ۲. ساختار چندزبانه با پرامپت قدرتمند
# ==========================================
LANGUAGES = {
    "English": {
        "title": "Vardast ⚡", "caption": "Your smart, free assistant.",
        "language": "Language", "theme": "Theme", "tone": "Tone",
        "tone_opts": {"Friendly": "Friendly", "Professional": "Professional", "Creative": "Creative", "Direct": "Direct"},
        "new_chat": "➕ New Chat", "chat_list": "History", "clear_chat": "🗑️ Clear Chat",
        "force_fa": "Force Persian Input", "placeholder": "Type your message here...",
        "send_btn": "Send 🚀", "upload_label": "Attach file (Optional)",
        "welcome": "👋 Hello! I am **Vardast**. How can I help you today?",
        "quick_1": "📝 Translate to English", "quick_2": "💡 Explain quantum physics",
        "quick_3": "🎨 Generate a cyberpunk image", "download_chat": "📥 Download Chat",
        # پرامپت جدید و قدرتمند برای پاسخگویی دقیق
        "system_prompt": """You are 'Vardast', a highly intelligent, precise, and helpful AI assistant. 
        Your goal is to provide accurate, detailed, and well-structured answers. 
        Always use Markdown formatting (bolding, lists, code blocks) to make your responses readable.
        If the user asks for an image, reply EXACTLY with 'IMAGE_GEN: [English prompt]'.
        Your tone should be {tone}. Never make up facts; if you don't know, say so.""",
        "creator": "Made with ❤️ by Seyed Mohammad Parsa Hosseini"
    },
    "فارسی": {
        "title": "ور دست ⚡", "caption": "دستیار هوشمند، رایگان و در دسترس همه",
        "language": "زبان", "theme": "تم", "tone": "لحن",
        "tone_opts": {"دوستانه": "دوستانه", "حرفه‌ای": "حرفه‌ای", "خلاقانه": "خلاقانه", "مستقیم": "مستقیم"},
        "new_chat": "➕ چت جدید", "chat_list": "تاریخچه", "clear_chat": "🗑️ پاک کردن",
        "force_fa": "ورودی انگلیسی", "placeholder": "پیام خود را اینجا بنویسید...",
        "send_btn": "ارسال 🚀", "upload_label": "📎 پیوست فایل (اختیاری)",
        "welcome": "👋 سلام! من **ور دست** هستم. چطور می‌تونم امروز کمکت کنم؟",
        "quick_1": "📝 ترجمه به انگلیسی", "quick_2": "💡 توضیح فیزیک کوانتوم",
        "quick_3": "🎨 ساخت عکس سایبرپانک", "download_chat": "📥 دانلود تاریخچه",
        # پرامپت جدید و قدرتمند برای پاسخگویی دقیق
        "system_prompt": """تو 'ور دست' هستی، یک دستیار هوش مصنوعی فوق‌العاده باهوش، دقیق و مفید. 
        هدف تو ارائه پاسخ‌های صحیح، کامل و ساختاریافته است. 
        همیشه از فرمت‌بندی Markdown (مثل بولد کردن، لیست، و کد) برای خوانایی بهتر استفاده کن.
        اگر کاربر ازت خواست عکس بسازی، دقیقاً بنویس 'IMAGE_GEN: [توضیح انگلیسی]'.
        لحن تو باید {tone} باشد. هرگز اطلاعات از خودت نساز؛ اگر چیزی را نمی‌دانی، صادقانه بگو.""",
        "creator": "ساخته شده با ❤️ توسط سید محمد پارسا حسینی"
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
if "input_key_counter" not in st.session_state: st.session_state.input_key_counter = 0

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
        
    if st.session_state.chats[st.session_state.current_chat]:
        chat_text = ""
        for msg in st.session_state.chats[st.session_state.current_chat]:
            role = "شما" if msg["role"] == "user" else "Vardast"
            chat_text += f"{role}:\n{msg['content']}\n\n"
        st.download_button(label=t["download_chat"], data=chat_text, file_name="vardast_chat.txt", mime="text/plain", use_container_width=True)

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
# ۸. نمایش چت (با آیکون جدید کاربر)
# ==========================================
current_messages = st.session_state.chats[st.session_state.current_chat]

if len(current_messages) == 0:
    with st.chat_message("assistant", avatar="⚡"):
        st.markdown(t["welcome"])
    
    st.write("")
    c1, c2, c3 = st.columns(3)
    if c1.button(t["quick_1"], use_container_width=True):
        st.session_state.quick_prompt = "این متن را به انگلیسی ترجمه کن: "
    if c2.button(t["quick_2"], use_container_width=True):
        st.session_state.quick_prompt = "فیزیک کوانتوم را به زبان ساده توضیح بده."
    if c3.button(t["quick_3"], use_container_width=True):
        st.session_state.quick_prompt = "یه عکس از یک شهر سایبرپانک در شب بساز."

for i, message in enumerate(current_messages):
    # تغییر آیکون کاربر به یک آدم معمولی (👤) به جای مرد پشت لپ‌تاپ
    avatar = "👤" if message["role"] == "user" else "⚡"
    
    with st.chat_message(message["role"], avatar=avatar):
        if message["role"] == "assistant" and message["content"].startswith("IMAGE_GEN:"):
            img_prompt = message["content"].replace("IMAGE_GEN:", "").strip()
            encoded_prompt = urllib.parse.quote(img_prompt)
            img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            st.image(img_url, caption=f"Prompt: {img_prompt}")
        else:
            if direction == "rtl": st.markdown(f"<div class='rtl'>{message['content']}</div>", unsafe_allow_html=True)
            else: st.markdown(message["content"])
            
            if message["role"] == "assistant":
                col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 1, 10])
                with col1:
                    if st.button("📋", key=f"copy_{i}"):
                        components.html(f"<script>navigator.clipboard.writeText(`{message['content']}`);</script>", height=0)
                        st.toast("کپی شد! ✅")
                with col2:
                    if st.button("👍", key=f"like_{i}"):
                        st.toast("ممنون از بازخوردت! ❤️")
                with col3:
                    if st.button("👎", key=f"dislike_{i}"):
                        st.toast("متأسفم که راضی نبودی. 😔")
                with col4:
                    if st.button("🔊", key=f"tts_{i}"):
                        try:
                            lang_code = "fa" if direction == "rtl" else "en"
                            tts = gTTS(text=message["content"], lang=lang_code)
                            audio_buffer = io.BytesIO()
                            tts.write_to_fp(audio_buffer)
                            audio_buffer.seek(0)
                            st.audio(audio_buffer, format="audio/mp3")
                        except Exception:
                            st.warning("⚠️ سرویس صوتی موقتاً در دسترس نیست.")
                with col5:
                    if st.button("↗️", key=f"share_{i}"):
                        st.toast("لینک کپی شد! (به زودی)")

# ==========================================
# ۹. کادر ورودی و ارسال
# ==========================================
st.write("")

with st.expander(t["upload_label"], expanded=False):
    uploaded_files = st.file_uploader("", accept_multiple_files=True, type=["jpg", "jpeg", "png", "pdf"], label_visibility="collapsed")

current_input_key = f"input_text_{st.session_state.input_key_counter}"

default_val = ""
if "quick_prompt" in st.session_state:
    default_val = st.session_state.quick_prompt
    del st.session_state.quick_prompt

user_text = st.text_area(t["placeholder"], value=default_val, height=100, key=current_input_key, label_visibility="collapsed")

send_clicked = st.button(t["send_btn"], type="primary", use_container_width=True)

if send_clicked:
    if user_text.strip() or uploaded_files:
        st.session_state.pending_text = user_text
        st.session_state.pending_files = uploaded_files
        st.session_state.input_key_counter += 1
        st.rerun()

if "pending_text" in st.session_state and st.session_state.pending_text:
    text_to_process = st.session_state.pending_text
    files_to_process = st.session_state.pending_files if "pending_files" in st.session_state else []
    
    del st.session_state.pending_text
    if "pending_files" in st.session_state:
        del st.session_state.pending_files
    
    display_content = text_to_process
    if files_to_process:
        display_content += f"\n[{len(files_to_process)} فایل پیوست شد]"
    
    current_messages.append({"role": "user", "content": display_content})
    
    api_content = [{"type": "text", "text": text_to_process if text_to_process else "این فایل را تحلیل کن."}]
    
    for file in files_to_process:
        if file.type.startswith("image"):
            image_bytes = file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            api_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{file.type};base64,{base64_image}"}
            })
        elif file.type == "application/pdf":
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.getvalue()))
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
                api_content.append({
                    "type": "text",
                    "text": f"متن استخراج شده از فایل PDF:\n{pdf_text[:2000]}..."
                })
            except Exception as e:
                st.error(f"خطا در خواندن PDF: {e}")
    
    sys_prompt = t["system_prompt"].format(tone=tone_value)
    if direction == "rtl":
        sys_prompt += " کاربر به زبان فارسی صحبت می‌کند، لطفاً به فارسی روان پاسخ بده."

    api_messages = [{"role": "system", "content": sys_prompt}]
    for m in current_messages[:-1]:
        api_messages.append({"role": m["role"], "content": m["content"]})
    api_messages.append({"role": "user", "content": api_content})

    try:
        with st.chat_message("assistant", avatar="⚡"):
            st.markdown('<div class="typing-indicator"><span></span></div>', unsafe_allow_html=True)
            
            stream = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=api_messages,
                temperature=1.0,
                stream=True,
                max_tokens=600
            )
            response = st.write_stream(stream)
            current_messages.append({"role": "assistant", "content": response})
            st.rerun()
    except Exception as e:
        st.error(f"⚠️ خطای اتصال: {e}")