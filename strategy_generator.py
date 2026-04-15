"""
Strategy Generator for IQ Option Trading Robot
================================================
Automatically searches for the best strategy by trying unlimited combinations
of indicators from multiple categories:
  - Trend (17 indicators)
  - Oscillator (14 indicators)
  - Volatility & Volume (10 indicators)
  - Level / Channel (7 indicators)
  - Advanced / Custom (12 indicators)
Total: 60 indicators

Periods are chosen RANDOMLY within sensible ranges on every iteration.
Runs an unlimited backtest loop until the user stops it.
"""

import random
import math
import logging
import time
from dataclasses import dataclass
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# INDICATOR MATH LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

def _sma(v, p):
    r = [None] * (p - 1)
    for i in range(p - 1, len(v)):
        r.append(sum(v[i - p + 1: i + 1]) / p)
    return r

def _ema(v, p):
    if len(v) < p:
        return [None] * len(v)
    r = [None] * (p - 1)
    sma = sum(v[:p]) / p
    r.append(sma)
    k = 2.0 / (p + 1)
    for x in v[p:]:
        r.append(r[-1] * (1 - k) + x * k)
    return r

def _wma(v, p):
    r = [None] * (p - 1)
    w = list(range(1, p + 1))
    d = sum(w)
    for i in range(p - 1, len(v)):
        r.append(sum(w[j] * v[i - p + 1 + j] for j in range(p)) / d)
    return r

def _rma(v, p):
    """Wilder's Smoothed MA (used in RSI, ATR)."""
    if len(v) < p:
        return [None] * len(v)
    r = [None] * (p - 1)
    r.append(sum(v[:p]) / p)
    alpha = 1.0 / p
    for x in v[p:]:
        r.append(r[-1] * (1 - alpha) + x * alpha)
    return r

