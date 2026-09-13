"""
🚀 CORE AGENT APPLICATION (DAY 03: CHATBOT VS REACT AGENT)
Thực thi so sánh giữa Chatbot Baseline (Cấp 2) và ReAct Agent kết nối MCP Server (Cấp 3).
"""

import json
import os
import sys
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from mcp_server import MCPFacilitiesServer
from prompts import (
    CHATBOT_BASELINE_PROMPT,
    REACT_AGENT_SYSTEM_PROMPT,
    MAX_ITERATIONS
)
from providers import get_llm_provider

load_dotenv()

def load_test_cases():
    """Tải danh sách 5 test cases từ config/test_cases.json hoặc config/test_cases.example.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        example_path = os.path.join(base_dir, "config", "test_cases.example.json")
        if os.path.exists(example_path):
            print("⚠️ [CONFIG NOTICE]: Chưa thấy file 'config/test_cases.json'. Đang dùng mẫu 'config/test_cases.example.json'.")
            print("👉 Hãy chạy: copy config/test_cases.example.json config/test_cases.json và viết test cases theo đề tài của bạn!\n")
            config_path = example_path
        else:
            config_path = "test_cases.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_waterfall_trace(trace_data: list):
    """Ghi vết log Waterfall Trace Log ra file docs/trace_waterfall.json"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    trace_path = os.path.join(docs_dir, "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as f:
        json.dump(trace_data, f, ensure_ascii=False, indent=2)
    print(f"📊 [OBSERVABILITY]: Đã lưu {len(trace_data)} sự kiện Waterfall Trace tại '{trace_path}'!")


def run_baseline_chatbot(user_query: str, provider):
    """Chạy Chatbot gốc (Cấp 2) không có công cụ gọi Tool"""
    print(f"\n💬 [CHATBOT BASELINE] Câu hỏi: {user_query}")
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"🤖 Chatbot phản hồi:\n{response}")


def _user_authorized_booking(user_query: str) -> bool:
    """Chỉ cho phép hành động đặt phòng khi người dùng yêu cầu rõ ràng."""
    normalized_query = user_query.casefold()
    booking_phrases = (
        "hãy đặt",
        "đặt giúp",
        "muốn đặt",
        "cần đặt",
        "và đặt phòng",
        "tạo booking",
        "thực hiện booking"
    )
    return any(phrase in normalized_query for phrase in booking_phrases)


def _build_react_context(user_query: str, history: list) -> str:
    """Đóng gói yêu cầu gốc và các Observation để LLM tiếp tục vòng lặp ReAct."""
    if not history:
        return user_query

    context = {
        "original_query": user_query,
        "booking_authorized": _user_authorized_booking(user_query),
        "history": history
    }
    return (
        "Tiếp tục xử lý yêu cầu gốc dựa trên lịch sử Action/Observation bên dưới. "
        "Nếu mục tiêu đã hoàn thành hoặc không thể tiếp tục, hãy trả Final Answer. "
        "Nếu vẫn cần hành động, hãy gọi đúng Tool tiếp theo.\n\n"
        f"REACT_CONTEXT_JSON:\n{json.dumps(context, ensure_ascii=False)}"
    )


