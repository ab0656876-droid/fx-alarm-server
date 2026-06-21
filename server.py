import os
import time
import requests
import firebase_admin
from firebase_admin import credentials, messaging

# Firebase init
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY")
CHECK_INTERVAL = 60  # seconds

SYMBOL_MAP = {
    "XAUUSD": "XAU/USD",
    "XAGUSD": "XAG/USD",
    "USOIL": "WTI/USD",
    "ETHUSD": "ETH/USD",
    "EURUSD": "EUR/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "AUDUSD": "AUD/USD",
    "USDCHF": "USD/CHF",
    "USDCAD": "USD/CAD",
    "US30": "DJI",
}

def get_candle(pair):
    symbol = SYMBOL_MAP.get(pair)
    if not symbol:
        return None
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1min&outputsize=1&apikey={TWELVEDATA_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        candle = data["values"][0]
        return {
            "high": float(candle["high"]),
            "low": float(candle["low"]),
            "close": float(candle["close"]),
        }
    except:
        return None

def send_notification(token, pair, target, current, mode):
    title = f"FX Alert: {pair}"
    body = f"Target {target} hit! Current: {current}"
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={"pair": pair, "target": str(target), "current": str(current), "mode": mode},
            token=token,
        )
        messaging.send(message)
        print(f"Sent notification for {pair}")
    except Exception as e:
        print(f"Error sending: {e}")

def check_alerts():
    # Render environment থেকে alerts নেবে
    alerts_str = os.environ.get("ALERTS", "")
    if not alerts_str:
        return
    
    import json
    try:
        alerts = json.loads(alerts_str)
    except:
        return

    pairs = list(set(a["pair"] for a in alerts if a.get("active", True)))
    
    for pair in pairs:
        candle = get_candle(pair)
        if not candle:
            continue
        
        for alert in alerts:
            if alert["pair"] != pair:
                continue
            if not alert.get("active", True):
                continue
                
            target = float(alert["targetPrice"])
            direction = alert["direction"]
            token = alert["fcmToken"]
            mode = alert.get("mode", "ALARM")
            
            triggered = False
            if direction == "ABOVE" and candle["high"] >= target:
                triggered = True
            elif direction == "BELOW" and candle["low"] <= target:
                triggered = True
            
            if triggered:
                send_notification(token, pair, target, candle["close"], mode)

if __name__ == "__main__":
    print("FX Alarm Server started...")
    while True:
        try:
            check_alerts()
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(CHECK_INTERVAL)
