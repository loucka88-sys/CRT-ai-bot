# -*- coding: utf-8 -*-

import os
import re
import base64
import threading
import requests

from flask import Flask, request
from anthropic import Anthropic

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
BROWSERLESS_API_KEY = os.getenv("BROWSERLESS_API_KEY")

MODEL = "claude-sonnet-4-5-20250929"

client = Anthropic(
    api_key=CLAUDE_API_KEY
)

TIMEFRAMES = {
    "4H": "240",
    "1H": "60",
    "15M": "15",
    "5M": "5"
}


def send_msg(text):

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": str(text)
        },
        timeout=30
    )


def extract_symbol(raw):

    raw = raw.upper()

    m = re.search(r'([A-Z0-9]{2,20}USDT)', raw)

    if m:
        return f"BINANCE:{m.group(1)}"

    m = re.search(
        r'(XAUUSD|XAGUSD|EURUSD|GBPUSD|USDJPY|AUDUSD|USDCAD|USDCHF)',
        raw
    )

    if m:
        return f"OANDA:{m.group(1)}"

    return None


def extract_tf(raw):

    raw = raw.upper()

    if "4H" in raw:
        return "240"

    if "1H" in raw:
        return "60"

    if "15" in raw:
        return "15"

    if "5" in raw:
        return "5"

    return "15"


def extract_price(raw):

    m = re.search(r'([0-9]+\.[0-9]+)', raw)

    return m.group(1) if m else "UNKNOWN"


def tv_url(symbol, tf):

    return f"https://www.tradingview.com/chart/?symbol={symbol}&interval={tf}"


def screenshot(symbol, tf):

    endpoint = f"https://production-sfo.browserless.io/screenshot?token={BROWSERLESS_API_KEY}"

    payload = {
        "url": tv_url(symbol, tf),
        "options": {
            "type": "png",
            "fullPage": False
        },
        "gotoOptions": {
            "waitUntil": "networkidle2",
            "timeout": 45000
        },
        "viewport": {
            "width": 1440,
            "height": 1000
        }
    }

    r = requests.post(
        endpoint,
        json=payload,
        timeout=80
    )

    if r.status_code != 200:

        raise Exception(
            f"Browserless error {r.status_code}: {r.text[:400]}"
        )

    return base64.b64encode(r.content).decode("utf-8")


def img_block(b64):

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": b64
        }
    }


def analyze_and_send(raw_text):

    try:

        symbol = extract_symbol(raw_text)
        trigger_tf = extract_tf(raw_text)
        trigger_price = extract_price(raw_text)

        if not symbol:

            send_msg(
                "⚠️ لم أستطع استخراج الرمز من التنبيه."
            )

            return

        content = [{
            "type": "text",
            "text": f"""
وصل تنبيه CRT من TradingView.

التنبيه:
{raw_text}

الأصل:
{symbol}

فريم التنبيه:
{trigger_tf}

السعر:
{trigger_price}

تنبيه CRT مجرد Radar.
حلل الشارتات بصريًا Top-Down ثم أعطني قرارًا واحدًا فقط.
"""
        }]

        for name, tf in TIMEFRAMES.items():

            b64 = screenshot(symbol, tf)

            content.append({
                "type": "text",
                "text": f"{symbol} timeframe {name}"
            })

            content.append(
                img_block(b64)
            )

        prompt = """
أنت محلل تداول احترافي.

تنبيه CRT مجرد Radar.
حلل الشارتات بصريًا Top-Down:
4H → 1H → 15M → 5M

اعتمد على:
- الاتجاه
- الهيكل
- السيولة
- MSS / CISD
- مناطق العرض والطلب
- OTE / Premium / Discount

القواعد:

- قرار واحد فقط.
- ممنوع سيناريوهين.
- ممنوع BUY و SELL معًا.
- إذا السوق سيئ = NO TRADE.
- إذا محتار = WAIT.
- إذا الصفقة ممتازة أعط:
BUY MARKET / SELL MARKET / BUY LIMIT / SELL LIMIT

- لا تعط صفقة RR أقل من 1:2.
- لا تشرح كثير.
- لا تعط تحليل طويل.
- ركز فقط على التنفيذ.

أرسل النتيجة بهذا الشكل فقط:

🚨 CRT AI

📊 الأصل:
📌 القرار:

💰 الدخول:
🛑 الستوب:
🎯 TP1:
🚀 TP2:

📐 R:R:
🎯 الثقة:

🧠 السبب:
سطرين فقط.
"""

        content.append({
            "type": "text",
            "text": prompt
        })

        response = client.messages.create(
            model=MODEL,
            max_tokens=900,
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ]
        )

        result = response.content[0].text.strip()

        send_msg(result)

    except Exception as e:

        send_msg(
            f"❌ خطأ في التحليل\n{str(e)}"
        )


@app.route("/")
def home():

    return "CRT AI BOT RUNNING"


@app.route("/webhook", methods=["POST"])
def webhook():

    raw_text = request.get_data(as_text=True)

    threading.Thread(
        target=analyze_and_send,
        args=(raw_text,),
        daemon=True
    ).start()

    return {
        "status": "received"
    }, 200


if __name__ == "__main__":

    port = int(
        os.environ.get("PORT", 5050)
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
