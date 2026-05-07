import os, re, concurrent.futures
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import yfinance as yf
import urllib.request as ur
import urllib.parse
import json as js
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)

# ──────────────────────────────────────────────────────────
# Israeli stock lookup: Hebrew name / short name → Yahoo ticker
# ──────────────────────────────────────────────────────────
IL_STOCKS = {
    # בנקים
    "לאומי":          "LUMI.TA",  "leumi":      "LUMI.TA", "lumi":   "LUMI.TA",
    "הפועלים":        "POLI.TA",  "hapoalim":   "POLI.TA", "poli":   "POLI.TA",
    "דיסקונט":        "DSCT.TA",  "discount":   "DSCT.TA", "dsct":   "DSCT.TA",
    "מזרחי":          "MZTF.TA",  "mizrahi":    "MZTF.TA", "mztf":   "MZTF.TA",
    "בנק ירושלים":    "JBNK.TA",  "jbnk":       "JBNK.TA",
    # ביטוח / פיננסים
    "הראל":           "HARL.TA",  "harl":       "HARL.TA",
    "מגדל":           "MGDL.TA",  "migdal":     "MGDL.TA", "mgdl":   "MGDL.TA",
    "כלל":            "CLIS.TA",  "clal":       "CLIS.TA",
    "מנורה":          "MNRT.TA",  "menora":     "MNRT.TA",
    "פיניקס":         "PHOE.TA",  "phoenix":    "PHOE.TA",
    # תקשורת
    "בזק":            "BEZQ.TA",  "bezeq":      "BEZQ.TA", "bezq":   "BEZQ.TA",
    "סלקום":          "SCOM.TA",  "cellcom":    "CEL",     "scom":   "SCOM.TA",
    "פרטנר":          "PTNR.TA",  "partner":    "PTNR.TA",
    "הוט":            "HOT.TA",   "hot":        "HOT.TA",
    # טכנולוגיה ישראלית
    "טבע":            "TEVA",     "teva":       "TEVA",
    "נייס":           "NICE",     "nice":       "NICE",
    "צ'ק פוינט":      "CHKP",     "checkpoint": "CHKP",   "chkp":   "CHKP",
    "אמדוקס":         "DOX",      "amdocs":     "DOX",
    "ויקס":           "WIX",      "wix":        "WIX",
    "מאנדיי":         "MNDY",     "monday":     "MNDY",
    "אינפיניטי":      "INFR.TA",
    "סייברארק":       "CYBR",     "cyberark":   "CYBR",
    "גילת":           "GILT.TA",  "gilat":      "GILT.TA",
    # נדל"ן
    "אמות":           "AMOT.TA",  "amot":       "AMOT.TA",
    "מליסרון":        "MLSR.TA",  "melisron":   "MLSR.TA",
    "עזריאלי":        "AZRG.TA",  "azrieli":    "AZRG.TA", "azrg":   "AZRG.TA",
    "ביג":            "BIG.TA",   "big":        "BIG.TA",
    "גב ים":          "GBIM.TA",  "gev yam":    "GBIM.TA",
    # אנרגיה / תעשייה
    "כיל":            "ICL",      "icl":        "ICL",
    "אלביט":          "ESLT",     "elbit":      "ESLT",
    "רפק":            "RPAC.TA",
    "אורמת":          "ORA",      "ormat":      "ORA",
    # צריכה / מזון
    "שטראוס":         "STRS.TA",  "strauss":    "STRS.TA",
    "עלית":           "ELIT.TA",  "elite":      "ELIT.TA",
    "אסם":            "ASMT.TA",  "osem":       "ASMT.TA",
    "שופרסל":         "SAE.TA",   "shufersal":  "SAE.TA",
    "רמי לוי":        "RMLI.TA",  "rami levy":  "RMLI.TA",
    # ביומד ישראלי
    "קמהדע":          "KMDA",     "kamada":     "KMDA",
    "מאיה":           "MAIA.TA",
    "אינסייטק":       "INSC.TA",
}