def run_react_agent(user_query: str, provider, mcp_server: MCPFacilitiesServer) -> list:
    """
    [REACT AGENT LOOP] Thực thi vòng lặp Thought -> Action -> Observation với MCP Server
    Trả về danh sách trace log của phiên thực thi.
    """
    print(f"\n🤖 [REACT AGENT] Câu hỏi: {user_query}")
    
    step = 0
    trace_logs = []
    react_history = []
    tools_list = mcp_server.list_tools()
    finished = False
    
    while step < MAX_ITERATIONS:
        step += 1
        step_start_time = time.time()
        print(f"\n--- 🔄 Vòng lặp ReAct Loop (Step {step}/{MAX_ITERATIONS}) ---")
        
        # Nạp Observation của các bước trước vào lượt suy luận kế tiếp.
        agent_prompt = _build_react_context(user_query, react_history)
        llm_start_time = time.time()
        llm_response = provider.generate_with_tools(
            agent_prompt,
            tools_list,
            system_prompt=REACT_AGENT_SYSTEM_PROMPT
        )
        llm_latency_ms = round((time.time() - llm_start_time) * 1000, 2)
        
        thought = llm_response.get("thought", "Đang suy luận...")
        print(f"🧠 [Thought]: {thought}")
        
        # Trường hợp 1: LLM quyết định trả lời bằng văn bản trực tiếp
        if llm_response.get("type") == "text":
            final_content = llm_response.get("content", "")
            print(f"🏁 [Final Answer]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "thought": thought,
                "output": final_content,
                "latency_ms": llm_latency_ms
            })
            finished = True
            break
            
        # Trường hợp 2: LLM đề xuất gọi Tool (Action)
        elif llm_response.get("type") == "tool_call":
            tool_name = llm_response.get("tool_name")
            arguments = llm_response.get("arguments", {})
            
            print(f"🛠️ [Action Proposed]: {tool_name}({arguments})")
            
            # Chặn side effect nếu LLM đề xuất đặt phòng ngoài ý định người dùng.
            booking_rejected = (
                tool_name == "book_meeting_room"
                and not _user_authorized_booking(user_query)
            )
            if booking_rejected:
                tool_latency_ms = 0.0
                obs_data = {
                    "status": "ACTION_REJECTED",
                    "message": (
                        "Yêu cầu gốc chỉ cho phép tra cứu; người dùng chưa yêu cầu "
                        "thực hiện đặt phòng."
                    )
                }
            else:
                tool_start_time = time.time()
                mcp_result = mcp_server.call_tool(tool_name, arguments)
                tool_latency_ms = round((time.time() - tool_start_time) * 1000, 2)
                obs_data = mcp_result.get("result", {
                    "status": "MCP_ERROR",
                    "message": mcp_result.get("error", "MCP Server không trả về result.")
                })
            print(f"👁️ [Observation từ MCP Server]: {json.dumps(obs_data, ensure_ascii=False)}")
            
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "ACTION_REJECTED" if booking_rejected else "TOOL_EXECUTION",
                "thought": thought,
                "tool_name": tool_name,
                "arguments": arguments,
                "observation": obs_data,
                "llm_latency_ms": llm_latency_ms,
                "tool_latency_ms": tool_latency_ms,
                "latency_ms": round((time.time() - step_start_time) * 1000, 2)
            })

            react_history.append({
                "step": step,
                "action": {
                    "tool_name": tool_name,
                    "arguments": arguments
                },
                "observation": obs_data
            })

            # Không kết luận tại đây: Observation sẽ được nạp lại cho LLM.
            print("↩️ [ReAct]: Đã nạp Observation, tiếp tục vòng lặp kế tiếp.")
            continue

        else:
            invalid_type = llm_response.get("type")
            final_content = f"LLM trả về kiểu phản hồi không hợp lệ: {invalid_type!r}."
            print(f"⚠️ [Agent Error]: {final_content}")
            trace_logs.append({
                "step": step,
                "query": user_query,
                "action_type": "AGENT_ERROR",
                "thought": thought,
                "output": final_content,
                "latency_ms": llm_latency_ms
            })
            finished = True
            break

    if not finished:
        final_content = f"Agent đã dừng sau {MAX_ITERATIONS} bước mà chưa hoàn thành mục tiêu."
        print(f"⛔ [Max Iterations]: {final_content}")
        trace_logs.append({
            "step": step + 1,
            "query": user_query,
            "action_type": "MAX_ITERATIONS_REACHED",
            "thought": "Dừng an toàn để tránh vòng lặp Tool vô hạn.",
            "output": final_content,
            "latency_ms": 0.0
        })

    return trace_logs


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI AI COURSE - DAY 03 LAB: CHATBOT VS REACT AGENT")
    print("==========================================================")
    
    provider = get_llm_provider()
    mcp_server = MCPFacilitiesServer()
    
    print(f"🔌 LLM Provider: {provider.__class__.__name__}")
    print(f"🌐 MCP Server: {mcp_server.server_name}\n")
    
    tests = load_test_cases()
    print(f"✅ Đã tải thành công {len(tests)} Test Cases thử nghiệm.\n")
    
    if "--interactive" in sys.argv:
        print("🎮 [INTERACTIVE MODE] Trò chuyện trực tiếp với ReAct Agent:")
        print("💡 Gợi ý câu hỏi thử nghiệm:")
        print("   - Câu hỏi chung: 'Quy định hủy hoặc đổi lịch đặt phòng họp là gì?'")
        print("   - Kiểm tra phòng: 'Phòng A201 có trống từ 14:00 đến 15:00 ngày 16/09/2026 không?'")
        print("   - Đặt phòng: 'Đặt phòng A201 cho họp Dự án AI từ 14:00 đến 15:00 ngày 16/09/2026'")
        print("   - Gõ 'exit' hoặc 'quit' để kết thúc phiên trò chuyện.\n")
        while True:
            try:
                user_input = input("👤 Sinh viên hỏi: ").strip()
                if not user_input or user_input.lower() in ["exit", "quit"]:
                    print("👋 Tạm biệt! Kết thúc phiên trò chuyện.")
                    break
                logs = run_react_agent(user_input, provider, mcp_server)
                save_waterfall_trace(logs)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Đã thoát phiên tương tác.")
                break
    elif "--all" in sys.argv:
        print("🚀 [TEST SUITE MODE] Kiểm tra 5 Test Cases:")
        completed_count = 0
        todo_count = 0
        all_traces = []
        
        for tc in tests:
            print(f"\n==================================================")
            print(f"🧪 [{tc['id']}] Loại test: {tc['type']} (Độ phức tạp: {tc['complexity']})")
            print(f"📌 Kỳ vọng: {tc['expected_behavior']}")
            
            if tc["question"].strip().startswith("TODO"):
                print(f"⏸️ [CHƯA KÍCH HOẠT - ĐANG LÀ TODO]:")
                print(f"   {tc['question']}")
                print(f"   👉 Hãy mở file 'config/test_cases.json' để viết câu hỏi thực tế cho Test Case này!")
                todo_count += 1
            else:
                logs = run_react_agent(tc["question"], provider, mcp_server)
                all_traces.extend(logs)
                completed_count += 1
                
        print(f"\n==================================================")
        print(f"📊 [KẾT QUẢ TEST SUITE]: Đã thực thi {completed_count}/{len(tests)} Test Cases | {todo_count} Test Cases đang chờ điền câu hỏi (TODO)")
        if all_traces:
            save_waterfall_trace(all_traces)
        print(f"💡 Để trò chuyện trực tiếp từng câu: Chạy 'python src/app.py --interactive'")
    else:
        # Chế độ mặc định khi chỉ gõ 'python src/app.py'
        print("ℹ️ HƯỚNG DẪN SỬ DỤNG CHƯƠNG TRÌNH:")
        print("  1. Chat trực tiếp liên tục:   python src/app.py --interactive")
        print("  2. Chạy toàn bộ Test Cases:    python src/app.py --all\n")
        
        sample_query = tests[1]["question"]
        print(f"--- 🏁 DEMO CHẠY THỬ 1 TEST CASE MẪU (TC02: Kiểm tra phòng họp) ---")
        logs = run_react_agent(sample_query, provider, mcp_server)
        save_waterfall_trace(logs)
        print("\n💡 Hãy thử ngay lệnh: python src/app.py --interactive để chat trực tiếp!")
