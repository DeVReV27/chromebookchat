import streamlit.components.v1 as components
from pathlib import Path

build_dir = Path(__file__).parent / "frontend" / "dist"
_component = components.declare_component("chat_header", path=str(build_dir))

def chat_header(title: str, subtitle: str = "", gradient: bool = True):
    return _component(title=title, subtitle=subtitle, gradient=gradient, default=None)