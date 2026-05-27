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

MEMORY = {}

TIMEFRAMES = {
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

    m = re.search(r"\b(XAUUSD|XAGUSD|[A-Z0-9]{3,15}USDT)\b", raw)
    if m:
        s = m.group(1)
        if s in ["XAUUSD", "XAGUSD"]:
            return f"OANDA:{s}"
        if s.endswith("USDT"):
            return f"BINANCE:{s}"
    return None

def extract_price(raw):
    m = re.search(r"price=([0-9.]+)", raw)
    return m.group(1) if m else "UNKNOWN"

def extract_tf(raw):
    m = re.search(r"timeframe=([A-Za-z0-9]+)", raw)
    return m.group(1) if m else "UNKNOWN"

def tv_url(symbol, tf):
    return f"https://www.tradingview.com/chart/?symbol={symbol}&interval={tf}"

def screenshot(symbol, tf):
    endpoint = f"https://production-sfo.browserless.io/screenshot?token={BROWSERLESS_API_KEY}"
    payload = {
        "url": tv_url(symbol, tf),
        "options": {"type": "png", "fullPage": False},
        "gotoOptions": {"waitUntil": "networkidle2", "timeout": 45000},
        "viewport": {"width": 1440, "height": 1000}
    }

    r = requests.post(endpoint, json=payload, timeout=80)
    if r.status_code != 200:
        raise Exception(f"Browserless error {r.status_code}: {r.text[:400]}")

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
            send_msg("⚠️ ما قدرت أستخرج الرمز. تأكد من رسالة التنبيه فيها symbol={{exchange}}:{{ticker}}")
            return

        old_memory = MEMORY.get(symbol, "لا توجد ذاكرة سابقة لهذا الأصل.")

        content = [{
            "type": "text",
            "text": f"""
وصل تنبيه CRT من TradingView.

نص التنبيه:
{raw_text}

الأصل:
{symbol}

فريم التنبيه:
{trigger_tf}

سعر التنبيه:
{trigger_price}

ذاكرة آخر تحليل لهذا الأصل:
{old_memory}

اعتبر التنبيه مجرد رادار. الآن افحص الفريمات بصريًا واستخرج الحركة القادمة.
"""
        }]

        for name, tf in TIMEFRAMES.items():
            b64 = screenshot(symbol, tf)
            content.append({"type": "text", "text": f"صورة {symbol} على فريم {name}"})
            content.append(img_block(b64))

        prompt = """
أنت Fractal Trading Engine + محلل تداول محترف.

مهمتك ليست تقييم التنبيه فقط.
مهمتك توقع الحركة القادمة واستخراج أفضل خطة دخول من الشارت.

استخدم أسلوبك بحرية:
- Price Action
- Market Structure
- Liquidity
- CRT
- MSS / CISD
- OTE
- Waves
- Fractal rhythm
- Expansion / Correction
- Supply & Demand
- Momentum

افحص الفريمات بهذا المنطق:

4H:
حدد الاتجاه والسياق الأكبر. هل الحركة الحالية تصحيح أم بداية انعكاس؟

1H:
حدد البنية والسيولة. هل هناك Sweep أو منطقة قرار؟

15M:
حدد النسخة المصغرة. هل الحركة الحالية تكرر حركة أكبر؟

5M:
حدد التريغر. هل يوجد MSS/CISD أو دخول جاهز أو ننتظر Pullback؟

Fractal Engine:
اسأل نفسك:
- هل 5M نسخة مصغرة من 15M؟
- هل 15M ينسخ 1H؟
- هل 1H يتماشى مع 4H؟
- ما السيناريو الأقرب: Sweep → MSS → Pullback → Expansion؟
- هل الحركة القادمة صعود أم نزول؟
- هل الدخول الآن أم Limit أم انتظار؟

قراراتك:
BUY MARKET
SELL MARKET
BUY LIMIT
SELL LIMIT
WAIT
NO TRADE

قواعد:
- لا تكن متشددًا لدرجة ترفض كل شيء.
- لا تكن متهورًا.
- إذا الدخول الحالي سيئ لكن فيه منطقة ممتازة، أعط LIMIT.
- إذا الفراكتال ناقص، أعط WAIT مع الشرط المطلوب.
- إذا الصفقة غير واضحة، NO TRADE.
- لازم الستوب والهدف منطقيين.
- لا تستخدم كلام طويل.

صيغة Telegram النهائية:

🚨 CRT AI Fractal Sniper

📊 الأصل:
⏱ فريم التنبيه:
📌 القرار:
🎚 النوع: STRONG / AGGRESSIVE / LIMIT / WAIT / NO TRADE
✅ الجودة:
🎯 الثقة:

💰 الدخول:
🛑 الستوب:
🎯 TP1:
🚀 TP2:
📐 R:R:
⌛ المدة:

🧬 قراءة الفراكتال:
-

🧭 الفريمات:
4H:
1H:
15M:
5M:

🧠 الحركة المتوقعة:
-

⚠️ التنفيذ:
-

🧾 ذاكرة للمتابعة:
اكتب جملة قصيرة جدًا تصلح أن تُحفظ للمرات القادمة.
"""

        content.append({"type": "text", "text": prompt})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1700,
            messages=[{"role": "user", "content": content}]
        )

        result = response.content[0].text.strip()

        memory_match = re.search(r"🧾 ذاكرة للمتابعة:\s*(.*)", result, re.S)
        if memory_match:
            MEMORY[symbol] = memory_match.group(1).strip()[:700]
        else:
            MEMORY[symbol] = result[-700:]

        send_msg(result)

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
