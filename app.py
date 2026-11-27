import os
from datetime import datetime

import streamlit as st
from openai import OpenAI
from supabase import create_client, Client

st.set_page_config(page_title="وردست | دستیار هوشمند", page_icon="🤖", layout="wide")

# ---------- Configuration ----------
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("تنظیمات Supabase کامل نیست. در Render متغیرهای SUPABASE_URL و SUPABASE_ANON_KEY را بررسی کن.")
    st.stop()
if not GROQ_API_KEY:
    st.error("کلید Groq پیدا نشد. متغیر GROQ_API_KEY را در Render بررسی کن.")
    st.stop()

if "supabase_client" not in st.session_state:
    st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
supabase = st.session_state.supabase_client
llm = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")

# ---------- Session state ----------
def init_state():
    defaults = {
        "user": None,
        "access_token": None,
        "conversation_id": None,
        "messages": [],
        "chat_list": [],
        "language": "فارسی",
        "tone": "دوستانه و روشن",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

# ---------- Helpers ----------
def auth_headers():
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def load_conversations():
    uid = st.session_state.user.id
    result = (supabase.table("conversations")
              .select("id,title,created_at")
              .eq("user_id", uid)
              .order("created_at", desc=True)
              .execute())
    st.session_state.chat_list = result.data or []


def load_messages(conversation_id):
    uid = st.session_state.user.id
    result = (supabase.table("messages")
              .select("id,role,content,created_at")
              .eq("user_id", uid)
              .eq("conversation_id", conversation_id)
              .order("created_at")
              .execute())
    st.session_state.messages = result.data or []
    st.session_state.conversation_id = conversation_id


def new_conversation(first_text="گفتگوی جدید"):
    uid = st.session_state.user.id
    title = first_text.strip().replace("\n", " ")[:40] if first_text else "گفتگوی جدید"
    result = (supabase.table("conversations")
              .insert({"user_id": uid, "title": title or "گفتگوی جدید"})
              .execute())
    conversation = result.data[0]
    st.session_state.conversation_id = conversation["id"]
    st.session_state.messages = []
    load_conversations()
    return conversation["id"]


def save_message(role, content):
    uid = st.session_state.user.id
    supabase.table("messages").insert({
        "conversation_id": st.session_state.conversation_id,
        "user_id": uid,
        "role": role,
        "content": content,
    }).execute()


def ask_groq(history, user_text):
    system_prompt = (
        "تو وردست، یک دستیار هوشمند مفید و دقیق هستی. "
        f"زبان پاسخ: {st.session_state.language}. "
        f"لحن پاسخ: {st.session_state.tone}. "
        "اگر پاسخ را نمی‌دانی، صادقانه بگو و اطلاعات ساختگی نساز. "
        "پاسخ‌ها را روشن، منظم و متناسب با سن و سطح کاربر بنویس."
    )
    messages = [{"role": "system", "content": system_prompt}]
    for item in history[-20:]:
        role = item.get("role")
        content = item.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_text})
    response = llm.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=0.6,
    )
    return response.choices[0].message.content or "پاسخی دریافت نشد."

# ---------- Authentication ----------
def auth_screen():
    st.title("🤖 وردست")
    st.caption("دستیار هوشمند شما")
    tab_login, tab_signup = st.tabs(["ورود", "ساخت حساب"])

    with tab_login:
        with st.form("login_form"):
            email = st.text_input("ایمیل", key="login_email")
            password = st.text_input("رمز عبور", type="password", key="login_password")
            submitted = st.form_submit_button("ورود", use_container_width=True)
        if submitted:
            try:
                result = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = result.user
                st.session_state.access_token = result.session.access_token if result.session else None
                st.session_state.messages = []
                st.session_state.conversation_id = None
                st.rerun()
            except Exception as exc:
                st.error(f"ورود انجام نشد: {exc}")

    with tab_signup:
        with st.form("signup_form"):
            name = st.text_input("نام نمایشی")
            email = st.text_input("ایمیل", key="signup_email")
            password = st.text_input("رمز عبور (حداقل ۶ کاراکتر)", type="password", key="signup_password")
            submitted = st.form_submit_button("ساخت حساب", use_container_width=True)
        if submitted:
            if len(password) < 6:
                st.warning("رمز عبور باید حداقل ۶ کاراکتر باشد.")
            else:
                try:
                    result = supabase.auth.sign_up({
                        "email": email,
                        "password": password,
                        "options": {"data": {"display_name": name}},
                    })
                    if result.session:
                        st.session_state.user = result.user
                        st.session_state.access_token = result.session.access_token
                        st.rerun()
                    else:
                        st.success("حساب ساخته شد. اگر تأیید ایمیل فعال است، ایمیلت را تأیید کن و سپس وارد شو.")
                except Exception as exc:
                    st.error(f"ساخت حساب انجام نشد: {exc}")

# ---------- Main app ----------
if not st.session_state.user:
    auth_screen()
    st.stop()

try:
    load_conversations()
except Exception as exc:
    st.error("ارتباط با جدول‌های Supabase برقرار نشد. تنظیمات دیتابیس و سیاست‌های RLS را بررسی کن.")
    st.code(str(exc))
    st.stop()

with st.sidebar:
    st.title("🤖 وردست")
    st.caption(f"حساب: {st.session_state.user.email}")
    st.divider()
    st.subheader("تنظیمات پاسخ")
    st.session_state.language = st.selectbox("زبان", ["فارسی", "English"], index=0 if st.session_state.language == "فارسی" else 1)
    st.session_state.tone = st.selectbox("لحن", ["دوستانه و روشن", "رسمی", "آموزشی و مرحله‌به‌مرحله", "خلاصه"], index=["دوستانه و روشن", "رسمی", "آموزشی و مرحله‌به‌مرحله", "خلاصه"].index(st.session_state.tone))
    st.divider()
    if st.button("＋ گفتگوی جدید", use_container_width=True):
        st.session_state.conversation_id = None
        st.session_state.messages = []
        st.rerun()
    st.subheader("گفتگوهای قبلی")
    for chat in st.session_state.chat_list:
        label = (chat.get("title") or "گفتگوی جدید")[:32]
        if st.button(label, key=f"chat_{chat['id']}", use_container_width=True):
            try:
                load_messages(chat["id"])
                st.rerun()
            except Exception as exc:
                st.error(f"باز کردن گفتگو ناموفق بود: {exc}")
    st.divider()
    if st.button("خروج از حساب", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        for key in ["user", "access_token", "conversation_id", "messages", "chat_list"]:
            st.session_state[key] = None if key in ["user", "access_token", "conversation_id"] else []
        st.rerun()

st.title("سلام! من وردست هستم 👋")
st.caption("سؤالت رو بنویس تا با هم بررسی کنیم.")

# Display conversation
for message in st.session_state.messages:
    with st.chat_message(message.get("role", "assistant")):
        st.markdown(message.get("content", ""))

prompt = st.chat_input("پیامت رو اینجا بنویس...")
if prompt:
    try:
        if not st.session_state.conversation_id:
            new_conversation(prompt)
        user_message = {"role": "user", "content": prompt}
        st.session_state.messages.append(user_message)
        save_message("user", prompt)
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("وردست در حال فکر کردن است..."):
                answer = ask_groq(st.session_state.messages[:-1], prompt)
                st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        save_message("assistant", answer)
        load_conversations()
    except Exception as exc:
        st.error(f"مشکلی پیش آمد: {exc}")

st.divider()
st.caption("ساخته‌شده توسط سید محمد پارسا حسینی")
