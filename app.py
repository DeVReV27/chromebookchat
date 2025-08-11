# app.py
import os, json, time, math, uuid
from typing import List, Dict, Any

import streamlit as st
from openai import OpenAI
from pathlib import Path

from src.chat_utils import render_markdown, format_usage, tool_registry, run_slash_tool
from src.presets import SYSTEM_PRESETS, ROLE_PROFILES

# ----------------------------
# Config / client
# ----------------------------
OPENAI_API_KEY = None
try:
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
except:
    pass
OPENAI_API_KEY = OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Avatar paths
USER_AVATAR = "assets/user.png"
BOT_AVATAR = "assets/bot.png"

st.set_page_config(
    page_title="GPT-5 Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load CSS
css_path = Path("src/ui.css")
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ----------------------------
# Session bootstrap
# ----------------------------
def new_chat(name: str = "New chat") -> Dict[str, Any]:
    return {
        "id": uuid.uuid4().hex[:8],
        "name": name,
        "messages": [],       # [{role, content}]
        "usage": [],          # usage snapshots
        "system": SYSTEM_PRESETS["Balanced"],
        "role_profile": "General",
    }

if "chats" not in st.session_state:
    st.session_state.chats: List[Dict[str, Any]] = [new_chat("Welcome")]
if "active_chat" not in st.session_state:
    st.session_state.active_chat = st.session_state.chats[0]["id"]

def get_chat(cid: str) -> Dict[str, Any]:
    for c in st.session_state.chats:
        if c["id"] == cid:
            return c
    # fallback
    st.session_state.active_chat = st.session_state.chats[0]["id"]
    return st.session_state.chats[0]

# ----------------------------
# Sidebar controls
# ----------------------------
with st.sidebar:
    # Display logo at top of sidebar
    #logo_path = Path("assets/Chromebook.png")
    #if logo_path.exists():
        #st.image("assets/Chromebook.png", width=500)
        #st.markdown("---")  # Add a separator line
    
    st.markdown("### ⚙️ Settings")
    model = st.selectbox("Model", ["gpt-5", "gpt-5-mini"], index=0)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.5, 0.05)
    max_output_tokens = st.slider("Max output tokens", 256, 8192, 2048, 128)
    verbosity = st.selectbox("Verbosity", ["low", "medium", "high"], index=1)
    reasoning_effort = st.selectbox("Reasoning effort", ["minimal", "medium", "high"], index=1)

    st.markdown("### 🧩 Role & System")
    role_name = st.selectbox("Role profile", list(ROLE_PROFILES.keys()))
    sys_preset = st.selectbox("System preset", list(SYSTEM_PRESETS.keys()))
    sys_custom = st.text_area("System instructions (editable)", height=160, value=SYSTEM_PRESETS[sys_preset])

    # apply role+system to active chat
    chat = get_chat(st.session_state.active_chat)
    chat["system"] = sys_custom
    chat["role_profile"] = role_name

    st.markdown("### 🛠 Tools")
    tools_enabled = st.toggle("Enable tool calling", value=True, help="Allow the model to call tools; will fallback to slash-tools like /calc, /time.")

    st.markdown('<div class="export-clear-buttons">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬇️ Export active chat", use_container_width=True):
            # Convert usage objects to dictionaries for JSON serialization
            usage_dicts = []
            for usage in chat["usage"]:
                if hasattr(usage, 'total_tokens'):
                    # OpenAI CompletionUsage object
                    usage_dicts.append({
                        "total_tokens": usage.total_tokens,
                        "prompt_tokens": usage.prompt_tokens,
                        "completion_tokens": usage.completion_tokens
                    })
                else:
                    # Already a dictionary
                    usage_dicts.append(usage)
            
            export = {
                "id": chat["id"],
                "name": chat["name"],
                "messages": chat["messages"],
                "usage": usage_dicts,
                "system": chat["system"],
                "role_profile": chat["role_profile"]
            }
            st.download_button(
                "Download JSON",
                data=json.dumps(export, indent=2),
                file_name=f"chat_{chat['name'].replace(' ','_')}.json",
                mime="application/json",
                use_container_width=True,
            )
    with col2:
        if st.button("🧹 Clear messages", use_container_width=True):
            chat["messages"].clear()
            chat["usage"].clear()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------------------
# Hero header (restored to original)
# ----------------------------
st.markdown("""
<div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; margin-bottom: 1rem;">
    <h1 style="color: white; font-size: 2.5rem; margin: 0;">🤖 Chromebook LLM Chat</h1>
    <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0;">Powered by Science & Magic.</p>
</div>
""", unsafe_allow_html=True)

# ----------------------------
# Multi-chat tabs (CRUD)
# ----------------------------
tab_labels = [c["name"] for c in st.session_state.chats] + ["＋"]
tabs = st.tabs(tab_labels)

# Render each chat tab; last tab is "add new"
for i, t in enumerate(tabs):
    with t:
        if i == len(st.session_state.chats):  # add new
            st.write("Create a new chat.")
            new_name = st.text_input("Chat name", value=f"Chat {len(st.session_state.chats)+1}")
            if st.button("Create chat", type="primary"):
                c = new_chat(new_name)
                st.session_state.chats.append(c)
                st.session_state.active_chat = c["id"]
                st.rerun()
        else:
            c = st.session_state.chats[i]
            # mark active when clicked
            if c["id"] != st.session_state.active_chat and st.button("Activate this chat", key=f"act_{c['id']}", use_container_width=True):
                st.session_state.active_chat = c["id"]
                st.rerun()
            # rename/delete
            with st.expander("Chat settings", expanded=False):
                new_title = st.text_input("Rename", value=c["name"], key=f"rename_{c['id']}")
                if new_title != c["name"]:
                    c["name"] = new_title
                colA, colB = st.columns(2)
                with colA:
                    st.caption(f"Chat ID: `{c['id']}`")
                with colB:
                    if st.button("🗑 Delete", key=f"del_{c['id']}"):
                        st.session_state.chats = [x for x in st.session_state.chats if x["id"] != c["id"]]
                        if not st.session_state.chats:
                            st.session_state.chats = [new_chat("New")]
                        st.session_state.active_chat = st.session_state.chats[0]["id"]
                        st.rerun()

# Work with active chat only below
chat = get_chat(st.session_state.active_chat)

# Role hint banner
st.markdown(
    f"""<div class="role-hint">🧩 Role: <b>{chat['role_profile']}</b></div>""",
    unsafe_allow_html=True,
)

# Render history
for msg in chat["messages"]:
    avatar = BOT_AVATAR if msg["role"] == "assistant" else USER_AVATAR
    with st.chat_message(msg["role"], avatar=avatar):
        render_markdown(msg["content"])

# ----------------------------
# Tool definitions for OpenAI function calling
# ----------------------------
def openai_tools():
    # Minimal set; extensible
    return [
        {
            "type": "function",
            "function": {
                "name": "get_current_time",
                "description": "Get the current time in ISO 8601 format.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Safely evaluate a basic math expression.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Math expression, e.g. 2*(3+4)/5"}
                    },
                    "required": ["expression"]
                }
            }
        }
    ]