# ──────────────────────────────────────────────────────────
# TASE security number → Yahoo Finance ticker
# ──────────────────────────────────────────────────────────
TASE_NUMBERS = {
    # בנקים
    "604611":  "LUMI.TA",   # לאומי
    "1082074": "POLI.TA",   # הפועלים
    "695437":  "DSCT.TA",   # דיסקונט
    "1101763": "MZTF.TA",   # מזרחי טפחות
    "662197":  "JBNK.TA",   # בנק ירושלים
    # ביטוח / פיננסים
    "1099900": "HARL.TA",   # הראל
    "1084251": "MGDL.TA",   # מגדל
    "1107843": "PHOE.TA",   # פיניקס
    "93017":   "CLIS.TA",   # כלל
    "70318":   "MNRT.TA",   # מנורה
    # תקשורת
    "525029":  "BEZQ.TA",   # בזק
    "1081242": "SCOM.TA",   # סלקום
    "1082413": "PTNR.TA",   # פרטנר
    "1081166": "HOT.TA",    # הוט
    # נדל"ן
    "444790":  "AZRG.TA",   # עזריאלי
    "1081021": "AMOT.TA",   # אמות
    "370929":  "MLSR.TA",   # מליסרון
    "1082546": "BIG.TA",    # ביג
    "584678":  "GBIM.TA",   # גב ים
    # טכנולוגיה / ביומד
    "159029":  "TEVA",      # טבע
    "1121242": "NICE",      # נייס
    "1081757": "CHKP",      # צ'ק פוינט
    "1096062": "WIX",       # ויקס
    "1131345": "MNDY",      # מאנדיי
    "1095584": "ESLT",      # אלביט
    "577093":  "ICL",       # כיל
    "1082545": "KMDA",      # קמהדע
    # צריכה / מזון
    "475020":  "STRS.TA",   # שטראוס
    "1082710": "SAE.TA",    # שופרסל
    "1082991": "RMLI.TA",   # רמי לוי
    "315015":  "ELIT.TA",   # עלית
    # אנרגיה
    "1093738": "ORA",       # אורמת
}

def resolve_ticker(raw: str) -> str:
    """
    Convert user input to a valid Yahoo Finance ticker.
    Handles: TASE security numbers, Hebrew names, English aliases, .TA suffix.
    """
    q = raw.strip()

    # 1. Pure number → TASE security number
    if q.isdigit():
        # Check static mapping first
        if q in TASE_NUMBERS:
            return TASE_NUMBERS[q]
        # Fallback: try {number}.TA format (Yahoo Finance supports some TASE numbers)
        return q + ".TA"

    # 2. Direct lookup in Hebrew/English dictionary
    found = IL_STOCKS.get(q.lower()) or IL_STOCKS.get(q)
    if found:
        return found

    # 3. Already has .TA
    if q.upper().endswith(".TA"):
        return q.upper()

    # 4. US ticker or unknown — return as-is uppercase
    return q.upper()

@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def fmt(val, decimals=2):
    if val is None: return "N/A"
    try: return round(float(val), decimals)
    except: return "N/A"

def pct(cur, prev):
    try:
        if not cur or not prev or float(prev) == 0: return 0
        return round((float(cur) - float(prev)) / float(prev) * 100, 2)
    except: return 0

# ──────────────────────────────────────────────────────────
# Multi-source analyst target fetcher
# ──────────────────────────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/json,*/*",
}

def _fetch_url(url, timeout=6):
    req = ur.Request(url, headers=HEADERS)
    return ur.urlopen(req, timeout=timeout).read().decode("utf-8", errors="ignore")

# ── Translation cache ─────────────────────────────────────
_TRANS_CACHE = {}

def translate_he(text):
    """Translate English text to Hebrew using MyMemory free API."""
    if not text or len(text.strip()) < 3:
        return text
    if any('א' <= c <= 'ת' for c in text):
        return text
    if text in _TRANS_CACHE:
        return _TRANS_CACHE[text]
    try:
        url = f"https://api.mymemory.translated.net/get?q={urllib.parse.quote(text[:400])}&langpair=en|he"
        r = js.loads(_fetch_url(url, timeout=5))
        translated = r.get("responseData", {}).get("translatedText", "")
        if translated and len(translated) > 2 and "MYMEMORY" not in translated.upper():
            _TRANS_CACHE[text] = translated
            return translated
    except:
        pass
    return text

