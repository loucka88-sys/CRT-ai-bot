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
client = Anthropic(api_key=CLAUDE_API_KEY)

ANALYSIS_TIMEFRAMES = {
    "4H": "240",
    "1H": "60",
    "15M": "15",
    "5M": "5"
}


def send_msg(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": str(text)},
        timeout=30
    )


def extract_symbol(raw):
    m = re.search(r"symbol=([A-Z0-9]+:[A-Z0-9]+)", raw)
    if m:
        return m.group(1)

    m = re.search(r"\b([A-Z]{3,10}USD|[A-Z0-9]{3,15}USDT)\b", raw)
    if m:
        s = m.group(1)
        if s in ["XAUUSD", "XAGUSD"]:
            return f"OANDA:{s}"
        if s.endswith("USDT"):
            return f"BINANCE:{s}"
        return s

    return None


def extract_trigger_timeframe(raw):
    m = re.search(r"timeframe=([A-Za-z0-9]+)", raw)
    return m.group(1) if m else "UNKNOWN"


def extract_price(raw):
    m = re.search(r"price=([0-9.]+)", raw)
    return m.group(1) if m else "UNKNOWN"


def tradingview_url(symbol, timeframe):
    return f"https://www.tradingview.com/chart/?symbol={symbol}&interval={timeframe}"


def screenshot_chart(symbol, timeframe_code):
    endpoint = f"https://production-sfo.browserless.io/screenshot?token={BROWSERLESS_API_KEY}"

    payload = {
        "url": tradingview_url(symbol, timeframe_code),
        "options": {"type": "png", "fullPage": False},
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": 45000},
        "viewport": {"width": 1440, "height": 1000}
    }

    r = requests.post(endpoint, json=payload, timeout=70)

    if r.status_code != 200:
        raise Exception(f"Browserless error {r.status_code}: {r.text[:500]}")

    return base64.b64encode(r.content).decode("utf-8")


def image_block(image_b64):
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": image_b64
        }
    }


def analyze_and_send(raw_text):
    try:
        symbol = extract_symbol(raw_text)
        trigger_tf = extract_trigger_timeframe(raw_text)
        trigger_price = extract_price(raw_text)

        if not symbol:
            send_msg(
                "⚠️ وصل تنبيه CRT لكن ما قدرت أستخرج الرمز.\n"
                "رسالة TradingView لازم تحتوي:\n"
                "symbol={{exchange}}:{{ticker}}"
            )
            return

        content = [{
            "type": "text",
            "text": f"""
وصل تنبيه CRT Pro من TradingView.

نص التنبيه:
{raw_text}

الرمز:
{symbol}

فريم التنبيه:
{trigger_tf}

سعر التنبيه:
{trigger_price}

اعتبر التنبيه رادار فقط. حلل الشارتات التالية بنفسك.
"""
        }]

        for tf_name, tf_code in ANALYSIS_TIMEFRAMES.items():
            image_b64 = screenshot_chart(symbol, tf_code)

            content.append({
                "type": "text",
                "text": f"صورة {symbol} على فريم {tf_name}"
            })

            content.append(image_block(image_b64))

        prompt = """
أنت محلل تداول محترف ومبدع. استخدم أفضل أسلوب تراه مناسبًا من:
Price Action, Market Structure, Liquidity, CRT, MSS, CISD, OTE, Waves, Fractals, Momentum.

لا تتقيد بطريقة واحدة.
حلل كأنك متداول بشري خبير يبحث عن أفضل فرصة دخول بعد تنبيه CRT.

الفريمات المتاحة:
4H / 1H / 15M / 5M

المطلوب:
- افهم الاتجاه والسياق من 4H و 1H.
- استخرج منطقة الدخول من 15M.
- دقق التريغر والستوب من 5M.
- قرر BUY أو SELL أو WAIT أو NO TRADE.
- إذا الفرصة جيدة لكن مخاطرتها أعلى، اكتب AGGRESSIVE.
- إذا الدخول الحالي غير مناسب لكن فيه منطقة أفضل، أعطني WAIT مع منطقة الدخول.
- لا تكن متشددًا زيادة ولا متهورًا.
- لا تعطيني صفقة بدون وقف وأهداف منطقية.

صيغة Telegram المطلوبة، مختصرة وواضحة:

🚨 CRT AI Sniper

📊 الأصل:
⏱ فريم التنبيه:
📌 القرار: BUY / SELL / WAIT / NO TRADE
🎚 النوع: STRONG / AGGRESSIVE / WAIT / NO TRADE
✅ الجودة:
🎯 الثقة:

💰 أفضل دخول:
🛑 وقف الخسارة:
🎯 TP1:
🚀 TP2:
📐 R:R:
⌛ المدة المتوقعة:

🧠 التحليل المختصر:
-

🧭 الفريمات:
4H:
1H:
15M:
5M:

⚠️ التنفيذ:
"""

        content.append({"type": "text", "text": prompt})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1300,
            messages=[{"role": "user", "content": content}]
        )

        send_msg(response.content[0].text.strip())

    except Exception as e:
        send_msg(f"❌ خطأ في التحليل\n{str(e)}")


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
