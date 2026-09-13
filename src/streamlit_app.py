"""Giao diện Streamlit cho VinUni Facilities ReAct Agent."""

import contextlib
import io
import json
import os
from typing import Any, Dict, List

import streamlit as st

from app import run_react_agent
from mcp_server import MCPFacilitiesServer
from providers import GeminiProvider, MockOfflineProvider, OpenAIProvider


st.set_page_config(
    page_title="VinUni Facilities Agent",
    page_icon="🏫",
    layout="wide"
)


def create_provider(provider_name: str, api_key: str, model_name: str):
    """Tạo provider mà không ghi API key xuống tệp hoặc log."""
    normalized_key = api_key.strip() or None
    normalized_model = model_name.strip() or None
    if provider_name == "OpenAI":
        return OpenAIProvider(api_key=normalized_key, model=normalized_model)
    if provider_name == "Gemini":
        return GeminiProvider(api_key=normalized_key, model=normalized_model)
    return MockOfflineProvider()


def get_final_answer(trace: List[Dict[str, Any]]) -> str:
    """Lấy câu trả lời cuối cùng từ Waterfall Trace."""
    for event in reversed(trace):
        if event.get("action_type") == "FINAL_ANSWER":
            return event.get("output", "Agent không trả về nội dung.")
        if event.get("action_type") in {"AGENT_ERROR", "MAX_ITERATIONS_REACHED"}:
            return event.get("output", "Agent chưa hoàn thành yêu cầu.")
    return "Agent chưa tạo Final Answer."


def render_trace(trace: List[Dict[str, Any]]) -> None:
    """Hiển thị từng bước Thought/Action/Observation của Agent."""
    for event in trace:
        step = event.get("step", "?")
        action_type = event.get("action_type", "UNKNOWN")
        if action_type in {"TOOL_EXECUTION", "ACTION_REJECTED"}:
            st.markdown(f"**Bước {step} · Tool:** `{event.get('tool_name', '')}`")
            st.caption(event.get("thought", ""))
            left, right = st.columns(2)
            with left:
                st.markdown("Arguments")
                st.json(event.get("arguments", {}))
            with right:
                st.markdown("Observation")
                st.json(event.get("observation", {}))
            st.caption(
                f"LLM: {event.get('llm_latency_ms', 0)} ms · "
                f"Tool: {event.get('tool_latency_ms', 0)} ms · "
                f"Tổng: {event.get('latency_ms', 0)} ms"
            )
        else:
            st.markdown(f"**Bước {step} · {action_type}**")
            st.caption(event.get("thought", ""))


if "facilities_server" not in st.session_state:
    st.session_state.facilities_server = MCPFacilitiesServer()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_traces" not in st.session_state:
    st.session_state.session_traces = []


st.title("🏫 VinUni Facilities ReAct Agent")
st.write("Kiểm tra phòng, tìm thiết bị và đặt phòng qua ReAct Agent kết nối MCP Server.")

with st.sidebar:
    st.header("Cấu hình LLM")
    provider_name = st.selectbox("Provider", ["OpenAI", "Gemini", "Mock offline"])
    default_models = {
        "OpenAI": "gpt-4o-mini",
        "Gemini": "gemini-2.5-flash",
        "Mock offline": "Offline-Mock-Model-2026"
    }
    model_name = st.text_input(
        "Model",
        value=default_models[provider_name],
        disabled=provider_name == "Mock offline",
        key=f"model_{provider_name}"
    )

    api_key = ""
    if provider_name != "Mock offline":
        env_name = "OPENAI_API_KEY" if provider_name == "OpenAI" else "GEMINI_API_KEY"
        api_key = st.text_input(
            f"{provider_name} API key",
            type="password",
            help=f"Để trống để dùng {env_name} trong file .env. Key chỉ được giữ trong phiên Streamlit."
        )
        env_value = os.getenv(env_name, "")
        env_ready = bool(env_value and not env_value.startswith("your_"))
        if api_key.strip():
            st.success("Đã nhận API key từ giao diện.")
        elif env_ready:
            st.info(f"Đang dùng {env_name} từ .env.")
        else:
            st.warning("Chưa có API key; request sẽ không thể gọi API thật.")
    else:
        st.info("Mock offline không dùng API key và không tốn token.")

    if st.button("Xóa hội thoại và reset booking", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_traces = []
        st.session_state.facilities_server = MCPFacilitiesServer()
        st.rerun()

    if st.session_state.session_traces:
        st.download_button(
            "Tải trace của phiên",
            data=json.dumps(st.session_state.session_traces, ensure_ascii=False, indent=2),
            file_name="streamlit_trace.json",
            mime="application/json",
            use_container_width=True
        )

    st.caption("API key không được ghi vào trace, source code hoặc trace_waterfall.json.")


for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("trace"):
            with st.expander("Xem Waterfall Trace"):
                render_trace(message["trace"])
        if message.get("console"):
            with st.expander("Xem console log"):
                st.code(message["console"], language="text")


user_query = st.chat_input(
    "Ví dụ: Tìm phòng 10 chỗ có máy chiếu rồi đặt từ 09:00 đến 10:30 ngày 17/09/2026"
)
if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        try:
            provider = create_provider(provider_name, api_key, model_name)
            console_buffer = io.StringIO()
            with st.spinner("Agent đang suy luận và gọi công cụ..."):
                with contextlib.redirect_stdout(console_buffer):
                    trace = run_react_agent(
                        user_query,
                        provider,
                        st.session_state.facilities_server
                    )

            console_output = console_buffer.getvalue()
            answer = get_final_answer(trace)
            st.markdown(answer)
            if "fallback về Mock" in console_output or "chuyển sang Mock" in console_output:
                st.warning("API thật gặp lỗi; request này đã fallback sang Mock Offline Provider.")
            with st.expander("Xem Waterfall Trace"):
                render_trace(trace)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "trace": trace,
                "console": console_output
            })
            st.session_state.session_traces.append({
                "query": user_query,
                "provider": provider_name,
                "model": model_name,
                "trace": trace
            })
        except Exception as exc:
            error_message = f"Không thể chạy Agent: {exc}"
            st.error(error_message)
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message
            })
