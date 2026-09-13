"""
🛠️ TOOL DEFINITIONS & EXECUTION BACKEND
Mã nguồn chứa danh sách Tool Schemas (JSON Schema) và Execution Layer phục vụ cho MCP Server.
"""

import json
from datetime import datetime
from typing import Dict, Any

# ==============================================================================
# 1. KHAI BÁO TOOL SCHEMAS CHUẨN NATIVE JSON SCHEMA (TASK 1.2)
# ==============================================================================

TOOLS_SCHEMA = [
    # Tool 1: Tra cứu phòng họp và thiết bị còn trống
    {
        "name": "check_room_availability",
        "description": "Kiểm tra tình trạng trống của phòng họp và thiết bị trong một khoảng thời gian; có thể lọc theo phòng, sức chứa và thiết bị.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_datetime": {
                    "type": "string",
                    "description": "Thời điểm bắt đầu cần kiểm tra, định dạng 'HH:MM DD/MM/YYYY' (ví dụ: '14:00 16/09/2026')."
                },
                "end_datetime": {
                    "type": "string",
                    "description": "Thời điểm kết thúc cần kiểm tra, định dạng 'HH:MM DD/MM/YYYY' (ví dụ: '15:00 16/09/2026')."
                },
                "room_id": {
                    "type": "string",
                    "description": "Mã phòng cần kiểm tra nếu người dùng chỉ định (ví dụ: 'A201'). Bỏ trống để tìm các phòng phù hợp."
                },
                "min_capacity": {
                    "type": "integer",
                    "description": "Số chỗ ngồi tối thiểu cần có (ví dụ: 10)."
                },
                "equipment": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách thiết bị bắt buộc, ví dụ: ['máy chiếu', 'bảng trắng']."
                }
            },
            "required": ["start_datetime", "end_datetime"]
        }
    },
    
    # Tool 2: Tạo booking phòng họp
    {
        "name": "book_meeting_room",
        "description": "Đặt phòng họp và thiết bị cho một cuộc họp sau khi đã xác nhận phòng còn trống.",
        "parameters": {
            "type": "object",
            "properties": {
                "room_id": {
                    "type": "string",
                    "description": "Mã phòng họp cần đặt (ví dụ: 'A201')."
                },
                "start_datetime": {
                    "type": "string",
                    "description": "Thời điểm bắt đầu cuộc họp, định dạng 'HH:MM DD/MM/YYYY'."
                },
                "end_datetime": {
                    "type": "string",
                    "description": "Thời điểm kết thúc cuộc họp, định dạng 'HH:MM DD/MM/YYYY'."
                },
                "purpose": {
                    "type": "string",
                    "description": "Mục đích hoặc tên cuộc họp (ví dụ: 'Họp vận hành tuần')."
                },
                "equipment": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách thiết bị cần chuẩn bị cùng phòng họp."
                }
            },
            "required": ["room_id", "start_datetime", "end_datetime", "purpose"]
        }
    }
]

# ==============================================================================
# 2. MÔ PHỎNG DỮ LIỆU & HÀM THỰC THI TOOL (EXECUTION LAYER)
# ==============================================================================

MOCK_DATABASE = {
    "rooms": {
        "A201": {
            "room_name": "Phòng họp A201",
            "location": "Tòa A, tầng 2",
            "capacity": 12,
            "equipment": ["máy chiếu", "bảng trắng", "hệ thống họp trực tuyến"],
            "bookings": [
                {
                    "start_datetime": "10:00 16/09/2026",
                    "end_datetime": "11:00 16/09/2026",
                    "purpose": "Họp nhóm nghiên cứu"
                }
            ]
        },
        "B105": {
            "room_name": "Phòng họp B105",
            "location": "Tòa B, tầng 1",
            "capacity": 8,
            "equipment": ["màn hình trình chiếu", "bảng trắng"],
            "bookings": [
                {
                    "start_datetime": "09:00 17/09/2026",
                    "end_datetime": "10:30 17/09/2026",
                    "purpose": "Phỏng vấn tuyển dụng"
                }
            ]
        },
        "C301": {
            "room_name": "Phòng họp C301",
            "location": "Tòa C, tầng 3",
            "capacity": 20,
            "equipment": ["máy chiếu", "bảng trắng", "hệ thống họp trực tuyến"],
            "bookings": []
        },
        "D401": {
            "room_name": "Phòng họp D401",
            "location": "Tòa D, tầng 4",
            "capacity": 30,
            "equipment": ["màn hình LED", "micro không dây"],
            "bookings": []
        }
    },
    "supported_equipment": [
        "máy chiếu",
        "màn hình trình chiếu",
        "bảng trắng",
        "hệ thống họp trực tuyến",
        "màn hình LED",
        "micro không dây"
    ]
}


DATETIME_FORMAT = "%H:%M %d/%m/%Y"


def _parse_datetime(value: str) -> datetime:
    """Chuyển chuỗi HH:MM DD/MM/YYYY thành datetime để so sánh chính xác."""
    return datetime.strptime(value.strip(), DATETIME_FORMAT)


def _normalize_room_id(room_id: str) -> str:
    """Chuẩn hóa mã phòng do người dùng hoặc LLM cung cấp."""
    return room_id.strip().upper()


def _normalize_equipment(equipment: list | None) -> list:
    """Loại bỏ khoảng trắng, phần tử trùng và chuẩn hóa chữ hoa/thường."""
    if not equipment:
        return []
    return list(dict.fromkeys(str(item).strip().casefold() for item in equipment if str(item).strip()))