# ── Technical target calculator ───────────────────────────
def calc_technical_target(ticker, current_price):
    """Calculate price target using technical analysis when no analyst target available."""
    try:
        hist = yf.Ticker(ticker).history(period="6mo", interval="1d")
        if hist.empty or len(hist) < 14:
            return None

        closes = [float(x) for x in hist['Close'].values]
        highs  = [float(x) for x in hist['High'].values]
        lows   = [float(x) for x in hist['Low'].values]

        n20 = min(20, len(closes)); n50 = min(50, len(closes))
        ma20 = sum(closes[-n20:]) / n20
        ma50 = sum(closes[-n50:]) / n50

        # RSI (14 periods)
        seg = closes[-15:]
        deltas = [seg[i] - seg[i-1] for i in range(1, len(seg))]
        g = sum(d for d in deltas if d > 0) / 14
        l = sum(-d for d in deltas if d < 0) / 14
        rsi = 100 - (100 / (1 + g / l)) if l > 0 else 80.0

        support    = min(lows[-20:])
        resistance = max(highs[-20:])

        r20 = closes[-n20:]
        m   = sum(r20) / len(r20)
        std = (sum((x - m) ** 2 for x in r20) / len(r20)) ** 0.5
        bb_upper = m + 2 * std
        bb_lower = m - 2 * std

        cp = float(current_price)
        if rsi < 35:
            target, method, confidence = resistance * 0.97, f"RSI={rsi:.0f} — מכירת יתר, יעד לפי התנגדות", "גבוהה"
        elif rsi > 72:
            target, method, confidence = cp * 1.04, f"RSI={rsi:.0f} — קנייה יתר, יעד שמרני", "נמוכה"
        elif ma20 > ma50:
            target, method, confidence = min(resistance * 1.03, cp * 1.18), f"מגמה עולה (MA20>MA50), יעד לפי התנגדות", "בינונית"
        else:
            target, method, confidence = min(ma50 * 1.05, cp * 1.09), "מגמה יורדת, יעד שמרני לפי MA50", "נמוכה"

        return {
            "target": round(target, 2), "method": method, "confidence": confidence,
            "rsi": round(rsi, 1), "ma20": round(ma20, 2), "ma50": round(ma50, 2),
            "support": round(support, 2), "resistance": round(resistance, 2),
            "bb_upper": round(bb_upper, 2), "bb_lower": round(bb_lower, 2),
            "technical": True,
        }
    except:
        return None

# ── Source 1: Yahoo Finance (via yfinance) ────────────────
def target_yahoo(ticker, info):
    try:
        t = info.get("targetMeanPrice")
        n = info.get("numberOfAnalystOpinions", 0)
        if t and float(t) > 0:
            return {"source": "Yahoo Finance", "target": float(t), "analysts": n or 1}
    except: pass
    return None

# ── Source 2: Finviz (US stocks only) ────────────────────
def target_finviz(ticker):
    try:
        if ".TA" in ticker.upper(): return None
        html  = _fetch_url(f"https://finviz.com/quote.ashx?t={ticker}&ty=c&ta=1&p=d")
        match = re.search(r'Target Price[^\d]*?([\d,.]+)', html)
        if match:
            val = float(match.group(1).replace(",",""))
            if val > 0:
                return {"source": "Finviz", "target": val, "analysts": 1}
    except: pass
    return None

# ── Source 3: Stock Analysis (US stocks) ─────────────────
def target_stockanalysis(ticker):
    try:
        if ".TA" in ticker.upper(): return None
        clean = ticker.replace("^","").lower()
        html  = _fetch_url(f"https://stockanalysis.com/stocks/{clean}/forecast/")
        match = re.search(r'"priceTarget"[^}]*?"average":\s*([\d.]+)', html)
        if not match:
            match = re.search(r'Price Target.*?\$([\d,.]+)', html)
        if match:
            val = float(match.group(1).replace(",",""))
            if val > 0:
                return {"source": "Stock Analysis", "target": val, "analysts": 1}
    except: pass
    return None

# ── Source 4: Macrotrends (US stocks) ────────────────────
def target_macrotrends(ticker):
    try:
        if ".TA" in ticker.upper(): return None
        clean = ticker.lower()
        html  = _fetch_url(f"https://www.macrotrends.net/assets/php/stock_price_history.php?t={clean}")
        match = re.search(r'price.target.*?\$([\d,.]+)', html, re.IGNORECASE)
        if match:
            val = float(match.group(1).replace(",",""))
            if val > 0:
                return {"source": "Macrotrends", "target": val, "analysts": 1}
    except: pass
    return None

