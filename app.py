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
import time as _time

# yfinance 공용 세션 (User-Agent로 차단 완화)
_YF_SESSION = requests.Session()
_YF_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
})


def yf_history_safe(ticker, period="1y", retries=3):
    """yfinance history 재시도 래퍼 (Rate Limit 대응)"""
    for i in range(retries):
        try:
            t = yf.Ticker(ticker, session=_YF_SESSION)
            h = t.history(period=period)
            if not h.empty:
                return h, t
        except Exception:
            pass
        _time.sleep(1.5 * (i + 1))
    return None, None


FRED_API_KEY = "5986a12ba743119f15c35ae435aa758a"

st.set_page_config(page_title="Alpha Pro Terminal v3", layout="wide", page_icon="📈")

# ============ 스타일 ============
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans KR', -apple-system, sans-serif;
    letter-spacing: -0.01em;
}
.stApp { background: #08090d; color: #e5e7eb; }
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1400px; }

/* 숫자는 무조건 고정폭 */
.num, .card-value, .v-main, .v-score {
    font-family: 'JetBrains Mono', 'SF Mono', Consolas, monospace !important;
    font-feature-settings: "tnum" 1, "zero" 1;
    letter-spacing: -0.02em;
}

/* 타이틀 */
.title-bar {
    font-size: 24px; font-weight: 800; color: #fafafa;
    letter-spacing: -0.02em; margin-bottom: 2px;
}
.title-sub { font-size: 12px; color: #6b7280; margin-bottom: 32px; font-weight: 500; }

/* 섹션 헤더 - 여백 ↑ */
.section-h {
    font-size: 13px; font-weight: 700; color: #d1d5db;
    margin: 36px 0 14px 0;
    display: flex; align-items: center; gap: 8px;
    letter-spacing: 0.02em;
}

/* 카드 - 보더 약하게, 여백 ↑ */
.card {
    background: #0f1117;
    border: 1px solid #1c1f26;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 12px;
    transition: border-color 0.2s;
}
.card:hover { border-color: #2d3138; }

.card-title {
    font-size: 11px;
    color: #6b7280;
    font-weight: 500;
    margin-bottom: 8px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.card-value {
    font-size: 28px;
    font-weight: 700;
    color: #fafafa;
    line-height: 1.1;
}
.card-sub {
    font-size: 11px;
    color: #6b7280;
    margin-top: 8px;
    font-weight: 500;
}

/* 색은 신호로만 - 채도 살짝 줄임 */
.pos { color: #4ade80; }
.neg { color: #f87171; }
.warn { color: #fbbf24; }

/* AI 종합 의견 - 색상 절제 */
.verdict {
    border-radius: 12px;
    padding: 28px 32px;
    color: white;
    margin: 20px 0 24px 0;
    border: 1px solid transparent;
}
.v-strong-buy { background: #15803d; }
.v-buy { background: #16a34a; }
.v-hold { background: #1f2937; border-color: #fbbf24; color: #fbbf24; }
.v-sell { background: #dc2626; }
.v-strong-sell { background: #991b1b; }
.v-label {
    font-size: 10px; opacity: 0.75; font-weight: 600;
    letter-spacing: 0.15em; text-transform: uppercase;
    font-family: 'Inter', sans-serif !important;
}
.v-main {
    font-size: 38px; font-weight: 800; margin-top: 6px;
}
.v-score {
    font-size: 13px; opacity: 0.85; margin-top: 10px;
    font-weight: 500;
}

/* 버튼 - 절제된 톤 */
.stButton>button {
    background: #1f2937;
    color: #fafafa;
    border: 1px solid #374151;
    font-weight: 600;
    border-radius: 8px;
    height: 42px;
    width: 100%;
    transition: all 0.15s;
}
.stButton>button:hover {
    background: #374151;
    border-color: #4b5563;
}

/* 인풋 */
.stTextInput input {
    background: #0f1117 !important;
    color: #fafafa !important;
    border: 1px solid #1c1f26 !important;
    border-radius: 8px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
.stTextInput input:focus { border-color: #374151 !important; }

/* 테이블 */
.stDataFrame, [data-testid="stDataFrame"] {
    background: #0f1117 !important;
    border: 1px solid #1c1f26 !important;
    border-radius: 8px !important;
}
.stDataFrame td, .stDataFrame th {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
}

/* 구분선 - 여백 기반 */
hr {
    border: none !important;
    border-top: 1px solid #1c1f26 !important;
    margin: 32px 0 !important;
}

/* 캡션 */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #4b5563 !important;
    font-size: 11px !important;
}

/* 체크박스 */
.stCheckbox > label > div[data-testid="stMarkdownContainer"] p {
    font-size: 13px !important;
    color: #d1d5db !important;
    font-weight: 500;
}

.stTextInput label, .stCheckbox label { color: #9ca3af !important; }

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }
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
    """FRED 시리즈 최신값 (재시도 + null 건너뛰기)"""
    for attempt in range(3):
        try:
            url = "https://api.stlouisfed.org/fred/series/observations"
            params = {"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json",
                      "sort_order": "desc", "limit": 10}  # 10개 받아서 null 건너뜀
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                obs = r.json().get("observations", [])
                vals = [float(o["value"]) for o in obs if o["value"] != "."]
                if len(vals) >= 2:
                    return vals[0], vals[1]
                elif len(vals) == 1:
                    return vals[0], vals[0]
        except Exception:
            pass
        _time.sleep(1)
    return None, None


@st.cache_data(ttl=600)
def yf_last(ticker):
    """yfinance 최근가 + 전일대비 (Rate Limit 재시도)"""
    h, _ = yf_history_safe(ticker, period="5d", retries=2)
    if h is not None and len(h) >= 2:
        return float(h['Close'].iloc[-1]), float(h['Close'].iloc[-2])
    return None, None


@st.cache_data(ttl=300, show_spinner=False)
def get_coinbase_premium():
    """Coinbase 프리미엄 = (Coinbase BTC - Binance BTC) / Binance * 100
    양수 = 미국 기관 매수 우위(강세) / 음수 = 매도 우위(약세)"""
    try:
        import requests
        cb = None; bn = None
        try:
            r = requests.get("https://api.exchange.coinbase.com/products/BTC-USD/ticker", timeout=5)
            if r.status_code == 200: cb = float(r.json()["price"])
        except Exception: pass
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=5)
            if r.status_code == 200: bn = float(r.json()["price"])
        except Exception: pass
        if cb and bn:
            return {"premium": (cb-bn)/bn*100, "coinbase": cb, "binance": bn, "source": "live"}
        h, _ = yf_history_safe("BTC-USD", period="5d", retries=2)
        if h is not None and not h.empty:
            return {"premium": None, "coinbase": float(h['Close'].iloc[-1]), "binance": None, "source": "fallback"}
    except Exception: pass
    return None


def interpret_premium(premium):
    """프리미엄 해석"""
    if premium is None:
        return ("⚪ 데이터 없음", "warn", "프리미엄 계산 불가")
    if premium > 0.1:
        return ("🟢 강한 매수세", "pos", f"+{premium:.3f}% · 미국 기관 적극 매수. 강세 - 추가 상승 여력")
    elif premium > 0.02:
        return ("🟢 매수 우위", "pos", f"+{premium:.3f}% · 미국 순매수. 코인베이스가 더 비쌈 = 미국 수요 강함")
    elif premium > -0.02:
        return ("⚪ 중립", "warn", f"{premium:+.3f}% · 미국-글로벌 가격 동일. 방향성 없음")
    elif premium > -0.1:
        return ("🔴 매도 우위", "neg", f"{premium:.3f}% · 미국 순매도. 코인베이스가 더 쌈 = 미국 자금 이탈")
    else:
        return ("🔴 강한 매도세", "neg", f"{premium:.3f}% · 미국 기관 적극 매도. 약세 - 추가 하락 주의")


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
    m["real_rate"] = fred_get("DFII10")               # 10년 실질금리 (TIPS)
    m["vix9d"] = yf_last("^VIX9D")                     # 9일 VIX
    m["vix3m"] = yf_last("^VIX3M")                     # 3개월 VIX
    m["vvix"] = yf_last("^VVIX")                       # VIX의 변동성
    m["skew"] = yf_last("^SKEW")                       # 블랙스완 지수
    m["ovx"] = yf_last("^OVX")                          # 유가 변동성 (인플레 신호)
    # SPY 옵션 PCR (시장 전체 옵션 심리)
    try:
        spy_opt = get_option_chain("SPY")
        m["spy_pcr"] = spy_opt["pcr"] if spy_opt else None
    except Exception:
        m["spy_pcr"] = None
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

    # 8. VIX (+ 기간구조 백워데이션 + SKEW 반영)
    vix = macro.get("vix", (None, None))[0]
    if vix:
        if vix < 14: s["VIX"] = 75; reasons_p.append(f"VIX {vix:.1f} - 매우안정")
        elif vix < 17: s["VIX"] = 65; reasons_p.append(f"VIX {vix:.1f} - 안정")
        elif vix < 20: s["VIX"] = 55
        elif vix < 25: s["VIX"] = 40; reasons_n.append(f"VIX {vix:.1f} - 경계")
        elif vix < 30: s["VIX"] = 28; reasons_n.append(f"VIX {vix:.1f} - 변동성↑")
        else: s["VIX"] = 15; reasons_n.append(f"VIX {vix:.1f} - 극단공포")
        # 백워데이션
        vix9d = macro.get("vix9d", (None, None))[0]
        vix3m = macro.get("vix3m", (None, None))[0]
        if vix9d and vix3m and vix9d > vix3m:
            s["VIX"] = max(10, s["VIX"] - 22); reasons_n.append("VIX 백워데이션 - 시장 균열")
        # SKEW
        skew = macro.get("skew", (None, None))[0]
        if skew:
            if skew > 150: s["VIX"] = max(10, s["VIX"] - 12); reasons_n.append(f"SKEW {skew:.0f} - 블랙스완 경계")
            elif skew > 145: s["VIX"] = max(10, s["VIX"] - 8); reasons_n.append(f"SKEW {skew:.0f} - 헤지급증")
            elif skew > 140: s["VIX"] = max(10, s["VIX"] - 4)
        # VVIX
        vvix = macro.get("vvix", (None, None))[0]
        if vvix and vvix > 105:
            s["VIX"] = max(10, s["VIX"] - 5); reasons_n.append(f"VVIX {vvix:.0f} - 옵션불안")
        # OVX 인플레 충격
        ovx = macro.get("ovx", (None, None))[0]
        if ovx and ovx > 50:
            s["VIX"] = max(10, s["VIX"] - 4); reasons_n.append(f"OVX {ovx:.0f} - 유가충격")
        # SPY PCR
        spy_pcr = macro.get("spy_pcr")
        if spy_pcr and spy_pcr > 1.2:
            s["VIX"] = max(10, s["VIX"] - 5); reasons_n.append(f"SPY PCR {spy_pcr:.2f} - 폭락헤지")
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

    # 10. 미국 금리 (+ 실질금리)
    us10y = macro.get("us10y", (None, None))[0]
    if us10y:
        if us10y < 3.5: s["금리"] = 70; reasons_p.append(f"美 10Y {us10y:.2f}% - 우호")
        elif us10y < 4.5: s["금리"] = 55
        else: s["금리"] = 35; reasons_n.append(f"美 10Y {us10y:.2f}% - 부담")
        # 실질금리 높으면 밸류 부담
        rr = macro.get("real_rate", (None, None))[0]
        if rr and rr > 2.5:
            s["금리"] = max(20, s["금리"] - 12); reasons_n.append(f"실질금리 {rr:.2f}% - 밸류 부담")
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

    if total >= 75: verdict, vclass = "적극 매수", "v-strong-buy"
    elif total >= 65: verdict, vclass = "매수", "v-buy"
    elif total >= 45: verdict, vclass = "중립 / 관망", "v-hold"
    elif total >= 35: verdict, vclass = "매도", "v-sell"
    else: verdict, vclass = "적극 매도", "v-strong-sell"

    return {"score": total, "verdict": verdict, "vclass": vclass,
            "breakdown": s, "weights": w,
            "reasons_p": reasons_p, "reasons_n": reasons_n}


# ============ AI 목표가 & 예측 곡선 ============
def calc_target(hist, info, rec_score, top_pattern=None, market_score=50):
    """목표가 계산 (보수적 재설계)
    - 기준점: 5일 평균가 (일봉 흔들림 방지)
    - 기술적 목표: 52주 고점 또는 애널리스트 목표가 사용 (과도한 추정 X)
    - 점수별 차등 상한: 매수 시그널만 +상승, 중립/매도는 제한적
    """
    curr = float(hist['Close'].iloc[-1])
    avg_5d = float(hist['Close'].iloc[-5:].mean()) if len(hist) >= 5 else curr

    high52 = float(hist['Close'].iloc[-252:].max()) if len(hist) >= 252 else float(hist['Close'].max())
    low52 = float(hist['Close'].iloc[-252:].min()) if len(hist) >= 252 else float(hist['Close'].min())
    analyst_t = info.get('targetMeanPrice')

    # === 기본 base 결정 (이전: 고점 + 범위*0.5로 너무 공격적이었음) ===
    # 보수적: 애널리스트 있으면 그것 우선, 없으면 52주 고점의 1.1배까지만
    if analyst_t and analyst_t > 0:
        # 애널리스트 목표 + 52주 고점 평균 (애널리스트 가중치 高)
        base = analyst_t * 0.7 + min(high52 * 1.05, analyst_t * 1.2) * 0.3
    else:
        # 애널리스트 데이터 없으면: 52주 고점 기준 +5% 정도까지만
        base = high52 * 1.05

    # === 점수별 차등 (보수적) ===
    # 80점: +15%, 70점: +8%, 60점: +3%, 50점: 0%, 40점: -5%, 30점: -15%, 20점: -25%
    if rec_score >= 75:
        score_mult = 1.15
    elif rec_score >= 65:
        score_mult = 1.08
    elif rec_score >= 55:
        score_mult = 1.03
    elif rec_score >= 45:
        score_mult = 1.00  # 중립
    elif rec_score >= 35:
        score_mult = 0.95
    elif rec_score >= 25:
        score_mult = 0.85
    else:
        score_mult = 0.75

    # 시장 점수 보정 (작게)
    if market_score >= 75: market_mult = 1.03
    elif market_score >= 60: market_mult = 1.01
    elif market_score >= 45: market_mult = 1.00
    elif market_score >= 30: market_mult = 0.97
    else: market_mult = 0.93

    final = base * score_mult * market_mult

    # === 상한 캡: 점수별로 절대 넘으면 안 되는 한계 ===
    # 매수 시그널이라도 6개월 +50% 이상은 비현실적
    if rec_score >= 65:
        cap = avg_5d * 1.50    # 매수: 최대 +50%
    elif rec_score >= 50:
        cap = avg_5d * 1.20    # 중립/관망: 최대 +20%
    elif rec_score >= 35:
        cap = avg_5d * 1.05    # 매도 약세: 최대 +5% (반등 한정)
    else:
        cap = avg_5d * 0.95    # 매도 강세: 현재가 아래

    final = min(final, cap)

    # === 하한 캡: 매수 시그널이면 너무 낮은 목표가 방지 ===
    if rec_score >= 65:
        floor = avg_5d * 1.05  # 매수면 최소 +5%
        final = max(final, floor)
    elif rec_score >= 50:
        floor = avg_5d * 0.95  # 중립이면 최소 -5%
        final = max(final, floor)

    # 약세 패턴 + 낮은 점수
    if top_pattern and top_pattern.get("signal") == "약세" and top_pattern["score"] > 30:
        if rec_score < 45:
            final = min(final, avg_5d * (0.85 if rec_score < 35 else 0.92))

    # 약세 추세에서 목표가 제한
    if top_pattern and top_pattern.get("trend") == "down" and rec_score < 55:
        final = min(final, avg_5d * 1.05)

    # tech_t는 표시용으로만 유지 (사용자 참고)
    tech_t = high52 * 1.05

    return {
        "current": curr, "avg_5d": avg_5d,
        "high52": high52, "low52": low52,
        "tech": tech_t, "analyst": analyst_t,
        "analyst_high": info.get('targetHighPrice'),
        "analyst_low": info.get('targetLowPrice'),
        "final": final, "upside": (final - curr) / curr * 100,
        "market_mult": market_mult, "market_score": market_score
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


# ============ 섹터 ETF (S&P500 11개 GICS + 추가 4개) ============
SECTOR_ETFS = {
    "에너지": "XLE",
    "필수소비재": "XLP",
    "금융": "XLF",
    "부동산/리츠": "XLRE",
    "통신서비스": "XLC",
    "헬스케어": "XLV",
    "유틸리티": "XLU",
    "소재": "XLB",
    "임의소비재": "XLY",
    "산업재": "XLI",
    "기술": "XLK",
    # 추가 테마
    "우주항공/방산": "ITA",
    "반도체": "SMH",
    "원자력/SMR": "NLR",
    "신흥국": "EEM",
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_sector_flow():
    """15개 섹터 ETF 1개월 등락률"""
    result = []
    for name, tk in SECTOR_ETFS.items():
        try:
            h, _ = yf_history_safe(tk, period="3mo", retries=2)
            if h is None or len(h) < 21: continue
            curr = float(h['Close'].iloc[-1])
            m_ago = float(h['Close'].iloc[-21])
            w_ago = float(h['Close'].iloc[-5]) if len(h) >= 5 else curr
            month_chg = (curr - m_ago) / m_ago * 100
            week_chg = (curr - w_ago) / w_ago * 100
            result.append({
                "name": name, "ticker": tk,
                "month": month_chg, "week": week_chg
            })
        except Exception:
            continue
    # 1개월 등락률 높은 순
    result.sort(key=lambda x: x["month"], reverse=True)
    return result


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
    if pd.isna(low) or pd.isna(high) or low >= high:
        return None, 50, "측정 불가"
    bin_edges = np.linspace(low, high, bins + 1)
    vol_at_price = np.zeros(bins)
    for i in range(len(sample)):
        p = sample['Close'].iloc[i]
        v = sample['Volume'].iloc[i]
        if pd.isna(p) or pd.isna(v): continue
        try:
            idx = min(int((p - low) / (high - low) * bins), bins - 1)
            if idx >= 0: vol_at_price[idx] += v
        except (ValueError, OverflowError):
            continue
    if vol_at_price.sum() == 0:
        return None, 50, "거래량 데이터 없음"
    poc_idx = int(np.argmax(vol_at_price))
    poc_price = (bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2
    curr = h['Close'].iloc[-1]
    if pd.isna(curr): return poc_price, 50, "현재가 없음"
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

    # 매매 타이밍 (장기추세 + 이격도, 보수적)
    long_trend = "상승" if curr > ma240 else "하락"
    if long_trend == "상승":
        if diverg < 3:
            timing = ("🟢 매수 타이밍", "pos", f"장기상승 추세 + MA240 매우 근접 (+{diverg:.1f}%) - 진입 적기")
        elif diverg < 10:
            timing = ("🟡 분할 매수 고려", "warn", f"장기상승 + 이격도 양호 (+{diverg:.1f}%)")
        elif diverg < 20:
            timing = ("🟠 관망", "warn", f"장기상승이지만 이격 확대 (+{diverg:.1f}%) - 신규 진입 자제")
        elif diverg < 30:
            timing = ("🔴 매도 준비", "neg", f"이격도 +{diverg:.1f}% 과열권 - 분할 매도 고려")
        else:
            timing = ("🔴 적극 매도", "neg", f"이격도 +{diverg:.1f}% 극단 과열 - 조정 임박")
    else:
        if diverg > -5:
            timing = ("🟠 관망", "warn", f"장기하락 추세 - 약세 유지")
        elif diverg > -20:
            timing = ("🔴 매도", "neg", f"장기하락 + 이격 ({diverg:.1f}%)")
        else:
            timing = ("🟡 반등 가능성 (역발상)", "warn", f"하락이격 {diverg:.1f}% 극단 - 보수적 분할 매수 고려")

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

    # 매수/매도 판단 (평균 + 승률 둘 다 고려, 보수적)
    if 5 in stats and 10 in stats:
        avg_10 = stats[10]["avg"]
        wr_10 = stats[10]["win_rate"]

        # 강한 매수: 승률 80%↑ + 평균 +5%↑ (엄격)
        if wr_10 >= 80 and avg_10 > 5:
            verdict = ("🟢 강한 매수 신호", "pos", f"10일 후 상승률 {wr_10:.0f}% · 평균 +{avg_10:.2f}%")
        elif wr_10 >= 70 and avg_10 > 2:
            verdict = ("🟡 매수 우위", "pos", f"10일 후 상승률 {wr_10:.0f}% · 평균 +{avg_10:.2f}%")
        # 매도: 승률 25%↓ or 평균 -3%↓
        elif wr_10 <= 25 or (wr_10 <= 40 and avg_10 < -3):
            verdict = ("🔴 매도 우위", "neg", f"10일 후 상승률 {wr_10:.0f}% · 평균 {avg_10:+.2f}%")
        # 평균과 승률 방향 다름
        elif (avg_10 > 0 and wr_10 < 50) or (avg_10 < 0 and wr_10 > 50):
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


@st.cache_data(ttl=60*60*24, show_spinner=False)  # 하루 1회
def get_market_breadth():
    """S&P500 상위 종목 중 200일선 위 비율 (Rate Limit 완화 위해 25개만)"""
    try:
        sample = SP500_TOP100[:25]
        above = 0; total = 0
        for tk in sample:
            h, _ = yf_history_safe(tk, period="1y", retries=2)
            if h is not None and len(h) >= 200:
                ma200 = h['Close'].rolling(200).mean().iloc[-1]
                if h['Close'].iloc[-1] > ma200: above += 1
                total += 1
        if total < 10: return None
        return {"above_pct": above / total * 100, "sample": total}
    except Exception:
        return None


@st.cache_data(ttl=600)
def get_index_trend(ticker):
    """지수 추세 - 200일선 대비, 1M 변화"""
    try:
        h, _ = yf_history_safe(ticker, period="1y", retries=2)
        if h is None or len(h) < 200: return None
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


def match_historical_scenarios(market_score, inf_score, rec_score, stag_met):
    """현재 상태와 가장 유사한 과거 시나리오 TOP 3
    각 시나리오에는 5가지 비교 데이터 포함:
    1) 금리 환경 (시작점, 속도)
    2) 주도 섹터 펀더멘털 (실적 vs 기대)
    3) 고용/GDP (실물경기)
    4) 유동성/QT (Fed 대차대조표)
    5) 신용 스프레드 (HY)
    """
    scenarios = [
        {
            "name": "1929 대공황 직전",
            "year": "1929.09",
            "market": 85, "inf": 60, "rec": 50, "stag": 1,
            "phase": "최고점 직전 (마지막 환호)",
            "what_happened": "1929.10 검은 화요일 → S&P -86% (3년간) → 대공황",
            "current_stage": "초기 단계 가능성",
            "risk": "neg",
            "compare": {
                "rates": ("Fed금리 6% (긴축 중)", "낮은 절대수준이지만 신용 경색 시작"),
                "earnings": ("철도/제조업 거품 - 실적 없이 주가만 상승", "당시는 펀더멘털 부재, 100% 기대감"),
                "macro": ("실업률 3.2% 완전고용, 산업생산 정점", "겉으로는 호황, 내부 부채 폭증"),
                "liquidity": ("Fed 긴축 + 은행 대출 회수", "유동성 급격 위축 = 직접적 폭락 트리거"),
                "credit": ("회사채 스프레드 급등 시작", "신용시장 균열 = 위기 신호")
            }
        },
        {
            "name": "1973-74 1차 오일쇼크",
            "year": "1973.01",
            "market": 65, "inf": 80, "rec": 55, "stag": 3,
            "phase": "스태그플레이션 초입",
            "what_happened": "S&P -48% (1974까지 21개월간), 인플레 12% 폭주",
            "current_stage": "초기~중기",
            "risk": "neg",
            "compare": {
                "rates": ("Fed금리 5% → 13% 급등", "유가 충격 + 인플레로 강제 인상"),
                "earnings": ("Nifty Fifty 거품 붕괴 - 50배 PER", "고PER 빅테크와 유사한 멀티플 압축"),
                "macro": ("실업률 5% → 9%, GDP -2.5% 침체", "고용·성장 동시 악화 = 전형적 스태그"),
                "liquidity": ("Fed 긴축 + 원유 공급 충격", "유가 4배 폭등이 결정타"),
                "credit": ("HY 스프레드 8%+ (위기급)", "기업 부도 급증")
            }
        },
        {
            "name": "1980 볼커 쇼크",
            "year": "1980.03",
            "market": 50, "inf": 90, "rec": 70, "stag": 4,
            "phase": "Fed 극단 긴축",
            "what_happened": "Fed 금리 20% 인상 → 침체 → 인플레 잡음 → 1982 반등",
            "current_stage": "현재와 유사도 낮음",
            "risk": "neg",
            "compare": {
                "rates": ("Fed금리 10% → 20% 인상 (역대 최고)", "볼커의 극단 긴축, 인플레 강제 진압"),
                "earnings": ("기업이익 침체로 -20%", "전 섹터 동반 악화"),
                "macro": ("실업률 10.8%, GDP -2.2% 침체", "1930년대 이후 최악"),
                "liquidity": ("Fed 극단 긴축, M2 급감", "통화량 인위적 축소"),
                "credit": ("HY 스프레드 10%+ 폭등", "기업 줄도산")
            }
        },
        {
            "name": "1987 블랙 먼데이",
            "year": "1987.08",
            "market": 90, "inf": 45, "rec": 30, "stag": 0,
            "phase": "고점 직전",
            "what_happened": "1987.10.19 하루 -22% 폭락. 다만 1년 내 회복",
            "current_stage": "단기 조정 가능",
            "risk": "warn",
            "compare": {
                "rates": ("Fed금리 6% → 7.25%", "급격하진 않으나 인상 추세"),
                "earnings": ("실적 양호, 그러나 PER 22배 과열", "기대감으로 가격만 폭등"),
                "macro": ("실업률 5.7% 정상, GDP 3.5%", "경제는 멀쩡함"),
                "liquidity": ("달러 약세 + 금리 인상 충돌", "정책 혼선이 매도 폭탄 촉발"),
                "credit": ("프로그램 매매 + LBO 거품", "기술적 요인의 폭락")
            }
        },
        {
            "name": "1989-90 후기사이클",
            "year": "1989.06",
            "market": 70, "inf": 65, "rec": 45, "stag": 2,
            "phase": "후기 사이클",
            "what_happened": "Fed 긴축 → 1990 침체 → S&P -20%",
            "current_stage": "중기 단계",
            "risk": "neg",
            "compare": {
                "rates": ("Fed금리 9.75% (긴축 정점)", "고금리 부담 누적"),
                "earnings": ("S&L 위기 + 부동산 거품", "금융 섹터 부실"),
                "macro": ("실업률 5.3% → 7.8% 상승", "고용 점진 악화"),
                "liquidity": ("Fed 긴축 + 일본 자금 회수", "글로벌 유동성 위축"),
                "credit": ("HY 스프레드 7%+ 확대", "정크본드 시장 붕괴")
            }
        },
        {
            "name": "2000 닷컴버블 정점",
            "year": "2000.03",
            "market": 88, "inf": 50, "rec": 35, "stag": 0,
            "phase": "버블 최고점",
            "what_happened": "나스닥 -78% (2002까지 30개월), S&P -49%",
            "current_stage": "AI 버블 의심시 유사",
            "risk": "neg",
            "compare": {
                "rates": ("Fed금리 5% → 6.5% 인상", "닷컴 거품 잡으려 긴축"),
                "earnings": ("닷컴 기업 적자 PSR 100배+", "수익 없이 가격만 - 빅테크와 다른 점"),
                "macro": ("실업률 4% 완전고용, GDP 4%", "실물은 멀쩡, 자산만 거품"),
                "liquidity": ("Y2K 풀린 유동성 회수", "Fed가 의도적으로 거품 잡음"),
                "credit": ("기술주 PSR 평균 30배", "검증 안 된 비즈니스 모델")
            }
        },
        {
            "name": "2007 GFC 직전",
            "year": "2007.07",
            "market": 72, "inf": 55, "rec": 50, "stag": 1,
            "phase": "후기사이클 + 신용리스크",
            "what_happened": "2008 GFC → S&P -57%, 글로벌 금융위기",
            "current_stage": "초기~중기 가능성",
            "risk": "neg",
            "compare": {
                "rates": ("Fed금리 4.25% → 5.25%", "주택 거품 잡으려 인상"),
                "earnings": ("금융주 부실 자산 폭증", "표면 실적은 좋았으나 내부 균열"),
                "macro": ("실업률 4.7% 정상, GDP 2.5%", "갑작스러운 신용 경색이 결정타"),
                "liquidity": ("MBS/CDO 시장 동결", "그림자 금융 시스템 붕괴"),
                "credit": ("서브프라임 디폴트 급증", "신용 위기 전염")
            }
        },
        {
            "name": "2018 4분기 조정",
            "year": "2018.10",
            "market": 65, "inf": 55, "rec": 30, "stag": 0,
            "phase": "Fed 긴축 우려",
            "what_happened": "2018.Q4 S&P -20% → Fed 인하 → 2019 회복",
            "current_stage": "현재와 가장 유사 가능",
            "risk": "warn",
            "compare": {
                "rates": ("Fed금리 2% → 2.5% (4회 인상)", "점진적 인상이었으나 시장 반발"),
                "earnings": ("기술주 PER 28배, 미중 무역갈등", "실적 우려 + 매크로 불확실성"),
                "macro": ("실업률 3.7% 완전고용, GDP 3%", "경제는 양호, 정책 우려가 주범"),
                "liquidity": ("Fed QT 가속 + 금리 인상 병행", "양쪽 동시 긴축이 충격"),
                "credit": ("HY 스프레드 4%대", "신용은 양호했음")
            }
        },
        {
            "name": "2022 인플레 충격",
            "year": "2022.01",
            "market": 55, "inf": 95, "rec": 40, "stag": 2,
            "phase": "긴축 시작",
            "what_happened": "S&P -25%, Fed 0→4.5% 인상, 2023 회복",
            "current_stage": "인플레 재상승 시 유사",
            "risk": "neg",
            "compare": {
                "rates": ("Fed금리 0% → 4.5% 사상 최속 인상", "제로금리에서 출발한 충격파 = 현재와 다른 환경"),
                "earnings": ("기술주 PER 30배+, 기대감 거품", "실적 없는 SPAC/밈주식 폭락"),
                "macro": ("실업률 3.5% → 3.7%, GDP -1.6% (Q1)", "기술적 침체 진입"),
                "liquidity": ("QT 시작 + 금리 인상 동시", "역대급 유동성 회수"),
                "credit": ("HY 스프레드 5% → 8%", "기업 부담 가중")
            }
        },
        {
            "name": "1995 보험성 인하 (성공)",
            "year": "1995.07",
            "market": 75, "inf": 30, "rec": 35, "stag": 0,
            "phase": "선제적 완화",
            "what_happened": "Fed 미리 인하 → 5년 강세장 (S&P 2배+)",
            "current_stage": "디스인플레+침체우려시 유사",
            "risk": "pos",
            "compare": {
                "rates": ("Fed금리 6% → 5.25% 인하", "선제적 0.75%p 완화"),
                "earnings": ("기술혁명 초기 (인터넷)", "실적 견조 + 신산업 기대"),
                "macro": ("실업률 5.5%, GDP 2.5%", "안정적 성장세 유지"),
                "liquidity": ("Fed 완화 시작 + 자본 유입", "환경 우호적"),
                "credit": ("HY 스프레드 3%대 안정", "신용시장 정상")
            }
        },
        {
            "name": "2019 보험성 인하 (성공)",
            "year": "2019.07",
            "market": 72, "inf": 35, "rec": 40, "stag": 0,
            "phase": "선제적 완화",
            "what_happened": "Fed 3차례 인하 → 시장 강세 → 코로나로 중단",
            "current_stage": "디스인플레+성장둔화시 유사",
            "risk": "pos",
            "compare": {
                "rates": ("Fed금리 2.5% → 1.75%", "예방적 0.75%p 인하"),
                "earnings": ("빅테크 견조한 실적", "구조적 성장 동력 유지"),
                "macro": ("실업률 3.7% 완전고용, GDP 2.3%", "양호한 실물경제"),
                "liquidity": ("Repo 위기 대응 + QT 중단", "Fed 적극 개입"),
                "credit": ("HY 스프레드 3.5%대", "신용 양호")
            }
        },
    ]

    matches = []
    for s in scenarios:
        diff_market = abs(s["market"] - market_score)
        diff_inf = abs(s["inf"] - inf_score)
        diff_rec = abs(s["rec"] - rec_score)
        diff_stag = abs(s["stag"] - stag_met) * 10
        total_diff = diff_market + diff_inf * 1.2 + diff_rec * 1.2 + diff_stag
        similarity = max(0, 100 - total_diff / 4)
        s_copy = dict(s)
        s_copy["similarity"] = similarity
        matches.append(s_copy)

    matches.sort(key=lambda x: x["similarity"], reverse=True)
    return matches[:3]


def get_current_macro_snapshot(macro):
    """현재 5가지 매크로 상태 텍스트"""
    cpi = macro.get("cpi_yoy_v", (None, None))[0]
    unemploy = macro.get("unemploy", (None, None))[0]
    gdp = macro.get("gdp", (None, None))[0]
    us10y = macro.get("us10y_yf", (None, None))[0] or macro.get("us10y", (None, None))[0]
    hy = macro.get("hy_spread", (None, None))[0]
    fed_assets = macro.get("fed_assets", (None, None))
    vix = macro.get("vix", (None, None))[0]

    # 1. 금리 환경
    rates_str = f"美10Y {us10y:.2f}%" if us10y else "데이터 없음"
    rates_desc = "현재 시장은 이미 고금리 환경에 적응 단계. 추가 변화가 충격 요소"

    # 2. 주도 섹터 펀더멘털 (S&P 추세로 판단)
    earnings_str = "AI 인프라/빅테크 주도"
    earnings_desc = "실제 실적과 현금흐름 동반 (단순 기대감 거품과 차이)"

    # 3. 고용 + GDP
    macro_str = ""
    if unemploy: macro_str += f"실업률 {unemploy:.1f}%"
    if gdp: macro_str += f" · GDP {gdp:.1f}%"
    macro_desc = "고용/성장 동반 양호 = 수요 견인 인플레 (스태그 아님)"
    if unemploy and unemploy > 4.5:
        macro_desc = "고용 둔화 시작 - 약한 신호"
    if gdp and gdp < 1.0:
        macro_desc = "성장 둔화 진행 중 - 침체 우려"

    # 4. 유동성
    liq_str = ""
    if fed_assets[0]:
        liq_str = f"Fed자산 {fed_assets[0]/1000:.2f}T"
        if fed_assets[1]:
            chg = fed_assets[0] - fed_assets[1]
            liq_str += f" ({'+'if chg>0 else ''}{chg:.0f}B)"
    liq_desc = "Fed QT 점진적 축소 중. 시장이 적응 중"

    # 5. 신용
    credit_str = f"HY 스프레드 {hy:.2f}%" if hy else "데이터 없음"
    if hy:
        if hy < 3.5: credit_desc = "신용시장 매우 안정 - 위기 신호 없음"
        elif hy < 5: credit_desc = "신용시장 정상 범위"
        elif hy < 7: credit_desc = "신용 경계 - 모니터링 필요"
        else: credit_desc = "신용 위기 신호"
    else:
        credit_desc = ""

    return {
        "rates": (rates_str, rates_desc),
        "earnings": (earnings_str, earnings_desc),
        "macro": (macro_str, macro_desc),
        "liquidity": (liq_str, liq_desc),
        "credit": (credit_str, credit_desc),
    }


@st.cache_data(ttl=60*60*24*7, show_spinner=False)
def get_crash_signals(macro):
    """5대 폭락 신호 지표"""
    signals = []

    # 1. 美 30Y 국채 금리 (Bond Vigilante)
    try:
        h, _ = yf_history_safe("^TYX", period="1mo", retries=2)
        if h is not None and not h.empty:
            tyx = float(h['Close'].iloc[-1])
            tyx_w = float(h['Close'].iloc[-5]) if len(h) >= 5 else tyx
            chg = tyx - tyx_w
            if tyx >= 5.3:
                status, cls = "🔴 위험 - 폭락 임박", "neg"
                msg = f"30Y {tyx:.2f}% - 5.3% 돌파, 채권 본격 매도 신호"
            elif tyx >= 5.0:
                status, cls = "🟠 경계", "warn"
                msg = f"30Y {tyx:.2f}% - 5% 돌파, 위험 수준 진입"
            elif tyx >= 4.5:
                status, cls = "🟡 주의", "warn"
                msg = f"30Y {tyx:.2f}% - 상승 추세 (+{chg:.2f}%p 주간)"
            else:
                status, cls = "🟢 안정", "pos"
                msg = f"30Y {tyx:.2f}% - 정상권"
            signals.append({"name": "美 30년물 국채금리",
                            "value": f"{tyx:.2f}%", "status": status, "cls": cls, "msg": msg,
                            "desc": "장기금리 사상최고 = 글로벌 빚폭탄 위험 신호"})
    except Exception:
        pass

    # 2. VIX (변동성)
    vix = macro.get("vix", (None, None))[0]
    if vix:
        if vix >= 30:
            status, cls = "🔴 공포 극단", "neg"
            msg = f"VIX {vix:.1f} - 폭락 진행 중 신호"
        elif vix >= 25:
            status, cls = "🟠 변동성 확대", "warn"
            msg = f"VIX {vix:.1f} - 매도 압력 증가"
        elif vix >= 20:
            status, cls = "🟡 경계", "warn"
            msg = f"VIX {vix:.1f} - 변동성 상승 중"
        else:
            status, cls = "🟢 평온", "pos"
            msg = f"VIX {vix:.1f} - 시장 평온 (그러나 '가짜 안전'일 수 있음)"
        signals.append({"name": "VIX 변동성 지수",
                        "value": f"{vix:.1f}", "status": status, "cls": cls, "msg": msg,
                        "desc": "S&P 5% 하락시 강제매도 1870억$ 대기 중"})

    # 3. 금융주(XLF) vs 기술주(QQQ) 상대 흐름
    try:
        xlf, _ = yf_history_safe("XLF", period="3mo", retries=2)
        qqq, _ = yf_history_safe("QQQ", period="3mo", retries=2)
        if xlf is not None and qqq is not None and not xlf.empty and not qqq.empty:
            xlf_chg = (float(xlf['Close'].iloc[-1]) - float(xlf['Close'].iloc[0])) / float(xlf['Close'].iloc[0]) * 100
            qqq_chg = (float(qqq['Close'].iloc[-1]) - float(qqq['Close'].iloc[0])) / float(qqq['Close'].iloc[0]) * 100
            spread = xlf_chg - qqq_chg
            if spread <= -20:
                status, cls = "🔴 GFC급 위험", "neg"
                msg = f"XLF-QQQ {spread:+.1f}%p - 2008년 금융위기급 외면"
            elif spread <= -10:
                status, cls = "🟠 은행 약세", "warn"
                msg = f"XLF-QQQ {spread:+.1f}%p - 은행주 외면, 신용 리스크"
            elif spread <= -5:
                status, cls = "🟡 약한 신호", "warn"
                msg = f"XLF-QQQ {spread:+.1f}%p - 자금이 테크로만 쏠림"
            else:
                status, cls = "🟢 균형", "pos"
                msg = f"XLF-QQQ {spread:+.1f}%p - 정상 범위"
            signals.append({"name": "은행주 vs 기술주 (3M)",
                            "value": f"{spread:+.1f}%p", "status": status, "cls": cls, "msg": msg,
                            "desc": "은행주 -25% 깨지면 GFC급 신용 위기 신호"})
    except Exception:
        pass

    # 4. Fed 금리 인상 확률 (간접)
    # 직접 API 없으니까 인플레+성장 점수로 추정
    cpi = macro.get("cpi_yoy_v", (None, None))[0]
    if cpi:
        if cpi >= 4:
            hike_prob = 70
            status, cls = "🔴 인상 임박", "neg"
            msg = f"CPI {cpi:.1f}% - Fed 추가 긴축 확률 高"
        elif cpi >= 3.5:
            hike_prob = 50
            status, cls = "🟠 인상 가능성", "warn"
            msg = f"CPI {cpi:.1f}% - Fed 매파적 전환 가능"
        elif cpi >= 3:
            hike_prob = 30
            status, cls = "🟡 동결 무게", "warn"
            msg = f"CPI {cpi:.1f}% - 인하 시기 늦어질 가능"
        else:
            hike_prob = 10
            status, cls = "🟢 인하 환경", "pos"
            msg = f"CPI {cpi:.1f}% - 인하 여력 충분"
        signals.append({"name": "Fed 추가 인상 확률 (추정)",
                        "value": f"{hike_prob}%", "status": status, "cls": cls, "msg": msg,
                        "desc": "인상 확정시 본격 폭락 진입 위험"})

    # 5. 시장 폭 (Breadth) - 가짜 강세 신호
    breadth = get_market_breadth()
    if breadth:
        bp = breadth["above_pct"]
        if bp < 30:
            status, cls = "🔴 가짜 강세", "neg"
            msg = f"{bp:.0f}% - 소수 빅테크만 강세, 시장 내부 붕괴"
        elif bp < 40:
            status, cls = "🟠 시장 폭 좁음", "warn"
            msg = f"{bp:.0f}% - 시장 강세가 광범위하지 않음"
        elif bp < 50:
            status, cls = "🟡 보통", "warn"
            msg = f"{bp:.0f}% - 시장 폭 보통 수준"
        else:
            status, cls = "🟢 강세 광범위", "pos"
            msg = f"{bp:.0f}% - 다수 종목 강세, 건강한 시장"
        signals.append({"name": "시장 폭 (S&P 50개 中)",
                        "value": f"{bp:.0f}%", "status": status, "cls": cls, "msg": msg,
                        "desc": "40년만의 가짜안전지표 - 지수만 오르고 내부 망가질 때 위험"})

    return signals


def fed_scenarios(market_score, inf_score, rec_score):
    """현재 상황에서 Fed 금리 정책에 따른 결과 해석"""
    # 인플레/침체 정도로 시나리오 우선순위 결정
    high_inf = inf_score >= 60
    low_inf = inf_score <= 35
    high_rec = rec_score >= 55
    low_rec = rec_score <= 35

    # 인상 시나리오
    if high_inf and not high_rec:
        # 인플레 高 + 경기 안정 = 후기 사이클
        hike = ("🔴 침체 가속화 가능성 高",
                "Fed 긴축으로 결국 경기 둔화 → 6~18개월 후 침체 진입 가능. 1989·2000·2007년 패턴. 시장은 단기 조정 → 중기 약세 전환 가능.")
        cut = ("🟡 인플레 재점화 위험",
               "물가가 아직 높은데 금리 인하시 1970년대처럼 인플레 재폭발 가능. 단기 시장 환호 후 중기 부담.")
        hold = ("🟢 가장 안전한 선택",
                "현재 정책 유지로 인플레 자연 둔화 + 경기 연착륙 시도. 다만 시장은 횡보·약세 가능.")
    elif high_inf and high_rec:
        # 스태그플레이션
        hike = ("🔴 침체 확정",
                "이미 침체 신호 있는데 추가 긴축 = 1980년 볼커 쇼크 재현. 주식·채권·부동산 동반 폭락 위험.")
        cut = ("🟠 스태그플레이션 고착",
               "물가↑ 상태에서 금리 인하 = 1970년대 재현. 인플레는 더 끈적해지고 경기 회복도 더딤.")
        hold = ("🟡 최악은 면함",
                "정책 유지로 시간 벌기. 그러나 양쪽 다 악화 가능성 있어 방어 자산 필수.")
    elif low_inf and high_rec:
        # 디스인플레 + 침체 임박 = 가장 명확한 인하 환경
        hike = ("🔴 침체 확정 + 디플레",
                "물가 낮은데 추가 긴축 = 2008년 이전 일본형 장기 침체. 절대 피해야 할 선택.")
        cut = ("🟢 가장 합리적 선택",
               "Fed 적극 완화로 경기 회복 시도. 2009·2020년 패턴. 6~12개월 후 강한 반등 종종 발생.")
        hold = ("🟠 침체 심화 위험",
                "Fed 늦으면 침체 깊어짐. 시장은 인하 기대로 일시 반등할 수 있으나 실제 인하 없으면 실망.")
    elif low_inf and not high_rec:
        # 골디락스
        hike = ("🟠 호재 종료",
                "잘 가고 있는데 굳이 긴축 = 시장 실망. 2018년 4분기 패턴. 일시 조정 후 회복.")
        cut = ("🟢 보험성 인하 (Goldilocks 강화)",
               "1995·2019년 패턴. 미리 완화로 침체 예방. 위험자산 강세 장기화 가능.")
        hold = ("🟢 현재 환경 유지",
                "특별한 액션 없이도 좋은 환경. 시장 안정적 상승 지속 가능.")
    else:
        # 중립 구간
        hike = ("🟠 시장 부담",
                "물가 잡혀가는데 추가 긴축은 과잉. 시장 단기 조정 가능.")
        cut = ("🟡 시기상조 가능",
               "확실한 디스인플레/침체 신호 없이 인하시 부작용 우려.")
        hold = ("🟢 안정적",
                "현재 데이터로는 정책 유지가 합리적.")

    return {"hike": hike, "cut": cut, "hold": hold}


def combined_diagnosis(market_score, inf_score, rec_score):
    """시장 상황 + 인플레 + 침체 조합 → 과거 사례 기반 진단"""
    # 시장 강도
    if market_score >= 70: mkt_state = "강세"
    elif market_score >= 55: mkt_state = "중립우호"
    elif market_score >= 40: mkt_state = "혼조"
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
        if vix < 14: positives.append("VIX 매우 안정"); weighted_score += 6
        elif vix < 17: positives.append("VIX 안정"); weighted_score += 3
        elif vix > 30: negatives.append("VIX 극단 (공포)"); weighted_score -= 12
        elif vix > 25: negatives.append("VIX 변동성 확대"); weighted_score -= 8
        elif vix > 20: negatives.append("VIX 경계"); weighted_score -= 5
        elif vix > 18: negatives.append("VIX 상승"); weighted_score -= 2
        # VIX 백워데이션 (단기>장기) = 즉각 위험
        vix9d = macro.get("vix9d", (None, None))[0]
        vix3m = macro.get("vix3m", (None, None))[0]
        if vix9d and vix3m:
            if vix9d > vix3m:
                negatives.append("VIX 백워데이션 - 시장 균열"); weighted_score -= 10
        # SKEW 블랙스완 (가중치 ↑)
        skew = macro.get("skew", (None, None))[0]
        if skew:
            if skew > 150: negatives.append(f"SKEW {skew:.0f} - 블랙스완 경계"); weighted_score -= 8
            elif skew > 145: negatives.append(f"SKEW {skew:.0f} - 꼬리위험 헤지↑"); weighted_score -= 5
            elif skew > 140: negatives.append(f"SKEW {skew:.0f} - 헤지 증가"); weighted_score -= 3
        # VVIX
        vvix = macro.get("vvix", (None, None))[0]
        if vvix:
            if vvix > 110: negatives.append(f"VVIX {vvix:.0f} - 옵션시장 불안"); weighted_score -= 4
            elif vvix > 100: negatives.append(f"VVIX {vvix:.0f} - 변동성↑"); weighted_score -= 2
        # OVX (유가변동성 → 인플레 충격 신호)
        ovx = macro.get("ovx", (None, None))[0]
        if ovx:
            if ovx > 50: negatives.append(f"OVX {ovx:.0f} - 유가 충격 위험"); weighted_score -= 5
            elif ovx > 40: negatives.append(f"OVX {ovx:.0f} - 유가 불안"); weighted_score -= 2
        # SPY PCR (옵션 심리)
        spy_pcr = macro.get("spy_pcr")
        if spy_pcr:
            if spy_pcr > 1.3: negatives.append(f"SPY PCR {spy_pcr:.2f} - 폭락 헤지 급증"); weighted_score -= 5
            elif spy_pcr > 1.0: negatives.append(f"SPY PCR {spy_pcr:.2f} - 방어 심리"); weighted_score -= 2
            elif spy_pcr < 0.7: positives.append(f"SPY PCR {spy_pcr:.2f} - 콜 우세"); weighted_score += 3

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
    # 4-1. 실질금리 (TIPS)
    rr = macro.get("real_rate", (None, None))[0]
    if rr:
        if rr > 2.5: negatives.append(f"실질금리 {rr:.2f}% - 밸류 부담"); weighted_score -= 6
        elif rr < 1: positives.append(f"실질금리 {rr:.2f}% - 우호"); weighted_score += 3

    # 5. 하이일드 스프레드 (신용 리스크) - 임계값 강화
    hy = macro.get("hy_spread", (None, None))[0]
    if hy:
        if hy < 2.8: positives.append(f"HY {hy:.2f}% - 신용 매우안정"); weighted_score += 4
        elif hy < 3.5: positives.append(f"HY {hy:.2f}% - 신용안정"); weighted_score += 2
        elif hy > 6: negatives.append(f"HY {hy:.2f}% - 신용경색"); weighted_score -= 10
        elif hy > 5: negatives.append(f"HY {hy:.2f}% - 스프레드 확대"); weighted_score -= 6
        elif hy > 4: negatives.append(f"HY {hy:.2f}% - 경계"); weighted_score -= 3

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

    if score >= 75: verdict, vcls = "위험자산 우호", "pos"
    elif score >= 60: verdict, vcls = "중립적 우호", "pos"
    elif score >= 50: verdict, vcls = "혼조", "warn"
    elif score >= 35: verdict, vcls = "방어적", "neg"
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

# ===== 오늘의 투자 명언 (날짜별 고정) =====
QUOTES = [
    ("시장은 인내심 없는 사람의 돈을 인내심 있는 사람에게 옮기는 도구다", "워런 버핏"),
    ("남들이 욕심낼 때 두려워하고, 남들이 두려워할 때 욕심내라", "워런 버핏"),
    ("10년간 보유할 주식이 아니라면 10분도 보유하지 마라", "워런 버핏"),
    ("위험은 자신이 무엇을 하는지 모르는 데서 온다", "워런 버핏"),
    ("주식 시장에서 가장 위험한 말은 '이번엔 다르다'이다", "존 템플턴"),
    ("강세장은 비관 속에서 태어나, 회의 속에서 자라며, 낙관 속에서 성숙하고, 행복 속에서 죽는다", "존 템플턴"),
    ("싸게 사는 것이 가장 확실한 수익의 원천이다", "벤저민 그레이엄"),
    ("투자자의 가장 큰 적은 바로 자기 자신이다", "벤저민 그레이엄"),
    ("가격은 당신이 지불하는 것이고, 가치는 당신이 얻는 것이다", "벤저민 그레이엄"),
    ("손실을 자르고 이익은 달리게 하라", "제시 리버모어"),
    ("시장은 항상 옳다. 시장과 싸우지 마라", "제시 리버모어"),
    ("기다림이 돈을 벌게 한다. 생각이 아니라", "제시 리버모어"),
    ("계란을 한 바구니에 담지 마라", "투자 격언"),
    ("떨어지는 칼날을 잡지 마라", "월가 격언"),
    ("소문에 사서 뉴스에 팔아라", "월가 격언"),
    ("나무는 하늘까지 자라지 않는다", "월가 격언"),
    ("공포에 사고 환희에 팔아라", "월가 격언"),
    ("당신이 잠든 사이에도 돈이 일하게 하라", "월가 격언"),
    ("시간이 시장을 이긴다. 타이밍을 맞추려 하지 마라", "피터 린치"),
    ("당신이 이해하지 못하는 것에 투자하지 마라", "피터 린치"),
    ("주식 시장의 조정에서 잃은 돈보다, 조정을 예상하다 잃은 돈이 더 많다", "피터 린치"),
    ("좋은 회사를 합리적인 가격에 사는 것이, 그저 그런 회사를 싸게 사는 것보다 낫다", "워런 버핏"),
    ("분산투자는 무지에 대한 방어책이다", "워런 버핏"),
    ("손실 후엔 쉬어라. 복수하려는 매매가 계좌를 비운다", "트레이딩 격언"),
    ("계획대로 매매하고, 매매한 대로 따르라", "트레이딩 격언"),
    ("시장에 늘 머물 필요는 없다. 현금도 포지션이다", "트레이딩 격언"),
    ("한 번의 큰 손실이 열 번의 작은 이익을 지운다", "리스크 관리 격언"),
    ("욕심은 차트를 왜곡시킨다", "트레이딩 격언"),
    ("최고의 매매는 때로 아무것도 하지 않는 것이다", "트레이딩 격언"),
    ("물타기는 전략이 아니라 희망이다", "리스크 관리 격언"),
]
# 날짜 기반 고정 인덱스
_day_seed = int(datetime.now().strftime("%Y%m%d"))
_q = QUOTES[_day_seed % len(QUOTES)]
st.markdown(f"""<div style='background:linear-gradient(135deg, #0f1117, #0a0c12); border:1px solid #1c1f26; border-left:3px solid #fbbf24; border-radius:10px; padding:16px 22px; margin-bottom:24px;'>
<div style='font-size:10px; color:#6b7280; letter-spacing:0.15em; font-weight:600; margin-bottom:6px;'>💬 오늘의 한 마디</div>
<div style='font-size:15px; color:#e5e7eb; font-style:italic; line-height:1.5;'>"{_q[0]}"</div>
<div style='font-size:12px; color:#9ca3af; margin-top:6px; text-align:right;'>— {_q[1]}</div>
</div>""", unsafe_allow_html=True)

import json
import os as _os

# === 검색 기록 (1주일 자동 삭제) ===
HISTORY_FILE = "search_history.json"

def load_history():
    try:
        if _os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r") as f:
                data = json.load(f)
            # 1주일 지난 거 삭제
            now = datetime.now().timestamp()
            week = 7 * 24 * 3600
            data = {tk: ts for tk, ts in data.items() if now - ts < week}
            return data
    except Exception: pass
    return {}

def save_history(tk):
    try:
        data = load_history()
        data[tk] = datetime.now().timestamp()
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f)
    except Exception: pass

history = load_history()
# 최근 검색순 정렬
history_sorted = sorted(history.items(), key=lambda x: x[1], reverse=True)

with st.form("f"):
    c1, c2 = st.columns([5, 1])
    with c1:
        ticker = st.text_input("티커 입력 (미국: TSLA, NVDA · 한국: 005930.KS, 035420.KS)",
                                value=history_sorted[0][0] if history_sorted else "TSLA",
                                label_visibility="collapsed").upper().strip()
    with c2:
        go_btn = st.form_submit_button("분석 실행")

# 최근 검색 버튼 (있을 때만)
if history_sorted:
    st.markdown("<div style='font-size:11px; color:#6b7280; font-weight:600; margin:8px 0 6px 0; letter-spacing:0.05em;'>🕐 최근 검색 · 1주일 보관</div>", unsafe_allow_html=True)
    hist_cols = st.columns(min(len(history_sorted), 8))
    for i, (tk, ts) in enumerate(history_sorted[:8]):
        days_ago = (datetime.now().timestamp() - ts) / 86400
        if days_ago < 1: time_label = "오늘"
        elif days_ago < 2: time_label = "어제"
        else: time_label = f"{int(days_ago)}일 전"
        with hist_cols[i]:
            if st.button(f"{tk}\n{time_label}", key=f"hist_{tk}", use_container_width=True):
                ticker = tk
                save_history(tk)
                st.rerun()

if not ticker:
    st.stop()

# 분석 버튼 누른 경우 기록 저장
if go_btn:
    save_history(ticker)

is_kr = ticker.endswith(".KS") or ticker.endswith(".KQ")
ccy = "₩" if is_kr else "$"

def integrate_stock_signals(rec, target, patterns, hist, ma_analysis, accu_avg, similar):
    """종목 모든 분석 통합
    AI 종합 의견(rec.score)과 일치하는 5단계 판정 + 6개 지표 투표 참고
    """
    curr = float(hist['Close'].iloc[-1])
    votes = {"매수": 0, "관망": 0, "매도": 0}
    details = []

    # 1. AI 종합 점수
    if rec["score"] >= 65:
        votes["매수"] += 1
        details.append(("AI 종합점수", f"{rec['score']:.0f}/100", "매수", "pos"))
    elif rec["score"] >= 45:
        votes["관망"] += 1
        details.append(("AI 종합점수", f"{rec['score']:.0f}/100", "관망", "warn"))
    else:
        votes["매도"] += 1
        details.append(("AI 종합점수", f"{rec['score']:.0f}/100", "매도", "neg"))

    # 2. 차트패턴 (임계값 완화 - score 20)
    if patterns and patterns[0]["score"] > 20:
        p = patterns[0]
        sig = p.get("signal", "중립")
        if sig == "강세":
            votes["매수"] += 1
            details.append(("차트패턴", p["name"], "매수", "pos"))
        elif sig == "약세":
            votes["매도"] += 1
            details.append(("차트패턴", p["name"], "매도", "neg"))
        else:
            votes["관망"] += 1
            details.append(("차트패턴", p["name"], "관망", "warn"))
    else:
        votes["관망"] += 1
        details.append(("차트패턴", "박스권", "관망", "warn"))

    # 3. 이평선 - timing + arrangement 같이 봄
    if ma_analysis:
        timing_name = ma_analysis.get("timing", ("관망", "warn", ""))[0]
        arr_name = ma_analysis.get("arrangement", ("", "", ""))[0]
        if "매수" in timing_name and "준비" not in timing_name:
            votes["매수"] += 1
            details.append(("이평선 타이밍", timing_name, "매수", "pos"))
        elif "매도" in timing_name or "역배열" in arr_name:
            votes["매도"] += 1
            details.append(("이평선 타이밍", timing_name or arr_name, "매도", "neg"))
        else:
            votes["관망"] += 1
            details.append(("이평선 타이밍", timing_name, "관망", "warn"))
    else:
        details.append(("이평선 타이밍", "데이터 부족", "관망", "warn"))

    # 4. 세력 매집 (임계값 완화)
    if accu_avg >= 55:
        votes["매수"] += 1
        details.append(("세력 매집", f"종합 {accu_avg:.0f}점", "매수", "pos"))
    elif accu_avg <= 45:
        votes["매도"] += 1
        details.append(("세력 매집", f"종합 {accu_avg:.0f}점", "매도", "neg"))
    else:
        votes["관망"] += 1
        details.append(("세력 매집", f"종합 {accu_avg:.0f}점", "관망", "warn"))

    # 5. 유사패턴 (임계값 완화)
    if similar and 10 in similar.get("stats", {}):
        wr = similar["stats"][10]["win_rate"]
        avg = similar["stats"][10]["avg"]
        if wr >= 60 and avg > 1:
            votes["매수"] += 1
            details.append(("유사패턴 통계", f"승률 {wr:.0f}% · 평균 {avg:+.1f}%", "매수", "pos"))
        elif wr <= 40 or avg < -1:
            votes["매도"] += 1
            details.append(("유사패턴 통계", f"승률 {wr:.0f}% · 평균 {avg:+.1f}%", "매도", "neg"))
        else:
            votes["관망"] += 1
            details.append(("유사패턴 통계", f"승률 {wr:.0f}% · 평균 {avg:+.1f}%", "관망", "warn"))
    else:
        details.append(("유사패턴 통계", "데이터 부족", "관망", "warn"))

    # 6. AI 6개월 목표가
    upside = target["upside"]
    if upside > 8:
        votes["매수"] += 1
        details.append(("AI 6개월 목표가", f"{upside:+.1f}% 상승여력", "매수", "pos"))
    elif upside < -3:
        votes["매도"] += 1
        details.append(("AI 6개월 목표가", f"{upside:+.1f}% 하락전망", "매도", "neg"))
    else:
        votes["관망"] += 1
        details.append(("AI 6개월 목표가", f"{upside:+.1f}% 제한적", "관망", "warn"))

    total = sum(votes.values())
    buy_pct = votes["매수"] / total * 100
    hold_pct = votes["관망"] / total * 100
    sell_pct = votes["매도"] / total * 100

    # === 최종 결론: AI 종합 점수(rec.score)와 같은 5단계 + 투표 결과 보정 ===
    score = rec["score"]
    # 투표 결과를 점수에 ±소폭 반영 (강한 합의면 강화)
    if buy_pct >= 60: score += 5
    elif sell_pct >= 60: score -= 5
    elif sell_pct >= 40 and buy_pct < 30: score -= 3
    elif buy_pct >= 40 and sell_pct < 30: score += 3

    if score >= 75:
        verdict = ("🟢 적극 매수", "pos", f"6개 지표 중 {votes['매수']}개 매수 · 강한 합의")
    elif score >= 65:
        verdict = ("🟢 매수", "pos", f"매수 {votes['매수']}/관망 {votes['관망']}/매도 {votes['매도']}")
    elif score >= 45:
        verdict = ("🟡 중립 / 관망", "warn", f"매수 {votes['매수']}/관망 {votes['관망']}/매도 {votes['매도']}")
    elif score >= 35:
        verdict = ("🔴 매도", "neg", f"매수 {votes['매수']}/관망 {votes['관망']}/매도 {votes['매도']}")
    else:
        verdict = ("🔴 적극 매도", "neg", f"6개 지표 중 {votes['매도']}개 매도 · 강한 약세")

    return {
        "votes": votes, "details": details, "verdict": verdict,
        "buy_pct": buy_pct, "hold_pct": hold_pct, "sell_pct": sell_pct,
        "final_score": score,
    }


def topdown_analysis(macro, mkt, sectors, ticker, info, rec_score):
    """탑다운 4단계 자동 분석"""
    us10y = macro.get("us10y", (None, None))[0]
    rr = macro.get("real_rate", (None, None))[0]
    dxy = macro.get("dxy", (None, None))[0]
    fa = macro.get("fed_assets", (None, None))
    cpi = macro.get("cpi_yoy_v", (None, None))[0]

    # 1단계: 거시
    macro_signals = []
    if us10y and dxy:
        if us10y > 4.5 and dxy > 105:
            macro_signals.append(("고금리·강달러", "neg", "신흥국·원자재 불리, 美 빅테크 부담"))
        elif us10y < 3.5 and dxy < 100:
            macro_signals.append(("저금리·약달러", "pos", "신흥국·원자재·위험자산 우호"))
        elif dxy < 100:
            macro_signals.append(("약달러 환경", "pos", "신흥국·금·원자재 유리"))
        else:
            macro_signals.append(("중립 환경", "warn", "방향성 모호"))
    if mkt["score"] >= 65 and cpi and cpi > 3:
        cycle = ("후기 사이클 (Late Cycle)", "warn", "성장 정점 + 인플레 압력 - 에너지/원자재/금융 우위")
    elif mkt["score"] >= 65:
        cycle = ("확장 국면 (Expansion)", "pos", "성장주·기술주·소비재 우위")
    elif mkt["score"] >= 45:
        cycle = ("혼조 구간", "warn", "방어주·고배당주 검토")
    else:
        cycle = ("수축/침체 (Contraction)", "neg", "필수소비재·유틸리티·헬스케어·국채 우위")
    if fa[0] and fa[1]:
        if fa[0] > fa[1]: liq_dir = ("유동성 확장 중", "pos", "Fed 자산 증가 - 위험자산 우호")
        else: liq_dir = ("유동성 축소 (QT)", "neg", "Fed 자산 감소 - 점진적 부담")
    else:
        liq_dir = ("데이터 부족", "warn", "")
    if rr:
        if rr > 2.5: real_sig = ("고실질금리", "neg", f"{rr:.2f}% - 성장주 밸류 부담")
        elif rr < 1: real_sig = ("저실질금리", "pos", f"{rr:.2f}% - 위험자산 우호")
        else: real_sig = ("중립 실질금리", "warn", f"{rr:.2f}%")
    else:
        real_sig = None

    # 2단계: 섹터
    sector_top = sectors[:3] if sectors else []
    sector_bot = sectors[-3:] if sectors else []
    structural_themes = {
        "에너지": "유가 변동성, OPEC+ 감산, 인플레 헤지",
        "반도체": "AI 데이터센터, 공급 제한 (TSMC·삼성 과점)",
        "원자력/SMR": "AI 전력 폭발 수요, 탈탄소 정책",
        "우주항공/방산": "지정학 긴장, 국방 예산 확대",
        "기술": "AI 인프라 + 빅테크 EPS 성장",
        "금융": "고금리 수혜, NIM 확대",
        "유틸리티": "전력 수요, 방어주",
        "헬스케어": "고령화, 방어주",
        "신흥국": "달러 약세시 자금 유입",
    }

    # 3단계: 종목 (병목)
    mcap = info.get("marketCap", 0) or 0
    if mcap > 1e12:
        position = ("대장주 (메가캡)", "pos", "ETF 자동 편입 + 기관 자금 지속 유입")
    elif mcap > 1e11:
        position = ("리더 (대형주)", "pos", "시장 주도, 기관 비중 높음")
    elif mcap > 1e10:
        position = ("주요 플레이어", "warn", "성장 여력 있으나 변동성 큼")
    elif mcap > 1e9:
        position = ("중형주", "warn", "급등락 가능")
    else:
        position = ("소형주", "neg", "유동성 부족, 변동성 매우 큼")

    # 4단계: 타이밍
    if rec_score >= 65:
        timing = ("🟢 진입 적기", "pos", "AI 점수 高 - 분할 매수 권장")
    elif rec_score >= 50:
        timing = ("🟡 분할 진입 고려", "warn", "AI 점수 중립 - 일부 비중만")
    elif rec_score >= 35:
        timing = ("🟠 관망", "warn", "AI 점수 낮음 - 신규 진입 보류")
    else:
        timing = ("🔴 진입 부적합", "neg", "AI 점수 매우 낮음")

    return {
        "macro_signals": macro_signals, "cycle": cycle, "liq_dir": liq_dir,
        "real_sig": real_sig, "sector_top": sector_top, "sector_bot": sector_bot,
        "structural_themes": structural_themes,
        "stock_sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "position": position, "timing": timing,
    }


@st.cache_data(ttl=600, show_spinner=False)
def get_option_chain(ticker):
    """가장 가까운 만기의 옵션 체인 분석
    - 콜/풋 최대 OI(미결제약정) 행사가
    - Max Pain (옵션 매도자가 가장 이득인 가격 = 마감 예상가)
    """
    try:
        t = yf.Ticker(ticker, session=_YF_SESSION)
        exps = t.options
        if not exps: return None
        # 가장 가까운 만기
        expiry = exps[0]
        chain = t.option_chain(expiry)
        calls = chain.calls[['strike', 'openInterest', 'volume', 'lastPrice']].copy()
        puts = chain.puts[['strike', 'openInterest', 'volume', 'lastPrice']].copy()
        calls = calls.fillna(0)
        puts = puts.fillna(0)
        if calls.empty or puts.empty: return None

        # 최대 OI 행사가
        max_call = calls.loc[calls['openInterest'].idxmax()]
        max_put = puts.loc[puts['openInterest'].idxmax()]

        # Max Pain 계산 (모든 행사가에서 총 손실 최소가 되는 지점)
        all_strikes = sorted(set(calls['strike'].tolist() + puts['strike'].tolist()))
        min_pain = None; max_pain_strike = None
        for s in all_strikes:
            # 이 가격에서 만기시 콜 매수자 총 가치
            call_pain = ((s - calls['strike']).clip(lower=0) * calls['openInterest']).sum()
            put_pain = ((puts['strike'] - s).clip(lower=0) * puts['openInterest']).sum()
            total_pain = call_pain + put_pain
            if min_pain is None or total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = s

        # 콜/풋 OI 총합 (시장 심리)
        total_call_oi = calls['openInterest'].sum()
        total_put_oi = puts['openInterest'].sum()
        pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 0

        # 상위 행사가별 OI (호가창용) - 현재가 주변
        return {
            "expiry": expiry,
            "max_call_strike": float(max_call['strike']),
            "max_call_oi": int(max_call['openInterest']),
            "max_put_strike": float(max_put['strike']),
            "max_put_oi": int(max_put['openInterest']),
            "max_pain": float(max_pain_strike),
            "pcr": pcr,
            "calls": calls.sort_values('strike'),
            "puts": puts.sort_values('strike'),
            "total_call_oi": int(total_call_oi),
            "total_put_oi": int(total_put_oi),
        }
    except Exception:
        return None


@st.cache_data(ttl=300, show_spinner=False)
def get_stock_data(ticker):
    """종목 데이터 5분 캐시 - 4년치 (Rate Limit 재시도)"""
    hist, t = yf_history_safe(ticker, period="4y", retries=4)
    if hist is None:
        return pd.DataFrame(), {}
    try:
        info = t.info
    except Exception:
        info = {}
    return hist, info


try:
    with st.spinner("데이터 수집 중..."):
        hist, info = get_stock_data(ticker)
        if hist.empty:
            st.error("⚠️ 데이터를 불러올 수 없습니다. 티커가 틀렸거나, Yahoo Finance가 일시적으로 요청을 차단(Rate Limit)했을 수 있습니다.")
            st.info("💡 잠시 (1~2분) 기다린 후 다시 시도하거나, 페이지를 새로고침 해주세요.")
            st.stop()
        # NaN 처리: 가격 행 ffill (직전 값으로 채움) + 그래도 비면 행 제거
        price_cols = ['Open', 'High', 'Low', 'Close']
        for c in price_cols:
            if c in hist.columns:
                hist[c] = hist[c].ffill().bfill()
        if 'Volume' in hist.columns:
            hist['Volume'] = hist['Volume'].fillna(0)
        hist = hist.dropna(subset=['Close']).copy()
        # 마지막 가격 확인
        if hist.empty or pd.isna(hist['Close'].iloc[-1]) or hist['Close'].iloc[-1] <= 0:
            st.error("⚠️ 가격 데이터가 비어있습니다. 신규 상장주거나 거래정지/지원되지 않는 종목일 수 있습니다.")
            st.info("💡 다른 티커를 시도해보세요. (예: NVDA, TSLA, 005930.KS)")
            st.stop()
        hist = compute_indicators(hist)
        patterns = detect_patterns(hist['Close'])
        macro = get_macro_all()
        # 시장 점수 먼저 계산 (목표가에 반영하기 위해)
        breadth = get_market_breadth()
        sp_trend = get_index_trend("^GSPC")
        mkt = make_market_summary(macro, breadth=breadth, sp_trend=sp_trend)
        market_score = mkt["score"]
        rec = score_all(hist, info, patterns, macro, is_kr)
        target = calc_target(hist, info, rec["score"], patterns[0], market_score=market_score)


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

    # ===== 변동성 구조 (Tail Risk) =====
    vix_v = macro.get("vix", (None, None))[0]
    vix9d = macro.get("vix9d", (None, None))[0]
    vix3m = macro.get("vix3m", (None, None))[0]
    vvix = macro.get("vvix", (None, None))[0]
    skew = macro.get("skew", (None, None))[0]

    if vix_v and (vix9d or vix3m or vvix or skew):
        st.markdown("<div class='section-h'>🌪️ 변동성 구조 (Tail Risk) <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 시장의 숨은 균열 감지</span></div>", unsafe_allow_html=True)
        v1, v2, v3 = st.columns(3)
        with v1:
            # VIX 기간구조 (콘탱고/백워데이션)
            if vix9d and vix3m:
                if vix9d > vix3m:
                    struct, scls, sdesc = "🔴 백워데이션", "neg", "단기>장기 - 즉각적 위험 신호"
                elif vix3m - vix9d > 3:
                    struct, scls, sdesc = "🟢 정상 콘탱고", "pos", "장기>단기 - 안정적"
                else:
                    struct, scls, sdesc = "🟡 평탄화", "warn", "구조 평탄 - 경계"
                st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {"#f87171" if scls=="neg" else "#fbbf24" if scls=="warn" else "#4ade80"};'>
                <div class='card-title'>VIX 기간구조</div>
                <div class='card-value {scls}' style='font-size:20px;'>{struct}</div>
                <div class='card-sub'>9D {vix9d:.1f} / 3M {vix3m:.1f} · {sdesc}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class='card' style='padding:18px 22px;'>
                <div class='card-title'>VIX 기간구조</div>
                <div class='card-value' style='color:#6b7280;'>N/A</div>
                <div class='card-sub'>데이터 수집 중</div></div>""", unsafe_allow_html=True)
        with v2:
            # VVIX (변동성의 변동성)
            if vvix:
                if vvix > 110: vc, vd = "neg", "급변동 위험 - 옵션시장 불안"
                elif vvix > 95: vc, vd = "warn", "변동성 상승 압력"
                else: vc, vd = "pos", "안정적"
                st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {"#f87171" if vc=="neg" else "#fbbf24" if vc=="warn" else "#4ade80"};'>
                <div class='card-title'>VVIX (변동성의 변동성)</div>
                <div class='card-value {vc}'>{vvix:.1f}</div>
                <div class='card-sub'>{vd}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class='card' style='padding:18px 22px;'>
                <div class='card-title'>VVIX</div>
                <div class='card-value' style='color:#6b7280;'>N/A</div>
                <div class='card-sub'>데이터 수집 중</div></div>""", unsafe_allow_html=True)
        with v3:
            # SKEW (블랙스완 지수)
            if skew:
                if skew > 145: kc, kd = "neg", "블랙스완 헤지 급증 - 큰손 폭락 대비"
                elif skew > 135: kc, kd = "warn", "꼬리위험 헤지 증가"
                else: kc, kd = "pos", "정상 범위"
                st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {"#f87171" if kc=="neg" else "#fbbf24" if kc=="warn" else "#4ade80"};'>
                <div class='card-title'>SKEW (블랙스완 지수)</div>
                <div class='card-value {kc}'>{skew:.0f}</div>
                <div class='card-sub'>{kd}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class='card' style='padding:18px 22px;'>
                <div class='card-title'>SKEW</div>
                <div class='card-value' style='color:#6b7280;'>N/A</div>
                <div class='card-sub'>데이터 수집 중</div></div>""", unsafe_allow_html=True)
        st.caption("💡 **백워데이션**(단기VIX>장기VIX)은 즉각적 시장 균열 신호. **VVIX**↑는 옵션시장 불안. **SKEW**↑는 큰손들이 폭락 보험(OTM 풋)을 비싸게 사들이는 중 = 꼬리위험 경계.")

        # 옵션 심리 (OVX + SPY PCR)
        ovx = macro.get("ovx", (None, None))[0]
        spy_pcr = macro.get("spy_pcr")
        op1, op2 = st.columns(2)
        with op1:
            if ovx:
                if ovx > 50: oc, od = "neg", "원유 변동성 폭증 - 인플레 충격 가능"
                elif ovx > 40: oc, od = "warn", "유가 불안정"
                else: oc, od = "pos", "유가 안정"
                st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {"#f87171" if oc=="neg" else "#fbbf24" if oc=="warn" else "#4ade80"};'>
                <div class='card-title'>OVX (유가 변동성)</div>
                <div class='card-value {oc}'>{ovx:.1f}</div>
                <div class='card-sub'>{od}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class='card' style='padding:18px 22px;'>
                <div class='card-title'>OVX</div>
                <div class='card-value' style='color:#6b7280;'>N/A</div>
                <div class='card-sub'>데이터 수집 중</div></div>""", unsafe_allow_html=True)
        with op2:
            if spy_pcr:
                if spy_pcr > 1.3: pc, pd_ = "neg", "풋 우세 - 시장 폭락 헤지 급증"
                elif spy_pcr > 1.0: pc, pd_ = "warn", "풋 약우세 - 방어 심리"
                elif spy_pcr > 0.8: pc, pd_ = "warn", "중립"
                else: pc, pd_ = "pos", "콜 우세 - 상승 기대"
                st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {"#f87171" if pc=="neg" else "#fbbf24" if pc=="warn" else "#4ade80"};'>
                <div class='card-title'>SPY 옵션 PCR</div>
                <div class='card-value {pc}'>{spy_pcr:.2f}</div>
                <div class='card-sub'>{pd_}</div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div class='card' style='padding:18px 22px;'>
                <div class='card-title'>SPY 옵션 PCR</div>
                <div class='card-value' style='color:#6b7280;'>N/A</div>
                <div class='card-sub'>데이터 수집 중</div></div>""", unsafe_allow_html=True)

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

    # Net Liquidity (실질 유동성) + 실질금리
    nl1, nl2 = st.columns(2)
    with nl1:
        # Net Liquidity = 연준자산 - TGA - RRP (단위 통일: B)
        fa = macro.get("fed_assets", (None, None))[0]   # 백만$ 단위 (WALCL)
        tga = macro.get("tga", (None, None))[0]
        rrp = macro.get("rrp", (None, None))[0]
        if fa and tga is not None and rrp is not None:
            # WALCL은 백만달러, TGA(WTREGEN)도 백만, RRP는 십억
            net_liq = (fa - tga) / 1000 - rrp  # 십억$ 단위로
            net_liq_t = net_liq / 1000  # 조$ 
            st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid #60a5fa;'>
            <div class='card-title'>💧 Net Liquidity (실질 유동성)</div>
            <div class='card-value'>{net_liq_t:.2f}T</div>
            <div class='card-sub'>연준자산 − TGA − RRP · 증시 유동성 핵심</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class='card' style='padding:18px 22px;'>
            <div class='card-title'>💧 Net Liquidity</div>
            <div class='card-value' style='color:#6b7280;'>N/A</div>
            <div class='card-sub'>데이터 수집 중</div>
            </div>""", unsafe_allow_html=True)
    with nl2:
        rr = macro.get("real_rate", (None, None))
        if rr[0] is not None:
            rr_v = rr[0]
            rr_prev = rr[1] if rr[1] is not None else rr_v
            rr_chg = rr_v - rr_prev
            # 실질금리 높으면 위험자산 부담
            if rr_v > 2.5: rr_cls, rr_desc = "neg", "고실질금리 - 밸류에이션 부담 큼"
            elif rr_v > 2: rr_cls, rr_desc = "warn", "실질금리 상승 - 주의"
            elif rr_v > 1: rr_cls, rr_desc = "warn", "중립 수준"
            else: rr_cls, rr_desc = "pos", "저실질금리 - 위험자산 우호"
            st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {"#f87171" if rr_cls=="neg" else "#fbbf24" if rr_cls=="warn" else "#4ade80"};'>
            <div class='card-title'>📊 10년 실질금리 (TIPS)</div>
            <div class='card-value {rr_cls}'>{rr_v:.2f}%</div>
            <div class='card-sub {rr_cls}'>{rr_desc} · 전일 {rr_chg:+.2f}%p</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class='card' style='padding:18px 22px;'>
            <div class='card-title'>📊 10년 실질금리</div>
            <div class='card-value' style='color:#6b7280;'>N/A</div>
            <div class='card-sub'>데이터 수집 중</div>
            </div>""", unsafe_allow_html=True)
    st.caption("💡 Net Liquidity가 늘면 증시로 돈이 유입(상승 우호), 줄면 유동성 위축. 실질금리(명목-기대인플레)가 치솟으면 성장주 밸류에이션 붕괴 위험.")

    # ===== 시장 종합 결론 (이미 위에서 계산함) =====
    pos_html = "<br>".join(f"<span class='pos'>✓ {p}</span>" for p in mkt["positives"]) or "<span style='color:#64748b;'>특이사항 없음</span>"
    neg_html = "<br>".join(f"<span class='neg'>✗ {n}</span>" for n in mkt["negatives"]) or "<span style='color:#64748b;'>특이사항 없음</span>"

    # 상세 결론 메시지 (보수적 표현)
    if mkt["score"] >= 75:
        detail = "유동성·금리·신용 환경이 위험자산에 우호적입니다. 다만 시장 전반의 고점 위험은 항상 존재. 분할 매수 + 손절선 명확히 설정 권장."
    elif mkt["score"] >= 60:
        detail = "전반적으로 우호적이지만 일부 부정 요인 존재. 신규 진입은 분할 매수로 천천히, 기존 포지션은 유지하되 익절선 점검."
    elif mkt["score"] >= 45:
        detail = "긍정/부정 요인이 혼재. 신규 진입 보류 권장. 기존 포지션 비중 점검, 손절선 상향."
    elif mkt["score"] >= 30:
        detail = "방어적 환경. 현금 비중 확대, 변동성 자산(개별주·암호화폐) 비중 축소. 단기채·금 등 안전자산 비중 검토."
    else:
        detail = "위험회피 국면 진입. 현금화 우선, 신규 진입 전면 보류. 시장 회복 신호(VIX 안정, 시장폭 회복) 확인 후 재진입."

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

    # ===== 탑다운 4단계 투자 흐름 =====
    sectors = get_sector_flow()  # 섹터 데이터 (탑다운에서 사용)
    td = topdown_analysis(macro, mkt, sectors, ticker, info, rec["score"])

    st.markdown("<div class='section-h'>🧭 탑다운 4단계 흐름 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 거시 → 섹터 → 종목 → 타이밍</span></div>", unsafe_allow_html=True)

    # 1단계: 거시
    macro_html = ""
    for label, cls, desc in td["macro_signals"]:
        macro_html += f"<div style='display:inline-block; margin:3px 6px 3px 0; padding:4px 10px; background:#0a0c12; border-radius:5px; border:1px solid #1c1f26;'><span class='{cls}' style='font-weight:700; font-size:12px;'>{label}</span> <span style='color:#9ca3af; font-size:11px;'>· {desc}</span></div>"
    cyc_name, cyc_cls, cyc_desc = td["cycle"]
    liq_name, liq_cls, liq_desc = td["liq_dir"]
    real_html = ""
    if td["real_sig"]:
        rn, rc, rd = td["real_sig"]
        real_html = f"<div style='margin-top:6px;'><span class='{rc}' style='font-weight:700; font-size:12px;'>{rn}</span> <span style='color:#9ca3af; font-size:11px;'>· {rd}</span></div>"

    st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid #60a5fa; margin-bottom:10px;'>
    <div style='display:flex; gap:14px; align-items:center; margin-bottom:10px;'>
    <span style='background:#1e3a8a; color:#fff; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:0.1em;'>STEP 1</span>
    <span style='font-size:15px; font-weight:800; color:#fafafa;'>🗺️ 거시 (지도 읽기)</span>
    <span style='color:#9ca3af; font-size:11px;'>돈이 어디로 흐르는가</span>
    </div>
    <div style='margin-bottom:8px;'>{macro_html}</div>
    <div style='padding:10px 12px; background:#0a0c12; border-radius:6px;'>
    <span class='{cyc_cls}' style='font-weight:700; font-size:13px;'>🔄 {cyc_name}</span>
    <span style='color:#cbd5e1; font-size:12px; margin-left:8px;'>{cyc_desc}</span>
    <div style='margin-top:6px;'><span class='{liq_cls}' style='font-weight:700; font-size:12px;'>💧 {liq_name}</span> <span style='color:#9ca3af; font-size:11px;'>· {liq_desc}</span></div>
    {real_html}
    </div>
    </div>""", unsafe_allow_html=True)

    # 2단계: 섹터
    if td["sector_top"]:
        top_sectors_html = " · ".join(
            f"<span class='pos' style='font-weight:700;'>{s['name']} {s['month']:+.1f}%</span>" for s in td["sector_top"]
        )
        bot_sectors_html = " · ".join(
            f"<span class='neg' style='font-weight:700;'>{s['name']} {s['month']:+.1f}%</span>" for s in td["sector_bot"]
        )
        # 강한 섹터 중 구조적 테마가 있는 것
        structural_html = ""
        for s in td["sector_top"]:
            if s["name"] in td["structural_themes"]:
                structural_html += f"<div style='padding:8px 12px; background:#0a1a13; border-left:2px solid #4ade80; border-radius:4px; margin:5px 0;'><span class='pos' style='font-weight:700; font-size:12px;'>★ {s['name']}</span> <span style='color:#cbd5e1; font-size:11px;'>· {td['structural_themes'][s['name']]}</span></div>"

        st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid #4ade80; margin-bottom:10px;'>
        <div style='display:flex; gap:14px; align-items:center; margin-bottom:10px;'>
        <span style='background:#15803d; color:#fff; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:0.1em;'>STEP 2</span>
        <span style='font-size:15px; font-weight:800; color:#fafafa;'>🎯 강한 섹터 (방향에 올라타기)</span>
        <span style='color:#9ca3af; font-size:11px;'>구조적 수혜 섹터</span>
        </div>
        <div style='padding:8px 12px; background:#0a0c12; border-radius:5px; margin-bottom:6px;'>
        <span style='color:#9ca3af; font-size:11px; font-weight:600;'>🔥 자금 유입 TOP 3 · </span>{top_sectors_html}
        </div>
        <div style='padding:8px 12px; background:#0a0c12; border-radius:5px; margin-bottom:8px;'>
        <span style='color:#9ca3af; font-size:11px; font-weight:600;'>❄️ 자금 유출 · </span>{bot_sectors_html}
        </div>
        {structural_html if structural_html else "<div style='color:#6b7280; font-size:11px;'>현재 자금이 유입되는 섹터 중 구조적 수혜 테마 없음 - 단기 모멘텀일 가능성</div>"}
        </div>""", unsafe_allow_html=True)

    # 3단계: 종목 (병목)
    pos_name, pos_cls, pos_desc = td["position"]
    sector_match = ""
    # 종목 섹터가 강한 섹터 TOP3에 있나?
    if td["sector_top"] and td["stock_sector"]:
        stock_sec_lower = td["stock_sector"].lower()
        top_names = " ".join(s["name"] for s in td["sector_top"]).lower()
        # GICS 영문 ↔ 한글 매칭
        sec_map = {
            "technology": "기술", "energy": "에너지", "financial": "금융",
            "healthcare": "헬스케어", "industrials": "산업재", "utilities": "유틸리티",
            "consumer": "소비재", "communication": "통신", "real estate": "부동산",
            "basic materials": "소재",
        }
        ko_sector = None
        for en, ko in sec_map.items():
            if en in stock_sec_lower:
                ko_sector = ko; break
        if ko_sector and ko_sector in top_names:
            sector_match = f"<div style='padding:8px 12px; background:#0a1a13; border-left:2px solid #4ade80; border-radius:4px; margin-top:8px;'><span class='pos' style='font-weight:700; font-size:12px;'>✓ 강한 섹터 흐름 일치</span> <span style='color:#cbd5e1; font-size:11px;'>· 종목 섹터({td['stock_sector']})가 TOP3 자금유입 섹터와 일치 - 방향에 올라탐</span></div>"
        elif ko_sector:
            sector_match = f"<div style='padding:8px 12px; background:#1a0e0e; border-left:2px solid #f87171; border-radius:4px; margin-top:8px;'><span class='neg' style='font-weight:700; font-size:12px;'>⚠ 섹터 흐름 불일치</span> <span style='color:#cbd5e1; font-size:11px;'>· 종목 섹터({td['stock_sector']})가 자금유입 TOP3에 없음 - 역풍 가능</span></div>"

    st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid #fbbf24; margin-bottom:10px;'>
    <div style='display:flex; gap:14px; align-items:center; margin-bottom:10px;'>
    <span style='background:#a16207; color:#fff; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:0.1em;'>STEP 3</span>
    <span style='font-size:15px; font-weight:800; color:#fafafa;'>🏢 종목 위치 (병목 장악)</span>
    <span style='color:#9ca3af; font-size:11px;'>이 기업이 가진 자리</span>
    </div>
    <div style='padding:8px 12px; background:#0a0c12; border-radius:5px;'>
    <span style='color:#9ca3af; font-size:11px;'>섹터: <b style='color:#d1d5db;'>{td['stock_sector'] or 'N/A'}</b> · 산업: <b style='color:#d1d5db;'>{td['industry'] or 'N/A'}</b></span>
    <div style='margin-top:6px;'><span class='{pos_cls}' style='font-weight:700; font-size:13px;'>📊 {pos_name}</span> <span style='color:#9ca3af; font-size:11px;'>· {pos_desc}</span></div>
    </div>
    {sector_match}
    </div>""", unsafe_allow_html=True)

    # 4단계: 타이밍
    tim_name, tim_cls, tim_desc = td["timing"]
    st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {"#4ade80" if tim_cls=="pos" else "#fbbf24" if tim_cls=="warn" else "#f87171"};'>
    <div style='display:flex; gap:14px; align-items:center; margin-bottom:10px;'>
    <span style='background:#7c2d12; color:#fff; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:0.1em;'>STEP 4</span>
    <span style='font-size:15px; font-weight:800; color:#fafafa;'>⏱️ 진입 타이밍</span>
    <span style='color:#9ca3af; font-size:11px;'>차트·수급으로 결정</span>
    </div>
    <div style='padding:10px 12px; background:#0a0c12; border-radius:5px;'>
    <span class='{tim_cls}' style='font-weight:800; font-size:16px;'>{tim_name}</span>
    <span style='color:#cbd5e1; font-size:12px; margin-left:8px;'>· {tim_desc}</span>
    <div style='color:#6b7280; font-size:11px; margin-top:6px;'>AI 종합점수: {rec["score"]:.1f}/100 · 아래 종목 상세 분석 참고</div>
    </div>
    </div>""", unsafe_allow_html=True)

    st.caption("💡 거시(돈의 흐름) → 섹터(구조적 수혜) → 종목(병목) → 타이밍 순서로 좁혀가면 개인 투자자에게 가장 현실적이고 승률이 높습니다.")

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
        (high_idx, high_p, "고점", ccy + f"{high_p:,.0f}", "#9ca3af", "top center"),
        (low_idx, low_p, "저점", ccy + f"{low_p:,.0f}", "#9ca3af", "bottom center"),
        (hist.index[-1], curr, "현재", ccy + f"{curr:,.0f}", "#fafafa", "top center"),
        (dates[-1], target["final"], "AI 목표", ccy + f"{target['final']:,.0f}", "#4ade80", "top center"),
    ]

    for d, p, label, price_str, c, pos in milestones:
        text_html = f"{label} {price_str}"
        fig.add_trace(go.Scatter(x=[d], y=[p], mode='markers+text',
                                 marker=dict(size=14, color=c, line=dict(width=2.5, color='#08090d')),
                                 text=[text_html], textposition=pos,
                                 textfont=dict(color='#e2e8f0', size=12, family='Inter'),
                                 showlegend=False, hoverinfo='skip',
                                 cliponaxis=False))

    fig.update_layout(
        height=520, margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor='#08090d', paper_bgcolor='#08090d',
        font=dict(family="Inter", color='#e2e8f0', size=11),
        xaxis=dict(gridcolor='#1c1f26', showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='#1c1f26', showgrid=True, zeroline=False),
        legend=dict(orientation="h", y=1.08, x=0, bgcolor='rgba(0,0,0,0)'),
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    # ===== 벤치마크 대비 상대 수익률 =====
    @st.cache_data(ttl=3600, show_spinner=False)
    def get_benchmark(period="1y"):
        spy, _ = yf_history_safe("SPY", period=period, retries=2)
        qqq, _ = yf_history_safe("QQQ", period=period, retries=2)
        return spy, qqq

    spy_h, qqq_h = get_benchmark("1y")
    if spy_h is not None and not spy_h.empty:
        # 1년치 종목 데이터 + SPY + QQQ를 0% 기준으로 정규화
        stock_1y = hist.iloc[-252:] if len(hist) >= 252 else hist
        spy_aligned = spy_h.iloc[-252:] if len(spy_h) >= 252 else spy_h
        qqq_aligned = qqq_h.iloc[-252:] if len(qqq_h) >= 252 else qqq_h

        # 정규화 (시작점 0%)
        stock_norm = (stock_1y['Close'] / stock_1y['Close'].iloc[0] - 1) * 100
        spy_norm = (spy_aligned['Close'] / spy_aligned['Close'].iloc[0] - 1) * 100
        qqq_norm = (qqq_aligned['Close'] / qqq_aligned['Close'].iloc[0] - 1) * 100

        # 종목 vs 벤치마크 비교
        stock_perf = float(stock_norm.iloc[-1])
        spy_perf = float(spy_norm.iloc[-1])
        qqq_perf = float(qqq_norm.iloc[-1])
        vs_spy = stock_perf - spy_perf
        vs_qqq = stock_perf - qqq_perf

        st.markdown("<div class='section-h'>📊 벤치마크 대비 상대 수익률 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 1년 기준 · S&P500 (SPY) + 나스닥 (QQQ)</span></div>", unsafe_allow_html=True)

        bench_fig = go.Figure()
        bench_fig.add_trace(go.Scatter(x=stock_1y.index, y=stock_norm,
                                        mode='lines', name=ticker,
                                        line=dict(color='#fafafa', width=2.5)))
        bench_fig.add_trace(go.Scatter(x=spy_aligned.index, y=spy_norm,
                                        mode='lines', name='S&P500',
                                        line=dict(color='#60a5fa', width=1.5, dash='dot')))
        bench_fig.add_trace(go.Scatter(x=qqq_aligned.index, y=qqq_norm,
                                        mode='lines', name='나스닥',
                                        line=dict(color='#a78bfa', width=1.5, dash='dot')))
        bench_fig.add_hline(y=0, line=dict(color='#374151', width=1, dash='solid'))
        bench_fig.update_layout(
            height=340, margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor='#08090d', paper_bgcolor='#08090d',
            font=dict(family="Inter", color='#d1d5db', size=11),
            xaxis=dict(gridcolor='#1c1f26', showgrid=True, zeroline=False),
            yaxis=dict(gridcolor='#1c1f26', showgrid=True, zeroline=False,
                       ticksuffix='%', tickfont=dict(family='JetBrains Mono')),
            legend=dict(orientation="h", y=1.06, x=0, bgcolor='rgba(0,0,0,0)'),
            hovermode='x unified'
        )
        st.plotly_chart(bench_fig, use_container_width=True)

        # 비교 카드
        spy_cls = "pos" if vs_spy > 0 else "neg"
        qqq_cls = "pos" if vs_qqq > 0 else "neg"
        spy_label = "아웃퍼폼" if vs_spy > 0 else "언더퍼폼"
        qqq_label = "아웃퍼폼" if vs_qqq > 0 else "언더퍼폼"
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            stock_cls = "pos" if stock_perf > 0 else "neg"
            st.markdown(f"""<div class='card' style='padding:16px 20px;'>
            <div class='card-title'>{ticker} 1년 수익률</div>
            <div class='card-value {stock_cls}'>{stock_perf:+.2f}%</div>
            </div>""", unsafe_allow_html=True)
        with bc2:
            st.markdown(f"""<div class='card' style='padding:16px 20px;'>
            <div class='card-title'>vs S&P500</div>
            <div class='card-value {spy_cls}'>{vs_spy:+.2f}%p</div>
            <div class='card-sub {spy_cls}'>{spy_label} · SPY {spy_perf:+.2f}%</div>
            </div>""", unsafe_allow_html=True)
        with bc3:
            st.markdown(f"""<div class='card' style='padding:16px 20px;'>
            <div class='card-title'>vs 나스닥</div>
            <div class='card-value {qqq_cls}'>{vs_qqq:+.2f}%p</div>
            <div class='card-sub {qqq_cls}'>{qqq_label} · QQQ {qqq_perf:+.2f}%</div>
            </div>""", unsafe_allow_html=True)

    # ===== 옵션 체인 분석 (마감 예상가) =====
    opt = get_option_chain(ticker)
    if opt:
        st.markdown(f"<div class='section-h'>🎰 옵션 체인 분석 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 만기 {opt['expiry']} · 콜/풋 최대 물량 + 예상 마감가</span></div>", unsafe_allow_html=True)

        # 3개 핵심 카드
        oc1, oc2, oc3 = st.columns(3)
        with oc1:
            # Max Pain (마감 예상가)
            mp = opt["max_pain"]
            mp_diff = (mp - curr) / curr * 100
            mp_cls = "pos" if mp_diff > 0 else "neg" if mp_diff < 0 else "warn"
            st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid #fbbf24;'>
            <div class='card-title'>🎯 Max Pain (마감 예상가)</div>
            <div class='card-value'>{ccy}{mp:,.2f}</div>
            <div class='card-sub {mp_cls}'>현재가 대비 {mp_diff:+.1f}% · 옵션상 수렴 지점</div>
            </div>""", unsafe_allow_html=True)
        with oc2:
            # 콜 최대 물량 (저항선)
            st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid #4ade80;'>
            <div class='card-title'>📈 콜 최대 물량 (저항선)</div>
            <div class='card-value pos'>{ccy}{opt['max_call_strike']:,.2f}</div>
            <div class='card-sub'>OI {opt['max_call_oi']:,} · 이 위로 잘 안 감</div>
            </div>""", unsafe_allow_html=True)
        with oc3:
            # 풋 최대 물량 (지지선)
            st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid #f87171;'>
            <div class='card-title'>📉 풋 최대 물량 (지지선)</div>
            <div class='card-value neg'>{ccy}{opt['max_put_strike']:,.2f}</div>
            <div class='card-sub'>OI {opt['max_put_oi']:,} · 이 아래로 잘 안 감</div>
            </div>""", unsafe_allow_html=True)

        # 호가창 스타일 차트 (현재가 주변 행사가별 OI)
        calls = opt["calls"].copy(); puts = opt["puts"].copy()
        # OI가 전부 0이면 volume(거래량) 사용
        oi_col = 'openInterest'
        if calls['openInterest'].sum() == 0 and puts['openInterest'].sum() == 0:
            oi_col = 'volume'
        # 현재가 ±25% 범위 (넓게)
        lo, hi = curr * 0.75, curr * 1.25
        calls_f = calls[(calls['strike'] >= lo) & (calls['strike'] <= hi)]
        puts_f = puts[(puts['strike'] >= lo) & (puts['strike'] <= hi)]
        # 그래도 비면 전체 사용
        if calls_f.empty and puts_f.empty:
            calls_f = calls; puts_f = puts

        # 행사가별로 콜/풋 나란히
        strikes = sorted(set(calls_f['strike'].tolist() + puts_f['strike'].tolist()))
        call_oi_map = dict(zip(calls_f['strike'], calls_f[oi_col]))
        put_oi_map = dict(zip(puts_f['strike'], puts_f[oi_col]))
        oi_label = "OI" if oi_col == 'openInterest' else "거래량"

        if not strikes or (sum(call_oi_map.values()) == 0 and sum(put_oi_map.values()) == 0):
            st.info("옵션 미결제약정/거래량 데이터가 없습니다 (만기 임박 또는 거래 한산).")
        else:
            fig_opt = go.Figure()
            fig_opt.add_trace(go.Bar(
                y=[f"{s:,.1f}" for s in strikes],
                x=[-put_oi_map.get(s, 0) for s in strikes],
                orientation='h', name='풋 (지지)',
                marker=dict(color='#f87171'),
                hovertemplate='행사가 %{y}<br>풋 '+oi_label+': %{customdata:,}<extra></extra>',
                customdata=[put_oi_map.get(s, 0) for s in strikes]
            ))
            fig_opt.add_trace(go.Bar(
                y=[f"{s:,.1f}" for s in strikes],
                x=[call_oi_map.get(s, 0) for s in strikes],
                orientation='h', name='콜 (저항)',
                marker=dict(color='#4ade80'),
                hovertemplate='행사가 %{y}<br>콜 '+oi_label+': %{x:,}<extra></extra>'
            ))
            fig_opt.update_layout(
                height=max(400, len(strikes)*22), barmode='relative',
                margin=dict(l=10, r=10, t=30, b=10),
                plot_bgcolor='#08090d', paper_bgcolor='#08090d',
                font=dict(family="Inter", color='#d1d5db', size=10),
                xaxis=dict(title=f"← 풋 {oi_label} · 콜 {oi_label} →", gridcolor='#1c1f26', zeroline=True,
                           zerolinecolor='#374151', tickformat=',d'),
                yaxis=dict(title=f"행사가 (현재가 {ccy}{curr:,.1f})", showgrid=False,
                           tickfont=dict(family='JetBrains Mono', size=10)),
                legend=dict(orientation="h", y=1.04, x=0, bgcolor='rgba(0,0,0,0)'),
            )
            st.plotly_chart(fig_opt, use_container_width=True)

        # 해석
        pcr = opt["pcr"]
        if pcr > 1.2:
            pcr_msg, pcr_cls = "풋 우세 - 하락 헤지/공포 심리 강함", "neg"
        elif pcr > 0.9:
            pcr_msg, pcr_cls = "중립 - 균형 잡힌 포지션", "warn"
        else:
            pcr_msg, pcr_cls = "콜 우세 - 상승 기대 심리 강함", "pos"
        st.markdown(f"""<div class='card' style='padding:14px 18px;'>
        <span style='color:#9ca3af; font-size:12px;'>Put/Call 비율</span>
        <span class='{pcr_cls}' style='font-weight:800; font-size:15px; margin-left:8px; font-family:JetBrains Mono;'>{pcr:.2f}</span>
        <span class='{pcr_cls}' style='font-size:12px; margin-left:8px;'>{pcr_msg}</span>
        </div>""", unsafe_allow_html=True)
        st.caption(f"💡 **Max Pain** = 옵션 매도자(주로 기관)가 가장 이득인 가격으로, 만기일에 주가가 이쪽으로 끌려가는 경향. **콜 최대물량**({ccy}{opt['max_call_strike']:,.0f})은 저항선, **풋 최대물량**({ccy}{opt['max_put_strike']:,.0f})은 지지선 역할. 옵션 만기({opt['expiry']}) 전후 변동성 주의.")

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

    # ===== 분할 매수/매도 (주 단위 고정) ======
    st.markdown("<div class='section-h'>💉 3단계 분할 매매 전략 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 5일 평균가 기준 · 매주 월요일 갱신</span></div>", unsafe_allow_html=True)

    # 5일 평균가를 기준점으로 사용 (일봉 흔들림 흡수)
    base_price = target["avg_5d"]

    # 분할매수: 5일평균 -3%, -7%, -12% (지지선 근처)
    buy_p1 = base_price * 0.97
    buy_p2 = base_price * 0.93
    buy_p3 = max(target["low52"] * 1.05, base_price * 0.88)
    # 분할매도: 5일평균 → 목표가 사이 33%, 66%, 100%
    diff_t = target["final"] - base_price
    sell_p1 = base_price + diff_t * 0.33
    sell_p2 = base_price + diff_t * 0.66
    sell_p3 = target["final"]

    # 이번 주 월요일 날짜
    today = hist.index[-1].to_pydatetime() if hasattr(hist.index[-1], 'to_pydatetime') else hist.index[-1]
    weekday = today.weekday()  # 월=0
    monday = today - timedelta(days=weekday)
    next_update = monday + timedelta(days=7)

    sp_col1, sp_col2 = st.columns(2)
    with sp_col1:
        st.markdown(f"""<div class='card' style='border-left:3px solid #4ade80; padding:18px 22px;'>
        <div style='color:#4ade80; font-weight:700; font-size:13px; margin-bottom:12px;'>📥 분할 매수 (3단계)</div>
        <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px dashed #1c1f26; font-size:13px;'>
        <span style='color:#9ca3af;'>1차 (30%) · -3%</span><b class='pos' style='font-family:JetBrains Mono;'>{ccy}{buy_p1:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px dashed #1c1f26; font-size:13px;'>
        <span style='color:#9ca3af;'>2차 (35%) · -7%</span><b class='pos' style='font-family:JetBrains Mono;'>{ccy}{buy_p2:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:8px 0; font-size:13px;'>
        <span style='color:#9ca3af;'>3차 (35%) · 저점 지지</span><b class='pos' style='font-family:JetBrains Mono;'>{ccy}{buy_p3:,.2f}</b></div>
        </div>""", unsafe_allow_html=True)
    with sp_col2:
        st.markdown(f"""<div class='card' style='border-left:3px solid #f87171; padding:18px 22px;'>
        <div style='color:#f87171; font-weight:700; font-size:13px; margin-bottom:12px;'>📤 분할 매도 (3단계)</div>
        <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px dashed #1c1f26; font-size:13px;'>
        <span style='color:#9ca3af;'>1차 (30%) · 목표 33%</span><b class='warn' style='font-family:JetBrains Mono;'>{ccy}{sell_p1:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px dashed #1c1f26; font-size:13px;'>
        <span style='color:#9ca3af;'>2차 (40%) · 목표 66%</span><b class='warn' style='font-family:JetBrains Mono;'>{ccy}{sell_p2:,.2f}</b></div>
        <div style='display:flex; justify-content:space-between; padding:8px 0; font-size:13px;'>
        <span style='color:#9ca3af;'>3차 (30%) · 최종 목표가</span><b class='warn' style='font-family:JetBrains Mono;'>{ccy}{sell_p3:,.2f}</b></div>
        </div>""", unsafe_allow_html=True)

    st.caption(f"💡 기준가: 5일 평균 {ccy}{base_price:,.2f} (현재가 {ccy}{curr:,.2f}) · 다음 갱신 {next_update.strftime('%Y-%m-%d')} (월요일)")

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
                plot_bgcolor='#08090d', paper_bgcolor='#08090d',
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
    # 세력 매집 종합 결론 (보수적)
    accu_avg = (obv_s + poc_s + vcp_s) / 3
    if accu_avg >= 75:
        accu_msg, accu_cls = "🔥 강한 세력 매집 - 매수 신호 (확정 전 분할진입)", "pos"
    elif accu_avg >= 60:
        accu_msg, accu_cls = "💡 매집 신호 감지 - 관심 단계", "pos"
    elif accu_avg <= 30:
        accu_msg, accu_cls = "⚠️ 세력 분산 - 매도 우위", "neg"
    elif accu_avg <= 40:
        accu_msg, accu_cls = "🟠 매집 약함 - 관망 권장", "warn"
    else:
        accu_msg, accu_cls = "⚖️ 매집/분산 혼조 - 신중", "warn"
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
                            plot_bgcolor='#08090d', paper_bgcolor='#08090d',
                            font=dict(color='#e2e8f0', size=12),
                            xaxis=dict(gridcolor='#1c1f26'),
                            yaxis=dict(gridcolor='#1c1f26'),
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

    sim = None  # 통합 박스에서 사용
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

    # ===== 🎯 종목 분석 통합 결론 =====
    st.markdown("---")
    integ = integrate_stock_signals(rec, target, patterns, hist, ma_data, accu_avg, sim)
    v_name, v_cls, v_desc = integ["verdict"]

    st.markdown(f"<div class='section-h'>🎯 종목 분석 통합 결론 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 6개 지표 일관성 진단</span></div>", unsafe_allow_html=True)

    # 메인 결론 박스 + 투표 분포 바
    bar_color = "#4ade80" if v_cls == "pos" else "#f87171" if v_cls == "neg" else "#fbbf24"
    st.markdown(f"""<div class='card' style='padding:22px 26px; border-left:4px solid {bar_color}; margin-bottom:12px;'>
    <div style='display:flex; justify-content:space-between; align-items:start; margin-bottom:14px;'>
    <div>
    <div style='font-size:11px; color:#6b7280; letter-spacing:0.1em; font-weight:600; margin-bottom:4px;'>📊 6개 지표 통합 진단</div>
    <div class='{v_cls}' style='font-size:24px; font-weight:900;'>{v_name}</div>
    <div style='color:#cbd5e1; font-size:12px; margin-top:4px;'>{v_desc}</div>
    </div>
    </div>
    <div style='display:flex; background:#0a0c12; border-radius:8px; height:32px; overflow:hidden; margin-top:14px;'>
    <div style='width:{integ["buy_pct"]}%; background:#15803d; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:12px; min-width:0;'>{f"매수 {integ['votes']['매수']}" if integ['buy_pct']>=12 else ''}</div>
    <div style='width:{integ["hold_pct"]}%; background:#a16207; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:12px; min-width:0;'>{f"관망 {integ['votes']['관망']}" if integ['hold_pct']>=12 else ''}</div>
    <div style='width:{integ["sell_pct"]}%; background:#991b1b; display:flex; align-items:center; justify-content:center; color:#fff; font-weight:700; font-size:12px; min-width:0;'>{f"매도 {integ['votes']['매도']}" if integ['sell_pct']>=12 else ''}</div>
    </div>
    </div>""", unsafe_allow_html=True)

    # 6개 지표 상세
    detail_html = ""
    for name, val, sig, cls in integ["details"]:
        sig_bg = "#15803d" if cls == "pos" else "#991b1b" if cls == "neg" else "#a16207"
        detail_html += f"""<div style='display:flex; justify-content:space-between; align-items:center; padding:10px 14px; background:#0a0c12; border-radius:6px; margin-bottom:6px;'>
        <div>
        <span style='color:#9ca3af; font-size:11px; font-weight:600;'>{name}</span>
        <div style='color:#f1f5f9; font-size:13px; font-weight:700; margin-top:2px;'>{val}</div>
        </div>
        <span style='background:{sig_bg}; color:#fff; padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700;'>{sig}</span>
        </div>"""
    st.markdown(f"<div>{detail_html}</div>", unsafe_allow_html=True)
    st.caption("💡 6개 지표가 같은 방향을 가리킬 때(80%+) 신호가 가장 신뢰도 높음. 혼조시 분할 진입/축소로 리스크 분산.")

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
        if not inf_factor_html:
            inf_factor_html = "<div style='color:#6b7280; font-size:12px; padding:8px 0;'>FRED CPI/Core CPI/PPI/PCE 데이터 일시 수집 불가 - 새로고침 시도</div>"
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
        if not rec_factor_html:
            rec_factor_html = "<div style='color:#6b7280; font-size:12px; padding:8px 0;'>경기침체 지표 데이터 수집 불가</div>"
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
    st.markdown(f"""<div class='card' style='margin-top:18px; padding:22px 26px; border-left:6px solid {"#ef4444" if combo_cls == "neg" else "#f59e0b" if combo_cls == "warn" else "#22c55e"};'>
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;'>
    <span style='font-size:13px; color:#94a3b8; font-weight:700; letter-spacing:1px;'>🎯 시장 × 인플레 × 침체 조합 진단</span>
    <div style='font-size:12px; color:#64748b;'>시장 {mkt["score"]:.0f} · 인플레 {eco["inf_score"]:.0f} · 침체 {eco["rec_score"]:.0f}</div>
    </div>
    <div class='{combo_cls}' style='font-size:22px; font-weight:900; margin-bottom:10px;'>{combo_name}</div>
    <div style='color:#cbd5e1; font-size:13px; line-height:1.7;'>📜 {combo_desc}</div>
    </div>""", unsafe_allow_html=True)

    # ===== Fed 금리 시나리오 =====
    fed = fed_scenarios(mkt["score"], eco["inf_score"], eco["rec_score"])
    st.markdown("<div class='section-h' style='margin-top:20px;'>🏛️ Fed 금리 시나리오 별 결과 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 현재 환경 기반 예상</span></div>", unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    def fed_card(title, icon, scenario, accent):
        label, desc = scenario
        # 상황 클래스 (제목 색)
        if "🟢" in label: bcolor = "#15803d"; lcls = "pos"
        elif "🔴" in label: bcolor = "#991b1b"; lcls = "neg"
        else: bcolor = "#a16207"; lcls = "warn"
        return f"""<div class='card' style='padding:18px 22px; border-top:3px solid {bcolor}; height:100%;'>
        <div style='display:flex; align-items:center; gap:8px; margin-bottom:10px;'>
        <span style='font-size:18px;'>{icon}</span>
        <span style='font-size:13px; color:#9ca3af; font-weight:700; letter-spacing:0.05em;'>{title}</span>
        </div>
        <div class='{lcls}' style='font-size:15px; font-weight:800; margin-bottom:10px; line-height:1.3;'>{label}</div>
        <div style='color:#cbd5e1; font-size:12px; line-height:1.6;'>{desc}</div>
        </div>"""

    with fc1: st.markdown(fed_card("금리 인상", "📈", fed["hike"], "neg"), unsafe_allow_html=True)
    with fc2: st.markdown(fed_card("금리 동결", "⏸️", fed["hold"], "warn"), unsafe_allow_html=True)
    with fc3: st.markdown(fed_card("금리 인하", "📉", fed["cut"], "pos"), unsafe_allow_html=True)

    # ===== 5대 폭락 신호 모니터링 =====
    st.markdown("<div class='section-h' style='margin-top:32px;'>🚨 5대 폭락 신호 모니터링 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 글로벌 위기 신호 · 매주 월요일 갱신</span></div>", unsafe_allow_html=True)

    crash = get_crash_signals(macro)
    if crash:
        for sig in crash:
            border_color = "#991b1b" if sig["cls"] == "neg" else "#a16207" if sig["cls"] == "warn" else "#15803d"
            st.markdown(f"""<div class='card' style='padding:16px 22px; border-left:3px solid {border_color};'>
            <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;'>
            <div>
            <div style='font-size:13px; font-weight:700; color:#fafafa;'>{sig["name"]}</div>
            <div style='font-size:11px; color:#6b7280; margin-top:2px;'>{sig["desc"]}</div>
            </div>
            <div style='text-align:right;'>
            <div style='font-size:18px; font-weight:800; color:#fafafa; font-family:JetBrains Mono;'>{sig["value"]}</div>
            <div class='{sig["cls"]}' style='font-size:12px; font-weight:700;'>{sig["status"]}</div>
            </div>
            </div>
            <div style='color:#cbd5e1; font-size:12px; margin-top:6px; padding-top:6px; border-top:1px dashed #1c1f26;'>💡 {sig["msg"]}</div>
            </div>""", unsafe_allow_html=True)

    # ===== 과거 시나리오 매칭 =====
    stag_met = stag.get("met", 0) if stag else 0
    matches = match_historical_scenarios(mkt["score"], eco["inf_score"], eco["rec_score"], stag_met)
    current_state = get_current_macro_snapshot(macro)

    st.markdown("<div class='section-h' style='margin-top:32px;'>📜 과거 시나리오 매칭 <span style='color:#6b7280; font-weight:400; font-size:11px; margin-left:8px;'>· 가장 유사한 과거 사례 + 정밀 비교</span></div>", unsafe_allow_html=True)

    # TOP 1 자세히
    m = matches[0]
    border_color = "#991b1b" if m["risk"] == "neg" else "#a16207" if m["risk"] == "warn" else "#15803d"
    sim_color = "#4ade80" if m["similarity"] >= 70 else "#fbbf24" if m["similarity"] >= 50 else "#9ca3af"

    st.markdown(f"""<div class='card' style='padding:24px 28px; border-left:5px solid {border_color}; margin-bottom:16px;'>
    <div style='display:flex; justify-content:space-between; align-items:start; margin-bottom:14px; padding-bottom:14px; border-bottom:1px solid #1c1f26;'>
    <div>
    <div style='font-size:11px; color:#6b7280; letter-spacing:0.1em; font-weight:600;'>🥇 TOP MATCH · {m["year"]}</div>
    <div style='font-size:22px; font-weight:800; color:#fafafa; margin-top:4px;'>{m["name"]}</div>
    <div style='font-size:12px; color:#9ca3af; margin-top:4px;'>📌 {m["phase"]}</div>
    </div>
    <div style='text-align:right;'>
    <div style='font-size:32px; font-weight:800; color:{sim_color}; font-family:JetBrains Mono;'>{m["similarity"]:.0f}%</div>
    <div style='font-size:10px; color:#6b7280; letter-spacing:0.05em;'>유사도</div>
    </div>
    </div>
    <div style='padding:12px 16px; background:#0a0c12; border-radius:6px; margin-bottom:10px;'>
    <div style='font-size:11px; color:#9ca3af; margin-bottom:4px; font-weight:600;'>📉 당시 결과</div>
    <div style='font-size:13px; color:#cbd5e1; line-height:1.5;'>{m["what_happened"]}</div>
    </div>
    </div>""", unsafe_allow_html=True)

    # 5가지 비교 표
    st.markdown("<div style='font-size:13px; font-weight:700; color:#d1d5db; margin:18px 0 10px 0;'>🔍 그때 vs 지금 - 5가지 정밀 비교</div>", unsafe_allow_html=True)

    compare_items = [
        ("💵 금리 환경", "rates"),
        ("📈 주도 섹터 펀더멘털", "earnings"),
        ("👷 고용 · 성장 (실물)", "macro"),
        ("💧 유동성 · Fed 정책", "liquidity"),
        ("⚠️ 신용 스프레드", "credit"),
    ]

    for label, key in compare_items:
        past_v, past_desc = m["compare"][key]
        cur_v, cur_desc = current_state[key]
        st.markdown(f"""<div class='card' style='padding:14px 18px; margin-bottom:8px;'>
        <div style='font-size:12px; font-weight:700; color:#fafafa; margin-bottom:10px;'>{label}</div>
        <div style='display:grid; grid-template-columns:1fr 1fr; gap:14px;'>
        <div style='padding:10px 12px; background:#1a0e0e; border-radius:5px; border-left:2px solid #ef4444;'>
        <div style='font-size:10px; color:#f87171; font-weight:600; letter-spacing:0.08em; margin-bottom:4px;'>📅 {m["year"]} 당시</div>
        <div style='font-size:13px; color:#fafafa; font-weight:700; margin-bottom:4px; font-family:JetBrains Mono;'>{past_v}</div>
        <div style='font-size:11px; color:#9ca3af; line-height:1.5;'>{past_desc}</div>
        </div>
        <div style='padding:10px 12px; background:#0e1a13; border-radius:5px; border-left:2px solid #4ade80;'>
        <div style='font-size:10px; color:#4ade80; font-weight:600; letter-spacing:0.08em; margin-bottom:4px;'>📍 지금</div>
        <div style='font-size:13px; color:#fafafa; font-weight:700; margin-bottom:4px; font-family:JetBrains Mono;'>{cur_v}</div>
        <div style='font-size:11px; color:#9ca3af; line-height:1.5;'>{cur_desc}</div>
        </div>
        </div>
        </div>""", unsafe_allow_html=True)

    # 종합 결론
    st.markdown(f"""<div class='card' style='padding:18px 22px; border-left:3px solid {border_color}; margin-top:10px;'>
    <div style='font-size:11px; color:#9ca3af; font-weight:600; letter-spacing:0.05em; margin-bottom:8px;'>🎯 종합 판단 · 지금은 어느 시점</div>
    <div style='font-size:13px; color:#cbd5e1; line-height:1.7;'>{m["current_stage"]}</div>
    </div>""", unsafe_allow_html=True)

    # 2~3위 간단 표시
    st.markdown("<div style='font-size:11px; font-weight:600; color:#6b7280; letter-spacing:0.05em; margin:20px 0 8px 0;'>📊 다른 유사 시나리오</div>", unsafe_allow_html=True)
    other_cols = st.columns(2)
    for idx, m2 in enumerate(matches[1:3]):
        with other_cols[idx]:
            sim2_color = "#fbbf24" if m2["similarity"] >= 50 else "#9ca3af"
            st.markdown(f"""<div class='card' style='padding:12px 16px;'>
            <div style='display:flex; justify-content:space-between; align-items:center;'>
            <div>
            <div style='font-size:11px; color:#6b7280;'>{m2["year"]}</div>
            <div style='font-size:14px; font-weight:700; color:#d1d5db;'>{m2["name"]}</div>
            </div>
            <div style='text-align:right;'>
            <div style='font-size:18px; font-weight:800; color:{sim2_color}; font-family:JetBrains Mono;'>{m2["similarity"]:.0f}%</div>
            </div>
            </div>
            </div>""", unsafe_allow_html=True)

    st.caption("⚠️ 과거 사례는 참고용입니다. 시장 상황은 매번 다르며 100% 일치하지 않습니다.")

except Exception as e:
    st.error(f"오류: {e}")
    st.exception(e)
