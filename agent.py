# -*- coding: utf-8 -*-

import os, re, base64, threading, requests
from flask import Flask, request
from anthropic import Anthropic

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
BROWSERLESS_API_KEY = os.getenv("BROWSERLESS_API_KEY")

MODEL = "claude-sonnet-4-5-20250929"
client = Anthropic(api_key=CLAUDE_API_KEY)

def send_msg(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": str(text)},
        timeout=30
    )

def extract_symbol(raw):
    m = re.search(r"symbol=([A-Z0-9]+:[A-Z0-9]+|[A-Z]{3,10}USD|[A-Z0-9]{3,15})", raw)
    if m:
        return m.group(1)

    pairs = re.findall(r"\b([A-Z]{3,10}USD|XAUUSD|XAGUSD|BTCUSDT|ETHUSDT|SOLUSDT)\b", raw)
    if pairs:
        s = pairs[0]
        if ":" not in s:
            if s in ["XAUUSD", "XAGUSD"]:
                return f"OANDA:{s}"
            return f"BINANCE:{s}"
        return s

    return None

def extract_timeframe(raw):
    m = re.search(r"timeframe=([A-Za-z0-9]+)", raw)
    if m:
        return m.group(1)

    m = re.search(r"\b(1m|3m|5m|15m|30m|1H|4H|1D|D|60|240|15)\b", raw, re.I)
    if m:
        tf = m.group(1).upper()
        return {"1H": "60", "4H": "240", "15M": "15", "1M": "1"}.get(tf, tf)

    return "60"

def tv_url(symbol, timeframe):
    return f"https://www.tradingview.com/chart/?symbol={symbol}&interval={timeframe}"

def take_screenshot(symbol, timeframe):
    url = tv_url(symbol, timeframe)

    endpoint = f"https://production-sfo.browserless.io/screenshot?token={BROWSERLESS_API_KEY}"

    payload = {
        "url": url,
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

    r = requests.post(endpoint, json=payload, timeout=70)

    if r.status_code != 200:
        raise Exception(f"Browserless error {r.status_code}: {r.text[:500]}")

    return base64.b64encode(r.content).decode("utf-8")

def analyze_and_send(raw_text):
    try:
        symbol = extract_symbol(raw_text)
        timeframe = extract_timeframe(raw_text)

        if not symbol:
            send_msg("⚠️ وصل تنبيه لكن ما قدرت أستخرج الرمز. لازم رسالة التنبيه تحتوي symbol أو اسم العملة.")
            return

        image_b64 = take_screenshot(symbol, timeframe)

        prompt = f"""
أنت أعظم محلل تداول بشري صارم، مدير مخاطر قبل أن تكون صياد فرص.

وصل تنبيه CRT Pro:
{raw_text}

الشارت المرفق هو {symbol} على فريم {timeframe}.

حلل الصورة بنفسك، لا تعتمد على التنبيه فقط.

افحص:
1. الاتجاه العام.
2. هل CRT مع الاتجاه أو ضده.
3. Sweep / Liquidity.
4. MSS / CISD.
5. OTE أو منطقة دخول منطقية.
6. وضوح الستوب.
7. هل الهدف قبل الستوب منطقي.
8. Risk/Reward لا يقل عن 1:2.
9. هل السعر تأخر وفات الدخول.
10. هل الفريم مناسب أم ضوضاء.

قراراتك فقط:
BUY / SELL / NO TRADE

إذا الصفقة ليست ممتازة قل NO TRADE.

اكتب الرسالة للتليقرام بهذا الشكل الجميل فقط بدون حشو:

🚨 توصية CRT AI

📊 الأصل:
⏱ الفريم:
📌 القرار:
✅ الجودة:
🎯 الثقة:

💰 الدخول:
🛑 وقف الخسارة:
🎯 الهدف الأول:
🚀 الهدف الثاني:
⌛ المدة المتوقعة:

🧠 سبب القرار:
⚠️ ملاحظة:
"""

        response = client.messages.create(
            model=MODEL,
            max_tokens=1200,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
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