# ── Source 5: Yahoo Finance API v2 (more detail) ─────────
def target_yahoo_v2(ticker):
    try:
        url  = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}?modules=financialData,recommendationTrend"
        data = js.loads(_fetch_url(url))
        fd   = data["quoteSummary"]["result"][0]["financialData"]
        t    = fd.get("targetMeanPrice", {}).get("raw")
        lo   = fd.get("targetLowPrice",  {}).get("raw")
        hi   = fd.get("targetHighPrice", {}).get("raw")
        n    = fd.get("numberOfAnalystOpinions", {}).get("raw", 0)
        if t and float(t) > 0:
            return {
                "source":   "Yahoo Finance (v2)",
                "target":   float(t),
                "low":      float(lo) if lo else None,
                "high":     float(hi) if hi else None,
                "analysts": int(n) if n else 1,
            }
    except: pass
    return None

# ── Source 6: Bizportal (Israeli stocks) ─────────────────
def target_bizportal(ticker):
    try:
        if ".TA" not in ticker.upper(): return None
        # Extract base symbol (LUMI from LUMI.TA)
        base = ticker.upper().replace(".TA","")
        # Bizportal analyst targets page
        html  = _fetch_url(f"https://www.bizportal.co.il/capitalmarket/quote/analyst/{base}")
        match = re.search(r'יעד מחיר[^\d]*([\d,]+)', html)
        if match:
            val = float(match.group(1).replace(",",""))
            if val > 0:
                return {"source": "Bizportal", "target": val, "analysts": 1}
    except: pass
    return None

# ── Aggregate all sources ─────────────────────────────────
def fetch_multi_targets(ticker, yf_info):
    """Run all source fetchers in parallel, aggregate results."""
    tasks = {
        "yahoo_v2":      lambda: target_yahoo_v2(ticker),
        "yahoo":         lambda: target_yahoo(ticker, yf_info),
        "finviz":        lambda: target_finviz(ticker),
        "stockanalysis": lambda: target_stockanalysis(ticker),
        "bizportal":     lambda: target_bizportal(ticker),
    }

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(fn): name for name, fn in tasks.items()}
        for future in concurrent.futures.as_completed(futures, timeout=8):
            try:
                r = future.result()
                if r and r.get("target") and float(r["target"]) > 0:
                    results.append(r)
            except: pass

    if not results:
        return None

    # Filter: remove targets below current price (stale)
    current = float(yf_info.get("currentPrice") or yf_info.get("regularMarketPrice") or 0)
    valid = [r for r in results if current == 0 or float(r["target"]) >= current * 0.95]
    if not valid:
        valid = results  # fallback: use all even if below price

    # Weighted average (sources with more analysts get more weight)
    total_weight = sum(r.get("analysts", 1) for r in valid)
    avg_target   = sum(r["target"] * r.get("analysts", 1) for r in valid) / total_weight

    # Collect low/high range
    lows  = [r["low"]  for r in valid if r.get("low")]
    highs = [r["high"] for r in valid if r.get("high")]

    total_analysts = sum(r.get("analysts", 1) for r in valid)

    return {
        "target":          round(avg_target, 2),
        "target_low":      round(min(lows),  2) if lows  else None,
        "target_high":     round(max(highs), 2) if highs else None,
        "sources":         [r["source"] for r in valid],
        "source_count":    len(valid),
        "analyst_count":   total_analysts,
        "breakdown":       valid,
        "stale_discarded": len(results) - len(valid),
    }

# ── News + psychology engine
# ──────────────────────────────────────────────────────────
POSITIVE_WORDS = [
    "beat","record","surge","jump","soar","profit","revenue","growth","upgrade",
    "buyback","dividend","partnership","deal","launch","approval","approved",
    "strong","bullish","rally","outperform","raised","higher","exceeded"
]
NEGATIVE_WORDS = [
    "miss","loss","decline","fall","drop","cut","downgrade","layoff","lawsuit",
    "recall","warning","concern","weak","bearish","below","disappoints","fraud",
    "investigation","debt","risk","lower","missed","sell"
]

def score_news(title):
    t = title.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in t)
    neg = sum(1 for w in NEGATIVE_WORDS if w in t)
    return pos - neg

