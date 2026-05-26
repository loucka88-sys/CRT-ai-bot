# -*- coding: utf-8 -*-

from flask import Flask, request
import requests
from anthropic import Anthropic
import json
import os

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

MODEL = "claude-sonnet-4-0"

client = Anthropic(api_key=CLAUDE_API_KEY)

app = Flask(__name__)

def send_msg(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": str(text)
        },
        timeout=30
    )

@app.route("/")
def home():
    return "CRT AI BOT RUNNING"

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data = request.json

        symbol = data.get("symbol", "UNKNOWN")
        timeframe = data.get("timeframe", "")
        price = data.get("price", "")
        direction = data.get("direction", "LONG")

        prompt = f"""
أنت محلل تداول احترافي.

وصل تنبيه CRT Pro:

العملة: {symbol}
الفريم: {timeframe}
السعر الحالي: {price}
الاتجاه: {direction}

اعطني فقط:
- هل الصفقة ممتازة أم لا
- نسبة الثقة
- نقطة الدخول
- وقف الخسارة
- الهدف الأول
- الهدف الثاني
- مدة الصفقة
- جودة الصفقة

إذا الصفقة ضعيفة قل:
NO TRADE
"""

        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        result = response.content[0].text

        send_msg(
f"""🔥 CRT ALERT

📊 {symbol}
⏱ {timeframe}
💰 السعر: {price}

{result}
"""
        )

        return {"status": "ok"}

    except Exception as e:
        send_msg(f"❌ ERROR\\n{str(e)}")
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
