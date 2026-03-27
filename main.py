import os
import re
from contextlib import asynccontextmanager

import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("CHATWOOT_API_URL", "https://devchat.telesip.vn").rstrip("/")
API_TOKEN = os.getenv("CHATWOOT_API_TOKEN", "").strip()
ACCOUNT_ID = os.getenv("CHATWOOT_ACCOUNT_ID", "1").strip()


def startup_log():
    token_preview = f"{API_TOKEN[:6]}...{API_TOKEN[-4:]}" if len(API_TOKEN) > 10 else "(short-or-empty)"
    print("==== STARTUP CONFIG ====")
    print("CHATWOOT_API_URL:", API_URL)
    print("CHATWOOT_ACCOUNT_ID:", ACCOUNT_ID)
    print("TOKEN_LEN:", len(API_TOKEN))
    print("TOKEN_PREVIEW:", token_preview)


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup_log()
    yield


app = FastAPI(lifespan=lifespan)

# ========================
# 🔧 CLEAN HTML
# ========================
def clean_html(raw_html):
    return re.sub(r"<.*?>", "", raw_html or "").strip()


# ========================
# 🔥 SEND REPLY (PRIVATE API)
# ========================
def _build_headers():
    headers = {
        "Content-Type": "application/json",
    }
    if API_TOKEN:
        # Chatwoot REST API expects api_access_token.
        # Avoid Authorization header because some deployments handle it differently.
        headers["api_access_token"] = API_TOKEN
    return headers


def send_reply(conversation_id, message):
    url = f"{API_URL}/api/v1/accounts/{ACCOUNT_ID}/conversations/{conversation_id}/messages"
    headers = _build_headers()

    payload = {
        "content": message,
        "message_type": "outgoing",
        "private": False,
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=10)

        print("==== DEBUG SEND ====")
        print("URL:", url)
        print("STATUS:", res.status_code)
        print("RESPONSE:", res.text)
        if res.status_code == 401:
            print(
                "AUTH ERROR: CHATWOOT_API_TOKEN không hợp lệ hoặc không có quyền trong account."
            )
            check_chatwoot_auth()
        elif res.status_code == 404:
            print(
                "NOT FOUND: CHATWOOT_ACCOUNT_ID hoặc conversation_id không đúng với token hiện tại."
            )

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

    # Ignore irrelevant webhook events.
    if data.get("event") != "message_created":
        return {"ok": True}

    # Process only user incoming messages.
    if data.get("message_type") != "incoming":
        return {"ok": True}

    # ========================
    # 📥 LẤY DATA
    # ========================
    raw_message = data.get("content", "")
    message = clean_html(raw_message)

    conversation = data.get("conversation") or {}
    conversation_id = conversation.get("id")
    if not conversation_id:
        print("SKIP: thiếu conversation_id trong webhook payload")
        return {"ok": True}

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
    if not API_TOKEN:
        print("CONFIG ERROR: chưa thiết lập CHATWOOT_API_TOKEN")
        return {"ok": False, "error": "missing_api_token"}

    send_reply(conversation_id, reply)

    return {"ok": True}


@app.get("/health")
def health():
    return {
        "ok": True,
        "chatwoot_api_url": API_URL,
        "chatwoot_account_id": ACCOUNT_ID,
        "has_token": bool(API_TOKEN),
    }


@app.get("/debug/auth")
def debug_auth():
    if not API_TOKEN:
        return {"ok": False, "error": "missing_api_token"}
    url = f"{API_URL}/api/v1/profile"
    try:
        res = requests.get(url, headers=_build_headers(), timeout=10)
        return {
            "ok": res.status_code == 200,
            "profile_status": res.status_code,
            "profile_response": res.text[:300],
            "token_len": len(API_TOKEN),
            "token_preview": f"{API_TOKEN[:6]}...{API_TOKEN[-4:]}" if len(API_TOKEN) > 10 else "(short-or-empty)",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_chatwoot_auth():
    if not API_TOKEN:
        print("AUTH CHECK: thiếu CHATWOOT_API_TOKEN")
        return
    url = f"{API_URL}/api/v1/profile"
    headers = _build_headers()
    try:
        res = requests.get(url, headers=headers, timeout=10)
        print("==== AUTH CHECK ====")
        print("PROFILE URL:", url)
        print("PROFILE STATUS:", res.status_code)
        print("PROFILE RESPONSE:", res.text[:500])
    except Exception as e:
        print("AUTH CHECK ERROR:", str(e))