import streamlit as st
import os

# --- NEW SERVICE IMPORT ---
from ..core.brain_service import Brain
from ..core.conversation_context import ConversationContext

# --- OTHER IMPORTS ---
from ..core.generate import answer_question, check_ollama_health, generate_search_queries
from ..data.load_data import load_documents
from ..data.split_text import split_docs
from ..storage.chat_store import (
    init_db, create_session, save_message,
    load_session_messages, get_all_sessions, delete_session, rename_session
)

# --- DB INIT ---
init_db()

# --- UI CONFIG ---
st.set_page_config(page_title="Gremlin RAG", page_icon="🦖", layout="centered")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(180deg, #0E1117 0%, #161B22 100%); }
    [data-testid="stChatMessage"] { border-radius: 15px; margin-bottom: 10px; border: 1px solid #30363D; }
    .st-emotion-cache-1c7n2ka { max-width: 800px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🦖 Corporate Brain v1.0")
st.caption("Local • Secure • Air-gapped AI Assistant")

# --- OLLAMA HEALTH CHECK ---
if "ollama_healthy" not in st.session_state:
    is_healthy, health_msg = check_ollama_health()
    st.session_state.ollama_healthy = is_healthy
    if not is_healthy:
        st.error(f"🔴 Ollama Issue: {health_msg}")
        st.stop()

# --- INITIALIZE BRAIN ---
if 'brain' not in st.session_state:
    # Instantiate our new Service!
    st.session_state.brain = Brain()
    
    with st.spinner("Waking up the brain..."):
        if st.session_state.brain.is_built():
            try:
                st.session_state.brain.load()
                st.success("Brain Connected! (FAISS + BM25)")
            except Exception as e:
                st.error(f"Failed to load brain: {e}\nTry clicking 'Sync Brain' in the sidebar.")
                st.stop()
        else:
            st.warning("No brain found. Upload documents and click 'Sync Brain' in the sidebar.")

# --- SESSION STATE DEFAULTS ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "renaming_id" not in st.session_state:
    st.session_state.renaming_id = None

# --- SIDEBAR ---
with st.sidebar:
    st.title("🦖 Settings")

    if st.session_state.get("ollama_healthy"):
        st.success("🟢 Ollama Connected")
    else:
        st.error("🔴 Ollama Offline")

    st.divider()

    # --- NEW CHAT ---
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.session_state.renaming_id = None
        st.rerun()

    st.divider()

    # --- DOCUMENT UPLOAD ---
    st.subheader("📂 Documents")
    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "txt", "md", "docx", "pptx", "xlsx", "csv"],
        accept_multiple_files=True,
        label_visibility="collapsed"
    )
    if uploaded_files:
        os.makedirs("data", exist_ok=True)
        saved = []
        for file in uploaded_files:
            save_path = os.path.join("data", file.name)
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
            saved.append(file.name)
        st.success(f"Saved: {', '.join(saved)}\nClick 'Sync Brain' to reindex.")

    # --- DOCUMENT MANAGER ---
    if os.path.exists("data") and os.listdir("data"):
        with st.expander("📋 Manage Documents"):
            files = sorted(os.listdir("data"))
            for filename in files:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.text(filename)
                with col2:
                    if st.button("🗑️", key=f"delfile_{filename}"):
                        os.remove(os.path.join("data", filename))
                        st.warning(f"Deleted {filename}. Click 'Sync Brain' to reindex.")
                        st.rerun()

    # --- BUILD BRAIN BUTTON ---
    if st.button("🔄 Sync Brain", use_container_width=True):
        if not os.path.exists("data") or not os.listdir("data"):
            st.error("No documents found in the data folder!")
        else:
            with st.spinner("Syncing brain... this might take a moment if you have new files!"):
                try:
                    # Look at this! No more manual loading/splitting here.
                    # The brain handles it all internally now.
                    st.session_state.brain.sync_indices()
                    
                    st.success("Brain synced successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Sync failed: {e}")

    st.divider()
    # Nuke & Rebuild Button
    if st.button("☢️ Nuke & Rebuild", use_container_width=True, type="secondary"):
        with st.spinner("Wiping old indices and building fresh from scratch..."):
            try:
                # No argument needed anymore! It will load the docs itself.
                st.session_state.brain.build() 
                st.success("Brain rebuilt from zero!")
                st.rerun()
            except Exception as e:
                st.error(f"Rebuild failed: {e}")
    # --- PAST CHATS ---
    sessions = get_all_sessions()
    if sessions:
        st.caption("Past Chats")
        for s in sessions:
            if st.session_state.renaming_id == s["id"]:
                new_title = st.text_input(
                    "Rename", value=s["title"], key=f"rename_input_{s['id']}", label_visibility="collapsed"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Save", key=f"save_rename_{s['id']}", use_container_width=True):
                        rename_session(s["id"], new_title)
                        st.session_state.renaming_id = None
                        st.rerun()
                with col2:
                    if st.button("❌ Cancel", key=f"cancel_rename_{s['id']}", use_container_width=True):
                        st.session_state.renaming_id = None
                        st.rerun()
            else:
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    if st.button(s["title"], key=f"load_{s['id']}", use_container_width=True):
                        st.session_state.session_id = s["id"]
                        st.session_state.messages = load_session_messages(s["id"])
                        st.session_state.renaming_id = None
                        st.rerun()
                with col2:
                    if st.button("✏️", key=f"rename_{s['id']}"):
                        st.session_state.renaming_id = s["id"]
                        st.rerun()
                with col3:
                    if st.button("🗑️", key=f"del_{s['id']}"):
                        delete_session(s["id"])
                        if st.session_state.session_id == s["id"]:
                            st.session_state.messages = []
                            st.session_state.session_id = None
                        st.rerun()
    else:
        st.caption("No past chats yet.")

    st.divider()

    if st.session_state.messages:
        chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
        st.download_button(label="📥 Export Chat", data=chat_text, file_name="chat_export.txt", mime="text/plain", use_container_width=True)

    st.info("Powered by Llama 3.1 8B + nomic-embed-text")

# --- MAIN CHAT AREA ---
if not st.session_state.messages:
    with st.chat_message("assistant"):
        st.markdown("Hello! I'm your Corporate Brain. I've loaded your documents and I'm ready to help. What's on your mind? (✧ω✧)")

for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- USER INPUT & AI RESPONSE ---
if prompt := st.chat_input("Ask me anything about the documents..."):

    if not st.session_state.brain.is_built():
        st.warning("Please upload documents and click 'Sync Brain' first!")
        st.stop()

    if st.session_state.session_id is None:
        st.session_state.session_id = create_session(prompt)

    save_message(st.session_state.session_id, "user", prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("🦖 Searching & Thinking...", expanded=False) as status:
            session_context = ConversationContext(st.session_state.session_id)
            enhanced_query, ctx_type = session_context.generate_context_aware_query(prompt)
            session_summary = session_context.get_summary_for_context_window(max_chars=400)

            st.write("Refining search query...")
            if ctx_type != "standalone":
                status.write(f"Detected conversation follow-up: {ctx_type}.")
            if session_summary:
                status.write("Applying recent session summary to search.")
                enhanced_query = f"{enhanced_query}. Recent context: {session_summary}"

            rewritten_query, query_variations = generate_search_queries(enhanced_query)

            st.write("Checking the library...")
            
            # THE MAGIC HAPPENS HERE: We just ask the Brain!
            docs, low_confidence, confidence_pct = st.session_state.brain.search(
                rewritten_query,
                extra_queries=query_variations
            )

            st.write("Consulting the Llama...")
            # --- FIXED: Removed history argument ---
            response_gen, sources = answer_question(
                prompt,
                docs,
                stream=True
            )
            status.update(label="I've got an answer!", state="complete", expanded=False)

        response = st.write_stream(response_gen)

        with st.expander("📄 Sources & Confidence"):
            if confidence_pct >= 70:
                conf_label, conf_color = "🟢 High", "green"
            elif confidence_pct >= 40:
                conf_label, conf_color = "🟡 Medium", "orange"
            else:
                conf_label, conf_color = "🔴 Low", "red"

            st.markdown(f"**Retrieval confidence:** :{conf_color}[{conf_label} — {confidence_pct}%]")
            st.progress(float(confidence_pct) / 100)
            if confidence_pct < 40:
                st.caption("⚠️ The documents may not cover this topic well. The answer above is the best available match.")

            # In app.py
            if sources:
                st.divider()
                st.markdown("### 📚 References")
                for s in sources:
                    # Check if it has our page format
                    if "(Page" in s:
                        st.write(f"• 📄 {s}")
                    else:
                        st.write(f"• 📄 {s}")

    save_message(st.session_state.session_id, "assistant", response)
    st.session_state.messages.append({"role": "assistant", "content": response})