def fetch_news(ticker):
    """Fetch recent news headlines via Yahoo Finance + translate to Hebrew."""
    try:
        t    = yf.Ticker(ticker)
        news = t.news or []
        items = []
        for n in news[:8]:
            content = n.get("content", {})
            title   = content.get("title") or n.get("title","")
            pub     = content.get("provider", {}).get("displayName") or n.get("publisher","")
            ts      = content.get("pubDate") or ""
            age = ""
            try:
                if ts:
                    dt  = datetime.fromisoformat(ts.replace("Z","+00:00"))
                    now = datetime.now(timezone.utc)
                    h   = int((now - dt).total_seconds() / 3600)
                    age = f"{h}ש'" if h < 24 else f"{h//24}י'"
            except: pass
            if title:
                items.append({
                    "title":    title,
                    "title_he": "",
                    "pub":      pub,
                    "age":      age,
                    "score":    score_news(title),
                    "url":      content.get("canonicalUrl",{}).get("url","") or n.get("link","")
                })
        # Translate all titles in parallel
        if items:
            def do_trans(item):
                item["title_he"] = translate_he(item["title"])
                return item
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                items = list(ex.map(do_trans, items, timeout=8))
        return items
    except:
        return []

def build_psychology(news_items, change, pos52, upside):
    """Generate investor psychology narrative from news + price data."""
    if not news_items:
        return {
            "sentiment": "ניטרלי",
            "summary":   "לא נמצאו חדשות אחרונות למניה זו.",
            "headlines": [],
            "outside_box": "כשאין חדשות — זו לפעמים ההזדמנות. השוק לא שם לב, המוסדיים כן."
        }

    total_score = sum(n["score"] for n in news_items)
    pos_count   = sum(1 for n in news_items if n["score"] > 0)
    neg_count   = sum(1 for n in news_items if n["score"] < 0)

    # Overall sentiment
    if total_score >= 3:   sentiment = "חיובי מאוד 🟢"
    elif total_score >= 1: sentiment = "חיובי 🟡"
    elif total_score <= -3: sentiment = "שלילי מאוד 🔴"
    elif total_score <= -1: sentiment = "שלילי 🟠"
    else:                   sentiment = "ניטרלי ⚪"

    # Build summary
    top_pos = [n["title"] for n in news_items if n["score"] > 0][:2]
    top_neg = [n["title"] for n in news_items if n["score"] < 0][:1]

    parts = []
    if top_pos:
        parts.append(f"חדשות חיוביות: {top_pos[0][:80]}{'...' if len(top_pos[0])>80 else ''}")
    if top_neg:
        parts.append(f"סיכון לשים לב אליו: {top_neg[0][:80]}{'...' if len(top_neg[0])>80 else ''}")
    summary = " | ".join(parts) if parts else "חדשות מעורבות — אין כיוון חד."

    # Outside-the-box insight
    outside = _outside_box(news_items, change, pos52, upside, total_score)

    return {
        "sentiment":   sentiment,
        "summary":     summary,
        "pos_count":   pos_count,
        "neg_count":   neg_count,
        "total_score": total_score,
        "headlines":   news_items[:5],
        "outside_box": outside
    }

def _outside_box(news, change, pos52, upside, score):
    """Generate a non-obvious insight."""
    hints = []

    # Contrarian check
    if score >= 3 and pos52 and pos52 > 85:
        hints.append("כולם נלהבים — זה בדיוק הזמן לבדוק אם המחיר כבר מגלם את הבשורה. שאל: מה עוד צריך לקרות כדי שיעלה יותר?")

    if score <= -2 and pos52 and pos52 < 30:
        hints.append("חדשות רעות + מחיר בשפל — לפעמים הפחד המקסימלי הוא נקודת הכניסה הטובה ביותר. בדוק אם הבעיה מבנית או זמנית.")

    # Momentum + news divergence
    if change and change > 3 and score < 0:
        hints.append("המניה עולה בזמן שהחדשות שליליות — סימן שהמוסדיים קונים בשקט. שוק נגד הנרטיב הפומבי.")

    if change and change < -2 and score > 1:
        hints.append("ירידה בזמן חדשות טובות — ייתכן שגדולים ממשים רווחים תוך ניצול האופטימיות. זהירות.")

    # Upside vs position
    if upside and upside > 40 and pos52 and pos52 < 50:
        hints.append(f"פוטנציאל עלייה של {upside}% לפי יעד האנליסטים, והמחיר עדיין בחצי התחתון של הטווח — נקודת כניסה היסטורית אפשרית.")

    if not hints:
        if upside and upside > 20:
            hints.append(f"האנליסטים רואים פוטנציאל +{upside}%, אך שאל את עצמך: מה הם יודעים שהשוק לא? חפש בדוחות הרבעון האחרון.")
        else:
            hints.append("הנתונים הטכניים סבירים, אבל הבדיקה האמיתית היא: מה מודל ההכנסות של החברה ב-3 השנים הקרובות? הגרף לא מספר את כל הסיפור.")

    return hints[0]

