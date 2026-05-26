# -*- coding: utf-8 -*-

import os
import requests
from flask import Flask, request
from anthropic import Anthropic

app = Flask(__name__)

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

client = Anthropic(api_key=CLAUDE_API_KEY)
MODEL = "claude-sonnet-4-5-20250929"


def send_msg(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": str(text)},
        timeout=30
    )


@app.route("/")
def home():
    return "CRT AI BOT RUNNING"


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        raw_text = request.get_data(as_text=True) or ""

        data = request.get_json(force=False, silent=True) or {}

        symbol = data.get("symbol") or data.get("ticker") or "UNKNOWN"
        timeframe = data.get("timeframe") or data.get("interval") or ""
        price = data.get("price") or ""
        signal = data.get("signal") or raw_text or "CRT ALERT"

        prompt = f"""
أنت محلل تداول محترف وصارم.

وصل تنبيه من TradingView / CRT Pro:

الرمز: {symbol}
الفريم: {timeframe}
السعر: {price}
الإشارة: {signal}

المطلوب:
- LONG فقط
- هل الصفقة صالحة أو لا؟
- نقطة الدخول
- وقف الخسارة
- TP1
- TP2
- المدة المتوقعة
- جودة الصفقة
- نسبة الثقة

إذا البيانات غير كافية أو الصفقة ضعيفة قل:
NO TRADE

اعطني الرد مختصر وواضح.
"""

        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        result = response.content[0].text

        send_msg(f"""🚨 CRT Alert وصل

📊 الرمز: {symbol}
⏱ الفريم: {timeframe}
💰 السعر: {price}

{result}
""")

        return {"status": "ok"}

    except Exception as e:
        send_msg(f"❌ WEBHOOK ERROR\n{str(e)}")
        return {"error": str(e)}, 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
