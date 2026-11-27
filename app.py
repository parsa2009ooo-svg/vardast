import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import os
import urllib.parse
import base64
import PyPDF2
import io
import requests

# ==========================================
# ۰. تنظیمات PWA
# ==========================================
pwa_html = """
<link rel="manifest" href="data:application/manifest+json,{%22name%22:%22Vardast%22,%22short_name%22:%22Vardast%22,%22description%22:%22A smart assistant for you.%22,%22start_url%22:%22/%22,%22display%22:%22standalone%22,%22background_color%22:%22%230e1117%22,%22theme_color%22:%22%230e1117%22}">
"""
components.html(pwa_html, height=0, width=0)

# ==========================================
# ۱. تنظیمات ظاهری (با پس‌زمینه تخت جمشید)
# ==========================================
st.set_page_config(page_title="Vardast | ور دست", page_icon="⚡", layout="wide")

# لینک عکس تخت جمشید از ویکی‌مدیا (مطمئن و در دسترس)
PERSIPOLIS_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2c/Persepolis_-_Panorama.jpg/1280px-Persepolis_-_Panorama.jpg"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&family=Vazirmatn:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] {{ font-family: 'Poppins', 'Vazirmatn', sans-serif; }}
    .rtl {{ direction: rtl; text-align: right; }}
    
    /* پس‌زمینه تخت جمشید (مات و تیره) */
    .stApp {{
        background-image: linear-gradient(rgba(14, 17, 23, 0.85), rgba(14, 17, 23, 0.95)), url("{PERSIPOLIS_IMAGE}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    
    /* هدر */
    .header-style {{ background: rgba(30, 35, 47, 0.7); backdrop-filter: blur(15px); padding: 25px; border-radius: 20px; margin-bottom: 25px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5); }}
    
    /* حباب‌های چت */
    [data-testid="stChatMessage"] {{ background: rgba(30, 35, 47, 0.6) !important; backdrop-filter: blur(20px); border-radius: 20px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.08); }}
    
    /* دکمه‌های منوی کناری */
    [data-testid="stSidebar"] .stButton > button {{ background: rgba(255, 255, 255, 0.05); color: #e0e0e0; border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; transition: all 0.3s ease; backdrop-filter: blur(5px); }}
    [data-testid="stSidebar"] .stButton > button:hover {{ background: rgba(255, 255, 255, 0.15); border-color: #4A90E2; color: white; transform: translateY(-2px); }}
    
    /* کادر متن */
    .stTextArea textarea {{ border-radius: 15px !important; padding: 15px !important; background-color: rgba(0,0,0,0.4) !important; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.15) !important; color: white !important; font-size: 16px !important; }}
    
    /* دکمه ارسال */
    div.stButton > button[kind="primary"] {{ border-radius: 50px !important; background: linear-gradient(90deg, #4A90E2, #8E44AD) !important; color: white !important; border: none !important; padding: 10px 30px !important; font-weight: 600 !important; box-shadow: 0 4px 15px rgba(74, 144, 226, 0.4) !important; transition: all 0.3s ease !important; }}
    div.stButton > button[kind="primary"]:hover {{ transform: scale(1.02) !important; box-shadow: 0 6px 20px rgba(74, 144, 226, 0.6) !important; }}
    
    /* === دکمه‌های مینیمال (کپی، لایک، دیس‌لایک، بلندگو) === */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] button {{
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
        width: 40px !important;
        height: 40px !important;
        font-size: 20px !important;
        color: #888 !important;
        transition: all 0.2s ease !important;
    }}
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] button:hover {{
        color: white !important;
        transform: scale(1.1) !important;
    }}
    
    /* انیمیشن سه نقطه */
    .typing-indicator {{ display: inline-block; position: relative; width: 40px; height: 20px; }}
    .typing-indicator::before, .typing-indicator::after, .typing-indicator span {{ content: ''; position: absolute; top: 50%; width: 6px; height: 6px; background-color: #888; border-radius: 50%; transform: translateY(-50%); animation: typing 1.4s infinite ease-in-out both; }}
    .typing-indicator::before {{ left: 0; animation-delay: -0.32s; }}
    .typing-indicator span {{ left: 12px; animation-delay: -0.16s; }}
    .typing-indicator::after {{ left: 24px; }}
    @keyframes typing {{ 0%, 80%, 100% {{ transform: translateY(-50%) scale(0); }} 40% {{ transform: translateY(-50%) scale(1); }} }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ۲. ساختار چندزبانه
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
        "system_prompt": """You are 'Vardast', a highly intelligent AI. 
        Provide detailed, accurate answers using Markdown.
        If asked to generate an image, you MUST reply with EXACTLY this format on a new line: 'IMAGE_GEN: [English prompt]'. Do not add any other text before or after it.
        Tone: {tone}.""",
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
        "system_prompt": """تو 'ور دست' هستی، یک دستیار هوش مصنوعی فوق‌العاده باهوش. 
        پاسخ‌هایت باید دقیق، کامل و با استفاده از Markdown باشد.
        اگر کاربر خواست عکس بسازی، باید دقیقاً در یک خط جداگانه اینطور بنویسی: 'IMAGE_GEN: [توضیح انگلیسی]'. هیچ متن دیگری قبل یا بعد از آن ننویس.
        لحن تو باید {tone} باشد.""",
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
# ۵. منوی کناری (با قابلیت حالت تمرکز)
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
    st.markdown("<style>[data-testid='stChatMessage'] { background-color: rgba(30, 35, 47, 0.7) !important; }</style>", unsafe_allow_html=True)
else:
    st.markdown("<style>.stApp { background-image: linear-gradient(rgba(248, 249, 250, 0.85), rgba(248, 249, 250, 0.95)), url('" + PERSIPOLIS_IMAGE + "') !important; color: #333; } [data-testid='stChatMessage'] { background-color: rgba(255, 255, 255, 0.8) !important; color: #333; }</style>", unsafe_allow_html=True)

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

if len(current_messages) == 0:
    with st.chat_message("assistant", avatar="⚡"):
        st.markdown(t["welcome"])
    
    st.write("")
    c1, c2, c3 = st.columns(3)
    if c1.button(t["quick_1"], use_container_width=True): 
        st.session_state.quick_prompt = "Translate this text to English: "
        st.rerun()
    if c2.button(t["quick_2"], use_container_width=True): 
        st.session_state.quick_prompt = "Explain quantum physics in simple terms."
        st.rerun()
    if c3.button(t["quick_3"], use_container_width=True): 
        st.session_state.quick_prompt = "Generate an image of a cyberpunk city at night."
        st.rerun()

for i, message in enumerate(current_messages):
    avatar = "👤" if message["role"] == "user" else "⚡"
    with st.chat_message(message["role"], avatar=avatar):
        
        content = message["content"]
        if message["role"] == "assistant" and "IMAGE_GEN:" in content:
            parts = content.split("IMAGE_GEN:")
            text_part = parts[0].strip()
            img_prompt = parts[1].strip() if len(parts) > 1 else "random image"
            
            if text_part:
                if direction == "rtl": st.markdown(f"<div class='rtl'>{text_part}</div>", unsafe_allow_html=True)
                else: st.markdown(text_part)
            
            encoded_prompt = urllib.parse.quote(img_prompt)
            img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
            st.image(img_url, caption=f"Prompt: {img_prompt}")
            
        else:
            if direction == "rtl": st.markdown(f"<div class='rtl'>{content}</div>", unsafe_allow_html=True)
            else: st.markdown(content)
            
            if message["role"] == "assistant":
                # دکمه‌های مینیمال (کپی، لایک، دیس‌لایک، بلندگو)
                col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 8])
                with col1:
                    if st.button("📋", key=f"copy_{i}", help="کپی"):
                        components.html(f"<script>navigator.clipboard.writeText(`{content}`);</script>", height=0)
                        st.toast("کپی شد! ✅")
                with col2:
                    if st.button("👍", key=f"like_{i}", help="لایک"):
                        st.toast("ممنون! ❤️")
                with col3:
                    if st.button("👎", key=f"dislike_{i}", help="دیس‌لایک"):
                        st.toast("متأسفم. 😔")
                with col4:
                    if st.button("🔊", key=f"tts_{i}", help="خواندن صوتی"):
                        try:
                            lang_code = "fa" if direction == "rtl" else "en"
                            # استفاده از سرویس Google Translate TTS برای پخش خودکار
                            url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(content[:200])}&tl={lang_code}&client=tw-ob"
                            headers = {'User-Agent': 'Mozilla/5.0'}
                            response = requests.get(url, headers=headers)
                            
                            if response.status_code == 200:
                                audio_buffer = io.BytesIO(response.content)
                                # پخش خودکار صدا با پارامتر autoplay
                                st.audio(audio_buffer, format="audio/mp3", autoplay=True)
                            else:
                                st.warning("⚠️ سرویس صوتی پاسخ نداد.")
                        except Exception as e:
                            st.warning(f"⚠️ خطا در صدا: {e}")

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
    if files_to_process: display_content += f"\n[{len(files_to_process)} فایل پیوست شد]"
    
    current_messages.append({"role": "user", "content": display_content})
    
    api_content = [{"type": "text", "text": text_to_process if text_to_process else "این فایل را تحلیل کن."}]
    
    for file in files_to_process:
        if file.type.startswith("image"):
            image_bytes = file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            api_content.append({"type": "image_url", "image_url": {"url": f"data:{file.type};base64,{base64_image}"}})
        elif file.type == "application/pdf":
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.getvalue()))
                pdf_text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages])
                api_content.append({"type": "text", "text": f"متن استخراج شده از فایل PDF:\n{pdf_text[:2000]}..."})
            except Exception as e:
                st.error(f"خطا در خواندن PDF: {e}")
    
    sys_prompt = t["system_prompt"].format(tone=tone_value)
    if direction == "rtl": sys_prompt += " کاربر به زبان فارسی صحبت می‌کند، لطفاً به فارسی روان پاسخ بده."

    api_messages = [{"role": "system", "content": sys_prompt}]
    for m in current_messages[:-1]: api_messages.append({"role": m["role"], "content": m["content"]})
    api_messages.append({"role": "user", "content": api_content})

    try:
        with st.chat_message("assistant", avatar="⚡"):
            st.markdown('<div class="typing-indicator"><span></span></div>', unsafe_allow_html=True)
            stream = client.chat.completions.create(model="qwen/qwen3.8-27b", messages=api_messages, temperature=1.0, stream=True, max_tokens=600)
            response = st.write_stream(stream)
            current_messages.append({"role": "assistant", "content": response})
            st.rerun()
    except Exception as e:
        st.error(f"⚠️ خطای اتصال: {e}")