# ──────────────────────────────────────────────────────────
# Core stock data
# ──────────────────────────────────────────────────────────
def get_stock_data(ticker, with_news=False):
    t    = yf.Ticker(ticker)
    inf  = t.fast_info
    info = t.info
    price  = fmt(inf.last_price)
    prev   = fmt(inf.previous_close)
    change = pct(price, prev)
    hi52   = fmt(inf.year_high)
    lo52   = fmt(inf.year_low)
    target = fmt(info.get("targetMeanPrice")) if info.get("targetMeanPrice") else None
    pe     = fmt(info.get("trailingPE"), 1)   if info.get("trailingPE")     else None

    try:
        pos52 = round((float(price)-float(lo52))/(float(hi52)-float(lo52))*100, 1)
    except: pos52 = 50

    # ── Multi-source analyst targets ──────────────────────
    multi = fetch_multi_targets(ticker, info)

    target_stale   = False
    target_sources = []
    analyst_count  = 0
    target_low     = None
    target_high    = None

    if multi and multi["target"]:
        target         = multi["target"]
        target_sources = multi["sources"]
        analyst_count  = multi["analyst_count"]
        target_low     = multi["target_low"]
        target_high    = multi["target_high"]
        if float(target) < float(price) * 0.95:
            target_stale = True
    elif target:
        if float(target) < float(price) * 0.99:
            target_stale = True
            target       = None

    # ── אם אין יעד אנליסטים תקף → ניתוח טכני עצמאי ──────
    tech_info = None
    if (not target or target_stale) and price != "N/A":
        tech_info = calc_technical_target(ticker, price)
        if tech_info:
            target         = tech_info["target"]
            target_sources = ["ניתוח טכני עצמאי"]
            target_stale   = False
            analyst_count  = 0
    # ──────────────────────────────────────────────────────

    upside = round((float(target)-float(price))/float(price)*100, 1) if target else None

    if upside and upside > 15 and change > 0 and pos52 < 80:     signal = "קנייה"
    elif upside and upside < 5 and pos52 > 80 and not target_stale:
                                                                  signal = "מכירה"
    elif upside and upside > 8:                                   signal = "קנייה מתונה"
    elif pos52 and pos52 > 85 and not upside:                     signal = "המתנה — שיא"
    else:                                                         signal = "המתנה"

    stop = fmt(float(price)*0.93) if price != "N/A" else "—"
    tp   = target if target else fmt(float(price)*1.10)

    # סימון מטבע נכון
    # ILA = אגורות (1/100 ₪), ILS = שקל — שניהם מוצגים עם ₪
    currency = info.get("currency", "USD")
    if currency in ("ILS", "ILA"):
        sym = "₪"
    elif currency == "USD":
        sym = "$"
    elif currency == "EUR":
        sym = "€"
    elif currency == "GBP":
        sym = "£"
    else:
        sym = currency + " "

    result = {
        "ticker":        ticker,
        "name":          info.get("longName") or info.get("shortName") or ticker,
        "price":         price, "prev": prev, "change": change, "up": change >= 0,
        "hi52":          hi52,  "lo52": lo52, "pos52": pos52,
        "sector":        info.get("sector","—"),
        "mktcap":        info.get("marketCap"),
        "pe":             pe,
        "target":         target,
        "target_low":     target_low,
        "target_high":    target_high,
        "target_sources": target_sources,
        "target_stale":   target_stale,
        "analyst_count":  analyst_count,
        "upside":         upside,
        "signal":         signal, "stop": stop, "tp": tp,
        "currency":       currency,
        "currency_sym":   sym,
        "volume":         fmt(inf.three_month_average_volume, 0) if hasattr(inf,"three_month_average_volume") else None,
        "tech_info":      tech_info,
    }

    if with_news:
        news_items = fetch_news(ticker)
        result["psychology"] = build_psychology(news_items, change, pos52, upside)

    return result

# ──────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────
MARKET_SYMBOLS = {
    "sp500":"^GSPC","nasdaq":"^IXIC","dow":"^DJI",
    "usdils":"USDILS=X","gold":"GC=F","oil":"BZ=F",
}

