# -*- coding: utf-8 -*-

import os
import threading
import requests
from flask import Flask, request
from anthropic import Anthropic

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

client = Anthropic(api_key=CLAUDE_API_KEY)
MODEL = "claude-sonnet-4-5-20250929"


def send_msg(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": str(text)},
        timeout=30
    )


def analyze_and_send(raw_text):
    try:
        prompt = f"""
أنت محلل تداول محترف وصارم.

وصل تنبيه CRT Pro من TradingView:

{raw_text}

المطلوب:
- حلل التنبيه كصفقة LONG فقط.
- لا ترسل النص الخام.
- إذا الصفقة ضعيفة أو البيانات ناقصة قل NO TRADE.
- لا تعطيني شورت.
- لا تعطيني صفقة بدون دخول ووقف وأهداف.
- ركز على جودة الصفقة والهدف قبل الستوب.

اكتب الرد بهذا الشكل فقط:

📊 الرمز:
⏱ الفريم:
📌 القرار: LONG أو NO TRADE
✅ الجودة:
🎯 الثقة:
💰 الدخول:
🛑 وقف الخسارة:
🎯 TP1:
🚀 TP2:
⌛ المدة المتوقعة:
🧠 السبب:
⚠️ ملاحظة:
"""

        response = client.messages.create(
            model=MODEL,
            max_tokens=900,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text.strip()
        send_msg(result)

    except Exception as e:
        send_msg(f"❌ خطأ في Claude\n{str(e)}")


@app.route("/")
def home():
    return "CRT AI BOT RUNNING"


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_text = request.get_data(as_text=True) or "NO DATA"

    threading.Thread(
        target=analyze_and_send,
        args=(raw_text,),
        daemon=True
    ).start()

    return {"status": "received"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
