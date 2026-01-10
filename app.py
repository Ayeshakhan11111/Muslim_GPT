import streamlit as st
from google import genai
from google.genai import types
from tinydb import TinyDB, Query
from dotenv import load_dotenv # NEW: Required for VS Code
import os, uuid

# 1. LOAD LOCAL KEYS (Only used for VS Code)
load_dotenv() 

# 2. SETUP & DATABASE
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except Exception:
    # This now works because load_dotenv() is called above
    api_key = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)
MODEL_ID = "gemini-2.0-flash-lite" 

# FIXED: Use /tmp/ on Linux (Cloud) but local path on Windows (VS Code)
db_path = '/tmp/chat_db.json' if os.name != 'nt' else 'chat_db.json'
db = TinyDB(db_path)
Chat = Query()

st.set_page_config(page_title="MuslimGPT", page_icon="🌙", layout="wide")

# 3. SESSION STATE
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. SIDEBAR
with st.sidebar:
    st.markdown("<h2 style='text-align:center; font-size:22px;'>MuslimGPT</h2>", unsafe_allow_html=True)
    if st.button("New Chat", use_container_width=True):
        st.session_state.chat_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    search_query = st.text_input("", placeholder="Search chats...")
    all_chats = db.all()
    unique_sessions = {}
    for entry in all_chats:
        if entry.get('chat_id') not in unique_sessions:
            unique_sessions[entry['chat_id']] = entry.get('title', 'New Chat')

    filtered_sessions = {
        c_id: title for c_id, title in unique_sessions.items()
        if search_query.lower() in title.lower()
    } if search_query else unique_sessions

    for c_id, title in reversed(list(filtered_sessions.items())):
        cols = st.columns([5, 1])
        with cols[0]:
            if st.button(f"{title[:30]}...", key=c_id, use_container_width=True):
                st.session_state.chat_id = c_id
                st.session_state.messages = [m for m in all_chats if m['chat_id'] == c_id]
                st.rerun()
        with cols[1]:
            if st.button("✕", key=f"del_{c_id}"):
                db.remove(Chat.chat_id == c_id)
                st.rerun()

# 5. THEME & CSS
st.markdown("""
<style>
.stApp { background-color: #0f1115 !important; color: #e3e3e3 !important; }
[data-testid="stSidebar"] { background: #131314 !important; border-right: 1px solid #2c2d2f; }
</style>
""", unsafe_allow_html=True)

# 6. CHAT LOGIC
st.markdown("<h1 style='text-align:center;'>Ask MuslimGPT</h1>", unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask an Islamic question..."):
    is_new_chat = len(st.session_state.messages) == 0
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    history_for_api = []
    for m in st.session_state.messages:
        role = "model" if m["role"] == "assistant" else "user"
        history_for_api.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))

    with st.chat_message("assistant"):
        try:
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=history_for_api,
                config=types.GenerateContentConfig(
                    system_instruction="You are MuslimGPT. Answer concisely. Use Sahih sources."
                )
            )
            full_response = response.text
            st.markdown(full_response)
            
            chat_title = prompt if is_new_chat else st.session_state.messages[0]['content']
            db.insert({'chat_id': st.session_state.chat_id, 'title': chat_title, 'role': 'user', 'content': prompt})
            db.insert({'chat_id': st.session_state.chat_id, 'title': chat_title, 'role': 'assistant', 'content': full_response})
            st.session_state.messages.append({"role": "assistant", "content": full_response})
        except Exception as e:
            st.error(f"Error: {e}")