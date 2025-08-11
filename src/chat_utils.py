# src/chat_utils.py
import re, json, time
import streamlit as st

def render_markdown(text: str) -> None:
    st.markdown(text, unsafe_allow_html=False)

def format_usage(usage) -> str:
    """Format usage from OpenAI CompletionUsage object or dict"""
    if hasattr(usage, 'total_tokens'):
        # OpenAI CompletionUsage object
        total = usage.total_tokens
        input_tok = usage.prompt_tokens
        output_tok = usage.completion_tokens
    else:
        # Dictionary fallback
        total = usage.get("total_tokens") or usage.get("total")
        input_tok = usage.get("input_tokens") or usage.get("prompt_tokens")
        output_tok = usage.get("output_tokens") or usage.get("completion_tokens")
    
    parts = []
    if input_tok is not None: parts.append(f"in: {input_tok}")
    if output_tok is not None: parts.append(f"out: {output_tok}")
    if total is not None: parts.append(f"total: {total}")
    return " / ".join(parts)

# ---- Slash-tool fallback ----------------------------------------------------

def tool_registry():
    return {
        "/time": {"hint": "Show the current time."},
        "/calc": {"hint": "Calculate an expression. Usage: /calc 2*(3+4)"},
    }

def run_slash_tool(user_text: str, chat) -> bool:
    """Return True if handled locally, appending assistant result."""
    text = user_text.strip()
    if text.startswith("/time"):
        import datetime as dt
        ans = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chat["messages"].append({"role": "assistant", "content": f"Current time: **{ans}**"})
        return True
    if text.startswith("/calc"):
        expr = text.replace("/calc", "", 1).strip()
        try:
            if not expr:
                raise ValueError("Provide an expression, e.g. /calc 2*(3+4)")
            if not all(ch in "0123456789.+-*/()% " for ch in expr):
                raise ValueError("Invalid characters")
            val = eval(expr)
            chat["messages"].append({"role": "assistant", "content": f"`{expr}` = **{val}**"})
            return True
        except Exception as e:
            chat["messages"].append({"role": "assistant", "content": f"Calc error: {e}"})
            return True
    return False
