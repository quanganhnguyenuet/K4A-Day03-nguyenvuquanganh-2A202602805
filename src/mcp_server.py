"""
🔌 MODEL CONTEXT PROTOCOL (MCP) SERVER MODULE
Mô phỏng kiến trúc MCP Server (Client-Server Architecture) cung cấp công cụ chuẩn hóa.
"""

import json
import sys
from typing import Dict, Any, List
from tools import TOOLS_SCHEMA, dispatch_tool_call

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class MCPFacilitiesServer:
    """
    Giả lập MCP Server quản lý phòng họp và thiết bị theo giao thức MCP.
    """
    def __init__(self, server_name: str = "vinuni-facilities-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"
        
    def list_tools(self) -> List[Dict[str, Any]]:
        """Trả về danh sách các Tools chuẩn giao thức MCP"""
        return TOOLS_SCHEMA
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        [TASK 2.1] HỌC VIÊN HOÀN THIỆN HÀM THỰC THI TOOL TRÊN MCP SERVER
        Thực thi request gọi Tool theo chuẩn MCP JSON-RPC
        """
        raw_result = dispatch_tool_call(tool_name, arguments)
        try:
            content = json.loads(raw_result)
        except (TypeError, json.JSONDecodeError) as exc:
            content = {
                "status": "INVALID_TOOL_RESPONSE",
                "message": "Kết quả Tool Router trả về không phải JSON hợp lệ.",
                "error": str(exc)
            }

        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content
        }


# Giữ tương thích với app.py starter trong khi chuyển đổi tên miền nghiệp vụ.
MCPAcademicServer = MCPFacilitiesServer


if __name__ == "__main__":
    print("==========================================================")
    print("🔌 KIỂM THỬ ĐỘC LẬP MCP SERVER (VINUNI FACILITIES)")
    print("==========================================================")
    
    server = MCPFacilitiesServer()
    tools = server.list_tools()
    print(f"✅ Khởi tạo thành công MCP Server: {server.server_name} (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(tools)}")

    required_tools = {"check_room_availability", "book_meeting_room"}
    published_tools = {tool.get("name") for tool in tools}
    schemas_valid = all(
        tool.get("parameters", {}).get("properties")
        and tool.get("parameters", {}).get("required")
        for tool in tools
        if tool.get("name") in required_tools
    )
    if required_tools.issubset(published_tools) and schemas_valid:
        print("✅ [TASK 1.2]: Hai Facilities Tool Schemas đã được công bố đầy đủ.")
    else:
        missing = sorted(required_tools - published_tools)
        print(f"❌ [TASK 1.2]: Tool Schema thiếu hoặc chưa hợp lệ: {missing}")

    availability_test = server.call_tool("check_room_availability", {
        "start_datetime": "14:00 16/09/2026",
        "end_datetime": "15:00 16/09/2026",
        "room_id": "A201",
        "equipment": ["máy chiếu"]
    })
    availability_result = availability_test.get("result", {})
    if (
        availability_result.get("status") == "SUCCESS"
        and availability_result.get("count", 0) > 0
    ):
        print("✅ [TASK 2.1]: MCP tra cứu phòng A201 thành công.")
    else:
        print(f"❌ [TASK 2.1]: MCP tra cứu phòng thất bại: {json.dumps(availability_test, ensure_ascii=False)}")

    booking_test = server.call_tool("book_meeting_room", {
        "room_id": "C301",
        "start_datetime": "13:00 19/09/2026",
        "end_datetime": "14:00 19/09/2026",
        "purpose": "Kiểm thử MCP Facilities",
        "equipment": ["máy chiếu"]
    })
    booking_result = booking_test.get("result", {})
    if booking_result.get("status") == "SUCCESS" and booking_result.get("booking_id"):
        print(f"✅ [TASK 2.1]: MCP đặt phòng thành công ({booking_result['booking_id']}).")
    else:
        print(f"❌ [TASK 2.1]: MCP đặt phòng thất bại: {json.dumps(booking_test, ensure_ascii=False)}")