def _hma(v, p):
    """Hull Moving Average = WMA(2*WMA(n/2) - WMA(n), sqrt(n))."""
    half = max(2, p // 2)
    sqr  = max(2, int(math.sqrt(p)))
    w1 = _wma(v, half)
    w2 = _wma(v, p)
    diff = []
    for a, b in zip(w1, w2):
        if a is None or b is None:
            diff.append(None)
        else:
            diff.append(2 * a - b)
    valid = [x for x in diff if x is not None]
    if len(valid) < sqr:
        return [None] * len(v)
    raw = _wma(valid, sqr)
    pad = len(v) - len(raw)
    return [None] * pad + raw

def _dema(v, p):
    e1 = _ema(v, p)
    val = [x for x in e1 if x is not None]
    if len(val) < p:
        return [None] * len(v)
    e2r = _ema(val, p)
    pad = len(v) - len(e2r)
    e2 = [None] * pad + e2r
    return [2 * a - b if (a is not None and b is not None) else None for a, b in zip(e1, e2)]

def _tema(v, p):
    e1 = _ema(v, p)
    v1 = [x for x in e1 if x is not None]
    if len(v1) < p:
        return [None] * len(v)
    e2r = _ema(v1, p)
    v2 = [x for x in e2r if x is not None]
    if len(v2) < p:
        return [None] * len(v)
    e3r = _ema(v2, p)
    n = len(e3r)
    pad1 = len(v) - n
    pad2 = len(v1) - n
    result = [None] * pad1
    for i in range(n):
        a = e1[pad1 + i]
        b = e2r[pad2 + i] if (pad2 + i) < len(e2r) else None
        c = e3r[i]
        result.append(3*a - 3*b + c if (a and b and c) else None)
    return result

def _zlema(v, p):
    """Zero-Lag EMA: EMA applied to (close + (close - close[lag]))."""
    lag = max(1, (p - 1) // 2)
    adjusted = []
    for i in range(len(v)):
        if i < lag:
            adjusted.append(v[i])
        else:
            adjusted.append(v[i] + (v[i] - v[i - lag]))
    return _ema(adjusted, p)

def _mcginley(v, p):
    """McGinley Dynamic: auto-adjusts to market speed."""
    r = [None] * (p - 1)
    r.append(v[p - 1])
    for i in range(p, len(v)):
        prev = r[-1]
        if prev is None or prev == 0:
            r.append(v[i])
        else:
            r.append(prev + (v[i] - prev) / (p * (v[i] / prev) ** 4))
    return r

def _rsi(c, p):
    if len(c) <= p:
        return [None] * len(c)
    r = [None] * p
    gains, losses = [], []
    for i in range(1, p + 1):
        d = c[i] - c[i-1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag, al = sum(gains)/p, sum(losses)/p
    r.append(100.0 if al == 0 else 100 - 100/(1 + ag/al))
    for i in range(p + 1, len(c)):
        d = c[i] - c[i-1]
        g, lo = max(d,0.0), max(-d,0.0)
        ag = (ag*(p-1)+g)/p
        al = (al*(p-1)+lo)/p
        r.append(100.0 if al == 0 else 100 - 100/(1 + ag/al))
    return r

def _macd(c, fast, slow, sig):
    ef = _ema(c, fast)
    es = _ema(c, slow)
    ml = [f - s if (f and s) else None for f, s in zip(ef, es)]
    val = [x for x in ml if x is not None]
    if len(val) < sig:
        return ml, [None]*len(ml), [None]*len(ml)
    sr = _ema(val, sig)
    pad = len(ml) - len(sr)
    sg = [None]*pad + sr
    hist = [m - s if (m is not None and s is not None) else None for m, s in zip(ml, sg)]
    return ml, sg, hist

def _stoch(hi, lo, c, kp, ks, ds):
    rk = []
    for i in range(len(c)):
        if i < kp - 1:
            rk.append(None); continue
        h = max(hi[i-kp+1:i+1])
        l = min(lo[i-kp+1:i+1])
        rk.append(50.0 if h == l else 100*(c[i]-l)/(h-l))
    sk = []
    for i in range(len(rk)):
        if i < kp + ks - 2:
            sk.append(None); continue
        w = [rk[j] for j in range(i-ks+1, i+1) if rk[j] is not None]
        sk.append(sum(w)/len(w) if w else None)
    sd = []
    for i in range(len(sk)):
        if i < kp + ks + ds - 3:
            sd.append(None); continue
        w = [sk[j] for j in range(i-ds+1, i+1) if sk[j] is not None]
        sd.append(sum(w)/len(w) if w else None)
    return sk, sd

def _cci(hi, lo, c, p):
    r = [None] * (p - 1)
    for i in range(p-1, len(c)):
        tp = [(hi[j]+lo[j]+c[j])/3 for j in range(i-p+1, i+1)]
        mean = sum(tp)/p
        mad  = sum(abs(x-mean) for x in tp)/p
        r.append((tp[-1]-mean)/(0.015*mad) if mad else 0.0)
    return r

def _williams_r(hi, lo, c, p):
    r = [None]*(p-1)
    for i in range(p-1, len(c)):
        h = max(hi[i-p+1:i+1])
        l = min(lo[i-p+1:i+1])
        r.append(-100*(h-c[i])/(h-l) if h != l else -50.0)
    return r

def _roc(c, p):
    r = [None]*p
    for i in range(p, len(c)):
        r.append((c[i]-c[i-p])/c[i-p]*100 if c[i-p] != 0 else 0.0)
    return r

def _mfi(hi, lo, c, vol, p):
    tp = [(hi[i]+lo[i]+c[i])/3 for i in range(len(c))]
    mf = [tp[i]*vol[i] for i in range(len(c))]
    r = [None]*p
    for i in range(p, len(c)):
        pos = sum(mf[j] for j in range(i-p+1, i+1) if tp[j] >= tp[j-1])
        neg = sum(mf[j] for j in range(i-p+1, i+1) if tp[j] < tp[j-1])
        r.append(100.0 if neg == 0 else 100 - 100/(1+pos/neg))
    return r

def _trix(c, p):
    """TRIX: 1-period percent change of triple-smoothed EMA."""
    e1 = _ema(c, p)
    v1 = [x for x in e1 if x is not None]
    if len(v1) < p: return [None]*len(c)
    e2r = _ema(v1, p)
    v2 = [x for x in e2r if x is not None]
    if len(v2) < p: return [None]*len(c)
    e3r = _ema(v2, p)
    n = len(e3r)
    pad = len(c) - n
    result = [None]*pad
    prev = None
    for x in e3r:
        if prev is None or prev == 0:
            result.append(0.0)
        else:
            result.append((x - prev)/prev*100)
        prev = x
    return result

def _demarker(hi, lo, c, p):
    """DeMarker oscillator."""
    dm_hi = [max(hi[i] - hi[i-1], 0) if i > 0 else 0 for i in range(len(c))]
    dm_lo = [max(lo[i-1] - lo[i], 0) if i > 0 else 0 for i in range(len(c))]
    sma_hi = _sma(dm_hi, p)
    sma_lo = _sma(dm_lo, p)
    r = []
    for h, l in zip(sma_hi, sma_lo):
        if h is None or l is None:
            r.append(None)
        elif h + l == 0:
            r.append(0.5)
        else:
            r.append(h / (h + l))
    return r

def _ultimate_osc(hi, lo, c, p1, p2, p3):
    """Ultimate Oscillator."""
    bp = []; tr = []
    for i in range(1, len(c)):
        lc = lo[i]
        pc = c[i-1]
        tl = min(lc, pc)
        bp.append(c[i] - tl)
        tr.append(max(hi[i], pc) - min(lc, pc))
    r = [None]*max(p1, p2, p3)
    for i in range(max(p1, p2, p3) - 1, len(bp)):
        def ratio(p):
            s_bp = sum(bp[i-p+1:i+1])
            s_tr = sum(tr[i-p+1:i+1])
            return s_bp/s_tr if s_tr else 0
        r.append(100*(4*ratio(p1) + 2*ratio(p2) + ratio(p3))/7)
    return [None] + r

def _awesome_osc(hi, lo):
    """Awesome Oscillator: SMA5 - SMA34 of midpoints."""
    mid = [(hi[i]+lo[i])/2 for i in range(len(hi))]
    s5  = _sma(mid, 5)
    s34 = _sma(mid, 34)
    return [a - b if (a and b) else None for a, b in zip(s5, s34)]

def _elder_ray(c, p):
    """Elder Ray Bull/Bear Power."""
    ma = _ema(c, p)
    bull = [c[i] - ma[i] if ma[i] is not None else None for i in range(len(c))]
    bear = [c[i] - ma[i] if ma[i] is not None else None for i in range(len(c))]
    return bull, bear

def _fisher(hi, lo, p):
    """Fisher Transform."""
    r = [None]*(p-1)
    prev = 0.0
    for i in range(p-1, len(hi)):
        h = max(hi[i-p+1:i+1])
        l = min(lo[i-p+1:i+1])
        val = 2*(hi[i] - l)/(h - l) - 1 if h != l else 0
        val = max(-0.999, min(0.999, val))
        fish = 0.5*math.log((1+val)/(1-val)) + 0.5*prev
        r.append(fish)
        prev = fish
    return r

def _vortex(hi, lo, c, p):
    """Vortex Indicator +VI and -VI."""
    vm_plus  = [abs(hi[i] - lo[i-1]) if i > 0 else 0 for i in range(len(c))]
    vm_minus = [abs(lo[i] - hi[i-1]) if i > 0 else 0 for i in range(len(c))]
    tr = [0.0]
    for i in range(1, len(c)):
        tr.append(max(hi[i]-lo[i], abs(hi[i]-c[i-1]), abs(lo[i]-c[i-1])))
    vi_plus  = [None]*(p-1)
    vi_minus = [None]*(p-1)
    for i in range(p-1, len(c)):
        s_tr = sum(tr[i-p+1:i+1])
        vi_plus.append(sum(vm_plus[i-p+1:i+1])/s_tr if s_tr else None)
        vi_minus.append(sum(vm_minus[i-p+1:i+1])/s_tr if s_tr else None)
    return vi_plus, vi_minus

def _tsi(c, r_p, s_p):
    """True Strength Index."""
    mom = [0.0] + [c[i] - c[i-1] for i in range(1, len(c))]
    abs_mom = [abs(x) for x in mom]
    # double smooth momentum and |momentum|
    def dsmooth(v, p1, p2):
        e1 = _ema(v, p1)
        valid = [x for x in e1 if x is not None]
        if not valid: return [None]*len(v)
        e2r = _ema(valid, p2)
        pad = len(v) - len(e2r)
        return [None]*pad + e2r
    ds_mom = dsmooth(mom, r_p, s_p)
    ds_abs = dsmooth(abs_mom, r_p, s_p)
    return [100*m/a if (m is not None and a) else None for m, a in zip(ds_mom, ds_abs)]

def _bollinger(c, p, m=2.0):
    mid = _sma(c, p)
    upper, lower = [], []
    for i in range(len(c)):
        if mid[i] is None:
            upper.append(None); lower.append(None); continue
        w = c[i-p+1:i+1]
        mean = mid[i]
        std = math.sqrt(sum((x-mean)**2 for x in w)/p)
        upper.append(mean + m*std)
        lower.append(mean - m*std)
    return upper, mid, lower

def _keltner(hi, lo, c, p, mult=2.0):
    """Keltner Channel: EMA ± mult×ATR."""
    ema_c = _ema(c, p)
    atr   = _atr(hi, lo, c, p)
    upper = [e + mult*a if (e and a) else None for e, a in zip(ema_c, atr)]
    lower = [e - mult*a if (e and a) else None for e, a in zip(ema_c, atr)]
    return upper, ema_c, lower

def _atr(hi, lo, c, p):
    tr = [None] + [max(hi[i]-lo[i], abs(hi[i]-c[i-1]), abs(lo[i]-c[i-1])) for i in range(1, len(c))]
    valid = [x for x in tr[1:] if x is not None]
    if len(valid) < p: return [None]*len(c)
    r = [None]*p
    av = sum(valid[:p])/p
    r.append(av)
    for v in valid[p:]:
        av = (av*(p-1)+v)/p
        r.append(av)
    return r

def _natr(hi, lo, c, p):
    """Normalised ATR = ATR/Close × 100."""
    atr = _atr(hi, lo, c, p)
    return [a/c[i]*100 if (a and c[i]) else None for i, a in enumerate(atr)]

def _adx(hi, lo, c, p):
    dm_p = [None] + [max(hi[i]-hi[i-1], 0) if hi[i]-hi[i-1] > lo[i-1]-lo[i] else 0 for i in range(1, len(c))]
    dm_m = [None] + [max(lo[i-1]-lo[i], 0) if lo[i-1]-lo[i] > hi[i]-hi[i-1] else 0 for i in range(1, len(c))]
    atr  = _atr(hi, lo, c, p)
    di_p = [100*dp/at if (dp is not None and at) else None for dp, at in zip(_rma([x if x else 0 for x in dm_p], p), atr)]
    di_m = [100*dm/at if (dm is not None and at) else None for dm, at in zip(_rma([x if x else 0 for x in dm_m], p), atr)]
    dx_vals = [abs(dp-dm)/(dp+dm)*100 if (dp and dm and dp+dm) else None for dp, dm in zip(di_p, di_m)]
    valid_dx = [x for x in dx_vals if x is not None]
    if len(valid_dx) < p: return [None]*len(c), di_p, di_m
    adx_r = _rma(valid_dx, p)
    pad = len(c) - len(adx_r)
    return [None]*pad + adx_r, di_p, di_m

def _chaikin_mf(hi, lo, c, vol, p):
    """Chaikin Money Flow."""
    mfm = [(c[i]-lo[i]-(hi[i]-c[i]))/(hi[i]-lo[i]) if hi[i] != lo[i] else 0 for i in range(len(c))]
    mfv = [m*v for m, v in zip(mfm, vol)]
    r = [None]*(p-1)
    for i in range(p-1, len(c)):
        sv = sum(vol[i-p+1:i+1])
        r.append(sum(mfv[i-p+1:i+1])/sv if sv else 0.0)
    return r

def _obv(c, vol):
    r = [0.0]
    for i in range(1, len(c)):
        if c[i] > c[i-1]: r.append(r[-1]+vol[i])
        elif c[i] < c[i-1]: r.append(r[-1]-vol[i])
        else: r.append(r[-1])
    return r

def _choppiness(hi, lo, c, p):
    """Choppiness Index — 100=chop, 0=trending."""
    atr1 = [max(hi[i]-lo[i], abs(hi[i]-c[i-1]) if i>0 else 0, abs(lo[i]-c[i-1]) if i>0 else 0) for i in range(len(c))]
    r = [None]*(p-1)
    for i in range(p-1, len(c)):
        tr_sum = sum(atr1[i-p+1:i+1])
        range_hl = max(hi[i-p+1:i+1]) - min(lo[i-p+1:i+1])
        if range_hl and tr_sum:
            r.append(100*math.log10(tr_sum/range_hl)/math.log10(p))
        else:
            r.append(None)
    return r

def _stdev(c, p):
    r = [None]*(p-1)
    for i in range(p-1, len(c)):
        w = c[i-p+1:i+1]
        mean = sum(w)/p
        r.append(math.sqrt(sum((x-mean)**2 for x in w)/p))
    return r

def _donchian(hi, lo, p):
    upper = [None]*(p-1)
    lower = [None]*(p-1)
    for i in range(p-1, len(hi)):
        upper.append(max(hi[i-p+1:i+1]))
        lower.append(min(lo[i-p+1:i+1]))
    return upper, lower

def _parabolic_sar(hi, lo, c, af0=0.02, af_step=0.02, af_max=0.2):
    sar = [None]*len(c)
    if len(c) < 2: return sar
    bull = c[1] > c[0]
    ep   = hi[1] if bull else lo[1]
    af   = af0
    sar[1] = lo[0] if bull else hi[0]
    for i in range(2, len(c)):
        p = sar[i-1]
        if bull:
            ns = p + af*(ep-p)
            ns = min(ns, lo[i-1], lo[i-2] if i > 2 else lo[i-1])
            if lo[i] < ns: bull, ns, ep, af = False, ep, lo[i], af0
            else:
                if hi[i] > ep: ep = hi[i]; af = min(af+af_step, af_max)
        else:
            ns = p + af*(ep-p)
            ns = max(ns, hi[i-1], hi[i-2] if i > 2 else hi[i-1])
            if hi[i] > ns: bull, ns, ep, af = True, ep, hi[i], af0
            else:
                if lo[i] < ep: ep = lo[i]; af = min(af+af_step, af_max)
        sar[i] = ns
    return sar

def _supertrend(hi, lo, c, p, mult):
    """Supertrend indicator."""
    atr = _atr(hi, lo, c, p)
    upper_band = [(hi[i]+lo[i])/2 + mult*atr[i] if atr[i] else None for i in range(len(c))]
    lower_band = [(hi[i]+lo[i])/2 - mult*atr[i] if atr[i] else None for i in range(len(c))]
    trend = [None]*len(c)
    direction = [None]*len(c)
    for i in range(1, len(c)):
        if lower_band[i] is None or upper_band[i] is None: continue
        lb = lower_band[i]
        ub = upper_band[i]
        # adjust bands
        if lower_band[i-1] is not None and lb < lower_band[i-1]:
            lb = lower_band[i-1]
        if upper_band[i-1] is not None and ub > upper_band[i-1]:
            ub = upper_band[i-1]
        lower_band[i] = lb
        upper_band[i] = ub
        if direction[i-1] is None:
            direction[i] = 1 if c[i] <= ub else -1
        elif direction[i-1] == 1:
            direction[i] = -1 if c[i] > ub else 1
        else:
            direction[i] = 1 if c[i] < lb else -1
        trend[i] = lb if direction[i] == -1 else ub
    return trend, direction

def _ichimoku(hi, lo, tenkan_p, kijun_p):
    """Ichimoku — returns (tenkan, kijun, above_cloud)."""
    def _midpoint(h, l, p, i):
        if i < p-1: return None
        return (max(h[i-p+1:i+1]) + min(l[i-p+1:i+1])) / 2
    tenkan = [_midpoint(hi, lo, tenkan_p, i) for i in range(len(hi))]
    kijun  = [_midpoint(hi, lo, kijun_p,  i) for i in range(len(hi))]
    return tenkan, kijun

def _squeeze(hi, lo, c, p, boll_m=2.0, kelt_m=1.5):
    """Squeeze Momentum: True when BB is inside KC (low volatility)."""
    bbu, _, bbl = _bollinger(c, p, boll_m)
    kcu, _, kcl = _keltner(hi, lo, c, p, kelt_m)
    squeeze = []
    for bu, bl, ku, kl in zip(bbu, bbl, kcu, kcl):
        if any(x is None for x in [bu, bl, ku, kl]):
            squeeze.append(None)
        else:
            squeeze.append(bu < ku and bl > kl)
    # Delta close from mid of keltner for momentum direction
    momentum = []
    for i in range(len(c)):
        ku, kl = kcu[i], kcl[i]
        if ku is None or kl is None: momentum.append(None); continue
        momentum.append(c[i] - (ku+kl)/2)
    return squeeze, momentum

def _pivot_points(hi, lo, c):
    """Classic Pivot Points based on previous bar."""
    pivots = [None]
    for i in range(1, len(c)):
        pp = (hi[i-1]+lo[i-1]+c[i-1])/3
        pivots.append(pp)
    return pivots

def _williams_fractal(hi, lo, p=2):
    """Detect fractal highs and lows (p bars each side)."""
    bull_frac = [False]*len(hi)
    bear_frac = [False]*len(hi)
    for i in range(p, len(hi)-p):
        if all(lo[i] < lo[i-j] and lo[i] < lo[i+j] for j in range(1, p+1)):
            bull_frac[i] = True
        if all(hi[i] > hi[i-j] and hi[i] > hi[i+j] for j in range(1, p+1)):
            bear_frac[i] = True
    return bull_frac, bear_frac


# ══════════════════════════════════════════════════════════════════════════════
# INDICATOR CATALOG  (60 indicators)
# ══════════════════════════════════════════════════════════════════════════════

INDICATOR_CATALOG = {
    # ── Trend (17) ──────────────────────────────────────────────────────────
    'SMA': {
        'category': 'Trend',
        'label': 'Simple MA (SMA)',
        'params': {'period': (5, 200)},
        'defaults': {'period': 20},
    },
    'EMA': {
        'category': 'Trend',
        'label': 'Exponential MA (EMA)',
        'params': {'period': (3, 200)},
        'defaults': {'period': 14},
    },
    'WMA': {
        'category': 'Trend',
        'label': 'Weighted MA (WMA)',
        'params': {'period': (5, 100)},
        'defaults': {'period': 14},
    },
    'HMA': {
        'category': 'Trend',
        'label': 'Hull MA (HMA)',
        'params': {'period': (9, 55)},
        'defaults': {'period': 16},
    },
    'DEMA': {
        'category': 'Trend',
        'label': 'Double EMA (DEMA)',
        'params': {'period': (5, 55)},
        'defaults': {'period': 14},
    },
    'TEMA': {
        'category': 'Trend',
        'label': 'Triple EMA (TEMA)',
        'params': {'period': (3, 30)},
        'defaults': {'period': 9},
    },
    'ZLEMA': {
        'category': 'Trend',
        'label': 'Zero-Lag EMA (ZLEMA)',
        'params': {'period': (5, 50)},
        'defaults': {'period': 14},
    },
    'MCGINLEY': {
        'category': 'Trend',
        'label': 'McGinley Dynamic',
        'params': {'period': (10, 40)},
        'defaults': {'period': 14},
    },
    'EMA_CROSS': {
        'category': 'Trend',
        'label': 'EMA Crossover (Fast/Slow)',
        'params': {'fast': (3, 30), 'slow': (10, 100)},
        'defaults': {'fast': 8, 'slow': 21},
    },
    'SMA_CROSS': {
        'category': 'Trend',
        'label': 'SMA Crossover (Fast/Slow)',
        'params': {'fast': (5, 50), 'slow': (20, 200)},
        'defaults': {'fast': 20, 'slow': 50},
    },
    'HMA_CROSS': {
        'category': 'Trend',
        'label': 'HMA Crossover (Fast/Slow)',
        'params': {'fast': (9, 30), 'slow': (20, 80)},
        'defaults': {'fast': 16, 'slow': 32},
    },
    'TRIPLE_EMA': {
        'category': 'Trend',
        'label': 'Triple EMA Alignment',
        'params': {'fast': (3, 15), 'mid': (8, 30), 'slow': (20, 100)},
        'defaults': {'fast': 3, 'mid': 8, 'slow': 50},
    },
    'ICHIMOKU': {
        'category': 'Trend',
        'label': 'Ichimoku (Tenkan/Kijun)',
        'params': {'tenkan': (5, 13), 'kijun': (16, 52)},
        'defaults': {'tenkan': 9, 'kijun': 26},
    },
    'PARABOLIC_SAR': {
        'category': 'Trend',
        'label': 'Parabolic SAR',
        'params': {},
        'defaults': {},
    },
    'SUPERTREND': {
        'category': 'Trend',
        'label': 'Supertrend',
        'params': {'period': (7, 21), 'mult': (15, 40)},  # mult stored ×10
        'defaults': {'period': 10, 'mult': 30},
    },
    'EMA_BOUNCE': {
        'category': 'Trend',
        'label': 'EMA Bounce',
        'params': {'period': (5, 55)},
        'defaults': {'period': 8},
    },
    'MA_RIBBON': {
        'category': 'Trend',
        'label': 'MA Ribbon (5/10/20/50)',
        'params': {},
        'defaults': {},
    },

    # ── Oscillator (14) ─────────────────────────────────────────────────────
    'RSI': {
        'category': 'Oscillator',
        'label': 'RSI',
        'params': {'period': (2, 21)},
        'defaults': {'period': 7},
    },
    'MACD': {
        'category': 'Oscillator',
        'label': 'MACD',
        'params': {'fast': (5, 20), 'slow': (10, 40), 'signal': (3, 12)},
        'defaults': {'fast': 12, 'slow': 26, 'signal': 9},
    },
    'STOCH': {
        'category': 'Oscillator',
        'label': 'Stochastic %K/%D',
        'params': {'k_period': (5, 21), 'k_smooth': (2, 5), 'd_smooth': (2, 5)},
        'defaults': {'k_period': 14, 'k_smooth': 3, 'd_smooth': 3},
    },
    'CCI': {
        'category': 'Oscillator',
        'label': 'CCI',
        'params': {'period': (5, 30)},
        'defaults': {'period': 14},
    },
    'WILLIAMS_R': {
        'category': 'Oscillator',
        'label': "Williams %R",
        'params': {'period': (5, 21)},
        'defaults': {'period': 14},
    },
    'ROC': {
        'category': 'Oscillator',
        'label': 'Rate of Change (ROC)',
        'params': {'period': (3, 20)},
        'defaults': {'period': 10},
    },
    'TRIX': {
        'category': 'Oscillator',
        'label': 'TRIX',
        'params': {'period': (5, 21)},
        'defaults': {'period': 14},
    },
    'DEMARKER': {
        'category': 'Oscillator',
        'label': 'DeMarker',
        'params': {'period': (5, 21)},
        'defaults': {'period': 14},
    },
    'ULTIMATE_OSC': {
        'category': 'Oscillator',
        'label': 'Ultimate Oscillator',
        'params': {'p1': (3, 10), 'p2': (7, 20), 'p3': (14, 40)},
        'defaults': {'p1': 7, 'p2': 14, 'p3': 28},
    },
    'AWESOME_OSC': {
        'category': 'Oscillator',
        'label': 'Awesome Oscillator',
        'params': {},
        'defaults': {},
    },
    'ELDER_RAY': {
        'category': 'Oscillator',
        'label': 'Elder Ray (Bull/Bear Power)',
        'params': {'period': (5, 21)},
        'defaults': {'period': 13},
    },
    'FISHER': {
        'category': 'Oscillator',
        'label': 'Fisher Transform',
        'params': {'period': (5, 21)},
        'defaults': {'period': 10},
    },
    'TSI': {
        'category': 'Oscillator',
        'label': 'True Strength Index (TSI)',
        'params': {'r_period': (10, 30), 's_period': (3, 13)},
        'defaults': {'r_period': 25, 's_period': 13},
    },
    'VORTEX': {
        'category': 'Oscillator',
        'label': 'Vortex Indicator (+VI/-VI)',
        'params': {'period': (7, 21)},
        'defaults': {'period': 14},
    },

    # ── Volatility & Volume (10) ─────────────────────────────────────────────
    'BOLLINGER': {
        'category': 'Volatility & Volume',
        'label': 'Bollinger Bands',
        'params': {'period': (10, 30)},
        'defaults': {'period': 20},
    },
    'ATR': {
        'category': 'Volatility & Volume',
        'label': 'ATR Filter',
        'params': {'period': (5, 21)},
        'defaults': {'period': 14},
    },
    'NATR': {
        'category': 'Volatility & Volume',
        'label': 'Normalised ATR (NATR)',
        'params': {'period': (5, 21)},
        'defaults': {'period': 14},
    },
    'KELTNER': {
        'category': 'Volatility & Volume',
        'label': 'Keltner Channel',
        'params': {'period': (10, 30)},
        'defaults': {'period': 20},
    },
    'SQUEEZE': {
        'category': 'Volatility & Volume',
        'label': 'Squeeze Momentum (BB+KC)',
        'params': {'period': (10, 30)},
        'defaults': {'period': 20},
    },
    'STDEV': {
        'category': 'Volatility & Volume',
        'label': 'Standard Deviation',
        'params': {'period': (5, 30)},
        'defaults': {'period': 14},
    },
    'CHOPPINESS': {
        'category': 'Volatility & Volume',
        'label': 'Choppiness Index',
        'params': {'period': (8, 30)},
        'defaults': {'period': 14},
    },
    'MFI': {
        'category': 'Volatility & Volume',
        'label': 'Money Flow Index (MFI)',
        'params': {'period': (5, 20)},
        'defaults': {'period': 14},
    },
    'CHAIKIN_MF': {
        'category': 'Volatility & Volume',
        'label': 'Chaikin Money Flow (CMF)',
        'params': {'period': (5, 21)},
        'defaults': {'period': 20},
    },
    'OBV': {
        'category': 'Volatility & Volume',
        'label': 'On-Balance Volume (OBV)',
        'params': {'period': (3, 20)},
        'defaults': {'period': 10},
    },

    # ── Level / Channel (7) ──────────────────────────────────────────────────
    'DONCHIAN': {
        'category': 'Level / Channel',
        'label': 'Donchian Channel',
        'params': {'period': (10, 55)},
        'defaults': {'period': 20},
    },
    'SUPPORT_RESISTANCE': {
        'category': 'Level / Channel',
        'label': 'Support / Resistance Break',
        'params': {'lookback': (5, 30)},
        'defaults': {'lookback': 10},
    },
    'PIVOT': {
        'category': 'Level / Channel',
        'label': 'Pivot Point Cross',
        'params': {},
        'defaults': {},
    },
    'FRACTAL': {
        'category': 'Level / Channel',
        'label': 'Williams Fractal',
        'params': {'bars': (2, 5)},
        'defaults': {'bars': 2},
    },
    'PRICE_CHANNEL': {
        'category': 'Level / Channel',
        'label': 'Price Channel Break',
        'params': {'period': (5, 30)},
        'defaults': {'period': 14},
    },
    'FIBONACCI': {
        'category': 'Level / Channel',
        'label': 'Fibonacci Retracement',
        'params': {'lookback': (10, 50)},
        'defaults': {'lookback': 20},
    },
    'KELTNER_BREAK': {
        'category': 'Level / Channel',
        'label': 'Keltner Channel Breakout',
        'params': {'period': (10, 30)},
        'defaults': {'period': 20},
    },

    # ── Advanced / Custom (12) ───────────────────────────────────────────────
    'ADX': {
        'category': 'Advanced / Custom',
        'label': 'ADX Trend Strength',
        'params': {'period': (7, 21), 'threshold': (20, 35)},
        'defaults': {'period': 14, 'threshold': 25},
    },
    'STOCH_RSI': {
        'category': 'Advanced / Custom',
        'label': 'Stoch + RSI Confluence',
        'params': {'rsi_period': (5, 14), 'stoch_k': (5, 21)},
        'defaults': {'rsi_period': 7, 'stoch_k': 14},
    },
    'MACD_RSI': {
        'category': 'Advanced / Custom',
        'label': 'MACD + RSI Confluence',
        'params': {'rsi_period': (5, 14), 'macd_fast': (8, 16), 'macd_slow': (18, 30)},
        'defaults': {'rsi_period': 7, 'macd_fast': 12, 'macd_slow': 26},
    },
    'TRIPLE_EMA_STOCH': {
        'category': 'Advanced / Custom',
        'label': 'Triple EMA + Stochastic',
        'params': {'fast': (3, 10), 'mid': (8, 20), 'slow': (20, 60), 'stoch_k': (5, 14)},
        'defaults': {'fast': 3, 'mid': 8, 'slow': 50, 'stoch_k': 14},
    },
    'MULTI_EMA_MOMENTUM': {
        'category': 'Advanced / Custom',
        'label': 'Multi-EMA + Momentum',
        'params': {'fast': (3, 15), 'slow': (10, 50), 'rsi_p': (5, 14)},
        'defaults': {'fast': 5, 'slow': 20, 'rsi_p': 7},
    },
    'SQUEEZE_BREAKOUT': {
        'category': 'Advanced / Custom',
        'label': 'Squeeze + RSI Breakout',
        'params': {'period': (10, 30), 'rsi_p': (5, 14)},
        'defaults': {'period': 20, 'rsi_p': 7},
    },
    'SUPERTREND_RSI': {
        'category': 'Advanced / Custom',
        'label': 'Supertrend + RSI',
        'params': {'st_period': (7, 21), 'st_mult': (15, 40), 'rsi_p': (5, 14)},
        'defaults': {'st_period': 10, 'st_mult': 30, 'rsi_p': 7},
    },
    'ADX_MACD': {
        'category': 'Advanced / Custom',
        'label': 'ADX Filter + MACD',
        'params': {'adx_p': (7, 21), 'adx_th': (20, 35), 'macd_fast': (8, 16), 'macd_slow': (18, 30)},
        'defaults': {'adx_p': 14, 'adx_th': 25, 'macd_fast': 12, 'macd_slow': 26},
    },
    'ICHIMOKU_RSI': {
        'category': 'Advanced / Custom',
        'label': 'Ichimoku + RSI',
        'params': {'tenkan': (5, 13), 'kijun': (16, 52), 'rsi_p': (5, 14)},
        'defaults': {'tenkan': 9, 'kijun': 26, 'rsi_p': 7},
    },
    'BOLLINGER_RSI': {
        'category': 'Advanced / Custom',
        'label': 'Bollinger + RSI Reversal',
        'params': {'bb_period': (10, 30), 'rsi_period': (5, 14)},
        'defaults': {'bb_period': 20, 'rsi_period': 7},
    },
    'VORTEX_ADX': {
        'category': 'Advanced / Custom',
        'label': 'Vortex + ADX Trend',
        'params': {'period': (7, 21), 'adx_th': (20, 30)},
        'defaults': {'period': 14, 'adx_th': 25},
    },
    'CANDLE_PATTERN': {
        'category': 'Advanced / Custom',
        'label': 'Candlestick Patterns',
        'params': {},
        'defaults': {},
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# SIGNAL FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _trend_ma_signal(c, ma, i):
    """Price above/below MA with crossover bias."""
    if ma[i] is None or ma[i-1] is None: return 0
    if c[i] > ma[i]: return 1
    if c[i] < ma[i]: return -1
    return 0

def _cross_signal(fast, slow, i):
    if any(v is None for v in [fast[i], slow[i]]): return 0
    if fast[i] > slow[i]: return 1
    if fast[i] < slow[i]: return -1
    return 0

def get_signal_at(i, indicator_id, params, D):
    """Return +1 (CALL), -1 (PUT), 0 (neutral)."""
    c, hi, lo, vol = D['closes'], D['highs'], D['lows'], D['volumes']
    opens = D['opens']

    # ── Trend ────────────────────────────────────────────────────────────────
    if indicator_id == 'SMA':
        return _trend_ma_signal(c, _sma(c, params['period']), i)

    if indicator_id == 'EMA':
        return _trend_ma_signal(c, _ema(c, params['period']), i)

    if indicator_id == 'WMA':
        return _trend_ma_signal(c, _wma(c, params['period']), i)

    if indicator_id == 'HMA':
        return _trend_ma_signal(c, _hma(c, params['period']), i)

    if indicator_id == 'DEMA':
        return _trend_ma_signal(c, _dema(c, params['period']), i)

    if indicator_id == 'TEMA':
        return _trend_ma_signal(c, _tema(c, params['period']), i)

    if indicator_id == 'ZLEMA':
        return _trend_ma_signal(c, _zlema(c, params['period']), i)

    if indicator_id == 'MCGINLEY':
        return _trend_ma_signal(c, _mcginley(c, params['period']), i)

    if indicator_id == 'EMA_CROSS':
        return _cross_signal(_ema(c, params['fast']), _ema(c, params['slow']), i)

    if indicator_id == 'SMA_CROSS':
        return _cross_signal(_sma(c, params['fast']), _sma(c, params['slow']), i)

    if indicator_id == 'HMA_CROSS':
        return _cross_signal(_hma(c, params['fast']), _hma(c, params['slow']), i)

    if indicator_id == 'TRIPLE_EMA':
        e1 = _ema(c, params['fast'])
        e2 = _ema(c, params['mid'])
        e3 = _ema(c, params['slow'])
        if any(v is None for v in [e1[i], e2[i], e3[i]]): return 0
        if e1[i] > e2[i] > e3[i]: return 1
        if e1[i] < e2[i] < e3[i]: return -1
        return 0

    if indicator_id == 'ICHIMOKU':
        ten, kij = _ichimoku(hi, lo, params['tenkan'], params['kijun'])
        if ten[i] is None or kij[i] is None: return 0
        if ten[i] > kij[i] and c[i] > kij[i]: return 1
        if ten[i] < kij[i] and c[i] < kij[i]: return -1
        return 0

    if indicator_id == 'PARABOLIC_SAR':
        sar = _parabolic_sar(hi, lo, c)
        if sar[i] is None: return 0
        return 1 if c[i] > sar[i] else -1

    if indicator_id == 'SUPERTREND':
        _, direction = _supertrend(hi, lo, c, params['period'], params['mult']/10.0)
        if direction[i] is None: return 0
        return -direction[i]  # direction=-1 means above supertrend → CALL

    if indicator_id == 'EMA_BOUNCE':
        ma = _ema(c, params['period'])
        if ma[i] is None or ma[i-1] is None: return 0
        tol = 0.0008
        if c[i-1] <= ma[i-1]*(1+tol) and c[i] > ma[i]: return 1
        if c[i-1] >= ma[i-1]*(1-tol) and c[i] < ma[i]: return -1
        return 0

    if indicator_id == 'MA_RIBBON':
        e5  = _ema(c, 5)
        e10 = _ema(c, 10)
        e20 = _ema(c, 20)
        e50 = _ema(c, 50)
        if any(v is None for v in [e5[i], e10[i], e20[i], e50[i]]): return 0
        if e5[i] > e10[i] > e20[i] > e50[i]: return 1
        if e5[i] < e10[i] < e20[i] < e50[i]: return -1
        return 0

    # ── Oscillator ───────────────────────────────────────────────────────────
    if indicator_id == 'RSI':
        r = _rsi(c, params['period'])
        if r[i] is None: return 0
        if r[i] < 35: return 1
        if r[i] > 65: return -1
        return 0

    if indicator_id == 'MACD':
        _, _, hist = _macd(c, params['fast'], params['slow'], params['signal'])
        if hist[i] is None or hist[i-1] is None: return 0
        if hist[i] > 0: return 1
        if hist[i] < 0: return -1
        return 0

    if indicator_id == 'STOCH':
        sk, sd = _stoch(hi, lo, c, params['k_period'], params['k_smooth'], params['d_smooth'])
        if sk[i] is None or sd[i] is None: return 0
        if sk[i] > sd[i] and sk[i] < 80: return 1
        if sk[i] < sd[i] and sk[i] > 20: return -1
        return 0

    if indicator_id == 'CCI':
        v = _cci(hi, lo, c, params['period'])
        if v[i] is None: return 0
        if v[i] > 100: return 1
        if v[i] < -100: return -1
        return 0

    if indicator_id == 'WILLIAMS_R':
        v = _williams_r(hi, lo, c, params['period'])
        if v[i] is None: return 0
        if v[i] < -80: return 1
        if v[i] > -20: return -1
        return 0

    if indicator_id == 'ROC':
        v = _roc(c, params['period'])
        if v[i] is None: return 0
        return 1 if v[i] > 0 else (-1 if v[i] < 0 else 0)

    if indicator_id == 'TRIX':
        v = _trix(c, params['period'])
        if v[i] is None or v[i-1] is None: return 0
        if v[i] > 0 and v[i] > v[i-1]: return 1
        if v[i] < 0 and v[i] < v[i-1]: return -1
        return 0

    if indicator_id == 'DEMARKER':
        v = _demarker(hi, lo, c, params['period'])
        if v[i] is None: return 0
        if v[i] < 0.3: return 1
        if v[i] > 0.7: return -1
        return 0

    if indicator_id == 'ULTIMATE_OSC':
        v = _ultimate_osc(hi, lo, c, params['p1'], params['p2'], params['p3'])
        if v[i] is None: return 0
        if v[i] > 70: return 1
        if v[i] < 30: return -1
        return 0

    if indicator_id == 'AWESOME_OSC':
        v = _awesome_osc(hi, lo)
        if v[i] is None or v[i-1] is None: return 0
        if v[i] > 0 and v[i] > v[i-1]: return 1
        if v[i] < 0 and v[i] < v[i-1]: return -1
        return 0

    if indicator_id == 'ELDER_RAY':
        bull, bear = _elder_ray(c, params['period'])
        if bull[i] is None: return 0
        if bull[i] > 0 and bear[i] > 0: return 1
        if bull[i] < 0 and bear[i] < 0: return -1
        return 0

    if indicator_id == 'FISHER':
        v = _fisher(hi, lo, params['period'])
        if v[i] is None or v[i-1] is None: return 0
        if v[i] > 0 and v[i] > v[i-1]: return 1
        if v[i] < 0 and v[i] < v[i-1]: return -1
        return 0

    if indicator_id == 'TSI':
        v = _tsi(c, params['r_period'], params['s_period'])
        if v[i] is None: return 0
        if v[i] > 25: return 1
        if v[i] < -25: return -1
        return 0

    if indicator_id == 'VORTEX':
        vp, vm = _vortex(hi, lo, c, params['period'])
        if vp[i] is None or vm[i] is None: return 0
        if vp[i] > vm[i]: return 1
        if vm[i] > vp[i]: return -1
        return 0

    # ── Volatility & Volume ──────────────────────────────────────────────────
    if indicator_id == 'BOLLINGER':
        upper, _, lower = _bollinger(c, params['period'])
        if upper[i] is None: return 0
        if c[i] <= lower[i]: return 1
        if c[i] >= upper[i]: return -1
        return 0

    if indicator_id == 'ATR':
        v = _atr(hi, lo, c, params['period'])
        if v[i] is None or v[i-1] is None: return 0
        return 1 if v[i] > v[i-1] else 0  # expanding range: direction from candle
        # actually let's use candle direction as confirmation
        if v[i] > v[i-1]:
            return 1 if c[i] > c[i-1] else -1
        return 0

    if indicator_id == 'NATR':
        v = _natr(hi, lo, c, params['period'])
        if v[i] is None: return 0
        # low natr → choppy, skip; high natr → trending signal
        if v[i] > 0.5:
            return 1 if c[i] > c[i-1] else -1
        return 0

    if indicator_id == 'KELTNER':
        upper, mid, lower = _keltner(hi, lo, c, params['period'])
        if upper[i] is None: return 0
        if c[i] <= lower[i]: return 1
        if c[i] >= upper[i]: return -1
        return 0

    if indicator_id == 'SQUEEZE':
        sq, mom = _squeeze(hi, lo, c, params['period'])
        if sq[i] is None or mom[i] is None: return 0
        if not sq[i]:  # not in squeeze → in momentum
            return 1 if mom[i] > 0 else -1
        return 0

    if indicator_id == 'STDEV':
        v = _stdev(c, params['period'])
        if v[i] is None or v[i-1] is None: return 0
        # rising stdev → breakout; use candle direction
        if v[i] > v[i-1] * 1.1:
            return 1 if c[i] > c[i-1] else -1
        return 0

    if indicator_id == 'CHOPPINESS':
        v = _choppiness(hi, lo, c, params['period'])
        if v[i] is None: return 0
        # below 38.2 → strong trend
        if v[i] < 38.2:
            return 1 if c[i] > c[i-1] else -1
        return 0

    if indicator_id == 'MFI':
        v = _mfi(hi, lo, c, vol, params['period'])
        if v[i] is None: return 0
        if v[i] < 20: return 1
        if v[i] > 80: return -1
        return 0

    if indicator_id == 'CHAIKIN_MF':
        v = _chaikin_mf(hi, lo, c, vol, params['period'])
        if v[i] is None: return 0
        if v[i] > 0.1: return 1
        if v[i] < -0.1: return -1
        return 0

    if indicator_id == 'OBV':
        obv = _obv(c, vol)
        ma  = _ema(obv, params['period'])
        if ma[i] is None: return 0
        if obv[i] > ma[i]: return 1
        if obv[i] < ma[i]: return -1
        return 0

    # ── Level / Channel ──────────────────────────────────────────────────────
    if indicator_id == 'DONCHIAN':
        upper, lower = _donchian(hi, lo, params['period'])
        if upper[i] is None: return 0
        if c[i] >= upper[i]: return 1
        if c[i] <= lower[i]: return -1
        return 0

    if indicator_id == 'SUPPORT_RESISTANCE':
        lb = params['lookback']
        if i < lb: return 0
        res = max(hi[i-lb:i])
        sup = min(lo[i-lb:i])
        if c[i] > res: return 1
        if c[i] < sup: return -1
        return 0

    if indicator_id == 'PIVOT':
        pv = _pivot_points(hi, lo, c)
        if pv[i] is None: return 0
        if c[i] > pv[i]: return 1
        if c[i] < pv[i]: return -1
        return 0

    if indicator_id == 'FRACTAL':
        p = params['bars']
        bf, brf = _williams_fractal(hi, lo, p)
        if i >= p and bf[i-p]: return 1
        if i >= p and brf[i-p]: return -1
        return 0

    if indicator_id == 'PRICE_CHANNEL':
        p = params['period']
        if i < p: return 0
        res = max(hi[i-p:i])
        sup = min(lo[i-p:i])
        if c[i] > res: return 1
        if c[i] < sup: return -1
        return 0

    if indicator_id == 'FIBONACCI':
        lb = params['lookback']
        if i < lb: return 0
        swing_hi = max(hi[i-lb:i])
        swing_lo = min(lo[i-lb:i])
        diff = swing_hi - swing_lo
        if diff == 0: return 0
        fib618 = swing_hi - 0.618 * diff
        fib382 = swing_hi - 0.382 * diff
        if c[i] < fib618 and c[i] > fib382 * 0.99: return 1
        if c[i] > fib382 and c[i] < fib618 * 1.01: return -1
        return 0

    if indicator_id == 'KELTNER_BREAK':
        upper, _, lower = _keltner(hi, lo, c, params['period'])
        if upper[i] is None or lower[i-1] is None: return 0
        if c[i] > upper[i] and c[i-1] <= upper[i-1]: return 1
        if c[i] < lower[i] and c[i-1] >= lower[i-1]: return -1
        return 0

    # ── Advanced / Custom ────────────────────────────────────────────────────
    if indicator_id == 'ADX':
        adx, di_p, di_m = _adx(hi, lo, c, params['period'])
        if adx[i] is None or di_p[i] is None: return 0
        if adx[i] >= params.get('threshold', 25):
            if di_p[i] > di_m[i]: return 1
            if di_m[i] > di_p[i]: return -1
        return 0

    if indicator_id == 'STOCH_RSI':
        rsi = _rsi(c, params['rsi_period'])
        sk, sd = _stoch(hi, lo, c, params['stoch_k'])
        if rsi[i] is None or sk[i] is None or sd[i] is None: return 0
        if rsi[i] < 50 and sk[i] > sd[i] and sk[i] < 80: return 1
        if rsi[i] > 50 and sk[i] < sd[i] and sk[i] > 20: return -1
        return 0

    if indicator_id == 'MACD_RSI':
        _, _, hist = _macd(c, params['macd_fast'], params['macd_slow'], 9)
        rsi = _rsi(c, params['rsi_period'])
        if hist[i] is None or rsi[i] is None: return 0
        if hist[i] > 0 and rsi[i] > 40 and rsi[i] < 70: return 1
        if hist[i] < 0 and rsi[i] < 60 and rsi[i] > 30: return -1
        return 0

    if indicator_id == 'TRIPLE_EMA_STOCH':
        e1 = _ema(c, params['fast'])
        e2 = _ema(c, params['mid'])
        e3 = _ema(c, params['slow'])
        sk, sd = _stoch(hi, lo, c, params['stoch_k'])
        if any(v is None for v in [e1[i], e2[i], e3[i], sk[i], sd[i]]): return 0
        if e1[i] > e2[i] > e3[i] and sk[i] > sd[i] and sk[i] < 80: return 1
        if e1[i] < e2[i] < e3[i] and sk[i] < sd[i] and sk[i] > 20: return -1
        return 0

    if indicator_id == 'MULTI_EMA_MOMENTUM':
        fast = _ema(c, params['fast'])
        slow = _ema(c, params['slow'])
        rsi  = _rsi(c, params['rsi_p'])
        if any(v is None for v in [fast[i], slow[i], rsi[i]]): return 0
        if fast[i] > slow[i] and rsi[i] < 60: return 1
        if fast[i] < slow[i] and rsi[i] > 40: return -1
        return 0

    if indicator_id == 'SQUEEZE_BREAKOUT':
        sq, mom = _squeeze(hi, lo, c, params['period'])
        rsi = _rsi(c, params['rsi_p'])
        if sq[i] is None or mom[i] is None or rsi[i] is None: return 0
        if not sq[i] and mom[i] > 0 and rsi[i] > 45: return 1
        if not sq[i] and mom[i] < 0 and rsi[i] < 55: return -1
        return 0

    if indicator_id == 'SUPERTREND_RSI':
        _, direction = _supertrend(hi, lo, c, params['st_period'], params['st_mult']/10.0)
        rsi = _rsi(c, params['rsi_p'])
        if direction[i] is None or rsi[i] is None: return 0
        if direction[i] == -1 and rsi[i] < 65: return 1
        if direction[i] == 1  and rsi[i] > 35: return -1
        return 0

    if indicator_id == 'ADX_MACD':
        adx, di_p, di_m = _adx(hi, lo, c, params['adx_p'])
        _, _, hist = _macd(c, params['macd_fast'], params['macd_slow'], 9)
        if adx[i] is None or hist[i] is None: return 0
        if adx[i] >= params['adx_th']:
            if hist[i] > 0 and di_p[i] is not None and di_p[i] > di_m[i]: return 1
            if hist[i] < 0 and di_m[i] is not None and di_m[i] > di_p[i]: return -1
        return 0

    if indicator_id == 'ICHIMOKU_RSI':
        ten, kij = _ichimoku(hi, lo, params['tenkan'], params['kijun'])
        rsi = _rsi(c, params['rsi_p'])
        if ten[i] is None or kij[i] is None or rsi[i] is None: return 0
        if ten[i] > kij[i] and c[i] > kij[i] and rsi[i] < 65: return 1
        if ten[i] < kij[i] and c[i] < kij[i] and rsi[i] > 35: return -1
        return 0

    if indicator_id == 'BOLLINGER_RSI':
        upper, _, lower = _bollinger(c, params['bb_period'])
        rsi = _rsi(c, params['rsi_period'])
        if upper[i] is None or rsi[i] is None: return 0
        if c[i] <= lower[i] and rsi[i] < 40: return 1
        if c[i] >= upper[i] and rsi[i] > 60: return -1
        return 0

    if indicator_id == 'VORTEX_ADX':
        adx, _, _ = _adx(hi, lo, c, params['period'])
        vp, vm    = _vortex(hi, lo, c, params['period'])
        if adx[i] is None or vp[i] is None: return 0
        if adx[i] >= params['adx_th']:
            if vp[i] > vm[i]: return 1
            if vm[i] > vp[i]: return -1
        return 0

    if indicator_id == 'CANDLE_PATTERN':
        if i < 2: return 0
        # Bullish Engulfing
        if (c[i-1] < opens[i-1] and      # prev bearish
            c[i]   > opens[i]   and      # curr bullish
            opens[i] <= c[i-1]  and      # opens below prev close
            c[i] >= opens[i-1]):         # closes above prev open
            return 1
        # Bearish Engulfing
        if (c[i-1] > opens[i-1] and
            c[i]   < opens[i]   and
            opens[i] >= c[i-1]  and
            c[i] <= opens[i-1]):
            return -1
        # Hammer (bullish)
        body = abs(c[i] - opens[i])
        lower_wick = opens[i] - lo[i] if c[i] > opens[i] else c[i] - lo[i]
        upper_wick = hi[i] - c[i] if c[i] > opens[i] else hi[i] - opens[i]
        if body > 0 and lower_wick > 2*body and upper_wick < 0.5*body: return 1
        if body > 0 and upper_wick > 2*body and lower_wick < 0.5*body: return -1
        return 0

    return 0


# ══════════════════════════════════════════════════════════════════════════════
# DATACLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class IndicatorConfig:
    indicator_id: str
    params: dict


@dataclass
class StrategyConfig:
    indicators: List[IndicatorConfig]
    min_agreement: int = 1


@dataclass
class TradingConfig:
    modal: float = 100.0
    amount: float = 10.0
    stop_loss: float = 30.0
    stop_win: float = 50.0
    martingale_steps: int = 3
    martingale_multiplier: float = 2.2
    payout: float = 0.82


@dataclass
class StrategyResult:
    config: StrategyConfig
    win_rate: float
    total_trades: int
    wins: int
    losses: int
    net_pnl: float
    max_consec_loss: int
    max_consec_win: int
    score: float
    indicators_desc: str
    sim_profit: float = 0.0
    sim_final_balance: float = 0.0
    sim_max_drawdown: float = 0.0


# ══════════════════════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def backtest_strategy(candles: list, strategy: StrategyConfig,
                      trading: TradingConfig, warmup: int = 70) -> Optional[StrategyResult]:
    if len(candles) < warmup + 10:
        return None

    c   = [x['close']           for x in candles]
    hi  = [x['high']            for x in candles]
    lo  = [x['low']             for x in candles]
    op  = [x['open']            for x in candles]
    vol = [x.get('volume', 1)   for x in candles]
    D   = {'closes': c, 'highs': hi, 'lows': lo, 'opens': op, 'volumes': vol}

    wins = losses = 0
    consec_w = consec_l = max_cw = max_cl = 0

    balance       = trading.modal
    cur_amount    = trading.amount
    mrt_step      = 0
    total_profit  = 0.0
    max_drawdown  = 0.0
    peak          = trading.modal

    for i in range(warmup, len(candles) - 1):
        votes = []
        for ind in strategy.indicators:
            try:
                s = get_signal_at(i, ind.indicator_id, ind.params, D)
                if s != 0:
                    votes.append(s)
            except Exception:
                pass

        if len(votes) < strategy.min_agreement:
            continue

        call_v = votes.count(1)
        put_v  = votes.count(-1)

        if call_v >= strategy.min_agreement and call_v > put_v:
            direction = 'call'
        elif put_v >= strategy.min_agreement and put_v > call_v:
            direction = 'put'
        else:
            continue

        entry   = candles[i + 1]['open']
        exit_px = candles[i + 1]['close']
        won = ((direction == 'call' and exit_px > entry) or
               (direction == 'put'  and exit_px < entry))

        bet = min(cur_amount, balance)
        if won:
            profit = bet * trading.payout
            balance      += profit
            total_profit += profit
            wins += 1
            consec_w += 1; consec_l = 0
            max_cw = max(max_cw, consec_w)
            mrt_step  = 0
            cur_amount = trading.amount
        else:
            balance      -= bet
            total_profit -= bet
            losses += 1
            consec_l += 1; consec_w = 0
            max_cl = max(max_cl, consec_l)
            if mrt_step < trading.martingale_steps:
                mrt_step  += 1
                cur_amount = trading.amount * (trading.martingale_multiplier ** mrt_step)
            else:
                mrt_step   = 0
                cur_amount = trading.amount

        peak = max(peak, balance)
        dd   = (peak - balance) / peak * 100 if peak > 0 else 0
        max_drawdown = max(max_drawdown, dd)

        if total_profit >= trading.stop_win:
            break
        if total_profit <= -trading.stop_loss:
            break

    total = wins + losses
    if total < 10:
        return None

    win_rate = wins / total * 100
    net_pnl  = wins * trading.payout - losses
    score    = win_rate * math.log1p(total)

    indicators_desc = '; '.join(
        f"{INDICATOR_CATALOG.get(ind.indicator_id, {}).get('label', ind.indicator_id)}"
        f"({', '.join(f'{k}={v}' for k, v in ind.params.items())})"
        for ind in strategy.indicators
    )

    return StrategyResult(
        config=strategy,
        win_rate=round(win_rate, 2),
        total_trades=total,
        wins=wins,
        losses=losses,
        net_pnl=round(net_pnl, 2),
        max_consec_loss=max_cl,
        max_consec_win=max_cw,
        score=round(score, 2),
        indicators_desc=indicators_desc,
        sim_profit=round(total_profit, 2),
        sim_final_balance=round(balance, 2),
        sim_max_drawdown=round(max_drawdown, 2),
    )


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY GENERATOR ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class StrategyGenerator:
    """
    Unlimited random-search loop over indicator combinations.
    Periods are chosen randomly within the range for each indicator on
    every single iteration — giving true parameter diversity.
    """

    def __init__(self, candles: list, trading: TradingConfig,
                 allowed_indicators: Optional[List[str]] = None,
                 min_indicators: int = 2,
                 max_indicators: int = 4,
                 top_n: int = 20,
                 min_agreement_ratio: float = 0.6):
        self.candles  = candles
        self.trading  = trading
        self.allowed  = allowed_indicators or list(INDICATOR_CATALOG.keys())
        self.min_ind  = min_indicators
        self.max_ind  = max_indicators
        self.top_n    = top_n
        self.ratio    = min_agreement_ratio

        self.running    = False
        self.iterations = 0
        self.best: List[StrategyResult] = []
        self.start_time = None

    def _random_strategy(self) -> StrategyConfig:
        n = random.randint(self.min_ind, min(self.max_ind, len(self.allowed)))
        chosen = random.sample(self.allowed, n)
        inds = []
        for iid in chosen:
            catalog = INDICATOR_CATALOG[iid]
            params  = {}
            fast_val = None
            for p_name, (lo, hi) in catalog['params'].items():
                if p_name == 'slow' and fast_val is not None:
                    # ensure slow > fast with meaningful gap
                    params[p_name] = random.randint(fast_val + 3, max(fast_val + 3, hi))
                elif p_name in ('fast', 'macd_fast', 'st_mult'):
                    params[p_name] = random.randint(lo, hi)
                    if p_name in ('fast', 'macd_fast'):
                        fast_val = params[p_name]
                else:
                    params[p_name] = random.randint(lo, hi)
            # Fix remaining fast/slow ordering
            if 'fast' in params and 'slow' in params and params['fast'] >= params['slow']:
                params['slow'] = params['fast'] + random.randint(3, 20)
            if 'macd_fast' in params and 'macd_slow' in params and params['macd_fast'] >= params['macd_slow']:
                params['macd_slow'] = params['macd_fast'] + random.randint(5, 15)
            if 'tenkan' in params and 'kijun' in params and params['tenkan'] >= params['kijun']:
                params['kijun'] = params['tenkan'] + random.randint(5, 20)
            if 'p1' in params and 'p2' in params and params['p1'] >= params['p2']:
                params['p2'] = params['p1'] + random.randint(3, 10)
            if 'p2' in params and 'p3' in params and params['p2'] >= params['p3']:
                params['p3'] = params['p2'] + random.randint(5, 15)
            inds.append(IndicatorConfig(indicator_id=iid, params=params))

        min_agreement = max(1, round(n * self.ratio))
        return StrategyConfig(indicators=inds, min_agreement=min_agreement)

    def _update_best(self, result: StrategyResult):
        self.best.append(result)
        self.best.sort(key=lambda r: (-r.win_rate, -r.total_trades))
        if len(self.best) > self.top_n:
            self.best = self.best[:self.top_n]

    def run(self, progress_cb: Optional[Callable] = None,
            max_iterations: Optional[int] = None):
        self.running    = True
        self.start_time = time.time()

        while self.running:
            if max_iterations and self.iterations >= max_iterations:
                break
            try:
                strategy = self._random_strategy()
                result   = backtest_strategy(self.candles, strategy, self.trading)
                if result is not None:
                    self._update_best(result)
            except Exception as ex:
                logger.debug(f'Generator iter error: {ex}')

            self.iterations += 1

            if progress_cb and self.iterations % 10 == 0:
                elapsed  = time.time() - self.start_time
                rate     = self.iterations / elapsed if elapsed > 0 else 0
                best_wr  = self.best[0].win_rate if self.best else 0.0
                progress_cb(self.iterations, len(self.best), best_wr, rate)

        self.running = False

    def stop(self):
        self.running = False

    def results_as_dicts(self) -> list:
        out = []
        for r in self.best:
            indicators = []
            for ind in r.config.indicators:
                cat_info = INDICATOR_CATALOG.get(ind.indicator_id, {})
                indicators.append({
                    'id':       ind.indicator_id,
                    'label':    cat_info.get('label', ind.indicator_id),
                    'category': cat_info.get('category', ''),
                    'params':   ind.params,
                })
            out.append({
                'win_rate':          r.win_rate,
                'total_trades':      r.total_trades,
                'wins':              r.wins,
                'losses':            r.losses,
                'net_pnl':           r.net_pnl,
                'max_consec_loss':   r.max_consec_loss,
                'max_consec_win':    r.max_consec_win,
                'score':             r.score,
                'indicators_desc':   r.indicators_desc,
                'sim_profit':        r.sim_profit,
                'sim_final_balance': r.sim_final_balance,
                'sim_max_drawdown':  r.sim_max_drawdown,
                'indicators':        indicators,
                'min_agreement':     r.config.min_agreement,
            })
        return out
