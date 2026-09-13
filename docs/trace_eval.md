# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** [Nguyễn Vũ Quang Anh]  
> **Mã Sinh Viên / Mã Học viên:** [2A202602805]  
> **Chủ đề Lựa chọn:** [Trợ lý Đặt Phòng họp & Thiết bị (Facilities Agent)]  

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 4 / 5 | Agent cần phân tích yêu cầu về thời gian, sức chứa và thiết bị; với yêu cầu phức tạp, phải tra cứu phòng phù hợp trước khi đặt phòng. |
| **2. Tool Interaction** | 5 / 5 | Hệ thống phải truy vấn lịch phòng, thông tin thiết bị và ghi nhận booking qua MCP Server hoặc cơ sở dữ liệu bên ngoài. |
| **3. Dynamic Decision** | 5 / 5 | Việc đặt phòng phụ thuộc trực tiếp vào Observation: phòng có trống, đủ sức chứa, có thiết bị yêu cầu hay cần đề xuất phòng thay thế. |
| **4. Long Horizon Goal** | 4 / 5 | Agent cần giữ xuyên suốt mục tiêu tạo booking hợp lệ qua các bước tra cứu, chọn phương án, đặt phòng và xác nhận kết quả. |
| **TỔNG ĐIỂM AGENTIC FIT** | **18 / 20** | *Bài toán rất phù hợp triển khai Agentic System vì tổng điểm lớn hơn 12/20.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
{
    "step": 1,
    "query": "Hãy tìm một phòng họp còn trống, có ít nhất 10 chỗ ngồi và máy chiếu từ 09:00 đến 10:30 ngày 17/09/2026; nếu tìm thấy, hãy đặt phòng đó cho cuộc họp vận hành tuần.",
    "action_type": "TOOL_EXECUTION",
    "thought": "OpenAI quyết định gọi công cụ 'check_room_availability' với tham số: {\"start_datetime\": \"09:00 17/09/2026\", \"end_datetime\": \"10:30 17/09/2026\", \"min_capacity\": 10, \"equipment\": [\"máy chiếu\"]}",
    "tool_name": "check_room_availability",
    "arguments": {
      "start_datetime": "09:00 17/09/2026",
      "end_datetime": "10:30 17/09/2026",
      "min_capacity": 10,
      "equipment": [
        "máy chiếu"
      ]
    },
    "observation": {
      "status": "SUCCESS",
      "query": {
        "start_datetime": "09:00 17/09/2026",
        "end_datetime": "10:30 17/09/2026",
        "room_id": null,
        "min_capacity": 10,
        "equipment": [
          "máy chiếu"
        ]
      },
      "available_rooms": [
        {
          "room_id": "A201",
          "room_name": "Phòng họp A201",
          "location": "Tòa A, tầng 2",
          "capacity": 12,
          "equipment": [
            "máy chiếu",
            "bảng trắng",
            "hệ thống họp trực tuyến"
          ]
        },
        {
          "room_id": "C301",
          "room_name": "Phòng họp C301",
          "location": "Tòa C, tầng 3",
          "capacity": 20,
          "equipment": [
            "máy chiếu",
            "bảng trắng",
            "hệ thống họp trực tuyến"
          ]
        }
      ],
      "count": 2
    },
    "llm_latency_ms": 1463.67,
    "tool_latency_ms": 0.0,
    "latency_ms": 1463.67
  },
  {
    "step": 2,
    "query": "Hãy tìm một phòng họp còn trống, có ít nhất 10 chỗ ngồi và máy chiếu từ 09:00 đến 10:30 ngày 17/09/2026; nếu tìm thấy, hãy đặt phòng đó cho cuộc họp vận hành tuần.",
    "action_type": "TOOL_EXECUTION",
    "thought": "OpenAI quyết định gọi công cụ 'book_meeting_room' với tham số: {\"room_id\": \"A201\", \"start_datetime\": \"09:00 17/09/2026\", \"end_datetime\": \"10:30 17/09/2026\", \"purpose\": \"Họp vận hành tuần\", \"equipment\": [\"máy chiếu\"]}",
    "tool_name": "book_meeting_room",
    "arguments": {
      "room_id": "A201",
      "start_datetime": "09:00 17/09/2026",
      "end_datetime": "10:30 17/09/2026",
      "purpose": "Họp vận hành tuần",
      "equipment": [
        "máy chiếu"
      ]
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-A201-003",
      "room_id": "A201",
      "booking": {
        "booking_id": "BK-A201-003",
        "room_id": "A201",
        "start_datetime": "09:00 17/09/2026",
        "end_datetime": "10:30 17/09/2026",
        "purpose": "Họp vận hành tuần",
        "equipment": [
          "máy chiếu"
        ]
      },
      "room": {
        "room_name": "Phòng họp A201",
        "location": "Tòa A, tầng 2",
        "capacity": 12,
        "equipment": [
          "máy chiếu",
          "bảng trắng",
          "hệ thống họp trực tuyến"
        ]
      },
      "message": "Đặt phòng 'A201' thành công từ 09:00 17/09/2026 đến 10:30 17/09/2026."
    },
    "llm_latency_ms": 1094.36,
    "tool_latency_ms": 0.0,
    "latency_ms": 1094.36
  },
  {
    "step": 3,
    "query": "Hãy tìm một phòng họp còn trống, có ít nhất 10 chỗ ngồi và máy chiếu từ 09:00 đến 10:30 ngày 17/09/2026; nếu tìm thấy, hãy đặt phòng đó cho cuộc họp vận hành tuần.",
    "action_type": "FINAL_ANSWER",
    "thought": "OpenAI phản hồi trực tiếp bằng văn bản (không cần gọi công cụ).",
    "output": "Đặt phòng 'A201' thành công cho cuộc họp vận hành tuần từ 09:00 đến 10:30 ngày 17/09/2026.\n\nThông tin chi tiết:\n- **Mã booking**: BK-A201-003\n- **Phòng**: A201 (Phòng họp A201, Tòa A, tầng 2)\n- **Sức chứa**: 12 chỗ\n- **Thiết bị**: Máy chiếu\n\nNếu cần thêm thông tin hay hỗ trợ gì khác, bạn hãy cho tôi biết!",
    "latency_ms": 1450.01
  }
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** 5 lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
