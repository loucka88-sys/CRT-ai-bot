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


def analyze_with_claude(raw_text):
    try:
        prompt = f"""
أنت محلل تداول صارم.

وصل تنبيه CRT Pro من TradingView:

{raw_text}

حلله كصفقة LONG فقط.

أعطني:
- القرار: TRADE أو NO TRADE
- الرمز
- الفريم
- الدخول
- الستوب
- TP1
- TP2
- الجودة
- الثقة %
- المدة المتوقعة
- السبب

إذا البيانات ناقصة أو الصفقة ضعيفة قل NO TRADE.
"""

        response = client.messages.create(
            model=MODEL,
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.content[0].text

        send_msg(f"""🚨 CRT ALERT

{result}
""")

    except Exception as e:
        send_msg(f"❌ CLAUDE ERROR\n{str(e)}")


@app.route("/")
def home():
    return "CRT AI BOT RUNNING"


@app.route("/webhook", methods=["POST"])
def webhook():
    raw_text = request.get_data(as_text=True) or "NO DATA"

    send_msg(f"""✅ وصل تنبيه CRT

{raw_text}

⏳ جاري تحليله عبر Claude...
""")

    threading.Thread(
        target=analyze_with_claude,
        args=(raw_text,),
        daemon=True
    ).start()

    return {"status": "received"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
