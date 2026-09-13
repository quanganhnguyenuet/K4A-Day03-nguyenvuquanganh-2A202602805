"""
🔌 MULTI-PROVIDER LLM ADAPTER (Google Gemini, OpenAI & Offline Mock)
Hỗ trợ Native Tool Calling và chuyển đổi linh hoạt qua biến môi trường LLM_PROVIDER.
"""

import os
import sys
import json
import re
from typing import Dict, Any, List
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

load_dotenv()

class BaseLLMProvider:
    """Interface cơ sở cho các LLM Provider hỗ trợ Native Tool Calling"""
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        raise NotImplementedError


class MockOfflineProvider(BaseLLMProvider):
    """Offline Mock Provider dùng để chạy thử mà không tốn API Key"""
    def __init__(self):
        self.model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return (
            "[Mock Chatbot Response]: Tôi có thể giải đáp thông tin chung về "
            "phòng họp VinUni, nhưng không thể kiểm tra lịch trống hoặc tạo booking "
            "vì Chatbot Baseline không được kết nối Tool."
        )

    @staticmethod
    def _tool_is_available(tool_name: str, tools_schema: List[Dict[str, Any]]) -> bool:
        return any(tool.get("name") == tool_name for tool in tools_schema)

    @staticmethod
    def _extract_time_range(prompt: str):
        match = re.search(
            r"từ\s*(\d{1,2}:\d{2})\s*đến\s*(\d{1,2}:\d{2})\s*ngày\s*(\d{1,2}/\d{1,2}/\d{4})",
            prompt,
            flags=re.IGNORECASE
        )
        if not match:
            return None, None
        start_time, end_time, date = match.groups()
        return f"{start_time} {date}", f"{end_time} {date}"

    @staticmethod
    def _extract_room_id(prompt: str):
        match = re.search(r"\b([A-Za-z]\d{3})\b", prompt)
        return match.group(1).upper() if match else None

    @staticmethod
    def _extract_min_capacity(prompt: str):
        match = re.search(r"(?:ít nhất|tối thiểu)\s*(\d+)\s*chỗ", prompt, flags=re.IGNORECASE)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_equipment(prompt: str) -> list:
        prompt_lower = prompt.casefold()
        equipment_names = [
            "máy chiếu",
            "màn hình trình chiếu",
            "bảng trắng",
            "hệ thống họp trực tuyến",
            "màn hình led",
            "micro không dây"
        ]
        return [item for item in equipment_names if item in prompt_lower]

    @staticmethod
    def _extract_purpose(prompt: str):
        before_time = re.search(
            r"cho\s+(?:nhóm|cuộc họp)?\s*(.+?)\s+từ\s*\d{1,2}:\d{2}",
            prompt,
            flags=re.IGNORECASE
        )
        if before_time:
            return before_time.group(1).strip()

        after_time = re.search(
            r"cho\s+cuộc họp\s+(.+?)(?:[.!?]|$)",
            prompt,
            flags=re.IGNORECASE
        )
        return after_time.group(1).strip() if after_time else None

    @staticmethod
    def _extract_react_context(prompt: str) -> Dict[str, Any]:
        marker = "REACT_CONTEXT_JSON:"
        if marker not in prompt:
            return {"original_query": prompt, "history": []}
        try:
            return json.loads(prompt.rsplit(marker, 1)[1].strip())
        except (TypeError, json.JSONDecodeError):
            return {"original_query": prompt, "history": []}

    @staticmethod
    def _observation_text(observation: Dict[str, Any]) -> str:
        status = observation.get("status", "UNKNOWN")
        if status == "SUCCESS":
            if "booking_id" in observation:
                return observation.get(
                    "message",
                    f"Đặt phòng thành công với mã {observation['booking_id']}."
                )
            rooms = observation.get("available_rooms", [])
            if not rooms:
                return "Không tìm thấy phòng đáp ứng đầy đủ các điều kiện yêu cầu."
            room_summaries = [
                f"{room['room_id']} ({room['capacity']} chỗ, {room['location']})"
                for room in rooms
            ]
            return "Các phòng còn trống: " + "; ".join(room_summaries) + "."
        return observation.get("message", f"Công cụ trả về trạng thái {status}.")

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        react_context = self._extract_react_context(prompt)
        original_query = react_context.get("original_query", prompt)
        history = react_context.get("history", [])

        prompt_lower = original_query.casefold()
        start_datetime, end_datetime = self._extract_time_range(original_query)
        room_id = self._extract_room_id(original_query)
        min_capacity = self._extract_min_capacity(original_query)
        equipment = self._extract_equipment(original_query)

        check_intent = any(phrase in prompt_lower for phrase in [
            "kiểm tra",
            "còn trống",
            "tìm phòng",
            "tìm một phòng"
        ])
        booking_intent = "đặt phòng" in prompt_lower or "booking" in prompt_lower
        policy_intent = any(phrase in prompt_lower for phrase in [
            "quy định",
            "chính sách",
            "hướng dẫn hủy",
            "hướng dẫn đổi"
        ])

        if not history and policy_intent:
            return {
                "type": "text",
                "content": (
                    "[Mock Agent Response]: Tôi chưa có dữ liệu chính sách nội bộ cụ thể "
                    "để xác nhận quy định này. Vui lòng liên hệ bộ phận Facilities VinUni."
                ),
                "thought": "Đây là câu hỏi chính sách chung, không cần gọi Tool dữ liệu thời gian thực."
            }

        if history:
            last_event = history[-1]
            last_tool = last_event.get("action", {}).get("tool_name")
            observation = last_event.get("observation", {})
            status = observation.get("status")

            if last_tool == "check_room_availability":
                available_rooms = observation.get("available_rooms", [])
                if status == "SUCCESS" and booking_intent and available_rooms:
                    purpose = self._extract_purpose(original_query)
                    if not purpose:
                        return {
                            "type": "text",
                            "content": "Vui lòng cung cấp mục đích cuộc họp trước khi đặt phòng.",
                            "thought": "Observation có phòng phù hợp nhưng yêu cầu còn thiếu mục đích."
                        }
                    arguments = {
                        "room_id": available_rooms[0]["room_id"],
                        "start_datetime": start_datetime,
                        "end_datetime": end_datetime,
                        "purpose": purpose
                    }
                    if equipment:
                        arguments["equipment"] = equipment
                    return {
                        "type": "tool_call",
                        "tool_name": "book_meeting_room",
                        "arguments": arguments,
                        "thought": "Đã tìm thấy phòng phù hợp trong Observation; tiếp tục tạo booking."
                    }

                return {
                    "type": "text",
                    "content": self._observation_text(observation),
                    "thought": "Đã có kết quả tra cứu và không cần thực hiện thêm Tool Call."
                }

            if last_tool == "book_meeting_room":
                return {
                    "type": "text",
                    "content": self._observation_text(observation),
                    "thought": "Đã nhận kết quả đặt phòng và có thể kết luận cho người dùng."
                }

        # Ý định kiểm tra được ưu tiên khi câu hỏi yêu cầu kiểm tra rồi mới đặt.
        if check_intent:
            tool_name = "check_room_availability"
            if not self._tool_is_available(tool_name, tools_schema):
                return {
                    "type": "text",
                    "content": f"Không thể kiểm tra phòng vì Tool '{tool_name}' chưa được cấu hình.",
                    "thought": "Facilities Tool Schema chưa được công bố."
                }
            if not start_datetime or not end_datetime:
                return {
                    "type": "text",
                    "content": "Vui lòng cung cấp đầy đủ giờ bắt đầu, giờ kết thúc và ngày cần sử dụng phòng.",
                    "thought": "Thiếu khoảng thời gian bắt buộc để kiểm tra phòng."
                }

            arguments = {
                "start_datetime": start_datetime,
                "end_datetime": end_datetime
            }
            if room_id:
                arguments["room_id"] = room_id
            if min_capacity is not None:
                arguments["min_capacity"] = min_capacity
            if equipment:
                arguments["equipment"] = equipment

            return {
                "type": "tool_call",
                "tool_name": tool_name,
                "arguments": arguments,
                "thought": "Cần kiểm tra dữ liệu phòng và thiết bị trước khi trả lời hoặc tiếp tục đặt phòng."
            }

        if booking_intent:
            tool_name = "book_meeting_room"
            if not self._tool_is_available(tool_name, tools_schema):
                return {
                    "type": "text",
                    "content": f"Không thể đặt phòng vì Tool '{tool_name}' chưa được cấu hình.",
                    "thought": "Facilities Tool Schema chưa được công bố."
                }

            purpose = self._extract_purpose(prompt)
            missing_fields = []
            if not room_id:
                missing_fields.append("mã phòng")
            if not start_datetime or not end_datetime:
                missing_fields.append("khoảng thời gian")
            if not purpose:
                missing_fields.append("mục đích cuộc họp")
            if missing_fields:
                return {
                    "type": "text",
                    "content": f"Vui lòng bổ sung: {', '.join(missing_fields)}.",
                    "thought": "Thiếu tham số bắt buộc nên chưa thể gọi Tool đặt phòng."
                }

            arguments = {
                "room_id": room_id,
                "start_datetime": start_datetime,
                "end_datetime": end_datetime,
                "purpose": purpose
            }
            if equipment:
                arguments["equipment"] = equipment

            return {
                "type": "tool_call",
                "tool_name": tool_name,
                "arguments": arguments,
                "thought": "Người dùng đã cung cấp đủ thông tin để tạo booking phòng họp."
            }

        return {
            "type": "text",
            "content": (
                "[Mock Agent Response]: Tôi chưa có dữ liệu chính sách nội bộ cụ thể "
                "để xác nhận quy định này. Vui lòng liên hệ bộ phận Facilities VinUni."
            ),
            "thought": "Câu hỏi chung không cần truy vấn dữ liệu phòng theo thời gian thực."
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini Provider (Native Tool Calling với Google GenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return "[Gemini Error]: Chưa cấu hình GEMINI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            contents = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(model=self.model_name, contents=contents)
            return response.text
        except Exception as e:
            return f"[Gemini Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            print("ℹ️ [Gemini Provider]: Chưa tìm thấy GEMINI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)
        
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=self.api_key)
            
            # Chuẩn hóa function declarations cho Gemini SDK
            function_declarations = []
            for tool in tools_schema:
                # Bỏ qua các tool schema chưa được định nghĩa hoàn chỉnh
                if not tool.get("name") or not tool.get("parameters"):
                    continue
                function_declarations.append({
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {})
                })

            config = types.GenerateContentConfig(
                system_instruction=system_prompt if system_prompt else None,
                tools=[{"function_declarations": function_declarations}] if function_declarations else None,
                temperature=0.2
            )

            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )

            # Kiểm tra xem Gemini có trả về Tool Call không
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if hasattr(call, 'args') and call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "thought": f"Gemini quyết định gọi công cụ '{call.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": response.text or "",
                    "thought": "Gemini phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }

        except Exception as e:
            print(f"⚠️ [Gemini API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


class OpenAIProvider(BaseLLMProvider):
    """OpenAI Provider (Native Tool Calling với OpenAI SDK)"""
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return "[OpenAI Error]: Chưa cấu hình OPENAI_API_KEY trong file .env! Đang sử dụng chế độ Mock."
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as e:
            return f"[OpenAI Exception]: {str(e)}"

    def generate_with_tools(self, prompt: str, tools_schema: List[Dict[str, Any]], system_prompt: str = "") -> Dict[str, Any]:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            print("ℹ️ [OpenAI Provider]: Chưa tìm thấy OPENAI_API_KEY hợp lệ. Tự động chuyển sang Mock Offline.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)

            tools = []
            for tool in tools_schema:
                if not tool.get("name"):
                    continue
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {})
                    }
                })

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            msg = response.choices[0].message
            if msg.tool_calls:
                call = msg.tool_calls[0]
                args = json.loads(call.function.arguments) if call.function.arguments else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": args,
                    "thought": f"OpenAI quyết định gọi công cụ '{call.function.name}' với tham số: {json.dumps(args, ensure_ascii=False)}"
                }
            else:
                return {
                    "type": "text",
                    "content": msg.content or "",
                    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ)."
                }
        except Exception as e:
            print(f"⚠️ [OpenAI API Warning]: Không thể kết nối live API ({str(e)}). Tự động fallback về Mock.")
            return MockOfflineProvider().generate_with_tools(prompt, tools_schema, system_prompt)


def get_llm_provider() -> BaseLLMProvider:
    """Factory function khởi tạo Provider theo LLM_PROVIDER env variable"""
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    
    if provider_type == "gemini":
        key = os.getenv("GEMINI_API_KEY")
        if key and key != "your_gemini_api_key_here":
            return GeminiProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "openai":
        key = os.getenv("OPENAI_API_KEY")
        if key and key != "your_openai_api_key_here":
            return OpenAIProvider()
        else:
            return MockOfflineProvider()
    elif provider_type == "mock":
        return MockOfflineProvider()
    else:
        return MockOfflineProvider()
