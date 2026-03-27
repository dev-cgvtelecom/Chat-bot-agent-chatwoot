from fastapi import FastAPI, Request
import requests
import re

app = FastAPI()

API_URL = "https://devchat.telesip.vn"
API_TOKEN = "EdPegfJRVotRVCqSav9hcsBT"   # 🔥 thay token thật
ACCOUNT_ID = 1

# ========================
# 🔧 CLEAN HTML
# ========================
def clean_html(raw_html):
    return re.sub('<.*?>', '', raw_html)


# ========================
# 🔥 SEND REPLY (PRIVATE API)
# ========================
def send_reply(conversation_id, message):
    url = f"{API_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conversation_id}/messages"

    headers = {
        "api_access_token": API_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "content": message,
        "message_type": 1   # 🔥 QUAN TRỌNG (outgoing)
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)

        print("==== DEBUG SEND ====")
        print("URL:", url)
        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)

    except Exception as e:
        print("ERROR SEND:", str(e))


# ========================
# 🤖 WEBHOOK
# ========================
@app.post("/chatwoot/bot")
async def bot(req: Request):
    data = await req.json()

    print("==== WEBHOOK DATA ====")
    print(data)

    # ❌ bỏ event không cần
    if data.get("event") != "message_created":
        return {"ok": True}

    # ❌ chỉ xử lý tin nhắn user
    if data.get("message_type") != "incoming":
        return {"ok": True}

    # ========================
    # 📥 LẤY DATA
    # ========================
    raw_message = data.get("content", "")
    message = clean_html(raw_message)

    conversation_id = data["conversation"]["id"]

    print(f"User send: {message}")
    print(f"conversation_id: {conversation_id}")

    # ========================
    # 🤖 LOGIC BOT
    # ========================
    msg = message.lower()

    if "xin chào" in msg or "hello" in msg:
        reply = "Xin chào 👋 tôi là chatbot CGV Telecom. Tôi có thể giúp gì cho bạn?"
    
    elif "giá" in msg:
        reply = "Bạn muốn hỏi giá dịch vụ nào ạ? Internet, SIP hay tổng đài?"

    elif "internet" in msg:
        reply = "Gói Internet bên mình từ 150k/tháng. Bạn cần tư vấn gói nào?"

    elif "sip" in msg:
        reply = "Dịch vụ SIP giúp bạn gọi VoIP tiết kiệm chi phí. Bạn muốn demo không?"

    elif "tạm biệt" in msg:
        reply = "Cảm ơn bạn đã liên hệ ❤️"

    else:
        reply = f"Bạn vừa nói: {message}"

    # ========================
    # 🚀 GỬI TRẢ LẠI CHATWOOT
    # ========================
    send_reply(conversation_id, reply)

    return {"ok": True}