@app.route("/api/history/<path:ticker>")
def history(ticker):
    """Return OHLCV candle data for charting (3 months, daily)."""
    resolved = resolve_ticker(ticker)
    try:
        t    = yf.Ticker(resolved)
        hist = t.history(period="3mo", interval="1d")
        if hist.empty:
            return jsonify([])
        data = []
        for ts, row in hist.iterrows():
            data.append({
                "time":  ts.strftime("%Y-%m-%d"),
                "open":  round(float(row['Open']),  4),
                "high":  round(float(row['High']),  4),
                "low":   round(float(row['Low']),   4),
                "close": round(float(row['Close']), 4),
            })
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/market")
def market():
    result = {}
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/TA35.TA?interval=1d&range=2d"
        req = ur.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        raw = js.loads(ur.urlopen(req, timeout=8).read())
        closes = raw["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        price  = fmt(closes[-1]); prev = fmt(closes[-2]) if len(closes)>1 else price
        change = pct(price, prev)
        result["ta35"] = {"price":price,"prev":prev,"change":change,"up":change>=0}
    except:
        result["ta35"] = {"price":"N/A","change":0,"up":True}

    for key, sym in MARKET_SYMBOLS.items():
        try:
            t=yf.Ticker(sym); inf=t.fast_info
            price=fmt(inf.last_price); prev=fmt(inf.previous_close)
            change=pct(price,prev)
            result[key]={"price":price,"prev":prev,"change":change,"up":change>=0}
        except:
            result[key]={"price":"N/A","change":0,"up":True}

    result["updated"] = datetime.now().strftime("%H:%M:%S")
    return jsonify(result)

@app.route("/api/stock/<path:ticker>")
def stock(ticker):
    resolved = resolve_ticker(ticker)
    errors   = []

    # Try resolved ticker first, then .TA variant, then original
    candidates = [resolved]
    if not resolved.endswith(".TA"):
        candidates.append(resolved + ".TA")
    if resolved != ticker.upper():
        candidates.append(ticker.upper())

    for candidate in candidates:
        try:
            data = get_stock_data(candidate, with_news=True)
            # Sanity check — if price came back as N/A, try next
            if data.get("price") == "N/A":
                errors.append(f"{candidate}: price N/A")
                continue
            return jsonify(data)
        except Exception as e:
            errors.append(f"{candidate}: {e}")
            continue

    return jsonify({"error": f"לא נמצאה מניה עבור '{ticker}'. נסה את הטיקר המלא (לדוגמה: LUMI.TA, BEZQ.TA).", "tried": errors}), 404


@app.route("/api/search/<path:query>")
def search(query):
    """Return matching tickers — supports Hebrew names, English, and TASE security numbers."""
    q    = query.strip()
    out  = []
    seen = set()

    # 1. TASE security number (pure digits)
    if q.isdigit():
        if q in TASE_NUMBERS:
            ticker = TASE_NUMBERS[q]
            out.append({"name": f"נייר ערך {q}", "ticker": ticker, "type": "tase_number"})
            seen.add(ticker)
        else:
            # Try {number}.TA
            out.append({"name": f"נייר ערך {q} (TASE)", "ticker": q + ".TA", "type": "tase_number"})
            seen.add(q + ".TA")
        return jsonify(out)

    # 2. Hebrew / English name lookup
    ql = q.lower()
    for name, ticker in IL_STOCKS.items():
        if ql in name.lower() or ql in ticker.lower():
            if ticker not in seen:
                seen.add(ticker)
                out.append({"name": name, "ticker": ticker, "type": "il"})

    # 3. Also search TASE numbers table by ticker match
    for num, ticker in TASE_NUMBERS.items():
        if ql in ticker.lower() and ticker not in seen:
            seen.add(ticker)
            out.append({"name": f"{ticker} (נייר {num})", "ticker": ticker, "type": "tase"})

    # 4. Yahoo Finance live search
    try:
        url = f"https://query1.finance.yahoo.com/v1/finance/search?q={query}&quotesCount=6&newsCount=0&enableFuzzyQuery=true"
        req = ur.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        raw = js.loads(ur.urlopen(req, timeout=5).read())
        for item in raw.get("quotes", [])[:6]:
            sym  = item.get("symbol","")
            name = item.get("longname") or item.get("shortname","")
            exch = item.get("exchange","")
            if sym and sym not in seen:
                seen.add(sym)
                label = f"{name}" + (f" ({exch})" if exch else "")
                out.append({"name": label, "ticker": sym, "type": "yahoo"})
    except: pass

    return jsonify(out[:8])

SCAN_LIST = [
    "NVDA","AAPL","MSFT","META","GOOGL","AMZN","TSLA","AMD","ORCL","CRM",
    "JPM","V","UNH","XOM","LLY","TEVA","NICE","CHKP","WIX","MNDY",
]

@app.route("/api/opportunity")
def opportunity():
    results = []
    for ticker in SCAN_LIST:
        try:
            d = get_stock_data(ticker, with_news=True)
            if d["signal"] in ("קנייה","קנייה מתונה") and d["upside"] and d["upside"]>8:
                results.append(d)
        except: continue
    results.sort(key=lambda x: x.get("upside") or 0, reverse=True)
    return jsonify(results[:5])

@app.route("/api/position/<ticker>/<float:entry_price>")
def position(ticker, entry_price):
    try:
        d     = get_stock_data(ticker.upper(), with_news=True)
        price = float(d["price"])
        pnl   = round((price - entry_price) / entry_price * 100, 2)
        d["entry"]  = entry_price
        d["pnl"]    = pnl
        d["pnl_up"] = pnl >= 0
        if pnl < -7:
            d["position_advice"] = "⚠️ מתחת לסטופ לוס — שקול לצאת"
        elif pnl > 20 and d["signal"] == "מכירה":
            d["position_advice"] = "✅ רווח יפה + איתות מכירה — שקול לממש"
        elif d["signal"] in ("קנייה","קנייה מתונה"):
            d["position_advice"] = "💪 המשך להחזיק — הכיוון חיובי"
        else:
            d["position_advice"] = "⏳ המתן לבהירות"
        return jsonify(d)
    except Exception as e:
        return jsonify({"error": str(e)}), 400

SECTORS = {
    "טכנולוגיה": ["NVDA","AAPL","MSFT","AMD","ORCL","META","GOOGL"],
    "בנקים":     ["JPM","BAC","WFC","GS","MS"],
    "ביומד":     ["LLY","JNJ","PFE","MRNA","ABBV","TEVA"],
    "אנרגיה":    ["XOM","CVX","BP","COP","SLB"],
    "נדלן":      ["AMT","PLD","CCI","EQIX","SPG"],
    "ישראלי":    ["TEVA","NICE","CHKP","WIX","MNDY"],
}

@app.route("/api/sector/<name>")
def sector(name):
    tickers = SECTORS.get(name, SECTORS.get("טכנולוגיה"))
    results = []
    for t in tickers:
        try: results.append(get_stock_data(t, with_news=False))
        except: continue
    results.sort(key=lambda x: x.get("change") or 0, reverse=True)

    if not results:
        return jsonify({"stocks": [], "analysis": {}})

    changes = [float(r["change"]) for r in results if r.get("change") is not None]
    upsides = [float(r["upside"]) for r in results if r.get("upside") is not None]
    signals = [r["signal"] for r in results if r.get("signal")]

    avg_change = round(sum(changes) / len(changes), 2) if changes else 0
    avg_upside = round(sum(upsides) / len(upsides), 2) if upsides else 0
    buy_count  = sum(1 for s in signals if "קנייה" in s)
    sell_count = sum(1 for s in signals if "מכירה" in s)

    if avg_change > 1:    trend = "עולה 🟢"
    elif avg_change < -1: trend = "יורד 🔴"
    else:                 trend = "ניטרלי ⚪"

    best  = results[0]
    worst = results[-1]

    analysis = {
        "trend":        trend,
        "avg_change":   avg_change,
        "avg_upside":   avg_upside,
        "buy_count":    buy_count,
        "sell_count":   sell_count,
        "total":        len(results),
        "best_ticker":  best["ticker"],
        "best_name":    best.get("name", best["ticker"]),
        "best_change":  best["change"],
        "worst_ticker": worst["ticker"],
        "worst_name":   worst.get("name", worst["ticker"]),
        "worst_change": worst["change"],
        "sentiment":    "שוריש 📈" if avg_change > 0 else "דובי 📉",
        "summary":      f"הסקטור {trend} בממוצע {abs(avg_change):.1f}% | {buy_count}/{len(results)} מניות עם איתות קנייה | פוטנציאל ממוצע +{avg_upside:.1f}%",
    }
    return jsonify({"stocks": results, "analysis": analysis})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"Server running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