def _validate_time_range(start_datetime: str, end_datetime: str):
    """Parse và xác nhận thời gian kết thúc phải sau thời gian bắt đầu."""
    try:
        start = _parse_datetime(start_datetime)
        end = _parse_datetime(end_datetime)
    except (AttributeError, TypeError, ValueError):
        return None, None, {
            "status": "INVALID_ARGUMENT",
            "message": "Thời gian phải có định dạng 'HH:MM DD/MM/YYYY'."
        }

    if end <= start:
        return None, None, {
            "status": "INVALID_ARGUMENT",
            "message": "Thời gian kết thúc phải sau thời gian bắt đầu."
        }
    return start, end, None


def _has_time_conflict(room: Dict[str, Any], start: datetime, end: datetime) -> bool:
    """Kiểm tra khoảng [start, end) có giao với booking hiện hữu hay không."""
    for booking in room["bookings"]:
        booking_start = _parse_datetime(booking["start_datetime"])
        booking_end = _parse_datetime(booking["end_datetime"])
        if start < booking_end and end > booking_start:
            return True
    return False


def check_room_availability(
    start_datetime: str,
    end_datetime: str,
    room_id: str = None,
    min_capacity: int = None,
    equipment: list = None
) -> str:
    """Kiểm tra phòng đáp ứng thời gian, sức chứa và thiết bị yêu cầu."""
    start, end, error = _validate_time_range(start_datetime, end_datetime)
    if error:
        return json.dumps(error, ensure_ascii=False)

    normalized_room_id = _normalize_room_id(room_id) if room_id else None
    rooms = MOCK_DATABASE["rooms"]
    if normalized_room_id and normalized_room_id not in rooms:
        return json.dumps({
            "status": "NOT_FOUND",
            "room_id": normalized_room_id,
            "message": f"Không tìm thấy phòng họp có mã '{normalized_room_id}'."
        }, ensure_ascii=False)

    requested_equipment = _normalize_equipment(equipment)
    available_rooms = []

    for rid, room in rooms.items():
        if normalized_room_id and rid != normalized_room_id:
            continue
        if min_capacity is not None and room["capacity"] < min_capacity:
            continue

        room_equipment = _normalize_equipment(room["equipment"])
        if not all(item in room_equipment for item in requested_equipment):
            continue
        if _has_time_conflict(room, start, end):
            continue

        available_rooms.append({
            "room_id": rid,
            "room_name": room["room_name"],
            "location": room["location"],
            "capacity": room["capacity"],
            "equipment": room["equipment"]
        })

    return json.dumps({
        "status": "SUCCESS",
        "query": {
            "start_datetime": start_datetime.strip(),
            "end_datetime": end_datetime.strip(),
            "room_id": normalized_room_id,
            "min_capacity": min_capacity,
            "equipment": requested_equipment
        },
        "available_rooms": available_rooms,
        "count": len(available_rooms)
    }, ensure_ascii=False)


def book_meeting_room(
    room_id: str,
    start_datetime: str,
    end_datetime: str,
    purpose: str,
    equipment: list = None
) -> str:
    """Đặt phòng sau khi kiểm tra phòng, thời gian và thiết bị."""
    normalized_room_id = _normalize_room_id(room_id)
    rooms = MOCK_DATABASE["rooms"]
    if normalized_room_id not in rooms:
        return json.dumps({
            "status": "NOT_FOUND",
            "room_id": normalized_room_id,
            "message": f"Không tìm thấy phòng họp có mã '{normalized_room_id}'."
        }, ensure_ascii=False)

    start, end, error = _validate_time_range(start_datetime, end_datetime)
    if error:
        return json.dumps(error, ensure_ascii=False)

    room = rooms[normalized_room_id]
    requested_equipment = _normalize_equipment(equipment)
    room_equipment = _normalize_equipment(room["equipment"])
    unavailable_equipment = [
        item for item in requested_equipment if item not in room_equipment
    ]
    if unavailable_equipment:
        return json.dumps({
            "status": "EQUIPMENT_NOT_AVAILABLE",
            "room_id": normalized_room_id,
            "unavailable_equipment": unavailable_equipment,
            "available_equipment": room["equipment"],
            "message": "Phòng không có đầy đủ thiết bị được yêu cầu."
        }, ensure_ascii=False)

    if _has_time_conflict(room, start, end):
        return json.dumps({
            "status": "CONFLICT",
            "room_id": normalized_room_id,
            "message": "Phòng đã được đặt trong khoảng thời gian này."
        }, ensure_ascii=False)

    booking_id = f"BK-{normalized_room_id}-{len(room['bookings']) + 1:03d}"
    new_booking = {
        "booking_id": booking_id,
        "room_id": normalized_room_id,
        "start_datetime": start_datetime.strip(),
        "end_datetime": end_datetime.strip(),
        "purpose": purpose.strip(),
        "equipment": requested_equipment
    }
    room["bookings"].append(new_booking)

    return json.dumps({
        "status": "SUCCESS",
        "booking_id": booking_id,
        "room_id": normalized_room_id,
        "booking": new_booking,
        "room": {
            "room_name": room["room_name"],
            "location": room["location"],
            "capacity": room["capacity"],
            "equipment": room["equipment"]
        },
        "message": (
            f"Đặt phòng '{normalized_room_id}' thành công "
            f"từ {start_datetime.strip()} đến {end_datetime.strip()}."
        )
    }, ensure_ascii=False)


# Router gọi tool thực tế
TOOL_ROUTER = {
    "check_room_availability": check_room_availability,
    "book_meeting_room": book_meeting_room
}

def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Hàm trung chuyển thực thi tool"""
    if tool_name in TOOL_ROUTER:
        try:
            return TOOL_ROUTER[tool_name](**arguments)
        except Exception as e:
            return json.dumps({"status": "EXECUTION_ERROR", "error": str(e)}, ensure_ascii=False)
    return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại!"}, ensure_ascii=False)
