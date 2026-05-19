"""
Alpha Pro Strategic Terminal v3
- AI 예측 곡선 (6개월) + 마일스톤 점 (IPO/현재가/저점/고점/AI목표가)
- FRED 매크로 (미국 + 한국)
- 차트패턴 인식 + 종합 점수 (100점 만점)
- 한국주식 지원 (예: 005930.KS)
"""
import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.signal import find_peaks
from datetime import datetime, timedelta
import requests

FRED_API_KEY = "5986a12ba743119f15c35ae435aa758a"

st.set_page_config(page_title="Alpha Pro Terminal v3", layout="wide", page_icon="📈")

# ============ 스타일 ============
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', 'Noto Sans KR', sans-serif; }
.stApp { background: #0a0e1a; color: #e2e8f0; }
.block-container { padding-top: 1.5rem; max-width: 1400px; }

.title-bar { font-size: 22px; font-weight: 800; color: #f1f5f9; margin-bottom: 4px; }
.title-sub { font-size: 13px; color: #64748b; margin-bottom: 18px; }

.card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; }
.card-title { font-size: 12px; color: #94a3b8; font-weight: 600; margin-bottom: 4px; letter-spacing: 0.5px; }
.card-value { font-size: 26px; font-weight: 900; color: #f1f5f9; line-height: 1.1; }
.card-sub { font-size: 11px; color: #64748b; margin-top: 4px; }
.pos { color: #22c55e; }
.neg { color: #ef4444; }
.warn { color: #f59e0b; }

.section-h { font-size: 14px; font-weight: 800; color: #f1f5f9; margin: 18px 0 10px 0; display: flex; align-items: center; gap: 6px; }

.verdict { border-radius: 12px; padding: 22px 24px; color: white; margin-bottom: 14px; }
.v-strong-buy { background: linear-gradient(135deg, #16a34a, #15803d); }
.v-buy { background: linear-gradient(135deg, #22c55e, #16a34a); }
.v-hold { background: linear-gradient(135deg, #eab308, #ca8a04); }
.v-sell { background: linear-gradient(135deg, #f97316, #ea580c); }
.v-strong-sell { background: linear-gradient(135deg, #dc2626, #b91c1c); }
.v-label { font-size: 12px; opacity: 0.9; font-weight: 700; letter-spacing: 1px; }
.v-main { font-size: 36px; font-weight: 900; margin-top: 4px; }
.v-score { font-size: 14px; opacity: 0.95; margin-top: 6px; }

.stButton>button { background: #2563eb; color: white; border: none; font-weight: 700; border-radius: 8px; height: 44px; width: 100%; }
.stButton>button:hover { background: #1d4ed8; }
.stTextInput input { background: #111827 !important; color: #f1f5f9 !important; border: 1px solid #334155 !important; }

#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ============ 데이터 수집 ============
@st.cache_data(ttl=3600)
def fred_yoy(series_id):
    """FRED 시리즈의 YoY 변화율 (전년동월 대비)"""
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json",
                  "sort_order": "desc", "limit": 14}
        r = requests.get(url, params=params, timeout=8)
        if r.status_code == 200:
            obs = r.json().get("observations", [])
            vals = [float(o["value"]) for o in obs if o["value"] != "."]
            if len(vals) >= 13:
                yoy = (vals[0] - vals[12]) / vals[12] * 100
                prev_yoy = (vals[1] - vals[13]) / vals[13] * 100 if len(vals) >= 14 else yoy
                return yoy, prev_yoy
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=3600)
def fred_get(series_id):
    """FRED 시리즈 최신값 가져오기"""
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations"
        params = {"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json",
                  "sort_order": "desc", "limit": 2}
        r = requests.get(url, params=params, timeout=8)
        if r.status_code == 200:
            obs = r.json().get("observations", [])
            if len(obs) >= 2:
                cur = float(obs[0]["value"]) if obs[0]["value"] != "." else None
                prev = float(obs[1]["value"]) if obs[1]["value"] != "." else None
                return cur, prev
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=300)
def yf_last(ticker):
    """yfinance 최근가 + 전일대비"""
    try:
        h = yf.Ticker(ticker).history(period="5d")
        if len(h) >= 2:
            return float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
    except Exception:
        pass
    return None, None


@st.cache_data(ttl=300)
def get_macro_all():
    """모든 매크로 지표"""
    m = {}
    # 글로벌 자산
    m["sp500"] = yf_last("^GSPC")
    m["nasdaq"] = yf_last("^IXIC")
    m["gold"] = yf_last("GC=F")
    m["btc"] = yf_last("BTC-USD")
    m["vix"] = yf_last("^VIX")
    m["dxy"] = yf_last("DX-Y.NYB")
    m["usdkrw"] = yf_last("KRW=X")
    m["usdjpy"] = yf_last("JPY=X")
    m["wti"] = yf_last("CL=F")
    m["kospi"] = yf_last("^KS11")
    # 금리 - yfinance가 FRED보다 실시간 (^TNX = 10년, ^FVX = 5년, ^IRX = 13주)
    # 2년물 (^TYX는 30년이라 안 맞음, FRED에서 가져옴)
    m["us10y_yf"] = yf_last("^TNX")
    # FRED 미국 유동성/금리
    m["fed_assets"] = fred_get("WALCL")      # 연준 총자산
    m["reserves"] = fred_get("WRESBAL")      # 지급준비금
    m["rrp"] = fred_get("RRPONTSYD")          # 역레포
    m["tga"] = fred_get("WTREGEN")            # TGA
    m["us10y"] = fred_get("DGS10")            # 10년물 (FRED 백업)
    m["us2y"] = fred_get("DGS2")              # 2년물
    m["hy_spread"] = fred_get("BAMLH0A0HYM2") # 하이일드 스프레드
    # 인플레이션 지표
    m["cpi_yoy"] = fred_get("CPIAUCSL")        # CPI (수준값, YoY 계산은 별도)
    m["core_cpi"] = fred_get("CPILFESL")        # Core CPI
    m["ppi"] = fred_get("PPIACO")               # PPI
    m["unemploy"] = fred_get("UNRATE")          # 실업률
    m["pce"] = fred_get("PCEPI")                # PCE 물가
    m["real_pce"] = fred_get("PCEC96")          # Real PCE
    # 경기침체 지표
    m["sahm"] = fred_get("SAHMREALTIME")        # 삼의 법칙 (실시간)
    m["lei"] = fred_get("USSLIND")              # 선행지수
    m["ism_pmi"] = fred_get("NAPM")             # ISM PMI
    m["recession_prob"] = fred_get("RECPROUSM156N")  # NY연준 경기침체 확률
    m["gdp"] = fred_get("A191RL1Q225SBEA")          # 실질 GDP 성장률 (분기)
    m["payrolls"] = fred_get("PAYEMS")                # 비농업 고용
    # YoY 변화율
    m["cpi_yoy_v"] = fred_yoy("CPIAUCSL")
    m["core_cpi_yoy"] = fred_yoy("CPILFESL")
    m["ppi_yoy"] = fred_yoy("PPIACO")
    m["pce_yoy"] = fred_yoy("PCEPI")
    # CNN 공포탐욕 (주식시장용)
    m["fg"] = (None, None)
    cnn_urls = [
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
        "https://production.dataviz.cnn.io/index/fearandgreed/graphdata/" + datetime.now().strftime("%Y-%m-%d"),
    ]
    for url in cnn_urls:
        try:
            r = requests.get(url,
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                                      "Accept": "application/json"},
                             timeout=8)
            if r.status_code == 200:
                d = r.json().get("fear_and_greed", {})
                cur = d.get("score")
                prev = d.get("previous_close")
                if cur is not None:
                    m["fg"] = (float(cur), float(prev) if prev is not None else None)
                    break
        except Exception:
            continue
    return m


# ============ 차트 패턴 인식 ============
def detect_pivots(prices, distance=10, prom_ratio=0.02):
    prom = prices.max() * prom_ratio
    peaks, _ = find_peaks(prices, distance=distance, prominence=prom)
    troughs, _ = find_peaks(-prices, distance=distance, prominence=prom)
    return peaks, troughs


def score_hs(prices, peaks):
    if len(peaks) < 3: return 0
    r = peaks[-min(6, len(peaks)):]
    best = 0
    for i in range(len(r) - 2):
        l, h, ri = r[i], r[i+1], r[i+2]
        pl, ph, pr = prices[l], prices[h], prices[ri]
        if ph > pl and ph > pr:
            sym = 1 - abs(pl - pr) / max(pl, pr)
            prom = (ph - max(pl, pr)) / ph
            s = (sym * 0.5 + prom * 0.5) * 100
            if s > best and sym > 0.85 and prom > 0.03: best = s
    return best


def score_ihs(prices, troughs):
    if len(troughs) < 3: return 0
    r = troughs[-min(6, len(troughs)):]
    best = 0
    for i in range(len(r) - 2):
        l, h, ri = r[i], r[i+1], r[i+2]
        pl, ph, pr = prices[l], prices[h], prices[ri]
        if ph < pl and ph < pr:
            sym = 1 - abs(pl - pr) / max(pl, pr)
            prom = (max(pl, pr) - ph) / max(pl, pr)
            s = (sym * 0.5 + prom * 0.5) * 100
            if s > best and sym > 0.85 and prom > 0.03: best = s
    return best


def score_dtop(prices, peaks):
    if len(peaks) < 2: return 0
    p1, p2 = peaks[-2], peaks[-1]
    sym = 1 - abs(prices[p1] - prices[p2]) / max(prices[p1], prices[p2])
    d = 1.0 if 15 <= (p2 - p1) <= 80 else 0.5
    s = sym * d * 100
    return s if sym > 0.92 and d > 0.7 else 0


def score_dbot(prices, troughs):
    if len(troughs) < 2: return 0
    t1, t2 = troughs[-2], troughs[-1]
    sym = 1 - abs(prices[t1] - prices[t2]) / max(prices[t1], prices[t2])
    d = 1.0 if 15 <= (t2 - t1) <= 80 else 0.5
    s = sym * d * 100
    return s if sym > 0.92 and d > 0.7 else 0


def score_cup(prices, troughs):
    if len(prices) < 60 or len(troughs) < 1: return 0
    rt = troughs[-min(4, len(troughs)):]
    if len(rt) == 0: return 0
    bi = rt[np.argmin([prices[t] for t in rt])]
    bot = prices[bi]
    ls, le = max(0, bi - 80), max(0, bi - 20)
    if le <= ls: return 0
    lrim = prices[ls:le].max()
    rseg = prices[bi:]
    if len(rseg) < 10: return 0
    rrim = rseg.max()
    sym = 1 - abs(lrim - rrim) / max(lrim, rrim)
    depth = (lrim - bot) / lrim
    ds = 1.0 if 0.10 <= depth <= 0.35 else 0.5
    rri = bi + np.argmax(rseg)
    hseg = prices[rri:]
    if len(hseg) >= 3:
        hd = (rrim - hseg.min()) / rrim
        hs_ = 1.0 if 0.02 <= hd <= 0.15 else 0.6
    else:
        hs_ = 0.5
    s = sym * ds * hs_ * 100
    return s if s > 50 and sym > 0.85 else 0


def score_asc_tri(prices, peaks, troughs):
    if len(peaks) < 2 or len(troughs) < 2: return 0
    rp = peaks[-min(3, len(peaks)):]
    rt = troughs[-min(3, len(troughs)):]
    pv = [prices[p] for p in rp]
    tv = [prices[t] for t in rt]
    flat = 1 - (max(pv) - min(pv)) / max(pv)
    rising = all(tv[i] < tv[i+1] for i in range(len(tv)-1)) if len(tv) >= 2 else False
    return flat * 100 if flat > 0.95 and rising else 0


def score_bull_flag(prices, lb=40):
    if len(prices) < lb + 20: return 0
    ps = prices[-lb-20]
    pe = prices[-lb]
    pg = (pe - ps) / ps
    rec = prices[-lb:]
    rng = (rec.max() - rec.min()) / rec.mean()
    drift = (rec[-1] - rec[0]) / rec[0]
    if pg > 0.20 and rng < 0.15 and -0.10 < drift < 0.05:
        return min(100, pg * 200 + (0.15 - rng) * 300)
    return 0


def detect_patterns(close):
    p = close.values
    peaks, troughs = detect_pivots(p)

    # 추세 방향 (최근 60일 vs 직전 60일 평균 비교)
    if len(p) >= 120:
        recent_avg = p[-60:].mean()
        prior_avg = p[-120:-60].mean()
        trend = "up" if recent_avg > prior_avg * 1.03 else "down" if recent_avg < prior_avg * 0.97 else "flat"
    else:
        trend = "flat"

    # 현재가 위치 (52주 박스 내 어디 있는지)
    high_52 = p[-252:].max() if len(p) >= 252 else p.max()
    low_52 = p[-252:].min() if len(p) >= 252 else p.min()
    pos = (p[-1] - low_52) / (high_52 - low_52) if high_52 > low_52 else 0.5

    # 최근 1개월 모멘텀
    mom_1m = (p[-1] - p[-21]) / p[-21] if len(p) >= 21 else 0

    pats = [
        {"name": "헤드앤숄더", "score": score_hs(p, peaks), "signal": "약세",
         "desc": "고점 3봉, 가운데가 가장 높음. 천장 반전 패턴."},
        {"name": "역헤드앤숄더", "score": score_ihs(p, troughs), "signal": "강세",
         "desc": "저점 3골, 가운데가 가장 깊음. 바닥 반전 패턴."},
        {"name": "더블탑", "score": score_dtop(p, peaks), "signal": "약세",
         "desc": "비슷한 두 봉우리. 저항 돌파 실패."},
        {"name": "더블바텀", "score": score_dbot(p, troughs), "signal": "강세",
         "desc": "비슷한 두 저점. 지지 확인 후 반전."},
        {"name": "컵앤핸들", "score": score_cup(p, troughs), "signal": "강세",
         "desc": "안정적 매집 후 돌파 시도."},
        {"name": "상승삼각형", "score": score_asc_tri(p, peaks, troughs), "signal": "강세",
         "desc": "수평저항 + 상승저점. 돌파 임박."},
        {"name": "불플래그", "score": score_bull_flag(p), "signal": "강세",
         "desc": "급등 후 횡보. 2차 상승 임박."},
    ]

    # 추세/위치 필터링 - 말이 안 되는 패턴은 점수 페널티
    for pat in pats:
        # 강세 패턴인데 고점권 + 하락 추세: 신뢰도 낮춤
        if pat["signal"] == "강세":
            if pos > 0.75 and trend == "down":
                pat["score"] *= 0.3  # 70% 깎음
            elif pos > 0.85:
                pat["score"] *= 0.5
            elif trend == "down" and mom_1m < -0.05:
                pat["score"] *= 0.6
        # 약세 패턴인데 저점권 + 상승 추세: 신뢰도 낮춤
        else:
            if pos < 0.25 and trend == "up":
                pat["score"] *= 0.3
            elif pos < 0.15:
                pat["score"] *= 0.5
            elif trend == "up" and mom_1m > 0.05:
                pat["score"] *= 0.6

    pats.sort(key=lambda x: x["score"], reverse=True)

    # 메타 정보 저장 (예측 곡선에서 활용)
    pats[0]["trend"] = trend
    pats[0]["pos"] = pos
    pats[0]["mom_1m"] = mom_1m
    return pats


# ============ 기술 지표 ============
def compute_indicators(h):
    h = h.copy()
    for p in [20, 60, 120, 240]:
        h[f'MA{p}'] = h['Close'].rolling(p).mean()
    delta = h['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    h['RSI'] = 100 - (100 / (1 + rs))
    e12 = h['Close'].ewm(span=12, adjust=False).mean()
    e26 = h['Close'].ewm(span=26, adjust=False).mean()
    h['MACD'] = e12 - e26
    h['MACD_sig'] = h['MACD'].ewm(span=9, adjust=False).mean()
    # 일목균형표
    h['Tenkan'] = (h['High'].rolling(9).max() + h['Low'].rolling(9).min()) / 2
    h['Kijun'] = (h['High'].rolling(26).max() + h['Low'].rolling(26).min()) / 2
    h['SenkouA'] = ((h['Tenkan'] + h['Kijun']) / 2).shift(26)
    h['SenkouB'] = ((h['High'].rolling(52).max() + h['Low'].rolling(52).min()) / 2).shift(26)
    h['Chikou'] = h['Close'].shift(-26)
    # 거래량 이동평균
    h['Vol_MA20'] = h['Volume'].rolling(20).mean()
    return h


def score_ichimoku(h):
    """일목균형표 점수 + 진단"""
    curr = h['Close'].iloc[-1]
    sa = h['SenkouA'].iloc[-1]
    sb = h['SenkouB'].iloc[-1]
    tenkan = h['Tenkan'].iloc[-1]
    kijun = h['Kijun'].iloc[-1]
    if pd.isna(sa) or pd.isna(sb):
        return 50, "데이터 부족"
    cloud_top = max(sa, sb)
    cloud_bot = min(sa, sb)
    score = 50
    diag = []
    if curr > cloud_top:
        score += 25; diag.append("구름대 위 (강세)")
    elif curr < cloud_bot:
        score -= 25; diag.append("구름대 아래 (약세)")
    else:
        diag.append("구름대 내부 (혼조)")
    if tenkan > kijun:
        score += 15; diag.append("전환선>기준선 (단기상승)")
    else:
        score -= 10; diag.append("전환선<기준선")
    if sa > sb:
        score += 10; diag.append("양운")
    else:
        score -= 10; diag.append("음운")
    return max(0, min(100, score)), " · ".join(diag)


def score_volume(h):
    """거래량 매매 신호"""
    if len(h) < 20: return 50, "데이터 부족"
    recent_vol = h['Volume'].iloc[-5:].mean()
    avg_vol = h['Vol_MA20'].iloc[-1]
    if pd.isna(avg_vol) or avg_vol == 0:
        return 50, "데이터 부족"
    ratio = recent_vol / avg_vol
    # 가격 방향
    price_chg = (h['Close'].iloc[-1] - h['Close'].iloc[-5]) / h['Close'].iloc[-5]
    score = 50
    diag = []
    if ratio > 1.5 and price_chg > 0.02:
        score = 75; diag.append(f"거래량 {ratio:.1f}배 + 상승 (매집)")
    elif ratio > 1.5 and price_chg < -0.02:
        score = 25; diag.append(f"거래량 {ratio:.1f}배 + 하락 (매도)")
    elif ratio < 0.7:
        score = 45; diag.append(f"거래량 {ratio:.1f}배 (관심 저조)")
    else:
        score = 55; diag.append(f"거래량 평이 ({ratio:.1f}배)")
    return score, " · ".join(diag)


# ============ AI 종합 점수 (100점 만점) ============
def score_all(hist, info, patterns, macro, is_kr=False):
    s = {}
    reasons_p, reasons_n = [], []
    curr = hist['Close'].iloc[-1]

    # 1. 차트 패턴
    top = patterns[0]
    if top["score"] > 30:
        if top["signal"] == "강세":
            s["차트패턴"] = 65 + min(30, top["score"] * 0.4)
            reasons_p.append(f"{top['name']} 강세패턴 (신뢰도 {top['score']:.0f})")
        else:
            s["차트패턴"] = 35 - min(30, top["score"] * 0.4)
            reasons_n.append(f"{top['name']} 약세패턴 (신뢰도 {top['score']:.0f})")
    else:
        s["차트패턴"] = 50

    # 추세 자체로 추가 페널티/보너스 (패턴 약해도 추세는 명확할 때)
    trend = top.get("trend", "flat")
    mom_1m = top.get("mom_1m", 0)
    if trend == "down" and mom_1m < -0.10:
        s["차트패턴"] = min(s["차트패턴"], 30)
        reasons_n.append(f"강한 하락추세 (1M {mom_1m*100:.1f}%)")
    elif trend == "up" and mom_1m > 0.10:
        s["차트패턴"] = max(s["차트패턴"], 70)

    # 2. 이평선 분석 (20/60/120/240)
    ma20 = hist['MA20'].iloc[-1]
    ma60 = hist['MA60'].iloc[-1]
    ma120 = hist['MA120'].iloc[-1] if not pd.isna(hist['MA120'].iloc[-1]) else ma60
    ma240 = hist['MA240'].iloc[-1] if not pd.isna(hist['MA240'].iloc[-1]) else ma60

    # 정배열/역배열 + 골든/데드크로스 + 이격도
    ma_score = 50
    # 정배열 (20>60>120>240)
    if ma20 > ma60 > ma120 > ma240:
        ma_score = 85; reasons_p.append("완벽 정배열 (20>60>120>240)")
    elif ma20 > ma60 > ma120:
        ma_score = 70; reasons_p.append("단중기 정배열")
    elif ma20 < ma60 < ma120 < ma240:
        ma_score = 15; reasons_n.append("완벽 역배열 (장기 하락)")
    elif ma20 < ma60 < ma120:
        ma_score = 30; reasons_n.append("단중기 역배열")
    else:
        ma_score = 50

    # 골든크로스 (20일선이 60일선 최근 상향돌파)
    if len(hist) >= 5:
        gc_now = hist['MA20'].iloc[-1] > hist['MA60'].iloc[-1]
        gc_prev = hist['MA20'].iloc[-5] <= hist['MA60'].iloc[-5]
        if gc_now and gc_prev:
            ma_score = max(ma_score, 80)
            reasons_p.append("최근 골든크로스 발생 (20>60)")
        dc_now = hist['MA20'].iloc[-1] < hist['MA60'].iloc[-1]
        dc_prev = hist['MA20'].iloc[-5] >= hist['MA60'].iloc[-5]
        if dc_now and dc_prev:
            ma_score = min(ma_score, 25)
            reasons_n.append("최근 데드크로스 발생 (20<60)")

    s["이평선"] = ma_score
    if curr > ma240:
        if curr / ma240 > 1.30:
            reasons_n.append(f"MA240 대비 +{(curr/ma240-1)*100:.0f}% 과열")
    else:
        reasons_n.append("장기추세선(MA240) 아래")

    # 3. RSI
    rsi = hist['RSI'].iloc[-1]
    if pd.isna(rsi): rsi = 50
    if rsi < 30:
        s["RSI"] = 85; reasons_p.append(f"RSI {rsi:.0f} - 과매도")
    elif rsi < 45: s["RSI"] = 65
    elif rsi < 55: s["RSI"] = 50
    elif rsi < 70: s["RSI"] = 35
    else:
        s["RSI"] = 15; reasons_n.append(f"RSI {rsi:.0f} - 과매수")

    # 4. MACD
    if hist['MACD'].iloc[-1] > hist['MACD_sig'].iloc[-1]:
        s["MACD"] = 70; reasons_p.append("MACD 골든크로스")
    else:
        s["MACD"] = 25; reasons_n.append("MACD 데드크로스")

    # 5. 성장성 (PER/PBR 제거 - 차트 기술적 분석 중심)
    g = info.get('revenueGrowth', 0) or 0
    if g > 0.30: s["성장성"] = 90; reasons_p.append(f"매출성장 {g*100:.0f}%")
    elif g > 0.15: s["성장성"] = 75
    elif g > 0.05: s["성장성"] = 60
    elif g > 0: s["성장성"] = 45
    elif g > -0.10: s["성장성"] = 25; reasons_n.append(f"매출성장 {g*100:.0f}%")
    else: s["성장성"] = 10; reasons_n.append(f"매출 급감 {g*100:.0f}%")

    # 8. VIX
    vix = macro.get("vix", (None, None))[0]
    if vix:
        if vix < 15: s["VIX"] = 70; reasons_p.append(f"VIX {vix:.1f} - 안정")
        elif vix < 20: s["VIX"] = 60
        elif vix < 30: s["VIX"] = 40; reasons_n.append(f"VIX {vix:.1f} - 변동성↑")
        else: s["VIX"] = 20; reasons_n.append(f"VIX {vix:.1f} - 극단공포")
    else:
        s["VIX"] = 50

    # 9. 공포탐욕
    fg = macro.get("fg", (None, None))[0]
    if fg:
        if fg < 25: s["공포탐욕"] = 75; reasons_p.append(f"공포탐욕 {fg:.0f} - 역발상매수")
        elif fg < 45: s["공포탐욕"] = 60
        elif fg < 55: s["공포탐욕"] = 50
        elif fg < 75: s["공포탐욕"] = 40
        else: s["공포탐욕"] = 25; reasons_n.append(f"공포탐욕 {fg:.0f} - 과열")
    else:
        s["공포탐욕"] = 50

    # 10. 미국 금리
    us10y = macro.get("us10y", (None, None))[0]
    if us10y:
        if us10y < 3.5: s["금리"] = 70; reasons_p.append(f"美 10Y {us10y:.2f}% - 우호")
        elif us10y < 4.5: s["금리"] = 55
        else: s["금리"] = 35; reasons_n.append(f"美 10Y {us10y:.2f}% - 부담")
    else:
        s["금리"] = 50

    # 11. 유동성 (연준 자산 추세)
    fa = macro.get("fed_assets", (None, None))
    if fa[0] and fa[1]:
        diff = fa[0] - fa[1]
        if diff > 0: s["유동성"] = 65; reasons_p.append("연준 자산 증가 (유동성↑)")
        else: s["유동성"] = 40; reasons_n.append("연준 자산 감소 (QT)")
    else:
        s["유동성"] = 50

    # 12. 하이일드 스프레드 (신용리스크)
    hy = macro.get("hy_spread", (None, None))[0]
    if hy:
        if hy < 3: s["신용"] = 70; reasons_p.append(f"HY스프레드 {hy:.2f}% - 안정")
        elif hy < 5: s["신용"] = 55
        else: s["신용"] = 30; reasons_n.append(f"HY스프레드 {hy:.2f}% - 신용경색")
    else:
        s["신용"] = 50

    # 13. 일목균형표
    ichi_score, ichi_diag = score_ichimoku(hist)
    s["일목"] = ichi_score
    if ichi_score >= 65: reasons_p.append(f"일목: {ichi_diag}")
    elif ichi_score <= 35: reasons_n.append(f"일목: {ichi_diag}")

    # 14. 거래량
    vol_score, vol_diag = score_volume(hist)
    s["거래량"] = vol_score
    if vol_score >= 65: reasons_p.append(vol_diag)
    elif vol_score <= 35: reasons_n.append(vol_diag)

    # 15. OBV (세력 매집)
    obv_s, obv_d = score_obv(hist)
    s["OBV"] = obv_s
    if obv_s >= 70: reasons_p.append(f"세력매집: {obv_d}")
    elif obv_s <= 35: reasons_n.append(f"세력분산: {obv_d}")

    # 16. POC (매물대)
    _, poc_s, poc_d = find_poc(hist)
    s["POC"] = poc_s
    if poc_s >= 70: reasons_p.append(f"POC: {poc_d}")
    elif poc_s <= 40: reasons_n.append(f"POC: {poc_d}")

    # 17. VCP (변동성 수축)
    vcp_s, vcp_d = score_vcp(hist)
    s["VCP"] = vcp_s
    if vcp_s >= 65: reasons_p.append(f"VCP: {vcp_d}")

    # 한국주식이면 원/달러 추가 반영
    if is_kr:
        krw = macro.get("usdkrw", (None, None))
        if krw[0] and krw[1]:
            if krw[0] < krw[1]: s["원화"] = 65; reasons_p.append("원화 강세 (외인유입 우호)")
            else: s["원화"] = 40; reasons_n.append("원화 약세")
        else:
            s["원화"] = 50

    # 가중치 (차트패턴 + 이평선 + 세력매집 중심)
    if is_kr:
        w = {"차트패턴": 0.18, "이평선": 0.15, "일목": 0.10,
             "RSI": 0.06, "MACD": 0.06, "거래량": 0.06,
             "OBV": 0.10, "POC": 0.09, "VCP": 0.07,
             "성장성": 0.04,
             "VIX": 0.02, "공포탐욕": 0.03, "금리": 0.02,
             "유동성": 0.01, "신용": 0.00, "원화": 0.01}
    else:
        w = {"차트패턴": 0.18, "이평선": 0.15, "일목": 0.10,
             "RSI": 0.06, "MACD": 0.06, "거래량": 0.06,
             "OBV": 0.11, "POC": 0.10, "VCP": 0.07,
             "성장성": 0.04,
             "VIX": 0.02, "공포탐욕": 0.03, "금리": 0.01,
             "유동성": 0.01, "신용": 0.00}
        tot = sum(w.values())
        w = {k: v/tot for k, v in w.items()}

    total = round(sum(s[k] * w.get(k, 0) for k in s), 1)

    if total >= 72: verdict, vclass = "적극 매수", "v-strong-buy"
    elif total >= 62: verdict, vclass = "매수", "v-buy"
    elif total >= 42: verdict, vclass = "중립 / 관망", "v-hold"
    elif total >= 30: verdict, vclass = "매도", "v-sell"
    else: verdict, vclass = "적극 매도", "v-strong-sell"

    return {"score": total, "verdict": verdict, "vclass": vclass,
            "breakdown": s, "weights": w,
            "reasons_p": reasons_p, "reasons_n": reasons_n}


# ============ AI 목표가 & 예측 곡선 ============
def calc_target(hist, info, rec_score, top_pattern=None):
    curr = hist['Close'].iloc[-1]
    high52 = hist['Close'].iloc[-252:].max() if len(hist) >= 252 else hist['Close'].max()
    low52 = hist['Close'].iloc[-252:].min() if len(hist) >= 252 else hist['Close'].min()
    tech_t = high52 + (high52 - low52) * 0.5
    analyst_t = info.get('targetMeanPrice')

    # 점수 보정 (50점=현재가, 더 극단적으로)
    # 80점이면 +30%, 20점이면 -30%
    score_mult = 1 + (rec_score - 50) / 100 * 0.8

    if analyst_t:
        base = tech_t * 0.35 + analyst_t * 0.65
    else:
        base = tech_t

    final = base * score_mult

    # 약세 패턴이고 점수 낮으면 현재가 아래로 떨어질 수도
    if top_pattern and top_pattern.get("signal") == "약세" and top_pattern["score"] > 30:
        if rec_score < 45:
            # 약세 패턴 + 낮은 점수 → 저점 방향
            final = min(final, curr * (0.85 if rec_score < 35 else 0.92))

    # 약세 추세에서는 목표가가 현재가보다 크게 높지 않게
    if top_pattern and top_pattern.get("trend") == "down" and rec_score < 55:
        final = min(final, curr * 1.05)

    return {
        "current": curr, "high52": high52, "low52": low52,
        "tech": tech_t, "analyst": analyst_t,
        "analyst_high": info.get('targetHighPrice'),
        "analyst_low": info.get('targetLowPrice'),
        "final": final, "upside": (final - curr) / curr * 100
    }


def build_forecast_curve(hist, target, top_pattern, months=6):
    """6개월 예측 곡선 - 패턴별로 다른 모양"""
    curr = target["current"]
    final = target["final"]
    days = months * 21
    last_date = hist.index[-1]
    dates = [last_date + timedelta(days=i*1.4) for i in range(1, days + 1)]
    t = np.linspace(0, 1, days)

    pname = top_pattern["name"] if top_pattern["score"] > 30 else ""
    signal = top_pattern["signal"] if top_pattern["score"] > 30 else "중립"
    diff = final - curr

    if pname == "더블바텀":
        # W자 마무리 후 상승: 한 번 더 살짝 눌렀다가 목표가로
        dip = -0.10 * np.exp(-((t - 0.2) ** 2) / 0.02)
        curve = curr + diff * (t ** 1.3) + dip * curr
    elif pname == "역헤드앤숄더":
        # 우견 형성 후 강한 상승
        dip = -0.06 * np.exp(-((t - 0.15) ** 2) / 0.015)
        curve = curr + diff * (1 / (1 + np.exp(-7 * (t - 0.35)))) + dip * curr
    elif pname == "컵앤핸들":
        # 핸들 형성 후 돌파
        handle = -0.04 * np.exp(-((t - 0.15) ** 2) / 0.01)
        curve = curr + diff * (t ** 1.5) + handle * curr
    elif pname == "상승삼각형" or pname == "불플래그":
        # 거의 직진 상승
        curve = curr + diff * (t ** 0.85)
    elif pname == "헤드앤숄더":
        # 우견 → 넥라인 붕괴
        bounce = 0.08 * np.exp(-((t - 0.15) ** 2) / 0.015)
        curve = curr + diff * (t ** 1.2) + bounce * curr
    elif pname == "더블탑":
        bounce = 0.06 * np.exp(-((t - 0.1) ** 2) / 0.01)
        curve = curr + diff * (t ** 1.1) + bounce * curr
    else:
        # 패턴 없음: 부드러운 sigmoid
        curve = curr + diff * (1 / (1 + np.exp(-6 * (t - 0.5))))

    return dates, curve


def smooth_series(series, window=5):
    """주가 부드럽게 (이동평균)"""
    return series.rolling(window, min_periods=1, center=True).mean()


# ============ S&P500 스크리너 (주 1회 캐시) ============
SP500_TOP100 = [
    "AAPL","MSFT","NVDA","GOOGL","AMZN","META","TSLA","BRK-B","AVGO","JPM",
    "LLY","V","XOM","UNH","MA","COST","WMT","HD","PG","JNJ",
    "ABBV","NFLX","BAC","CRM","ORCL","MRK","CVX","KO","AMD","ADBE",
    "PEP","TMO","LIN","CSCO","ACN","MCD","WFC","ABT","DIS","TMUS",
    "CAT","IBM","GE","TXN","ISRG","VZ","INTU","QCOM","NOW","CMCSA",
    "BKNG","RTX","AXP","PFE","AMGN","NEE","MS","SPGI","UBER","GS",
    "T","BLK","UNP","PGR","HON","SYK","LOW","DE","ETN","SCHW",
    "BSX","COP","C","MDT","BX","ELV","FI","BA","ANET","SBUX",
    "ADP","ADI","VRTX","MMC","GILD","LMT","KKR","TJX","CB","REGN",
    "PLD","MDLZ","INTC","PANW","KLAC","UPS","CI","SHW","ICE","SO"
]


def quick_score(ticker):
    """가벼운 점수 평가 (캐시용)"""
    try:
        stock = yf.Ticker(ticker)
        h = stock.history(period="6mo")
        if len(h) < 60: return None
        info = stock.info
        curr = float(h['Close'].iloc[-1])
        # 이동평균
        ma20 = h['Close'].rolling(20).mean().iloc[-1]
        ma60 = h['Close'].rolling(60).mean().iloc[-1]
        # RSI
        delta = h['Close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - 100 / (1 + rs)).iloc[-1]
        # MACD
        e12 = h['Close'].ewm(span=12, adjust=False).mean()
        e26 = h['Close'].ewm(span=26, adjust=False).mean()
        macd = (e12 - e26).iloc[-1]
        macd_sig = ((e12 - e26).ewm(span=9, adjust=False).mean()).iloc[-1]

        score = 50
        if curr > ma20: score += 8
        if curr > ma60: score += 10
        if ma20 > ma60: score += 8
        if rsi < 30: score += 12
        elif rsi > 70: score -= 12
        elif rsi < 50: score += 5
        if macd > macd_sig: score += 8
        else: score -= 5

        per = info.get('forwardPE') or info.get('trailingPE')
        if per and per > 0:
            if per < 15: score += 8
            elif per < 25: score += 3
            elif per > 40: score -= 8

        g = info.get('revenueGrowth', 0) or 0
        if g > 0.20: score += 10
        elif g > 0.05: score += 4
        elif g < 0: score -= 8

        # 최근 한달 변동률 (모멘텀)
        mom = (curr - h['Close'].iloc[-21]) / h['Close'].iloc[-21] * 100 if len(h) >= 21 else 0
        if mom > 10: score += 5
        elif mom < -10: score -= 5

        score = max(0, min(100, score))
        return {
            "ticker": ticker,
            "name": info.get('shortName', ticker)[:25],
            "price": curr,
            "score": round(score, 1),
            "rsi": round(rsi, 1),
            "mom_1m": round(mom, 1),
            "per": round(per, 1) if per else None,
            "mcap": info.get('marketCap', 0) or 0,
        }
    except Exception:
        return None


@st.cache_data(ttl=60*60*24*7, show_spinner=False)  # 주 1회
def scan_sp500():
    """S&P500 상위 100개 스캔"""
    results = []
    for tk in SP500_TOP100:
        r = quick_score(tk)
        if r: results.append(r)
    return results



@st.cache_data(ttl=60*60*24*7, show_spinner=False)
def get_ai_pick():
    """주 1회 - S&P500 상위 100개 중 가장 점수 높은 종목 1개 추천"""
    results = scan_sp500()
    if not results: return None
    # 점수 가장 높은 거 + 1M 모멘텀이 너무 과열되지 않은 거
    candidates = [r for r in results if r["score"] >= 60 and r["mom_1m"] < 25]
    if not candidates:
        candidates = [r for r in results if r["score"] >= 55]
    if not candidates: return None
    # 점수 1순위
    top = sorted(candidates, key=lambda x: x["score"], reverse=True)[0]
    return top


# ============ 세력 매집 지표 (OBV / POC / VCP) ============
def compute_obv(h):
    """누적 거래량 - 매집/분산 추적"""
    direction = np.sign(h['Close'].diff().fillna(0))
    obv = (direction * h['Volume']).cumsum()
    return obv


def score_obv(h):
    """OBV 추세 점수"""
    if len(h) < 60: return 50, "데이터 부족"
    obv = compute_obv(h)
    recent = obv.iloc[-30:].mean()
    prior = obv.iloc[-60:-30].mean()
    if prior == 0: return 50, "측정 불가"
    chg = (recent - prior) / abs(prior) * 100
    p_chg = (h['Close'].iloc[-1] - h['Close'].iloc[-30]) / h['Close'].iloc[-30] * 100
    if chg > 10 and p_chg < 5:
        return 88, f"OBV 급등 가격 정체 → 강한 매집"
    elif chg > 5:
        return 72, f"OBV 상승(+{chg:.0f}%) → 매집 우세"
    elif chg < -10 and p_chg > -5:
        return 18, f"OBV 급락 → 세력 분산"
    elif chg < -5:
        return 32, f"OBV 하락({chg:.0f}%) → 매도 우세"
    return 50, f"OBV 중립 ({chg:+.0f}%)"


def find_poc(h, bins=20):
    """Point of Control - 거래량 집중 가격대"""
    if len(h) < 30: return None, 50, "데이터 부족"
    sample = h.iloc[-120:] if len(h) >= 120 else h
    low, high = sample['Low'].min(), sample['High'].max()
    if low >= high: return None, 50, "측정 불가"
    bin_edges = np.linspace(low, high, bins + 1)
    vol_at_price = np.zeros(bins)
    for i in range(len(sample)):
        p = sample['Close'].iloc[i]
        v = sample['Volume'].iloc[i]
        idx = min(int((p - low) / (high - low) * bins), bins - 1)
        if idx >= 0: vol_at_price[idx] += v
    poc_idx = int(np.argmax(vol_at_price))
    poc_price = (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2
    curr = h['Close'].iloc[-1]
    dist = (curr - poc_price) / poc_price * 100
    if -3 <= dist <= 3:
        return poc_price, 78, f"POC ${poc_price:,.2f} 근접 → 매집 진입구간"
    elif 3 < dist <= 10:
        return poc_price, 62, f"POC 위 +{dist:.0f}% → 돌파 시도"
    elif dist > 10:
        return poc_price, 45, f"POC 위 +{dist:.0f}% → 과열 가능"
    else:
        return poc_price, 35, f"POC 아래 {dist:.0f}% → 매물대 부담"


def score_vcp(h):
    """VCP - 변동성 수축 패턴 (매집 후 돌파 임박)"""
    if len(h) < 60: return 50, "데이터 부족"
    # 최근 3개 구간의 변동폭 비교
    seg = 15
    ranges = []
    for i in range(3):
        s = h.iloc[-(seg*(i+1)):-(seg*i)] if i > 0 else h.iloc[-seg:]
        if len(s) < 5: return 50, "데이터 부족"
        r = (s['High'].max() - s['Low'].min()) / s['Close'].mean() * 100
        ranges.append(r)
    # 변동성이 계속 줄어드는지 (수축)
    if ranges[0] < ranges[1] < ranges[2]:
        ratio = ranges[2] / ranges[0] if ranges[0] > 0 else 1
        if ratio > 2:
            return 82, f"강한 변동성 수축 → 돌파 임박"
        return 68, f"변동성 수축 진행 중"
    elif ranges[0] > ranges[1] > ranges[2]:
        return 40, "변동성 확대 중"
    return 50, "변동성 횡보"


def analyze_ma(h):
    """이평선 종합 분석 - 확산/수렴, 이격도, 매매타이밍"""
    if len(h) < 240: return None
    curr = h['Close'].iloc[-1]
    ma20 = h['MA20'].iloc[-1]
    ma60 = h['MA60'].iloc[-1]
    ma120 = h['MA120'].iloc[-1]
    ma240 = h['MA240'].iloc[-1]
    if any(pd.isna(x) for x in [ma20, ma60, ma120, ma240]):
        return None

    # 배열 상태
    if ma20 > ma60 > ma120 > ma240:
        arrangement = ("정배열 ✓", "pos", "단·중·장기 모두 상승 정렬 - 강한 상승 추세")
    elif ma20 < ma60 < ma120 < ma240:
        arrangement = ("역배열", "neg", "단·중·장기 모두 하락 정렬 - 강한 하락 추세")
    elif ma20 > ma60 and ma60 > ma120:
        arrangement = ("단중기 정배열", "pos", "단기·중기 상승, 장기는 횡보")
    elif ma20 < ma60 and ma60 < ma120:
        arrangement = ("단중기 역배열", "neg", "단기·중기 하락, 장기는 횡보")
    else:
        arrangement = ("혼조 (꼬임)", "warn", "이평선이 엉켜있음 - 방향성 모호")

    # 확산/수렴 (240선 대비 평균 거리)
    spread = (abs(ma20 - ma240) + abs(ma60 - ma240) + abs(ma120 - ma240)) / ma240 * 100
    spreads = []
    for i in range(-60, 0):
        if pd.isna(h['MA20'].iloc[i]) or pd.isna(h['MA240'].iloc[i]): continue
        sp = (abs(h['MA20'].iloc[i] - h['MA240'].iloc[i]) +
              abs(h['MA60'].iloc[i] - h['MA240'].iloc[i]) +
              abs(h['MA120'].iloc[i] - h['MA240'].iloc[i])) / h['MA240'].iloc[i] * 100
        spreads.append(sp)
    avg_spread = np.mean(spreads) if spreads else spread
    if spread > avg_spread * 1.3:
        diffusion = ("확산 (벌어짐)", "warn", f"이평선 간격 {spread:.1f}% (평균 {avg_spread:.1f}%) - 추세 강화")
    elif spread < avg_spread * 0.7:
        diffusion = ("수렴 (모임)", "pos", f"이평선 간격 {spread:.1f}% (평균 {avg_spread:.1f}%) - 변곡점 임박")
    else:
        diffusion = ("정상", "", f"이평선 간격 {spread:.1f}% - 평균 수준")

    diverg = (curr - ma240) / ma240 * 100

    # 골든/데드크로스
    cross = ("최근 30일 내 크로스 없음", "")
    for back in range(1, min(31, len(h)-1)):
        prev_diff = h['MA20'].iloc[-back-1] - h['MA60'].iloc[-back-1]
        now_diff = h['MA20'].iloc[-back] - h['MA60'].iloc[-back]
        if pd.isna(prev_diff) or pd.isna(now_diff): continue
        if now_diff > 0 and prev_diff <= 0:
            cross = (f"{back}일 전 ⚡ 골든크로스 (MA20↗MA60)", "pos")
            break
        if now_diff < 0 and prev_diff >= 0:
            cross = (f"{back}일 전 ⚠️ 데드크로스 (MA20↘MA60)", "neg")
            break

    # 매매 타이밍 (장기추세 + 이격도)
    long_trend = "상승" if curr > ma240 else "하락"
    if long_trend == "상승":
        if diverg < 5:
            timing = ("🟢 매수 타이밍", "pos", f"장기상승 추세 + MA240 근접 (+{diverg:.1f}%) - 좋은 진입점")
        elif diverg < 15:
            timing = ("🟡 관망", "warn", f"장기상승 + 이격도 보통 (+{diverg:.1f}%)")
        elif diverg < 30:
            timing = ("🟠 매도 준비", "warn", f"장기상승 + 이격 확대 (+{diverg:.1f}%) - 과열 진입")
        else:
            timing = ("🔴 적극 매도", "neg", f"이격도 +{diverg:.1f}% 극단 과열 - 조정 임박")
    else:
        if diverg > -5:
            timing = ("🟡 관망", "warn", f"장기하락 + MA240 근접 ({diverg:.1f}%) - 약세 유지")
        elif diverg > -15:
            timing = ("🔴 매도", "neg", f"장기하락 + 이격 ({diverg:.1f}%)")
        else:
            timing = ("🟢 매수 타이밍 (역발상)", "pos", f"하락이격 {diverg:.1f}% 극단 - 반등 가능")

    return {
        "ma20": ma20, "ma60": ma60, "ma120": ma120, "ma240": ma240,
        "arrangement": arrangement, "diffusion": diffusion,
        "diverg": diverg, "cross": cross, "timing": timing,
        "long_trend": long_trend
    }


def compute_atr(h, period=14):
    """ATR (Average True Range) 계산"""
    h = h.copy()
    h['H-L'] = h['High'] - h['Low']
    h['H-PC'] = (h['High'] - h['Close'].shift()).abs()
    h['L-PC'] = (h['Low'] - h['Close'].shift()).abs()
    h['TR'] = h[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    return h['TR'].rolling(period).mean()


def compute_bb(h, period=20, std=2):
    """볼린저밴드 위치 (0~1)"""
    ma = h['Close'].rolling(period).mean()
    sd = h['Close'].rolling(period).std()
    upper = ma + sd * std
    lower = ma - sd * std
    pos = (h['Close'] - lower) / (upper - lower)
    return pos


def find_similar_patterns(hist, indicators_used, lookforward_days=[1, 5, 10]):
    """현재 보조지표 상태와 유사한 과거 시점 검색
    indicators_used: 사용할 지표 리스트 ['BB', 'RSI', 'MACD', 'OBV']
    """
    h = hist.copy()
    if len(h) < 200: return None

    # 지표 계산
    h['BB_pos'] = compute_bb(h)
    delta = h['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    h['RSI_v'] = 100 - (100 / (1 + gain / loss))
    e12 = h['Close'].ewm(span=12, adjust=False).mean()
    e26 = h['Close'].ewm(span=26, adjust=False).mean()
    h['MACD_v'] = e12 - e26
    h['MACD_sig_v'] = h['MACD_v'].ewm(span=9, adjust=False).mean()
    h['MACD_diff'] = h['MACD_v'] - h['MACD_sig_v']
    # OBV
    direction = np.sign(h['Close'].diff().fillna(0))
    h['OBV_v'] = (direction * h['Volume']).cumsum()
    h['OBV_chg'] = h['OBV_v'].pct_change(20) * 100  # 20일 변화율

    # 현재 시점 값
    cur_idx = len(h) - 1
    cur_state = {}
    if 'BB' in indicators_used and not pd.isna(h['BB_pos'].iloc[cur_idx]):
        cur_state['BB'] = h['BB_pos'].iloc[cur_idx]
    if 'RSI' in indicators_used and not pd.isna(h['RSI_v'].iloc[cur_idx]):
        cur_state['RSI'] = h['RSI_v'].iloc[cur_idx]
    if 'MACD' in indicators_used and not pd.isna(h['MACD_diff'].iloc[cur_idx]):
        cur_state['MACD'] = h['MACD_diff'].iloc[cur_idx]
    if 'OBV' in indicators_used and not pd.isna(h['OBV_chg'].iloc[cur_idx]):
        cur_state['OBV'] = h['OBV_chg'].iloc[cur_idx]

    if not cur_state: return None

    # 과거 시점 순회하면서 유사도 계산
    candidates = []
    max_lookforward = max(lookforward_days)
    for i in range(50, cur_idx - max_lookforward - 30):  # 최근 30일 제외
        score = 0
        valid = True
        # 각 지표별 유사도 (작을수록 유사)
        for ind, cur_v in cur_state.items():
            if ind == 'BB':
                p_v = h['BB_pos'].iloc[i]
                if pd.isna(p_v): valid = False; break
                # 둘 다 0~1 범위
                score += abs(cur_v - p_v) * 100
            elif ind == 'RSI':
                p_v = h['RSI_v'].iloc[i]
                if pd.isna(p_v): valid = False; break
                # 0~100, 차이 5점 이하면 좋음
                score += abs(cur_v - p_v)
            elif ind == 'MACD':
                p_v = h['MACD_diff'].iloc[i]
                if pd.isna(p_v): valid = False; break
                # 부호 일치 + 크기 비슷
                if np.sign(cur_v) != np.sign(p_v): valid = False; break
                score += abs(cur_v - p_v) / max(abs(cur_v), 0.1) * 10
            elif ind == 'OBV':
                p_v = h['OBV_chg'].iloc[i]
                if pd.isna(p_v): valid = False; break
                # 부호 일치 우선
                if np.sign(cur_v) != np.sign(p_v): score += 30
                score += abs(cur_v - p_v) / 5
        if not valid: continue
        candidates.append({"idx": i, "score": score, "date": h.index[i]})

    if not candidates: return None

    # 유사도 상위 5개
    candidates.sort(key=lambda x: x['score'])
    top5 = candidates[:5]

    # 이후 가격 변동 통계
    stats = {}
    for d in lookforward_days:
        chgs = []
        for c in top5:
            if c['idx'] + d < len(h):
                p_now = h['Close'].iloc[c['idx']]
                p_then = h['Close'].iloc[c['idx'] + d]
                chgs.append((p_then - p_now) / p_now * 100)
        if chgs:
            stats[d] = {
                "avg": np.mean(chgs),
                "wins": sum(1 for c in chgs if c > 0),
                "total": len(chgs),
                "win_rate": sum(1 for c in chgs if c > 0) / len(chgs) * 100,
                "max": max(chgs),
                "min": min(chgs),
            }

    # 매수/매도 판단 (평균 + 승률 둘 다 고려)
    if 5 in stats and 10 in stats:
        avg_10 = stats[10]["avg"]
        wr_10 = stats[10]["win_rate"]

        # 강한 매수: 승률 높고 평균도 양수
        if wr_10 >= 70 and avg_10 > 3:
            verdict = ("🟢 강한 매수 신호", "pos", f"10일 후 상승률 {wr_10:.0f}% · 평균 +{avg_10:.2f}%")
        elif wr_10 >= 60 and avg_10 > 0:
            verdict = ("🟡 매수 우위", "pos", f"10일 후 상승률 {wr_10:.0f}% · 평균 +{avg_10:.2f}%")
        # 명확한 매도: 승률 낮고 평균도 음수
        elif wr_10 <= 30 and avg_10 < -2:
            verdict = ("🔴 매도 우위", "neg", f"10일 후 상승률 {wr_10:.0f}% · 평균 {avg_10:+.2f}%")
        # 평균과 승률 방향 다름
        elif (avg_10 > 0 and wr_10 < 40) or (avg_10 < 0 and wr_10 > 60):
            verdict = ("⚠️ 신호 혼조", "warn", f"평균 {avg_10:+.2f}% · 승률 {wr_10:.0f}% - 방향 불일치, 보수적 접근")
        else:
            verdict = ("⚪ 중립", "warn", f"10일 후 상승률 {wr_10:.0f}% · 평균 {avg_10:+.2f}% - 뚜렷한 신호 없음")
    else:
        verdict = ("⚪ 데이터 부족", "warn", "")

    # 현재 지표 상태 텍스트
    cur_desc = {}
    if 'BB' in cur_state:
        cur_desc['BB'] = f"밴드 {cur_state['BB']*100:.0f}% 위치"
    if 'RSI' in cur_state:
        rsi_v = cur_state['RSI']
        rsi_label = "과매도" if rsi_v < 30 else "과매수" if rsi_v > 70 else "중립"
        cur_desc['RSI'] = f"{rsi_v:.0f} ({rsi_label})"
    if 'MACD' in cur_state:
        macd_v = cur_state['MACD']
        cur_desc['MACD'] = f"{'양전환' if macd_v > 0 else '음전환'} {macd_v:+.2f}"
    if 'OBV' in cur_state:
        obv_v = cur_state['OBV']
        cur_desc['OBV'] = f"{obv_v:+.1f}% (20일)"

    return {
        "cur_state": cur_state,
        "cur_desc": cur_desc,
        "matches": top5,
        "stats": stats,
        "verdict": verdict,
    }


def backtest_prediction(hist, info):
    """2년 전 시점에서 똑같이 예측 → 현재값과 비교"""
    if len(hist) < 750: return None  # 3년 이상 데이터 필요
    # 2년 전 시점
    past_idx = len(hist) - 504  # 2년 ≈ 504영업일
    past_hist = hist.iloc[:past_idx].copy()
    if len(past_hist) < 252: return None

    past_curr = past_hist['Close'].iloc[-1]
    past_high = past_hist['Close'].iloc[-252:].max()
    past_low = past_hist['Close'].iloc[-252:].min()
    past_tech = past_high + (past_high - past_low) * 0.5
    analyst_t = info.get('targetMeanPrice')
    if analyst_t:
        past_target = past_tech * 0.35 + analyst_t * 0.65
    else:
        past_target = past_tech
    actual_curr = hist['Close'].iloc[-1]

    err_pct = abs(past_target - actual_curr) / actual_curr * 100
    pred_dir = "상승" if past_target > past_curr else "하락"
    actual_dir = "상승" if actual_curr > past_curr else "하락"
    dir_match = pred_dir == actual_dir
    actual_change = (actual_curr - past_curr) / past_curr * 100

    if err_pct < 10: acc_score = 90
    elif err_pct < 20: acc_score = 75
    elif err_pct < 35: acc_score = 55
    elif err_pct < 50: acc_score = 35
    else: acc_score = 15

    return {
        "past_date": past_hist.index[-1].strftime("%Y-%m-%d"),
        "past_price": past_curr,
        "past_target": past_target,
        "actual_price": actual_curr,
        "actual_change": actual_change,
        "err_pct": err_pct,
        "pred_dir": pred_dir,
        "actual_dir": actual_dir,
        "dir_match": dir_match,
        "acc_score": acc_score,
        "period_years": 2,
    }


def analyze_economy(macro, hist=None):
    """통합 경제 위험도 - 인플레/경기침체/스태그플레이션"""
    # 지표 수집
    cpi = macro.get("cpi_yoy_v", (None, None))[0]
    core_cpi = macro.get("core_cpi_yoy", (None, None))[0]
    ppi = macro.get("ppi_yoy", (None, None))[0]
    pce = macro.get("pce_yoy", (None, None))[0]
    unemploy = macro.get("unemploy", (None, None))
    sahm = macro.get("sahm", (None, None))[0]
    lei = macro.get("lei", (None, None))[0]
    pmi = macro.get("ism_pmi", (None, None))[0]
    rec_prob = macro.get("recession_prob", (None, None))[0]
    us10y = macro.get("us10y", (None, None))[0]
    us2y = macro.get("us2y", (None, None))[0]
    hy = macro.get("hy_spread", (None, None))[0]

    # ====== 인플레이션 점수 (낮을수록 안정) ======
    inf_score = 50
    inf_factors = []
    if cpi is not None:
        if cpi > 5: inf_score += 35; inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "심각", "neg"))
        elif cpi > 4: inf_score += 25; inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "위험", "neg"))
        elif cpi > 3.5: inf_score += 18; inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "고위험", "neg"))
        elif cpi > 3: inf_score += 12; inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "주의", "warn"))
        elif cpi > 2.5: inf_score += 5; inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "약한주의", "warn"))
        elif cpi >= 2: inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "Fed목표 근접", ""))
        elif cpi >= 1: inf_score -= 8; inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "안정", "pos"))
        else: inf_score -= 15; inf_factors.append(("CPI YoY", f"{cpi:.1f}%", "디스인플레", "warn"))

    if core_cpi is not None:
        if core_cpi > 5: inf_score += 22; inf_factors.append(("Core CPI", f"{core_cpi:.1f}%", "극심", "neg"))
        elif core_cpi > 4: inf_score += 16; inf_factors.append(("Core CPI", f"{core_cpi:.1f}%", "끈적함", "neg"))
        elif core_cpi > 3.5: inf_score += 12; inf_factors.append(("Core CPI", f"{core_cpi:.1f}%", "고위험", "neg"))
        elif core_cpi > 3: inf_score += 8; inf_factors.append(("Core CPI", f"{core_cpi:.1f}%", "주의", "warn"))
        elif core_cpi > 2.5: inf_score += 3; inf_factors.append(("Core CPI", f"{core_cpi:.1f}%", "약한주의", "warn"))
        else: inf_factors.append(("Core CPI", f"{core_cpi:.1f}%", "정상", "pos"))

    if ppi is not None:
        if ppi > 8: inf_score += 14; inf_factors.append(("PPI YoY", f"{ppi:.1f}%", "급등", "neg"))
        elif ppi > 5: inf_score += 10; inf_factors.append(("PPI YoY", f"{ppi:.1f}%", "생산자물가↑↑", "neg"))
        elif ppi > 3: inf_score += 5; inf_factors.append(("PPI YoY", f"{ppi:.1f}%", "생산자물가↑", "warn"))
        elif ppi > 1: inf_factors.append(("PPI YoY", f"{ppi:.1f}%", "정상", ""))
        else: inf_score -= 5; inf_factors.append(("PPI YoY", f"{ppi:.1f}%", "안정", "pos"))

    if pce is not None:
        if pce > 4: inf_score += 14; inf_factors.append(("PCE YoY", f"{pce:.1f}%", "Fed목표 크게 초과", "neg"))
        elif pce > 3: inf_score += 8; inf_factors.append(("PCE YoY", f"{pce:.1f}%", "Fed목표 초과", "warn"))
        elif pce > 2.5: inf_score += 3; inf_factors.append(("PCE YoY", f"{pce:.1f}%", "약한 초과", ""))
        elif pce >= 2: inf_factors.append(("PCE YoY", f"{pce:.1f}%", "Fed목표 근접", "pos"))
        else: inf_score -= 5; inf_factors.append(("PCE YoY", f"{pce:.1f}%", "양호", "pos"))
    inf_score = max(0, min(100, inf_score))

    # ====== 경기침체 점수 (높을수록 위험) ======
    rec_score = 30
    rec_factors = []
    # 장단기 금리역전
    if us10y and us2y:
        spread = us10y - us2y
        if spread < 0:
            rec_score += 25; rec_factors.append(("10Y-2Y", f"{spread:+.2f}%", "🔴 역전", "neg"))
        elif spread < 0.5:
            rec_score += 10; rec_factors.append(("10Y-2Y", f"{spread:+.2f}%", "압축", "warn"))
        else:
            rec_factors.append(("10Y-2Y", f"{spread:+.2f}%", "정상", "pos"))
    # 삼의 법칙 (실업률 3개월평균이 최근 12개월 최저 대비 +0.5% 이상이면 침체)
    if sahm is not None:
        if sahm >= 0.5:
            rec_score += 30; rec_factors.append(("삼의 법칙", f"{sahm:.2f}", "🔴 침체 신호 발동", "neg"))
        elif sahm >= 0.3:
            rec_score += 15; rec_factors.append(("삼의 법칙", f"{sahm:.2f}", "근접", "warn"))
        else:
            rec_factors.append(("삼의 법칙", f"{sahm:.2f}", "정상", "pos"))
    # 실업률
    if unemploy[0] is not None:
        u_cur = unemploy[0]
        u_prev = unemploy[1] if unemploy[1] else u_cur
        chg = u_cur - u_prev
        if u_cur > 5:
            rec_score += 15; rec_factors.append(("실업률", f"{u_cur:.1f}%", "둔화", "neg"))
        elif chg > 0.3:
            rec_score += 10; rec_factors.append(("실업률", f"{u_cur:.1f}%", "급등", "warn"))
        elif u_cur < 4:
            rec_factors.append(("실업률", f"{u_cur:.1f}%", "완전고용", "pos"))
        else:
            rec_factors.append(("실업률", f"{u_cur:.1f}%", "정상", ""))
    # LEI (선행지수)
    if lei is not None:
        if lei < -1:
            rec_score += 15; rec_factors.append(("LEI 선행지수", f"{lei:.2f}", "수축", "neg"))
        elif lei < 0:
            rec_score += 8; rec_factors.append(("LEI 선행지수", f"{lei:.2f}", "둔화", "warn"))
        else:
            rec_factors.append(("LEI 선행지수", f"{lei:.2f}", "확장", "pos"))
    # ISM PMI (50 기준)
    if pmi is not None:
        if pmi < 47:
            rec_score += 12; rec_factors.append(("ISM PMI", f"{pmi:.1f}", "수축", "neg"))
        elif pmi < 50:
            rec_score += 6; rec_factors.append(("ISM PMI", f"{pmi:.1f}", "위축경계", "warn"))
        else:
            rec_factors.append(("ISM PMI", f"{pmi:.1f}", "확장", "pos"))
    # NY연준 경기침체 확률
    if rec_prob is not None:
        if rec_prob > 40:
            rec_score += 20; rec_factors.append(("NY연준 침체확률", f"{rec_prob:.0f}%", "高", "neg"))
        elif rec_prob > 20:
            rec_score += 10; rec_factors.append(("NY연준 침체확률", f"{rec_prob:.0f}%", "주의", "warn"))
        else:
            rec_factors.append(("NY연준 침체확률", f"{rec_prob:.0f}%", "낮음", "pos"))
    # 하이일드 스프레드
    if hy is not None:
        if hy > 5:
            rec_score += 10; rec_factors.append(("HY스프레드", f"{hy:.2f}%", "신용경색", "neg"))
        else:
            rec_factors.append(("HY스프레드", f"{hy:.2f}%", "안정", "pos"))
    rec_score = max(0, min(100, rec_score))

    # ====== 스태그플레이션 (인플레↑ + 성장↓) ======
    stag = False
    stag_reason = ""
    if inf_score >= 60 and rec_score >= 55:
        stag = True
        stag_reason = "물가는 높은데 경기는 둔화 중"

    # ====== 종합 평가 ======
    if stag:
        overall = "⚠️ 스태그플레이션 우려"
        overall_cls = "neg"
        msg = f"인플레와 경기둔화가 동시에 진행 중. {stag_reason}. 현금/금/필수소비재 등 방어 자산 권장."
    elif rec_score >= 70:
        overall = "🔴 경기침체 임박"
        overall_cls = "neg"
        msg = "선행지표가 침체 신호를 보이고 있습니다. 현금 비중 확대 권장."
    elif inf_score >= 70:
        overall = "🔴 인플레 위험 高"
        overall_cls = "neg"
        msg = "물가 압력이 큽니다. 금/원자재/실물자산 비중 확대 고려."
    elif rec_score >= 55 or inf_score >= 55:
        overall = "🟠 경계 구간"
        overall_cls = "warn"
        msg = "일부 지표에서 경고 신호. 분할 매수, 방어 비중 확보."
    elif rec_score <= 35 and inf_score <= 45:
        overall = "🟢 안정 (골디락스)"
        overall_cls = "pos"
        msg = "물가 안정 + 경기 확장. 위험자산 비중 확대 적기."
    else:
        overall = "🟡 중립"
        overall_cls = "warn"
        msg = "특별한 경고 신호 없이 보통 상태."

    return {
        "inf_score": inf_score, "rec_score": rec_score,
        "inf_factors": inf_factors, "rec_factors": rec_factors,
        "stag": stag, "overall": overall, "overall_cls": overall_cls, "msg": msg
    }


@st.cache_data(ttl=3600)
def get_market_breadth():
    """S&P500 상위 종목 중 200일선 위에 있는 비율"""
    try:
        # 상위 50개로 약식 측정 (전체 500개 돌리면 너무 느림)
        sample = SP500_TOP100[:50]
        above = 0; total = 0
        for tk in sample:
            try:
                h = yf.Ticker(tk).history(period="1y")
                if len(h) >= 200:
                    ma200 = h['Close'].rolling(200).mean().iloc[-1]
                    if h['Close'].iloc[-1] > ma200: above += 1
                    total += 1
            except Exception:
                continue
        if total < 20: return None
        return {"above_pct": above / total * 100, "sample": total}
    except Exception:
        return None


@st.cache_data(ttl=300)
def get_index_trend(ticker):
    """지수 추세 - 200일선 대비, 1M 변화"""
    try:
        h = yf.Ticker(ticker).history(period="1y")
        if len(h) < 200: return None
        curr = h['Close'].iloc[-1]
        ma200 = h['Close'].rolling(200).mean().iloc[-1]
        mom_1m = (curr - h['Close'].iloc[-21]) / h['Close'].iloc[-21] * 100 if len(h) >= 21 else 0
        return {"curr": curr, "ma200": ma200, "above_ma200": curr > ma200,
                "diverg": (curr - ma200) / ma200 * 100, "mom_1m": mom_1m}
    except Exception:
        return None


def detect_stagflation(macro):
    """스태그플레이션 정밀 판정
    4가지 조건 모두 충족해야 진짜 스태그플레이션:
    1) CPI ≥ 4% (높은 인플레)
    2) GDP < 1% (성장 둔화)
    3) 실업률 상승 (전월 대비)
    4) Core CPI ≥ 3% (끈적한 인플레)
    """
    cpi = macro.get("cpi_yoy_v", (None, None))[0]
    core_cpi = macro.get("core_cpi_yoy", (None, None))[0]
    gdp = macro.get("gdp", (None, None))[0]
    unemploy = macro.get("unemploy", (None, None))

    conditions = []
    met = 0

    # 1. CPI ≥ 4%
    if cpi is not None:
        c1 = cpi >= 4
        conditions.append({
            "name": "높은 인플레", "metric": f"CPI {cpi:.1f}%",
            "threshold": "≥ 4.0%", "met": c1,
            "desc": "물가 압력이 위험 수준"
        })
        if c1: met += 1

    # 2. Core CPI ≥ 3% (끈적함)
    if core_cpi is not None:
        c2 = core_cpi >= 3
        conditions.append({
            "name": "끈적한 인플레", "metric": f"Core CPI {core_cpi:.1f}%",
            "threshold": "≥ 3.0%", "met": c2,
            "desc": "근원 물가도 높음 = 단기에 안 잡힘"
        })
        if c2: met += 1

    # 3. GDP < 1.5%
    if gdp is not None:
        c3 = gdp < 1.5
        conditions.append({
            "name": "성장 둔화", "metric": f"실질GDP {gdp:.1f}%",
            "threshold": "< 1.5%", "met": c3,
            "desc": "경제 성장 약화"
        })
        if c3: met += 1

    # 4. 실업률 상승 (전월 대비 +0.2%p)
    if unemploy[0] is not None and unemploy[1] is not None:
        u_chg = unemploy[0] - unemploy[1]
        c4 = u_chg >= 0.2 or unemploy[0] >= 4.5
        conditions.append({
            "name": "고용 둔화", "metric": f"실업률 {unemploy[0]:.1f}% ({u_chg:+.1f})",
            "threshold": "상승 or ≥ 4.5%", "met": c4,
            "desc": "노동시장 약화"
        })
        if c4: met += 1

    total = len(conditions)
    if total == 0:
        return {"status": "측정불가", "cls": "warn", "msg": "데이터 부족", "conditions": [], "met": 0, "total": 0}

    ratio = met / total
    if met == total and total == 4:
        status = "🔴 스태그플레이션 확정"
        cls = "neg"
        msg = f"4개 조건 모두 충족 ({met}/{total}). 1970년대 후반 미국, 2022년 영국 유사. 주식·채권 동반 약세 가능성 高. 금/원자재/필수소비재 비중 권장."
    elif ratio >= 0.75:
        status = "🟠 스태그플레이션 임박"
        cls = "neg"
        msg = f"{met}/{total} 조건 충족. 한두 지표만 더 악화되면 본격 진입. 방어 포지션 구축 시작 권장."
    elif ratio >= 0.5:
        status = "🟡 스태그플레이션 우려"
        cls = "warn"
        msg = f"{met}/{total} 조건 충족. 잠재적 위험 존재하나 아직 본격 진입 아님. 주시 필요."
    elif ratio >= 0.25:
        status = "🟢 부분 신호"
        cls = "warn"
        msg = f"{met}/{total} 조건만 충족. 일부 우려 있으나 스태그플레이션은 아님."
    else:
        status = "🟢 스태그 위험 없음"
        cls = "pos"
        msg = f"{met}/{total} 조건 충족. 정상 경제 환경."

    return {"status": status, "cls": cls, "msg": msg,
            "conditions": conditions, "met": met, "total": total}


def combined_diagnosis(market_score, inf_score, rec_score):
    """시장 상황 + 인플레 + 침체 조합 → 과거 사례 기반 진단"""
    # 시장 강도
    if market_score >= 65: mkt_state = "강세"
    elif market_score >= 50: mkt_state = "중립우호"
    elif market_score >= 35: mkt_state = "혼조"
    else: mkt_state = "약세"

    # 인플레 강도
    if inf_score >= 70: inf_state = "고인플레"
    elif inf_score >= 55: inf_state = "인플레 경계"
    elif inf_score >= 40: inf_state = "중립"
    else: inf_state = "디스인플레"

    # 침체 강도
    if rec_score >= 60: rec_state = "침체임박"
    elif rec_score >= 45: rec_state = "경계"
    else: rec_state = "정상"

    # 조합 진단 (역사적 사례)
    combos = {
        # (시장, 인플레, 침체)
        ("강세", "고인플레", "정상"):
            ("🔴 후기 사이클 (Late Cycle)",
             "1970년대 후반·2021년 패턴. 시장은 강하지만 인플레가 끈적해 Fed 긴축 가능성↑. 빅테크 보다 에너지·원자재·금융주가 유리했음.",
             "neg"),
        ("강세", "고인플레", "경계"):
            ("🔴 스태그플레이션 진입",
             "1973-74년 유사. 시장 강세에도 불구하고 침체 신호 + 인플레. 결국 큰 조정으로 이어진 경우 많음. 방어주(헬스케어/필수소비재) 권장.",
             "neg"),
        ("강세", "고인플레", "침체임박"):
            ("⚠️ 위험한 강세 (분배 구간)",
             "1929·2000·2007 패턴. 표면적 강세지만 침체+인플레 동반은 폭락 전조였음. 현금 비중↑ 강력 권장.",
             "neg"),
        ("강세", "인플레 경계", "정상"):
            ("🟡 후기 확장 (Mid-Late Cycle)",
             "2017-18년 패턴. 시장은 좋고 인플레 압력 시작. 6~12개월 내 Fed 긴축 가능. 성장주 비중 점진 축소 권장.",
             "warn"),
        ("강세", "중립", "정상"):
            ("🟢 골디락스 (Goldilocks)",
             "2019·2024년 패턴. 시장 강세 + 물가 안정 + 경기 정상. 위험자산 비중 확대 적기. 성장주·기술주 강세 지속 경향.",
             "pos"),
        ("강세", "디스인플레", "정상"):
            ("🟢 이상적 환경",
             "Fed 완화 가능성↑ + 시장 강세. 1995-96, 2013년 유사. 위험자산 강세 장기화 가능.",
             "pos"),
        ("중립우호", "고인플레", "정상"):
            ("🟠 스태그 우려",
             "시장은 그저 그런데 물가만 높음. 1974, 2022년 패턴. 금/원자재/단기채 비중 확대.",
             "warn"),
        ("중립우호", "중립", "정상"):
            ("🟡 보통 확장기",
             "특별한 위험 신호 없음. 분할 매수 + 균형 잡힌 포트폴리오 유지.",
             "warn"),
        ("혼조", "고인플레", "경계"):
            ("🔴 스태그플레이션",
             "1970년대 전형. 주식·채권 동반 약세. 금·원자재·실물자산이 유일한 피난처였음.",
             "neg"),
        ("혼조", "중립", "경계"):
            ("🟠 침체 진입 (초기)",
             "2007년 하반기·2019년 말 패턴. 시장은 위태롭고 침체 신호 점등. 방어주 + 장기채 매수 시점.",
             "warn"),
        ("혼조", "중립", "정상"):
            ("🟡 박스권 횡보",
             "방향성 모호. 종목 선별 중요. 변동성 활용한 매매가 유리.",
             "warn"),
        ("약세", "고인플레", "침체임박"):
            ("🔴 위기 국면",
             "2008년·1980년대 초 유사. 모든 자산 약세. 현금이 왕. 회복 시 큰 기회였음.",
             "neg"),
        ("약세", "중립", "침체임박"):
            ("🔴 침체 진행",
             "2008·2020년 초기. 주식 약세, 단기 변동성 큼. 침체 후반부에 매수 기회 발생.",
             "neg"),
        ("약세", "디스인플레", "침체임박"):
            ("🟡 침체 + 디플레",
             "2008년 말 패턴. 통화완화 가속화 가능성↑. 6~12개월 후 강한 반등 종종 발생.",
             "warn"),
        ("약세", "중립", "경계"):
            ("🟠 위험회피",
             "현금/단기채 비중 확대. 시장 바닥 신호(VIX 40↑, 공포탐욕 10↓) 모니터링.",
             "warn"),
    }

    key = (mkt_state, inf_state, rec_state)
    if key in combos:
        return combos[key]

    # 기본값
    if inf_score >= 60 and rec_score >= 50:
        return ("⚠️ 스태그플레이션 위험", "물가↑ + 경기↓ 동반. 방어자산 권장.", "neg")
    elif market_score >= 60 and inf_score < 50 and rec_score < 40:
        return ("🟢 우호적 환경", "시장·물가·경기 모두 양호. 위험자산 비중 확대 가능.", "pos")
    elif market_score < 40:
        return ("🔴 시장 약세", "방어적 포지션 권장.", "neg")
    else:
        return ("🟡 혼조", f"시장 {mkt_state}, 인플레 {inf_state}, 침체 {rec_state}. 균형 잡힌 포트폴리오.", "warn")


def make_market_summary(macro, breadth=None, sp_trend=None, ndx_trend=None):
    """매크로 지표 종합 결론 (강화판)"""
    positives, negatives = [], []
    weighted_score = 50  # 가중 점수

    # 1. VIX (가중치 高)
    vix = macro.get("vix", (None, None))[0]
    if vix:
        if vix < 15: positives.append("VIX 안정 (15↓)"); weighted_score += 6
        elif vix < 18: positives.append("VIX 양호"); weighted_score += 3
        elif vix > 30: negatives.append("VIX 극단 (공포)"); weighted_score -= 10
        elif vix > 25: negatives.append("VIX 변동성 확대"); weighted_score -= 6
        elif vix > 20: negatives.append("VIX 경계"); weighted_score -= 3

    # 2. 공포탐욕 (가중치 中)
    fg = macro.get("fg", (None, None))[0]
    if fg:
        if fg > 80: negatives.append(f"공포탐욕 {fg:.0f} - 극단 과열"); weighted_score -= 8
        elif fg > 70: negatives.append(f"공포탐욕 {fg:.0f} - 과열"); weighted_score -= 4
        elif fg < 20: positives.append(f"공포탐욕 {fg:.0f} - 극단공포 (역발상)"); weighted_score += 6
        elif fg < 30: positives.append(f"공포탐욕 {fg:.0f} - 공포구간"); weighted_score += 4
        elif fg > 55: weighted_score += 2  # 약한 탐욕

    # 3. 장단기 금리차 (가중치 高 - 침체 선행지표)
    us10y = macro.get("us10y", (None, None))[0]
    us2y = macro.get("us2y", (None, None))[0]
    if us10y and us2y:
        spread = us10y - us2y
        if spread < 0: negatives.append(f"장단기 역전 ({spread:+.2f}%)"); weighted_score -= 10
        elif spread > 0.8: positives.append("금리커브 정상화"); weighted_score += 5
        elif spread < 0.3: weighted_score -= 3

    # 4. 절대 금리 수준
    if us10y:
        if us10y > 5: negatives.append(f"美10Y {us10y:.2f}% - 극단 고금리"); weighted_score -= 8
        elif us10y > 4.5: negatives.append(f"美10Y {us10y:.2f}% - 고금리 부담"); weighted_score -= 4
        elif us10y < 3.5: positives.append("저금리 환경"); weighted_score += 4

    # 5. 하이일드 스프레드 (신용 리스크)
    hy = macro.get("hy_spread", (None, None))[0]
    if hy:
        if hy < 3: positives.append("신용시장 안정"); weighted_score += 4
        elif hy > 6: negatives.append("신용경색 심각"); weighted_score -= 8
        elif hy > 5: negatives.append("신용 스프레드 확대"); weighted_score -= 4

    # 6. 유동성 (연준 자산)
    fa = macro.get("fed_assets", (None, None))
    if fa[0] and fa[1]:
        if fa[0] > fa[1]: positives.append("연준 자산 증가 (유동성↑)"); weighted_score += 3
        else: negatives.append("연준 QT 진행"); weighted_score -= 3

    # 7. 달러
    dxy = macro.get("dxy", (None, None))[0]
    if dxy:
        if dxy > 108: negatives.append(f"강달러 {dxy:.1f} (위험자산 부담)"); weighted_score -= 6
        elif dxy > 105: negatives.append(f"강달러 {dxy:.1f}"); weighted_score -= 3
        elif dxy < 98: positives.append("달러 약세 (위험자산 우호)"); weighted_score += 4

    # 8. S&P 추세 (가중치 高)
    if sp_trend:
        if sp_trend["above_ma200"]:
            if sp_trend["diverg"] > 10:
                negatives.append(f"S&P 과열 (200MA +{sp_trend['diverg']:.1f}%)"); weighted_score -= 3
            else:
                positives.append("S&P 200일선 위"); weighted_score += 5
        else:
            negatives.append(f"S&P 200일선 아래 ({sp_trend['diverg']:+.1f}%)"); weighted_score -= 7
        if sp_trend["mom_1m"] < -5:
            negatives.append(f"S&P 1M 모멘텀 {sp_trend['mom_1m']:+.1f}%"); weighted_score -= 4

    # 9. 시장 폭 (Breadth)
    if breadth:
        bp = breadth["above_pct"]
        if bp >= 60: positives.append(f"시장 폭 {bp:.0f}% (강세 광범위)"); weighted_score += 5
        elif bp >= 50: weighted_score += 2
        elif bp < 30: negatives.append(f"시장 폭 {bp:.0f}% (소수 종목만 강세)"); weighted_score -= 8
        elif bp < 40: negatives.append(f"시장 폭 {bp:.0f}% 약함"); weighted_score -= 4

    # 10. 비트코인 (위험자산 선행지표)
    btc = macro.get("btc", (None, None))
    if btc[0] and btc[1]:
        chg = (btc[0] - btc[1]) / btc[1] * 100
        if chg < -5: negatives.append("BTC 급락 (위험회피)"); weighted_score -= 3
        elif chg > 5: positives.append("BTC 급등 (위험선호)"); weighted_score += 3

    # 11. 금 (안전자산 선호)
    gold = macro.get("gold", (None, None))
    if gold[0] and gold[1]:
        chg = (gold[0] - gold[1]) / gold[1] * 100
        if chg > 3: negatives.append("금 급등 (안전자산 선호)"); weighted_score -= 3

    # 12. 원유 (경기/인플레)
    wti = macro.get("wti", (None, None))
    if wti[0]:
        if wti[0] > 110: negatives.append(f"WTI ${wti[0]:.0f} - 인플레 압력"); weighted_score -= 3
        elif wti[0] < 60: negatives.append(f"WTI ${wti[0]:.0f} - 수요둔화 우려"); weighted_score -= 2

    score = max(0, min(100, weighted_score))

    if score >= 70: verdict, vcls = "위험자산 우호", "pos"
    elif score >= 55: verdict, vcls = "중립적 우호", "pos"
    elif score >= 45: verdict, vcls = "혼조", "warn"
    elif score >= 30: verdict, vcls = "방어적", "neg"
    else: verdict, vcls = "위험회피 국면", "neg"

    return {"score": score, "verdict": verdict, "vcls": vcls,
            "positives": positives, "negatives": negatives}


# ============ 헬퍼 ============
def card(label, value, sub="", value_cls=""):
    return f"""<div class='card'><div class='card-title'>{label}</div>
    <div class='card-value {value_cls}'>{value}</div>
    <div class='card-sub'>{sub}</div></div>"""


def fmt_diff(cur, prev, unit="", pct=False):
    if cur is None or prev is None: return ""
    d = cur - prev
    if pct:
        dp = (cur - prev) / prev * 100 if prev else 0
        sign = "▲" if d >= 0 else "▼"
        cls = "pos" if d >= 0 else "neg"
        return f"<span class='{cls}'>{sign} {abs(dp):.2f}% 전일</span>"
    sign = "▲" if d >= 0 else "▼"
    cls = "pos" if d >= 0 else "neg"
    return f"<span class='{cls}'>{sign} {abs(d):.2f}{unit} 전일</span>"


# ============================== UI ==============================
st.markdown("<div class='title-bar'>📈 Alpha Pro Strategic Terminal v3</div>", unsafe_allow_html=True)
st.markdown(f"<div class='title-sub'>AI 차트패턴 인식 · 매크로 종합 · 6개월 목표가 예측 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>", unsafe_allow_html=True)

with st.form("f"):
    c1, c2 = st.columns([5, 1])
    with c1:
        ticker = st.text_input("티커 입력 (미국: TSLA, NVDA · 한국: 005930.KS, 035420.KS)",
                                value="TSLA", label_visibility="collapsed").upper().strip()
    with c2:
        go_btn = st.form_submit_button("분석 실행")

if not ticker:
    st.stop()

is_kr = ticker.endswith(".KS") or ticker.endswith(".KQ")
ccy = "₩" if is_kr else "$"

@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(ticker):
    """종목 데이터 5분 캐시 - 4년치"""
    stock = yf.Ticker(ticker)
    hist = stock.history(period="4y")
    info = stock.info
    return hist, info


try:
    with st.spinner("데이터 수집 중..."):
        hist, info = get_stock_data(ticker)
        if hist.empty:
            st.error("데이터를 불러올 수 없습니다. 티커를 확인하세요.")
            st.stop()
        hist = compute_indicators(hist)
        patterns = detect_patterns(hist['Close'])
        macro = get_macro_all()
        tmp_score = 50
        target = calc_target(hist, info, tmp_score, patterns[0])
        rec = score_all(hist, info, patterns, macro, is_kr)
        target = calc_target(hist, info, rec["score"], patterns[0])


    company = info.get('longName') or info.get('shortName') or ticker
    curr = target["current"]

    # ===== 상단 글로벌 자산 =====
    st.markdown("<div class='section-h'>🌐 글로벌 자산</div>", unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns(4)

    def asset_card(label, data, prefix="", suffix="", decimals=2, is_k=False):
        cur, prev = data if data else (None, None)
        if cur is None:
            return card(label, "N/A")
        val = f"{prefix}{cur/1000:.1f}K{suffix}" if is_k and cur > 1000 else f"{prefix}{cur:,.{decimals}f}{suffix}"
        return card(label, val, fmt_diff(cur, prev, pct=True))

    with g1: st.markdown(asset_card("S&P 500", macro["sp500"]), unsafe_allow_html=True)
    with g2: st.markdown(asset_card("나스닥", macro["nasdaq"]), unsafe_allow_html=True)
    with g3: st.markdown(asset_card("금", macro["gold"], prefix="$"), unsafe_allow_html=True)
    with g4: st.markdown(asset_card("비트코인", macro["btc"], prefix="$", is_k=True), unsafe_allow_html=True)

    # ===== 시장 심리 =====
    st.markdown("<div class='section-h'>📊 시장 심리</div>", unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    fg_v, fg_p = macro.get("fg", (None, None))
    with s1:
        if fg_v is not None:
            fg_label = "탐욕" if fg_v > 55 else "공포" if fg_v < 45 else "중립"
            fg_cls = "warn" if fg_v > 55 else "neg" if fg_v < 45 else ""
            st.markdown(card("공포탐욕지수", f"{fg_v:.0f}", f"{fg_label} · CNN Fear & Greed", fg_cls), unsafe_allow_html=True)
        else:
            st.markdown(card("공포탐욕지수", "N/A", "CNN Fear & Greed"), unsafe_allow_html=True)
    with s2: st.markdown(asset_card("VIX 변동성", macro["vix"]), unsafe_allow_html=True)
    us10y_d = macro["us10y"]
    us2y_d = macro["us2y"]
    with s3:
        if us10y_d[0] and us2y_d[0]:
            spread = us10y_d[0] - us2y_d[0]
            prev_sp = us10y_d[1] - us2y_d[1] if us10y_d[1] and us2y_d[1] else spread
            label_sub = ("정상" if spread > 0 else "역전") + " · 10Y-2Y"
            st.markdown(card("장단기 금리차", f"{spread:.2f}%",
                            fmt_diff(spread, prev_sp, unit="%p") + " · " + label_sub), unsafe_allow_html=True)
        else:
            st.markdown(card("장단기 금리차", "N/A", "10Y-2Y"), unsafe_allow_html=True)
    hy_d = macro["hy_spread"]
    with s4:
        if hy_d[0]:
            st.markdown(card("하이일드 스프레드", f"{hy_d[0]:.2f}%",
                            fmt_diff(hy_d[0], hy_d[1] or hy_d[0], unit="%p") + " · 신용시장"), unsafe_allow_html=True)
        else:
            st.markdown(card("하이일드 스프레드", "N/A", "신용시장"), unsafe_allow_html=True)

    # ===== 매크로 (환율, 금리, 유가) =====
    st.markdown("<div class='section-h'>🌍 매크로</div>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(asset_card("달러인덱스", macro["dxy"]), unsafe_allow_html=True)
    with m2:
        krw_d = macro["usdkrw"]
        if krw_d[0]:
            st.markdown(card("달러/원", f"{krw_d[0]:,.1f}원",
                            fmt_diff(krw_d[0], krw_d[1] or krw_d[0], unit="원")), unsafe_allow_html=True)
    with m3:
        # yfinance 우선 (실시간), 없으면 FRED
        us10y_yf = macro.get("us10y_yf", (None, None))
        if us10y_yf[0]:
            st.markdown(card("美 10년물 금리", f"{us10y_yf[0]:.2f}%",
                            fmt_diff(us10y_yf[0], us10y_yf[1] or us10y_yf[0], unit="%p") + " · 실시간"), unsafe_allow_html=True)
        elif us10y_d[0]:
            st.markdown(card("美 10년물 금리", f"{us10y_d[0]:.2f}%",
                            fmt_diff(us10y_d[0], us10y_d[1] or us10y_d[0], unit="%p") + " · 전일종가"), unsafe_allow_html=True)
    with m4: st.markdown(asset_card("WTI 원유", macro["wti"], prefix="$"), unsafe_allow_html=True)

    # ===== 유동성 (FRED) =====
    st.markdown("<div class='section-h'>💧 유동성</div>", unsafe_allow_html=True)
    l1, l2, l3, l4 = st.columns(4)

    def liq_card(label, data, sub):
        cur, prev = data if data else (None, None)
        if cur is None: return card(label, "N/A")
        # 단위 자동
        if cur > 1e6:
            val = f"{cur/1e6:.2f}T"
            diff_str = fmt_diff(cur/1e6, (prev or cur)/1e6, unit="T")
        elif cur > 1e3:
            val = f"{cur/1e3:.1f}B"
            diff_str = fmt_diff(cur/1e3, (prev or cur)/1e3, unit="B")
        else:
            val = f"${cur:.0f}B"
            diff_str = fmt_diff(cur, prev or cur, unit="B")
        return card(label, val, diff_str + " · " + sub)

    with l1: st.markdown(liq_card("연준 총자산", macro["fed_assets"], "QE/QT"), unsafe_allow_html=True)
    with l2: st.markdown(liq_card("연준 지급준비금", macro["reserves"], "은행 준비금"), unsafe_allow_html=True)
    with l3: st.markdown(liq_card("역레포(RRP)", macro["rrp"], "유동성 흡수"), unsafe_allow_html=True)
    with l4: st.markdown(liq_card("TGA 잔액", macro["tga"], "재무부 계정"), unsafe_allow_html=True)

    # ===== 시장 종합 결론 =====
    breadth = get_market_breadth()
    sp_trend = get_index_trend("^GSPC")
    mkt = make_market_summary(macro, breadth=breadth, sp_trend=sp_trend)
    pos_html = "<br>".join(f"<span class='pos'>✓ {p}</span>" for p in mkt["positives"]) or "<span style='color:#64748b;'>특이사항 없음</span>"
    neg_html = "<br>".join(f"<span class='neg'>✗ {n}</span>" for n in mkt["negatives"]) or "<span style='color:#64748b;'>특이사항 없음</span>"

    # 상세 결론 메시지
    if mkt["score"] >= 70:
        detail = "유동성, 금리, 신용 환경이 위험자산에 우호적입니다. 주식·암호화폐 등 성장 자산 비중 확대 구간."
    elif mkt["score"] >= 55:
        detail = "전반적으로 우호적이지만 일부 부정 요인 존재. 선별적 매수 + 분할 매수 전략 권장."
    elif mkt["score"] >= 45:
        detail = "긍정/부정 요인이 혼재. 신규 진입보다는 기존 포지션 관리 중심으로."
    elif mkt["score"] >= 30:
        detail = "방어적 환경. 현금 비중 확대, 단기채·금 등 안전자산 선호 권장."
    else:
        detail = "위험회피 국면 진입. 현금화 우선, 변동성 자산 비중 축소."

    st.markdown(f"""<div class='card' style='margin-top:14px; padding:18px 22px; border-left:4px solid #3b82f6;'>
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;'>
    <span style='font-size:13px; color:#94a3b8; font-weight:700;'>🌐 현재 세계 시장 종합 판단</span>
    <span class='{mkt["vcls"]}' style='font-size:20px; font-weight:900;'>{mkt["verdict"]} ({mkt["score"]:.0f}/100)</span>
    </div>
    <div style='color:#cbd5e1; font-size:13px; line-height:1.6; margin-bottom:12px; padding-bottom:12px; border-bottom:1px dashed #334155;'>💡 {detail}</div>
    <div style='display:grid; grid-template-columns:1fr 1fr; gap:16px;'>
    <div style='font-size:13px; line-height:1.8;'>{pos_html}</div>
    <div style='font-size:13px; line-height:1.8;'>{neg_html}</div>
    </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ===== 종목 헤더 =====
    st.markdown(f"### {company} ({ticker})")
    prev_close = hist['Close'].iloc[-2]
    chg = curr - prev_close
    chg_pct = chg / prev_close * 100
    chg_cls = "pos" if chg >= 0 else "neg"
    chg_sign = "+" if chg >= 0 else ""

    h1, h2, h3, h4 = st.columns(4)
    with h1: st.markdown(card("현재가", f"{ccy}{curr:,.2f}",
                              f"<span class='{chg_cls}'>{chg_sign}{chg:.2f} ({chg_sign}{chg_pct:.2f}%)</span>"),
                         unsafe_allow_html=True)
    with h2:
        mcap = info.get('marketCap')
        if mcap:
            if mcap >= 1e12: mcap_v = f"{mcap/1e12:.2f}T"
            elif mcap >= 1e9: mcap_v = f"{mcap/1e9:.1f}B"
            else: mcap_v = f"{mcap/1e6:.0f}M"
            mcap_sub = "시가총액"
        else:
            mcap_v = "N/A"; mcap_sub = "데이터 없음"
        st.markdown(card("시총", mcap_v, mcap_sub), unsafe_allow_html=True)
    with h3:
        g = info.get('revenueGrowth')
        if g is not None:
            g_v = f"{g*100:+.1f}%"
            g_cls = "pos" if g > 0.05 else "neg" if g < 0 else "warn"
            g_sub = "매출성장 YoY"
            st.markdown(card("매출성장", g_v, g_sub, g_cls), unsafe_allow_html=True)
        else:
            st.markdown(card("매출성장", "N/A", "데이터 없음"), unsafe_allow_html=True)
    with h4:
        up_cls = "pos" if target["upside"] >= 0 else "neg"
        st.markdown(card("AI 목표가", f"{ccy}{target['final']:,.2f}",
                         f"<span class='{up_cls}'>상승여력 {target['upside']:+.1f}%</span>"), unsafe_allow_html=True)

    # ===== AI 종합 판정 =====
    pn = len(rec['reasons_p'])
    nn = len(rec['reasons_n'])
    st.markdown(f"""<div class='verdict {rec['vclass']}'>
        <div class='v-label'>AI 종합 투자의견</div>
        <div class='v-main'>{rec['verdict']}</div>
        <div class='v-score'>종합 점수 <b>{rec['score']} / 100</b> · 긍정 {pn}개 · 부정 {nn}개</div>
    </div>""", unsafe_allow_html=True)

    # ===== 6개월 예측 곡선 + 마일스톤 =====
    pattern_label = patterns[0]["name"] if patterns[0]["score"] > 30 else "박스권"
    st.markdown(f"<div class='section-h'>🎯 AI 6개월 예측 곡선 & 목표가 <span style='color:#64748b; font-weight:500; font-size:12px; margin-left:8px;'>패턴: <b style='color:#fbbf24;'>{pattern_label}</b> 기반</span></div>", unsafe_allow_html=True)

    dates, curve = build_forecast_curve(hist, target, patterns[0], months=6)

    fig = go.Figure()
    plot_hist = hist.iloc[-756:] if len(hist) >= 756 else hist  # 3년치
    smoothed = smooth_series(plot_hist['Close'], window=7)

    # 패턴 구간 배경 하이라이트 (vrect)
    if patterns[0]["score"] > 30:
        pat_start_idx = len(plot_hist) * 2 // 3
        pat_start = plot_hist.index[pat_start_idx]
        pat_end = plot_hist.index[-1]
        fig.add_vrect(x0=pat_start, x1=pat_end,
                      fillcolor="#fbbf24", opacity=0.10,
                      layer="below", line_width=0,
                      annotation_text=f"📍 {pattern_label} 구간",
                      annotation_position="top left",
                      annotation_font=dict(color="#fbbf24", size=11))

    # 실제 주가 (fill 없애서 y축 자동 조정)
    fig.add_trace(go.Scatter(x=plot_hist.index, y=smoothed,
                             mode='lines', line=dict(color='#3b82f6', width=2.2, shape='spline', smoothing=1.3),
                             name='실제 주가'))
    # AI 예측
    connected_dates = [hist.index[-1]] + list(dates)
    connected_curve = [curr] + list(curve)
    fig.add_trace(go.Scatter(x=connected_dates, y=connected_curve, mode='lines',
                             line=dict(color='#22c55e', width=2.8, dash='dash', shape='spline', smoothing=1.3),
                             name='AI 예측'))

    # 마일스톤 (3년 범위 - 저점/고점/현재/AI목표만)
    low_idx = plot_hist['Close'].idxmin()
    high_idx = plot_hist['Close'].idxmax()
    low_p = plot_hist.loc[low_idx, 'Close']
    high_p = plot_hist.loc[high_idx, 'Close']

    milestones = [
        (high_idx, high_p, "고점", ccy + f"{high_p:,.0f}", "#f59e0b", "top center"),
        (low_idx, low_p, "저점", ccy + f"{low_p:,.0f}", "#ef4444", "bottom center"),
        (hist.index[-1], curr, "현재", ccy + f"{curr:,.0f}", "#3b82f6", "top center"),
        (dates[-1], target["final"], "AI 목표", ccy + f"{target['final']:,.0f}", "#22c55e", "top center"),
    ]

    for d, p, label, price_str, c, pos in milestones:
        text_html = f"{label} {price_str}"
        fig.add_trace(go.Scatter(x=[d], y=[p], mode='markers+text',
                                 marker=dict(size=14, color=c, line=dict(width=2.5, color='#0a0e1a')),
                                 text=[text_html], textposition=pos,
                                 textfont=dict(color='#e2e8f0', size=12, family='Inter'),
                                 showlegend=False, hoverinfo='skip',
                                 cliponaxis=False))

    fig.update_layout(
        height=520, margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor='#0a0e1a', paper_bgcolor='#0a0e1a',
        font=dict(family="Inter", color='#e2e8f0', size=11),
        xaxis=dict(gridcolor='#1f2937', showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='#1f2937', showgrid=True, zeroline=False),
        legend=dict(orientation="h", y=1.08, x=0, bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # ===== 목표가 계산식 =====
    st.markdown("<div class='section-h'>💰 AI 목표가 계산식</div>", unsafe_allow_html=True)
    range_v = target["high52"] - target["low52"]
    tech_t = target["tech"]
    analyst_str = f"{ccy}{target['analyst']:,.2f}" if target['analyst'] else "데이터 없음"
    score_mult = 1 + (rec['score'] - 50) / 100 * 0.5

    st.markdown(f"""<div class='card' style='padding: 18px 22px;'>
    <div style='display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px dashed #334155;'>
    <span style='color:#94a3b8;'>52주 고점</span><span><b>{ccy}{target['high52']:,.2f}</b></span></div>
    <div style='display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px dashed #334155;'>
    <span style='color:#94a3b8;'>52주 저점</span><span><b>{ccy}{target['low52']:,.2f}</b></span></div>
    <div style='display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px dashed #334155;'>
    <span style='color:#94a3b8;'>박스권 폭 (고점 - 저점)</span><span><b>{ccy}{range_v:,.2f}</b></span></div>
    <div style='display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px dashed #334155;'>
    <span style='color:#94a3b8;'>기술적 목표가 (고점 + 폭×0.5)</span><span><b>{ccy}{tech_t:,.2f}</b></span></div>
    <div style='display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px dashed #334155;'>
    <span style='color:#94a3b8;'>애널리스트 평균 목표가</span><span><b>{analyst_str}</b></span></div>
    <div style='display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px dashed #334155;'>
    <span style='color:#94a3b8;'>AI 점수 보정계수 ({rec['score']}점)</span><span><b>×{score_mult:.3f}</b></span></div>
    <div style='display:flex; justify-content:space-between; padding:12px 0 4px 0; font-weight:900; font-size:16px;'>
    <span class='pos'>최종 AI 목표가</span><span class='pos'>{ccy}{target['final']:,.2f} ({target['upside']:+.1f}%)</span></div>
    </div>""", unsafe_allow_html=True)

    # ===== 분할 매수/매도 ======
    st.markdown("<div class='section-h'>💉 3단계 분할 매매 전략</div>", unsafe_allow_html=True)
    # 분할매수: 현재가 기준 -3%, -7%, -12% (지지선 근처)
    buy_p1 = curr * 0.97
    buy_p2 = curr * 0.93
    buy_p3 = max(target["low52"] * 1.05, curr * 0.88)
    # 분할매도: 현재가 → 목표가 사이 33%, 66%, 100%
    diff_t = target["final"] - curr
    sell_p1 = curr + diff_t * 0.33
    sell_p2 = curr + diff_t * 0.66
    sell_p3 = target["final"]

    sp_col1, sp_col2 = st.columns(2)
    with sp_col1:
        st.markdown(f"""<div class='card' style='border-left:4px solid #22c55e;'>
        <div style='color:#22c55e; font-weight:800; font-size:14px; margin-bottom:10px;'>📥 분할 매수 (3단계)</div>
        <div style='display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed #334155;'>
        <span style='color:#94a3b8;'>1차 (30%) · 현재가 -3%</span><b class='pos'>{ccy}{buy_p1:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed #334155;'>
        <span style='color:#94a3b8;'>2차 (35%) · 현재가 -7%</span><b class='pos'>{ccy}{buy_p2:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:6px 0;'>
        <span style='color:#94a3b8;'>3차 (35%) · 저점 지지</span><b class='pos'>{ccy}{buy_p3:,.2f}</b></div>
        </div>""", unsafe_allow_html=True)
    with sp_col2:
        st.markdown(f"""<div class='card' style='border-left:4px solid #ef4444;'>
        <div style='color:#ef4444; font-weight:800; font-size:14px; margin-bottom:10px;'>📤 분할 매도 (3단계)</div>
        <div style='display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed #334155;'>
        <span style='color:#94a3b8;'>1차 (30%) · 목표 33%</span><b class='warn'>{ccy}{sell_p1:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed #334155;'>
        <span style='color:#94a3b8;'>2차 (40%) · 목표 66%</span><b class='warn'>{ccy}{sell_p2:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:6px 0;'>
        <span style='color:#94a3b8;'>3차 (30%) · 최종 목표가</span><b class='warn'>{ccy}{sell_p3:,.2f}</b></div>
        </div>""", unsafe_allow_html=True)

    # ===== 차트 패턴 + 점수 분해 =====
    pc1, pc2 = st.columns([1, 1])
    with pc1:
        st.markdown("<div class='section-h'>🔍 차트 패턴 인식</div>", unsafe_allow_html=True)
        top = patterns[0]
        if top["score"] > 30:
            sc_color = "#22c55e" if top["signal"] == "강세" else "#ef4444"
            st.markdown(f"""<div class='card' style='border-color:{sc_color};'>
            <div style='font-size:20px; font-weight:900; color:{sc_color};'>{top['name']}</div>
            <div style='font-size:12px; color:#94a3b8; margin-top:4px;'>신뢰도 {top['score']:.0f}% · {top['signal']} 시그널</div>
            <div style='font-size:13px; color:#cbd5e1; margin-top:10px;'>{top['desc']}</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='card'>뚜렷한 패턴 없음 (박스권 횡보)</div>", unsafe_allow_html=True)
        # 전체 패턴
        pat_df = pd.DataFrame([{"패턴": p["name"], "신호": p["signal"], "점수": f"{p['score']:.0f}"}
                               for p in patterns])
        st.dataframe(pat_df, use_container_width=True, hide_index=True)

    with pc2:
        st.markdown("<div class='section-h'>📋 점수 분해 (가중치 반영)</div>", unsafe_allow_html=True)
        bd = rec["breakdown"]
        ww = rec["weights"]
        rows = []
        for k in bd:
            wgt = ww.get(k, 0) * 100
            contrib = bd[k] * ww.get(k, 0)
            rows.append({"지표": k, "점수": f"{bd[k]:.0f}", "가중치": f"{wgt:.0f}%", "기여도": f"{contrib:.1f}"})
        bd_df = pd.DataFrame(rows)
        # 정렬 (기여도 큰 순)
        bd_df["_sort"] = bd_df["기여도"].astype(float)
        bd_df = bd_df.sort_values("_sort", ascending=False).drop("_sort", axis=1)
        st.dataframe(bd_df, use_container_width=True, hide_index=True)

    # ===== 긍정/부정 신호 (도넛 차트) =====
    st.markdown("<div class='section-h'>⚖️ 긍정 vs 부정 신호 비율</div>", unsafe_allow_html=True)
    rd1, rd2 = st.columns([1, 1.4])
    with rd1:
        p_count = len(rec["reasons_p"])
        n_count = len(rec["reasons_n"])
        if p_count + n_count == 0:
            st.markdown("<div class='card'>신호 없음</div>", unsafe_allow_html=True)
        else:
            ratio_pos = p_count / (p_count + n_count) * 100
            fig_d = go.Figure(go.Pie(
                values=[p_count, n_count],
                labels=['긍정', '부정'],
                hole=0.65,
                marker=dict(colors=['#22c55e', '#ef4444'], line=dict(color='#0a0e1a', width=2)),
                textinfo='label+value',
                textfont=dict(color='white', size=14, family='Inter'),
                hoverinfo='label+percent'
            ))
            fig_d.update_layout(
                height=280, margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor='#0a0e1a', paper_bgcolor='#0a0e1a',
                showlegend=False,
                annotations=[dict(
                    text=f"<b style='color:#22c55e; font-size:22px;'>{ratio_pos:.0f}%</b><br><span style='color:#94a3b8; font-size:11px;'>긍정</span>",
                    x=0.5, y=0.5, showarrow=False
                )]
            )
            st.plotly_chart(fig_d, use_container_width=True)
    with rd2:
        list_html = "<div class='card' style='padding:14px 18px;'>"
        if rec["reasons_p"]:
            list_html += "<div style='color:#22c55e; font-weight:700; font-size:13px; margin-bottom:6px;'>✅ 긍정</div><ul style='margin:0 0 12px 0; padding-left:18px;'>"
            for r in rec["reasons_p"]:
                list_html += f"<li style='margin-bottom:4px; color:#86efac; font-size:13px;'>{r}</li>"
            list_html += "</ul>"
        if rec["reasons_n"]:
            list_html += "<div style='color:#ef4444; font-weight:700; font-size:13px; margin-bottom:6px;'>⚠️ 부정</div><ul style='margin:0; padding-left:18px;'>"
            for r in rec["reasons_n"]:
                list_html += f"<li style='margin-bottom:4px; color:#fca5a5; font-size:13px;'>{r}</li>"
            list_html += "</ul>"
        list_html += "</div>"
        st.markdown(list_html, unsafe_allow_html=True)

    # ===== 기술 지표 상세 =====
    st.markdown("<div class='section-h'>📐 기술 지표 상세</div>", unsafe_allow_html=True)
    ti1, ti2 = st.columns(2)
    with ti1:
        ichi_s, ichi_d = score_ichimoku(hist)
        ichi_cls = "pos" if ichi_s >= 60 else "neg" if ichi_s <= 40 else "warn"
        st.markdown(f"""<div class='card'>
        <div class='card-title'>🌥 일목균형표</div>
        <div class='card-value {ichi_cls}'>{ichi_s:.0f}점</div>
        <div class='card-sub' style='font-size:12px; margin-top:8px; line-height:1.6;'>{ichi_d}</div>
        </div>""", unsafe_allow_html=True)
    with ti2:
        vol_s, vol_d = score_volume(hist)
        vol_cls = "pos" if vol_s >= 60 else "neg" if vol_s <= 40 else "warn"
        st.markdown(f"""<div class='card'>
        <div class='card-title'>📊 거래량 분석</div>
        <div class='card-value {vol_cls}'>{vol_s:.0f}점</div>
        <div class='card-sub' style='font-size:12px; margin-top:8px; line-height:1.6;'>{vol_d}</div>
        </div>""", unsafe_allow_html=True)

    # ===== 이평선 정밀 분석 =====
    ma_data = analyze_ma(hist)
    if ma_data:
        st.markdown("<div class='section-h'>📈 이동평균선 정밀 분석 <span style='color:#64748b; font-weight:500; font-size:11px; margin-left:8px;'>MA20 · 60 · 120 · 240</span></div>", unsafe_allow_html=True)
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            arr_name, arr_cls, arr_desc = ma_data["arrangement"]
            st.markdown(f"""<div class='card'>
            <div class='card-title'>이평선 배열</div>
            <div class='card-value {arr_cls}' style='font-size:20px;'>{arr_name}</div>
            <div class='card-sub' style='font-size:11px; margin-top:8px; line-height:1.5;'>{arr_desc}</div>
            </div>""", unsafe_allow_html=True)
        with mc2:
            dif_name, dif_cls, dif_desc = ma_data["diffusion"]
            st.markdown(f"""<div class='card'>
            <div class='card-title'>확산 / 수렴</div>
            <div class='card-value {dif_cls}' style='font-size:20px;'>{dif_name}</div>
            <div class='card-sub' style='font-size:11px; margin-top:8px; line-height:1.5;'>{dif_desc}</div>
            </div>""", unsafe_allow_html=True)
        with mc3:
            cross_txt, cross_cls = ma_data["cross"]
            div_cls = "pos" if -3 < ma_data["diverg"] < 15 else "neg" if ma_data["diverg"] > 25 or ma_data["diverg"] < -15 else "warn"
            st.markdown(f"""<div class='card'>
            <div class='card-title'>MA240 이격도</div>
            <div class='card-value {div_cls}' style='font-size:22px;'>{ma_data["diverg"]:+.1f}%</div>
            <div class='card-sub {cross_cls}' style='font-size:11px; margin-top:8px; line-height:1.5;'>{cross_txt}</div>
            </div>""", unsafe_allow_html=True)
        with mc4:
            tim_name, tim_cls, tim_desc = ma_data["timing"]
            st.markdown(f"""<div class='card' style='border:1px solid {"#22c55e" if tim_cls == "pos" else "#ef4444" if tim_cls == "neg" else "#f59e0b"};'>
            <div class='card-title'>매매 타이밍</div>
            <div class='card-value {tim_cls}' style='font-size:18px;'>{tim_name}</div>
            <div class='card-sub' style='font-size:11px; margin-top:8px; line-height:1.5;'>{tim_desc}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown(f"""<div class='card' style='margin-top:8px; padding:10px 18px; font-size:12px; color:#94a3b8;'>
        💡 <b>기준</b>: 장기추세({ma_data["long_trend"]}) 기준 · MA240과 {"가까울수록" if ma_data["long_trend"] == "상승" else "멀수록(음수)"} 매수 / {"멀수록" if ma_data["long_trend"] == "상승" else "가까울수록"} 매도
        </div>""", unsafe_allow_html=True)

    # ===== 세력 매집 구간 분석 =====
    st.markdown("<div class='section-h'>🔥 세력 매집 구간 분석 <span style='color:#64748b; font-weight:500; font-size:11px; margin-left:8px;'>OBV · POC · VCP</span></div>", unsafe_allow_html=True)
    wc1, wc2, wc3 = st.columns(3)
    obv_s, obv_d = score_obv(hist)
    poc_p, poc_s, poc_d = find_poc(hist)
    vcp_s, vcp_d = score_vcp(hist)
    obv_cls = "pos" if obv_s >= 60 else "neg" if obv_s <= 40 else "warn"
    poc_cls = "pos" if poc_s >= 60 else "neg" if poc_s <= 40 else "warn"
    vcp_cls = "pos" if vcp_s >= 60 else "neg" if vcp_s <= 40 else "warn"
    with wc1:
        st.markdown(f"""<div class='card'>
        <div class='card-title'>💰 OBV (누적 거래량)</div>
        <div class='card-value {obv_cls}'>{obv_s:.0f}점</div>
        <div class='card-sub' style='font-size:12px; margin-top:8px; line-height:1.6;'>{obv_d}</div>
        </div>""", unsafe_allow_html=True)
    with wc2:
        st.markdown(f"""<div class='card'>
        <div class='card-title'>🎯 POC (매물대 중심)</div>
        <div class='card-value {poc_cls}'>{poc_s:.0f}점</div>
        <div class='card-sub' style='font-size:12px; margin-top:8px; line-height:1.6;'>{poc_d}</div>
        </div>""", unsafe_allow_html=True)
    with wc3:
        st.markdown(f"""<div class='card'>
        <div class='card-title'>🌀 VCP (변동성 수축)</div>
        <div class='card-value {vcp_cls}'>{vcp_s:.0f}점</div>
        <div class='card-sub' style='font-size:12px; margin-top:8px; line-height:1.6;'>{vcp_d}</div>
        </div>""", unsafe_allow_html=True)
    # 세력 매집 종합 결론
    accu_avg = (obv_s + poc_s + vcp_s) / 3
    if accu_avg >= 70:
        accu_msg, accu_cls = "🔥 강한 세력 매집 구간 - 매수 우위", "pos"
    elif accu_avg >= 55:
        accu_msg, accu_cls = "💡 매집 신호 감지 - 관심", "pos"
    elif accu_avg <= 35:
        accu_msg, accu_cls = "⚠️ 세력 분산 - 매도 우위", "neg"
    else:
        accu_msg, accu_cls = "⚖️ 매집/분산 혼조", "warn"
    st.markdown(f"<div class='card' style='margin-top:8px; padding:12px 18px;'><span class='{accu_cls}' style='font-weight:800;'>{accu_msg}</span> <span style='color:#94a3b8; margin-left:8px; font-size:13px;'>· 종합 {accu_avg:.0f}점</span></div>", unsafe_allow_html=True)


    # ===== 애널리스트 분포 =====
    if target['analyst']:
        st.markdown("<div class='section-h'>📊 애널리스트 목표가 분포</div>", unsafe_allow_html=True)
        a_data = pd.DataFrame({
            "구분": ["애널리스트 최고", "애널리스트 평균", "AI 종합 목표가", "기술적 목표가", "현재가", "애널리스트 최저"],
            "가격": [target['analyst_high'] or target['analyst'], target['analyst'],
                   target['final'], target['tech'], curr, target['analyst_low'] or target['analyst']]
        }).sort_values("가격", ascending=True)
        colors_a = []
        for lbl in a_data['구분']:
            if "현재가" in lbl: colors_a.append('#f1f5f9')
            elif "AI" in lbl: colors_a.append('#22c55e')
            elif "최저" in lbl: colors_a.append('#ef4444')
            elif "최고" in lbl: colors_a.append('#86efac')
            else: colors_a.append('#64748b')
        fig_a = go.Figure(go.Bar(x=a_data['가격'], y=a_data['구분'], orientation='h',
                                  marker_color=colors_a,
                                  text=[f"{ccy}{p:,.2f}" for p in a_data['가격']],
                                  textposition='outside'))
        fig_a.update_layout(height=280, margin=dict(l=10, r=80, t=10, b=10),
                            plot_bgcolor='#0a0e1a', paper_bgcolor='#0a0e1a',
                            font=dict(color='#e2e8f0', size=12),
                            xaxis=dict(gridcolor='#1f2937'),
                            yaxis=dict(gridcolor='#1f2937'),
                            showlegend=False)
        st.plotly_chart(fig_a, use_container_width=True)

    st.markdown("""<div style='margin-top:24px; padding:14px; background:#1e293b;
    border-left:4px solid #f59e0b; border-radius:6px; font-size:12px; color:#cbd5e1;'>
    ⚠️ <b>유의사항</b> · 본 분석은 알고리즘 기반 참고 자료입니다. 모든 투자 책임은 본인에게 있습니다.
    </div>""", unsafe_allow_html=True)

    # ===== 백테스트 (예측 정확도 검증) =====
    bt = backtest_prediction(hist, info)
    if bt:
        st.markdown("---")
        st.markdown("<div class='section-h'>🔬 백테스트: AI 예측 정확도 검증 <span style='color:#64748b; font-weight:500; font-size:11px; margin-left:8px;'>· 2년 전 시점 → 현재 비교</span></div>", unsafe_allow_html=True)
        bc1, bc2, bc3, bc4 = st.columns(4)
        with bc1:
            st.markdown(card(f"2년 전 기준일", bt["past_date"],
                            f"당시 주가 {ccy}{bt['past_price']:,.2f}"), unsafe_allow_html=True)
        with bc2:
            st.markdown(card("당시 AI 예측가", f"{ccy}{bt['past_target']:,.2f}",
                            f"방향: {bt['pred_dir']}"), unsafe_allow_html=True)
        with bc3:
            ch_cls = "pos" if bt["actual_change"] >= 0 else "neg"
            st.markdown(card("현재 실제가", f"{ccy}{bt['actual_price']:,.2f}",
                            f"<span class='{ch_cls}'>2년 {bt['actual_change']:+.1f}%</span>"), unsafe_allow_html=True)
        with bc4:
            acc_cls = "pos" if bt["acc_score"] >= 70 else "neg" if bt["acc_score"] <= 40 else "warn"
            match_txt = "✓ 적중" if bt["dir_match"] else "✗ 빗나감"
            match_cls = "pos" if bt["dir_match"] else "neg"
            st.markdown(card("예측 정확도", f"{bt['acc_score']}점",
                            f"오차 {bt['err_pct']:.1f}% · <span class='{match_cls}'>방향 {match_txt}</span>",
                            acc_cls), unsafe_allow_html=True)
        if bt["acc_score"] >= 70 and bt["dir_match"]:
            bt_msg = "🟢 과거 예측이 실제와 매우 근접했습니다. 이번 예측도 신뢰도 높음."
            bt_cls = "pos"
        elif bt["dir_match"]:
            bt_msg = "🟡 방향은 맞았으나 가격 오차가 있습니다. 참고용으로 활용."
            bt_cls = "warn"
        else:
            bt_msg = "🔴 과거 예측이 빗나갔습니다. 이번 예측도 보수적으로 해석 필요."
            bt_cls = "neg"
        st.markdown(f"<div class='card' style='margin-top:8px; padding:14px 18px;'><span class='{bt_cls}' style='font-weight:700;'>{bt_msg}</span></div>", unsafe_allow_html=True)

    # ===== 유사 패턴 검색 (과거 비슷한 상황 통계) =====
    st.markdown("---")
    st.markdown("<div class='section-h'>🔍 유사 패턴 검색 <span style='color:#64748b; font-weight:500; font-size:11px; margin-left:8px;'>· 보조지표 상태가 비슷했던 과거 시점 → 이후 통계</span></div>", unsafe_allow_html=True)
    st.caption("✅ 사용할 지표 선택 → 비슷한 과거 5개 시점을 찾아 1일/5일/10일 후 평균 변동률과 승률을 보여줍니다")

    pat_col = st.columns(4)
    with pat_col[0]:
        use_bb = st.checkbox("📊 볼린저밴드", value=True, key="ind_bb")
    with pat_col[1]:
        use_rsi = st.checkbox("📈 RSI", value=True, key="ind_rsi")
    with pat_col[2]:
        use_macd = st.checkbox("📉 MACD", value=True, key="ind_macd")
    with pat_col[3]:
        use_obv = st.checkbox("💰 OBV", value=True, key="ind_obv")

    inds = []
    if use_bb: inds.append('BB')
    if use_rsi: inds.append('RSI')
    if use_macd: inds.append('MACD')
    if use_obv: inds.append('OBV')

    if not inds:
        st.warning("최소 1개 이상의 지표를 선택하세요")
    else:
        with st.spinner("유사 패턴 검색 중..."):
            sim = find_similar_patterns(hist, inds)

        if sim is None:
            st.info("유사 패턴을 찾을 수 없습니다 (데이터 부족)")
        else:
            # 현재 지표 상태
            cur_html = ""
            for ind in inds:
                if ind in sim['cur_desc']:
                    cur_html += f"<div style='display:inline-block; padding:6px 12px; margin:3px; background:#1e293b; border-radius:6px; font-size:12px;'><span style='color:#94a3b8;'>{ind}:</span> <b style='color:#f1f5f9;'>{sim['cur_desc'][ind]}</b></div>"

            v_name, v_cls, v_desc = sim['verdict']
            st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:4px solid {"#22c55e" if v_cls=="pos" else "#ef4444" if v_cls=="neg" else "#f59e0b"};'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
            <div>
            <div style='color:#94a3b8; font-size:12px; font-weight:700; margin-bottom:6px;'>📍 현재 지표 상태</div>
            <div>{cur_html}</div>
            </div>
            <div style='text-align:right;'>
            <span class='{v_cls}' style='font-size:20px; font-weight:900;'>{v_name}</span>
            <div style='color:#94a3b8; font-size:12px; margin-top:4px;'>{v_desc}</div>
            </div>
            </div>
            </div>""", unsafe_allow_html=True)

            # 이후 가격 변화 통계 (1일/5일/10일)
            st.markdown("<div style='font-weight:700; color:#94a3b8; font-size:13px; margin:14px 0 8px 0;'>📊 유사 패턴 이후 가격 변화 통계 (과거 5개 시점 평균)</div>", unsafe_allow_html=True)
            stat_cols = st.columns(3)
            for idx, d in enumerate([1, 5, 10]):
                with stat_cols[idx]:
                    if d in sim['stats']:
                        st_d = sim['stats'][d]
                        avg = st_d['avg']
                        wr = st_d['win_rate']
                        avg_cls = "pos" if avg > 0 else "neg"
                        st.markdown(f"""<div class='card' style='padding:16px 20px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:13px; font-weight:600;'>{d}일 후</div>
                        <div class='{avg_cls}' style='font-size:32px; font-weight:900; margin:8px 0;'>{avg:+.2f}%</div>
                        <div style='color:#cbd5e1; font-size:13px;'>승률 <b>{wr:.0f}%</b> · 최고 {st_d['max']:+.1f}% · 최저 {st_d['min']:+.1f}%</div>
                        </div>""", unsafe_allow_html=True)

            # 유사 시점 리스트
            st.markdown("<div style='font-weight:700; color:#94a3b8; font-size:13px; margin:14px 0 8px 0;'>🕒 유사도 높은 과거 시점 5개</div>", unsafe_allow_html=True)
            rows = []
            for m in sim['matches']:
                row = {"날짜": m['date'].strftime("%Y-%m-%d"), "당시 주가": f"{ccy}{hist['Close'].iloc[m['idx']]:,.2f}"}
                for d in [1, 5, 10]:
                    if m['idx'] + d < len(hist):
                        p_then = hist['Close'].iloc[m['idx'] + d]
                        p_now = hist['Close'].iloc[m['idx']]
                        chg = (p_then - p_now) / p_now * 100
                        row[f"{d}일 후"] = f"{chg:+.2f}%"
                rows.append(row)
            sim_df = pd.DataFrame(rows)
            st.dataframe(sim_df, use_container_width=True, hide_index=True)
            st.caption("💡 과거 패턴 기반 참고 통계입니다 · 투자 판단과 책임은 사용자에게 있습니다")

    # ===== 경제 위험도 분석 (인플레 + 경기침체 통합) =====
    st.markdown("---")
    st.markdown("<div class='section-h'>🌡️ 경제 위험도 종합 분석 <span style='color:#64748b; font-weight:500; font-size:11px; margin-left:8px;'>· 인플레 + 경기침체 + 스태그플레이션</span></div>", unsafe_allow_html=True)

    eco = analyze_economy(macro, hist)

    # 종합 판정 박스
    st.markdown(f"""<div class='card' style='padding:22px 26px; border-left:6px solid {"#ef4444" if eco['overall_cls'] == "neg" else "#f59e0b" if eco['overall_cls'] == "warn" else "#22c55e"};'>
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;'>
    <span style='font-size:13px; color:#94a3b8; font-weight:700; letter-spacing:1px;'>현재 경제 국면</span>
    <span class='{eco["overall_cls"]}' style='font-size:24px; font-weight:900;'>{eco["overall"]}</span>
    </div>
    <div style='color:#cbd5e1; font-size:13px; line-height:1.6;'>💬 {eco["msg"]}</div>
    </div>""", unsafe_allow_html=True)

    # 인플레이션 + 경기침체 점수
    eco_c1, eco_c2 = st.columns(2)
    with eco_c1:
        inf_cls = "neg" if eco["inf_score"] >= 65 else "warn" if eco["inf_score"] >= 50 else "pos"
        inf_factor_html = ""
        for name, val, status, cls in eco["inf_factors"]:
            inf_factor_html += f"<div style='display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed #334155;'><span style='color:#94a3b8; font-size:13px;'>{name}</span><span><b style='color:#f1f5f9;'>{val}</b> <span class='{cls}' style='font-size:11px; margin-left:6px;'>{status}</span></span></div>"
        st.markdown(f"""<div class='card' style='padding:18px 22px;'>
        <div style='display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px;'>
        <span style='color:#94a3b8; font-weight:700; font-size:13px;'>🔥 인플레이션 위험도</span>
        <span class='{inf_cls}' style='font-size:28px; font-weight:900;'>{eco["inf_score"]:.0f}<span style='font-size:14px; color:#64748b;'>/100</span></span>
        </div>
        {inf_factor_html}
        </div>""", unsafe_allow_html=True)
    with eco_c2:
        rec_cls = "neg" if eco["rec_score"] >= 55 else "warn" if eco["rec_score"] >= 40 else "pos"
        rec_factor_html = ""
        for name, val, status, cls in eco["rec_factors"]:
            rec_factor_html += f"<div style='display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px dashed #334155;'><span style='color:#94a3b8; font-size:13px;'>{name}</span><span><b style='color:#f1f5f9;'>{val}</b> <span class='{cls}' style='font-size:11px; margin-left:6px;'>{status}</span></span></div>"
        st.markdown(f"""<div class='card' style='padding:18px 22px;'>
        <div style='display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px;'>
        <span style='color:#94a3b8; font-weight:700; font-size:13px;'>📉 경기침체 위험도</span>
        <span class='{rec_cls}' style='font-size:28px; font-weight:900;'>{eco["rec_score"]:.0f}<span style='font-size:14px; color:#64748b;'>/100</span></span>
        </div>
        {rec_factor_html}
        </div>""", unsafe_allow_html=True)

    st.caption("📚 **인플레 지표**: CPI, Core CPI, PPI, PCE (Fed 목표 2%) · **경기침체 지표**: 장단기금리역전, 삼의법칙, 실업률, LEI 선행지수, ISM PMI, NY연준 침체확률, 하이일드 스프레드")

    # ===== 스태그플레이션 정밀 판정 =====
    stag = detect_stagflation(macro)
    if stag["total"] > 0:
        cond_html = ""
        for c in stag["conditions"]:
            check_icon = "✅" if c["met"] else "⬜"
            check_cls = "pos" if c["met"] else ""
            cond_html += f"""<div style='display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px dashed #334155;'>
            <div style='display:flex; align-items:center; gap:10px;'>
            <span style='font-size:18px;'>{check_icon}</span>
            <div>
            <div style='color:#f1f5f9; font-weight:700; font-size:14px;'>{c["name"]}</div>
            <div style='color:#64748b; font-size:11px;'>{c["desc"]}</div>
            </div>
            </div>
            <div style='text-align:right;'>
            <div class='{check_cls}' style='font-weight:800; font-size:14px;'>{c["metric"]}</div>
            <div style='color:#64748b; font-size:11px;'>기준: {c["threshold"]}</div>
            </div>
            </div>"""

        ratio_pct = stag["met"] / stag["total"] * 100
        bar_color = "#ef4444" if ratio_pct >= 75 else "#f59e0b" if ratio_pct >= 50 else "#22c55e"

        st.markdown(f"""<div class='card' style='margin-top:18px; padding:22px 26px; border-left:6px solid {bar_color};'>
        <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;'>
        <span style='font-size:13px; color:#94a3b8; font-weight:700; letter-spacing:1px;'>🌀 스태그플레이션 정밀 판정</span>
        <div style='text-align:right;'>
        <span class='{stag["cls"]}' style='font-size:22px; font-weight:900;'>{stag["status"]}</span>
        <div style='color:#64748b; font-size:12px; margin-top:2px;'>{stag["met"]} / {stag["total"]} 조건 충족</div>
        </div>
        </div>
        <div style='background:#0a0e1a; border-radius:4px; height:8px; margin-bottom:16px; overflow:hidden;'>
        <div style='background:{bar_color}; height:100%; width:{ratio_pct}%;'></div>
        </div>
        <div style='color:#cbd5e1; font-size:13px; line-height:1.6; margin-bottom:14px; padding-bottom:14px; border-bottom:1px solid #334155;'>💡 {stag["msg"]}</div>
        <div style='color:#94a3b8; font-size:12px; font-weight:700; margin-bottom:8px;'>📋 4가지 충족 조건 (모두 만족시 스태그플레이션 확정)</div>
        {cond_html}
        </div>""", unsafe_allow_html=True)

    # ===== 시장 × 인플레 × 침체 조합 진단 =====
    combo_name, combo_desc, combo_cls = combined_diagnosis(mkt["score"], eco["inf_score"], eco["rec_score"])
    st.markdown(f"""<div class='card' style='margin-top:18px; padding:22px 26px; border-left:6px solid {"#ef4444" if combo_cls == "neg" else "#f59e0b" if combo_cls == "warn" else "#22c55e"}; background:linear-gradient(135deg, rgba(59,130,246,0.04), transparent);'>
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
    <span style='font-size:13px; color:#94a3b8; font-weight:700; letter-spacing:1px;'>🎯 시장 × 인플레 × 침체 조합 진단</span>
    <div style='font-size:12px; color:#64748b;'>시장 {mkt["score"]:.0f} · 인플레 {eco["inf_score"]:.0f} · 침체 {eco["rec_score"]:.0f}</div>
    </div>
    <div class='{combo_cls}' style='font-size:22px; font-weight:900; margin-bottom:10px;'>{combo_name}</div>
    <div style='color:#cbd5e1; font-size:13px; line-height:1.7;'>📜 {combo_desc}</div>
    </div>""", unsafe_allow_html=True)

except Exception as e:
    st.error(f"오류: {e}")
    st.exception(e)