def exec_tool(name: str, args: Dict[str, Any]) -> str:
    if name == "get_current_time":
        import datetime as _dt
        return _dt.datetime.now().isoformat()
    if name == "calculator":
        expr = args.get("expression","")
        try:
            # safe tiny eval: numbers and operators only
            if not all(ch in "0123456789.+-*/()% " for ch in expr):
                raise ValueError("Invalid characters")
            return str(eval(expr))
        except Exception as e:
            return f"Error: {e}"
    return "Unsupported tool"

# ----------------------------
# Chat input / send
# ----------------------------
user_text = st.chat_input("Type your message here…")
if user_text:
    # Push user message
    chat["messages"].append({"role": "user", "content": user_text})
    with st.chat_message("user", avatar=USER_AVATAR):
        render_markdown(user_text)

    # Slash-tool fallback (fast path)
    if run_slash_tool(user_text, chat):
        st.rerun()

    # Build conversation
    base_messages = []
    if chat["system"].strip():
        base_messages.append({"role": "system", "content": chat["system"]})
    # Role priming
    role_text = ROLE_PROFILES.get(chat["role_profile"], "")
    if role_text:
        base_messages.append({"role": "system", "content": role_text})
    base_messages += chat["messages"]

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        placeholder = st.empty()
        stream_text = ""
        usage_snapshot = None

        try:
            if not client:
                stream_text = "⚠️ No OpenAI API key configured. Please set OPENAI_API_KEY environment variable or add it to .streamlit/secrets.toml"
                placeholder.markdown(stream_text)
                chat["messages"].append({"role": "assistant", "content": stream_text})
            else:
                # Use correct OpenAI API syntax
                tools = openai_tools() if tools_enabled else None
                
                # First try with tools if enabled
                # Map gpt-5 models to actual OpenAI models
                actual_model = model.replace("gpt-5-mini", "gpt-4o-mini").replace("gpt-5", "gpt-4o")
                completion = client.chat.completions.create(
                    model=actual_model,
                    messages=base_messages,
                    temperature=temperature,
                    max_tokens=max_output_tokens,
                    tools=tools if tools else None,
                    tool_choice="auto" if tools else None,
                    stream=False
                )

                # Extract response content
                message = completion.choices[0].message
                stream_text = message.content or ""
                
                # Handle tool calls if present
                if message.tool_calls:
                    tool_messages = []
                    for tool_call in message.tool_calls:
                        result = exec_tool(tool_call.function.name, 
                                         json.loads(tool_call.function.arguments) if tool_call.function.arguments else {})
                        tool_messages.append({
                            "role": "tool",
                            "content": result,
                            "tool_call_id": tool_call.id
                        })
                    
                    # Second call with tool results
                    second_completion = client.chat.completions.create(
                        model=actual_model,
                        messages=base_messages + [message] + tool_messages,
                        temperature=temperature,
                        max_tokens=max_output_tokens,
                        stream=False
                    )
                    stream_text = second_completion.choices[0].message.content or ""
                    usage_snapshot = second_completion.usage
                else:
                    usage_snapshot = completion.usage

                if not stream_text:
                    stream_text = "_(No content returned.)_"

                placeholder.markdown(stream_text)
                chat["messages"].append({"role": "assistant", "content": stream_text})
                if usage_snapshot:
                    chat["usage"].append(usage_snapshot)
                    st.caption(format_usage(usage_snapshot))

        except Exception as e:
            st.error(f"Request failed: {e}")
