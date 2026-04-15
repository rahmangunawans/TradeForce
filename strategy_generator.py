"""
Strategy Generator for IQ Option Trading Robot
================================================
Automatically searches for the best strategy by trying unlimited combinations
of indicators from multiple categories (Trend, Oscillator, Volatility & Volume,
Level / Channel, Advanced / Custom) with configurable period ranges.

Runs a backtest on real IQ Option candle data and scores each combination.
Keeps the top-N results sorted by win rate, with minimum trade count filter.
"""

import random
import math
import logging
import time
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Callable

logger = logging.getLogger(__name__)


# ─── Pure-Python indicator helpers ──────────────────────────────────────────

def _sma(values: list, period: int) -> list:
    result = [None] * (period - 1)
    for i in range(period - 1, len(values)):
        result.append(sum(values[i - period + 1: i + 1]) / period)
    return result


def _ema(values: list, period: int) -> list:
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    sma = sum(values[:period]) / period
    result.append(sma)
    k = 2.0 / (period + 1)
    for v in values[period:]:
        result.append(result[-1] * (1 - k) + v * k)
    return result


def _wma(values: list, period: int) -> list:
    result = [None] * (period - 1)
    weights = list(range(1, period + 1))
    denom = sum(weights)
    for i in range(period - 1, len(values)):
        s = sum(weights[j] * values[i - period + 1 + j] for j in range(period))
        result.append(s / denom)
    return result


def _dema(values: list, period: int) -> list:
    e1 = _ema(values, period)
    valid = [v for v in e1 if v is not None]
    if len(valid) < period:
        return [None] * len(values)
    e1_clean = [0.0] * (len(values) - len(valid)) + valid
    e2 = _ema(valid, period)
    pad = len(values) - len(e2)
    e2_padded = [None] * pad + e2
    result = []
    for a, b in zip(e1_clean, e2_padded):
        if b is None:
            result.append(None)
        else:
            result.append(2 * a - b)
    return result


def _tema(values: list, period: int) -> list:
    e1 = _ema(values, period)
    valid1 = [v for v in e1 if v is not None]
    if len(valid1) < period:
        return [None] * len(values)
    e2_raw = _ema(valid1, period)
    valid2 = [v for v in e2_raw if v is not None]
    if len(valid2) < period:
        return [None] * len(values)
    e3_raw = _ema(valid2, period)
    n3 = len(e3_raw)
    result = [None] * (len(values) - n3)
    for i in range(n3):
        e1v = e1[len(values) - n3 + i]
        e2v = e2_raw[len(valid1) - n3 + i] if len(valid1) >= n3 else None
        e3v = e3_raw[i]
        if e1v is None or e2v is None or e3v is None:
            result.append(None)
        else:
            result.append(3 * e1v - 3 * e2v + e3v)
    return result


def _rsi(closes: list, period: int) -> list:
    if len(closes) <= period:
        return [None] * len(closes)
    result = [None] * period
    gains, losses = [], []
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    avg_g = sum(gains) / period
    avg_l = sum(losses) / period
    result.append(100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l))
    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        g = max(d, 0.0)
        lo = max(-d, 0.0)
        avg_g = (avg_g * (period - 1) + g) / period
        avg_l = (avg_l * (period - 1) + lo) / period
        result.append(100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l))
    return result


def _macd(closes: list, fast: int, slow: int, signal_p: int):
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = []
    for f, s in zip(ema_fast, ema_slow):
        if f is None or s is None:
            macd_line.append(None)
        else:
            macd_line.append(f - s)
    valid = [v for v in macd_line if v is not None]
    if len(valid) < signal_p:
        return macd_line, [None] * len(macd_line), [None] * len(macd_line)
    sig_raw = _ema(valid, signal_p)
    pad = len(macd_line) - len(sig_raw)
    sig = [None] * pad + sig_raw
    hist = []
    for m, s in zip(macd_line, sig):
        if m is None or s is None:
            hist.append(None)
        else:
            hist.append(m - s)
    return macd_line, sig, hist


def _stoch(highs, lows, closes, k_period=14, k_smooth=3, d_smooth=3):
    raw_k = []
    for i in range(len(closes)):
        if i < k_period - 1:
            raw_k.append(None)
            continue
        h = max(highs[i - k_period + 1: i + 1])
        lo = min(lows[i - k_period + 1: i + 1])
        raw_k.append(50.0 if h == lo else 100 * (closes[i] - lo) / (h - lo))
    k_smooth_vals = []
    for i in range(len(raw_k)):
        if i < k_period + k_smooth - 2:
            k_smooth_vals.append(None)
            continue
        window = [raw_k[j] for j in range(i - k_smooth + 1, i + 1) if raw_k[j] is not None]
        k_smooth_vals.append(sum(window) / len(window) if window else None)
    d_smooth_vals = []
    for i in range(len(k_smooth_vals)):
        if i < k_period + k_smooth + d_smooth - 3:
            d_smooth_vals.append(None)
            continue
        window = [k_smooth_vals[j] for j in range(i - d_smooth + 1, i + 1) if k_smooth_vals[j] is not None]
        d_smooth_vals.append(sum(window) / len(window) if window else None)
    return k_smooth_vals, d_smooth_vals


def _bollinger(closes: list, period: int, std_mult: float = 2.0):
    mid = _sma(closes, period)
    upper, lower = [], []
    for i in range(len(closes)):
        if mid[i] is None:
            upper.append(None)
            lower.append(None)
            continue
        window = closes[i - period + 1: i + 1]
        mean = mid[i]
        std = math.sqrt(sum((x - mean) ** 2 for x in window) / period)
        upper.append(mean + std_mult * std)
        lower.append(mean - std_mult * std)
    return upper, mid, lower


def _atr(highs, lows, closes, period: int) -> list:
    tr = [None]
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr.append(max(hl, hc, lc))
    atr = [None] * period
    valid = [v for v in tr[1:] if v is not None]
    if len(valid) < period:
        return [None] * len(closes)
    atr_val = sum(valid[:period]) / period
    atr.append(atr_val)
    for v in valid[period:]:
        atr_val = (atr_val * (period - 1) + v) / period
        atr.append(atr_val)
    return atr


def _cci(highs, lows, closes, period: int) -> list:
    result = [None] * (period - 1)
    for i in range(period - 1, len(closes)):
        tp_window = [(highs[j] + lows[j] + closes[j]) / 3 for j in range(i - period + 1, i + 1)]
        mean = sum(tp_window) / period
        mad = sum(abs(v - mean) for v in tp_window) / period
        tp = (highs[i] + lows[i] + closes[i]) / 3
        result.append((tp - mean) / (0.015 * mad) if mad != 0 else 0.0)
    return result


def _williams_r(highs, lows, closes, period: int) -> list:
    result = [None] * (period - 1)
    for i in range(period - 1, len(closes)):
        h = max(highs[i - period + 1: i + 1])
        lo = min(lows[i - period + 1: i + 1])
        result.append(-100 * (h - closes[i]) / (h - lo) if h != lo else -50.0)
    return result


def _roc(closes: list, period: int) -> list:
    result = [None] * period
    for i in range(period, len(closes)):
        if closes[i - period] != 0:
            result.append((closes[i] - closes[i - period]) / closes[i - period] * 100)
        else:
            result.append(0.0)
    return result


def _adx(highs, lows, closes, period: int):
    dm_plus = [None]
    dm_minus = [None]
    for i in range(1, len(closes)):
        up = highs[i] - highs[i - 1]
        down = lows[i - 1] - lows[i]
        dm_plus.append(max(up, 0) if up > down else 0)
        dm_minus.append(max(down, 0) if down > up else 0)
    atr_vals = _atr(highs, lows, closes, period)
    di_plus = [None] * len(closes)
    di_minus = [None] * len(closes)
    adx_vals = [None] * len(closes)
    if len(atr_vals) >= period + 1:
        for i in range(period, len(closes)):
            if atr_vals[i] is None or atr_vals[i] == 0:
                continue
            dmp = sum(dm_plus[i - period + 1: i + 1]) / atr_vals[i]
            dmm = sum(dm_minus[i - period + 1: i + 1]) / atr_vals[i]
            di_plus[i] = 100 * dmp
            di_minus[i] = 100 * dmm
        dx_list = []
        for i in range(period, len(closes)):
            if di_plus[i] is None or di_minus[i] is None:
                continue
            s = di_plus[i] + di_minus[i]
            dx_list.append(abs(di_plus[i] - di_minus[i]) / s * 100 if s != 0 else 0)
        if len(dx_list) >= period:
            adx_val = sum(dx_list[:period]) / period
            start_idx = period * 2
            if start_idx < len(closes):
                adx_vals[start_idx] = adx_val
                for j, i in enumerate(range(start_idx + 1, len(closes))):
                    if j < len(dx_list) - period:
                        adx_val = (adx_val * (period - 1) + dx_list[period + j]) / period
                        adx_vals[i] = adx_val
    return adx_vals, di_plus, di_minus


def _donchian(highs, lows, period: int):
    upper = [None] * (period - 1)
    lower = [None] * (period - 1)
    for i in range(period - 1, len(highs)):
        upper.append(max(highs[i - period + 1: i + 1]))
        lower.append(min(lows[i - period + 1: i + 1]))
    return upper, lower


def _obv(closes, volumes):
    obv = [0.0]
    for i in range(1, len(closes)):
        if closes[i] > closes[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif closes[i] < closes[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])
    return obv


def _mfi(highs, lows, closes, volumes, period: int) -> list:
    result = [None] * period
    tp = [(highs[i] + lows[i] + closes[i]) / 3 for i in range(len(closes))]
    raw_mf = [tp[i] * volumes[i] for i in range(len(closes))]
    for i in range(period, len(closes)):
        pos = sum(raw_mf[j] for j in range(i - period + 1, i + 1) if tp[j] >= tp[j - 1])
        neg = sum(raw_mf[j] for j in range(i - period + 1, i + 1) if tp[j] < tp[j - 1])
        result.append(100.0 if neg == 0 else 100 - 100 / (1 + pos / neg))
    return result


def _parabolic_sar(highs, lows, closes, af_start=0.02, af_step=0.02, af_max=0.2):
    sar = [None] * len(closes)
    if len(closes) < 2:
        return sar
    bull = closes[1] > closes[0]
    ep = highs[1] if bull else lows[1]
    af = af_start
    sar[1] = lows[0] if bull else highs[0]
    for i in range(2, len(closes)):
        prev_sar = sar[i - 1]
        if bull:
            new_sar = prev_sar + af * (ep - prev_sar)
            new_sar = min(new_sar, lows[i - 1], lows[i - 2] if i > 2 else lows[i - 1])
            if lows[i] < new_sar:
                bull = False
                new_sar = ep
                ep = lows[i]
                af = af_start
            else:
                if highs[i] > ep:
                    ep = highs[i]
                    af = min(af + af_step, af_max)
        else:
            new_sar = prev_sar + af * (ep - prev_sar)
            new_sar = max(new_sar, highs[i - 1], highs[i - 2] if i > 2 else highs[i - 1])
            if highs[i] > new_sar:
                bull = True
                new_sar = ep
                ep = highs[i]
                af = af_start
            else:
                if lows[i] < ep:
                    ep = lows[i]
                    af = min(af + af_step, af_max)
        sar[i] = new_sar
    return sar


# ─── Indicator Catalog ───────────────────────────────────────────────────────

INDICATOR_CATALOG = {
    # ── Trend ──────────────────────────────────────────────────────────────
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
    'DEMA': {
        'category': 'Trend',
        'label': 'Double EMA (DEMA)',
        'params': {'period': (5, 50)},
        'defaults': {'period': 14},
    },
    'TEMA': {
        'category': 'Trend',
        'label': 'Triple EMA (TEMA)',
        'params': {'period': (3, 30)},
        'defaults': {'period': 9},
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
    'TRIPLE_EMA': {
        'category': 'Trend',
        'label': 'Triple EMA Alignment',
        'params': {'fast': (3, 15), 'mid': (8, 30), 'slow': (20, 100)},
        'defaults': {'fast': 3, 'mid': 8, 'slow': 50},
    },
    # ── Oscillator ─────────────────────────────────────────────────────────
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
    'MFI': {
        'category': 'Volatility & Volume',
        'label': 'Money Flow Index (MFI)',
        'params': {'period': (5, 20)},
        'defaults': {'period': 14},
    },
    # ── Volatility & Volume ────────────────────────────────────────────────
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
    'VOLUME_MA': {
        'category': 'Volatility & Volume',
        'label': 'Volume MA Surge',
        'params': {'period': (5, 30)},
        'defaults': {'period': 20},
    },
    'OBV': {
        'category': 'Volatility & Volume',
        'label': 'On-Balance Volume (OBV)',
        'params': {'period': (3, 20)},
        'defaults': {'period': 10},
    },
    # ── Level / Channel ────────────────────────────────────────────────────
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
        'params': {'period': (5, 20)},
        'defaults': {'period': 10},
    },
    # ── Advanced / Custom ──────────────────────────────────────────────────
    'ADX': {
        'category': 'Advanced / Custom',
        'label': 'ADX Trend Strength',
        'params': {'period': (7, 21), 'threshold': (20, 35)},
        'defaults': {'period': 14, 'threshold': 25},
    },
    'PARABOLIC_SAR': {
        'category': 'Advanced / Custom',
        'label': 'Parabolic SAR',
        'params': {},
        'defaults': {},
    },
    'EMA_BOUNCE': {
        'category': 'Advanced / Custom',
        'label': 'EMA Bounce',
        'params': {'period': (5, 50)},
        'defaults': {'period': 8},
    },
    'STOCH_RSI': {
        'category': 'Advanced / Custom',
        'label': 'Stoch + RSI Confluence',
        'params': {'rsi_period': (5, 14), 'stoch_k': (5, 21)},
        'defaults': {'rsi_period': 7, 'stoch_k': 14},
    },
    'MULTI_EMA_MOMENTUM': {
        'category': 'Advanced / Custom',
        'label': 'Multi-EMA + Momentum',
        'params': {'fast': (3, 15), 'slow': (10, 50), 'rsi_p': (5, 14)},
        'defaults': {'fast': 5, 'slow': 20, 'rsi_p': 7},
    },
}


# ─── Signal functions for each indicator ────────────────────────────────────

def _signal_trend_ma(closes, ma_vals, i):
    if ma_vals[i] is None or ma_vals[i - 1] is None:
        return 0
    if closes[i] > ma_vals[i] and closes[i - 1] <= ma_vals[i - 1]:
        return 1
    if closes[i] < ma_vals[i] and closes[i - 1] >= ma_vals[i - 1]:
        return -1
    if closes[i] > ma_vals[i]:
        return 1
    if closes[i] < ma_vals[i]:
        return -1
    return 0


def _signal_cross(fast, slow, i):
    if any(v is None for v in [fast[i], slow[i], fast[i - 1], slow[i - 1]]):
        return 0
    if fast[i] > slow[i]:
        return 1
    if fast[i] < slow[i]:
        return -1
    return 0


def get_signal_at(i, indicator_id, params, ind_data):
    """Return 1 (CALL), -1 (PUT), or 0 (no signal) for a single indicator."""
    closes = ind_data['closes']
    highs = ind_data['highs']
    lows = ind_data['lows']
    volumes = ind_data['volumes']

    if indicator_id == 'SMA':
        ma = _sma(closes, params['period'])
        return _signal_trend_ma(closes, ma, i)

    elif indicator_id == 'EMA':
        ma = _ema(closes, params['period'])
        return _signal_trend_ma(closes, ma, i)

    elif indicator_id == 'WMA':
        ma = _wma(closes, params['period'])
        return _signal_trend_ma(closes, ma, i)

    elif indicator_id == 'DEMA':
        ma = _dema(closes, params['period'])
        return _signal_trend_ma(closes, ma, i)

    elif indicator_id == 'TEMA':
        ma = _tema(closes, params['period'])
        return _signal_trend_ma(closes, ma, i)

    elif indicator_id == 'EMA_CROSS':
        fast = _ema(closes, params['fast'])
        slow = _ema(closes, params['slow'])
        return _signal_cross(fast, slow, i)

    elif indicator_id == 'SMA_CROSS':
        fast = _sma(closes, params['fast'])
        slow = _sma(closes, params['slow'])
        return _signal_cross(fast, slow, i)

    elif indicator_id == 'TRIPLE_EMA':
        e1 = _ema(closes, params['fast'])
        e2 = _ema(closes, params['mid'])
        e3 = _ema(closes, params['slow'])
        if any(v is None for v in [e1[i], e2[i], e3[i]]):
            return 0
        if e1[i] > e2[i] > e3[i]:
            return 1
        if e1[i] < e2[i] < e3[i]:
            return -1
        return 0

    elif indicator_id == 'RSI':
        rsi = _rsi(closes, params['period'])
        if rsi[i] is None:
            return 0
        if rsi[i] < 35:
            return 1
        if rsi[i] > 65:
            return -1
        return 0

    elif indicator_id == 'MACD':
        _, sig, hist = _macd(closes, params['fast'], params['slow'], params['signal'])
        if hist[i] is None or hist[i - 1] is None:
            return 0
        if hist[i] > 0 and hist[i - 1] <= 0:
            return 1
        if hist[i] < 0 and hist[i - 1] >= 0:
            return -1
        if hist[i] > 0:
            return 1
        if hist[i] < 0:
            return -1
        return 0

    elif indicator_id == 'STOCH':
        stk, std = _stoch(highs, lows, closes, params['k_period'], params['k_smooth'], params['d_smooth'])
        if stk[i] is None or std[i] is None:
            return 0
        if stk[i] > std[i] and stk[i] < 80:
            return 1
        if stk[i] < std[i] and stk[i] > 20:
            return -1
        return 0

    elif indicator_id == 'CCI':
        cci = _cci(highs, lows, closes, params['period'])
        if cci[i] is None:
            return 0
        if cci[i] > 100:
            return 1
        if cci[i] < -100:
            return -1
        return 0

    elif indicator_id == 'WILLIAMS_R':
        wr = _williams_r(highs, lows, closes, params['period'])
        if wr[i] is None:
            return 0
        if wr[i] < -80:
            return 1
        if wr[i] > -20:
            return -1
        return 0

    elif indicator_id == 'ROC':
        roc = _roc(closes, params['period'])
        if roc[i] is None:
            return 0
        if roc[i] > 0:
            return 1
        if roc[i] < 0:
            return -1
        return 0

    elif indicator_id == 'MFI':
        mfi = _mfi(highs, lows, closes, volumes, params['period'])
        if mfi[i] is None:
            return 0
        if mfi[i] < 20:
            return 1
        if mfi[i] > 80:
            return -1
        return 0

    elif indicator_id == 'BOLLINGER':
        upper, mid, lower = _bollinger(closes, params['period'])
        if upper[i] is None or lower[i] is None:
            return 0
        if closes[i] <= lower[i]:
            return 1
        if closes[i] >= upper[i]:
            return -1
        return 0

    elif indicator_id == 'ATR':
        atr = _atr(highs, lows, closes, params['period'])
        if atr[i] is None or atr[i - 1] is None:
            return 0
        if atr[i] > atr[i - 1]:
            return 1
        return 0

    elif indicator_id == 'VOLUME_MA':
        vma = _sma(volumes, params['period'])
        if vma[i] is None:
            return 0
        if volumes[i] > vma[i] * 1.5:
            if closes[i] > closes[i - 1]:
                return 1
            return -1
        return 0

    elif indicator_id == 'OBV':
        obv = _obv(closes, volumes)
        obv_ma = _ema(obv, params['period'])
        if obv_ma[i] is None or obv_ma[i - 1] is None:
            return 0
        if obv[i] > obv_ma[i] and obv[i - 1] <= obv_ma[i - 1]:
            return 1
        if obv[i] < obv_ma[i] and obv[i - 1] >= obv_ma[i - 1]:
            return -1
        if obv[i] > obv_ma[i]:
            return 1
        if obv[i] < obv_ma[i]:
            return -1
        return 0

    elif indicator_id == 'DONCHIAN':
        upper, lower = _donchian(highs, lows, params['period'])
        if upper[i] is None or lower[i] is None:
            return 0
        if closes[i] >= upper[i]:
            return 1
        if closes[i] <= lower[i]:
            return -1
        return 0

    elif indicator_id == 'SUPPORT_RESISTANCE':
        lb = params['lookback']
        if i < lb:
            return 0
        res = max(highs[i - lb: i])
        sup = min(lows[i - lb: i])
        if closes[i] > res:
            return 1
        if closes[i] < sup:
            return -1
        return 0

    elif indicator_id == 'PIVOT':
        p = params['period']
        if i < p:
            return 0
        pivot = (max(highs[i - p: i]) + min(lows[i - p: i]) + closes[i - 1]) / 3
        if closes[i] > pivot:
            return 1
        if closes[i] < pivot:
            return -1
        return 0

    elif indicator_id == 'ADX':
        adx_v, di_plus, di_minus = _adx(highs, lows, closes, params['period'])
        if adx_v[i] is None or di_plus[i] is None or di_minus[i] is None:
            return 0
        if adx_v[i] >= params.get('threshold', 25):
            if di_plus[i] > di_minus[i]:
                return 1
            if di_minus[i] > di_plus[i]:
                return -1
        return 0

    elif indicator_id == 'PARABOLIC_SAR':
        sar = _parabolic_sar(highs, lows, closes)
        if sar[i] is None:
            return 0
        if closes[i] > sar[i]:
            return 1
        if closes[i] < sar[i]:
            return -1
        return 0

    elif indicator_id == 'EMA_BOUNCE':
        ma = _ema(closes, params['period'])
        if ma[i] is None or ma[i - 1] is None:
            return 0
        tol = 0.0008
        if closes[i - 1] <= ma[i - 1] * (1 + tol) and closes[i] > ma[i]:
            return 1
        if closes[i - 1] >= ma[i - 1] * (1 - tol) and closes[i] < ma[i]:
            return -1
        return 0

    elif indicator_id == 'STOCH_RSI':
        rsi = _rsi(closes, params['rsi_period'])
        stk, std = _stoch(highs, lows, closes, params['stoch_k'])
        if rsi[i] is None or stk[i] is None or std[i] is None:
            return 0
        call = rsi[i] < 50 and stk[i] > std[i] and stk[i] < 80
        put = rsi[i] > 50 and stk[i] < std[i] and stk[i] > 20
        if call:
            return 1
        if put:
            return -1
        return 0

    elif indicator_id == 'MULTI_EMA_MOMENTUM':
        fast = _ema(closes, params['fast'])
        slow = _ema(closes, params['slow'])
        rsi = _rsi(closes, params['rsi_p'])
        if any(v is None for v in [fast[i], slow[i], rsi[i]]):
            return 0
        if fast[i] > slow[i] and rsi[i] < 60:
            return 1
        if fast[i] < slow[i] and rsi[i] > 40:
            return -1
        return 0

    return 0


# ─── Strategy config & result dataclasses ───────────────────────────────────

@dataclass
class IndicatorConfig:
    indicator_id: str
    params: dict


@dataclass
class StrategyConfig:
    indicators: List[IndicatorConfig]
    min_agreement: int = 1  # minimum indicators that must agree


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


# ─── Backtest engine ─────────────────────────────────────────────────────────

def backtest_strategy(candles: list, strategy: StrategyConfig,
                      trading: TradingConfig, warmup: int = 60) -> Optional[StrategyResult]:
    if len(candles) < warmup + 10:
        return None

    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    volumes = [c.get('volume', 0) for c in candles]

    ind_data = {'closes': closes, 'highs': highs, 'lows': lows, 'volumes': volumes}

    wins = losses = 0
    consec_w = consec_l = max_cw = max_cl = 0

    # Martingale simulation
    balance = trading.modal
    current_amount = trading.amount
    mrt_step = 0
    total_profit = 0.0
    max_drawdown = 0.0
    peak = trading.modal

    for i in range(warmup, len(candles) - 1):
        votes = []
        for ind in strategy.indicators:
            try:
                s = get_signal_at(i, ind.indicator_id, ind.params, ind_data)
                if s != 0:
                    votes.append(s)
            except Exception:
                pass

        if len(votes) < strategy.min_agreement:
            continue

        call_votes = votes.count(1)
        put_votes = votes.count(-1)

        if call_votes == 0 and put_votes == 0:
            continue

        if call_votes >= strategy.min_agreement and call_votes > put_votes:
            direction = 'call'
        elif put_votes >= strategy.min_agreement and put_votes > call_votes:
            direction = 'put'
        else:
            continue

        entry = candles[i + 1]['open']
        exit_px = candles[i + 1]['close']

        won = ((direction == 'call' and exit_px > entry) or
               (direction == 'put' and exit_px < entry))

        bet = min(current_amount, balance)
        if won:
            profit = bet * trading.payout
            balance += profit
            total_profit += profit
            wins += 1
            consec_w += 1
            consec_l = 0
            max_cw = max(max_cw, consec_w)
            mrt_step = 0
            current_amount = trading.amount
        else:
            balance -= bet
            total_profit -= bet
            losses += 1
            consec_l += 1
            consec_w = 0
            max_cl = max(max_cl, consec_l)
            if mrt_step < trading.martingale_steps:
                mrt_step += 1
                current_amount = trading.amount * (trading.martingale_multiplier ** mrt_step)
            else:
                mrt_step = 0
                current_amount = trading.amount

        if balance > peak:
            peak = balance
        dd = (peak - balance) / peak * 100 if peak > 0 else 0
        max_drawdown = max(max_drawdown, dd)

        if total_profit >= trading.stop_win:
            break
        if total_profit <= -trading.stop_loss:
            break

    total = wins + losses
    if total < 10:
        return None

    win_rate = wins / total * 100
    net_pnl = wins * trading.payout - losses
    score = win_rate * math.log1p(total)

    indicators_desc = '; '.join(
        f"{INDICATOR_CATALOG.get(ind.indicator_id, {}).get('label', ind.indicator_id)} "
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


# ─── Strategy Generator engine ──────────────────────────────────────────────

class StrategyGenerator:
    """
    Runs an unlimited random-search loop over indicator combinations,
    calling a progress callback periodically. Thread-safe result storage.
    """

    def __init__(self, candles: list, trading: TradingConfig,
                 allowed_indicators: Optional[List[str]] = None,
                 min_indicators: int = 2,
                 max_indicators: int = 4,
                 top_n: int = 20,
                 min_agreement_ratio: float = 0.6):
        self.candles = candles
        self.trading = trading
        self.allowed = allowed_indicators or list(INDICATOR_CATALOG.keys())
        self.min_ind = min_indicators
        self.max_ind = max_indicators
        self.top_n = top_n
        self.min_agreement_ratio = min_agreement_ratio

        self.running = False
        self.iterations = 0
        self.best: List[StrategyResult] = []
        self.start_time = None

    def _random_strategy(self) -> StrategyConfig:
        n = random.randint(self.min_ind, min(self.max_ind, len(self.allowed)))
        chosen = random.sample(self.allowed, n)
        inds = []
        for iid in chosen:
            catalog = INDICATOR_CATALOG[iid]
            params = {}
            for p_name, (lo, hi) in catalog['params'].items():
                if p_name in ('fast', 'slow') and len(params) > 0:
                    # Ensure fast < slow
                    if 'fast' in params:
                        params[p_name] = random.randint(params['fast'] + 1, hi)
                        continue
                params[p_name] = random.randint(lo, hi)
            # fix fast < slow constraints
            if 'fast' in params and 'slow' in params:
                if params['fast'] >= params['slow']:
                    params['slow'] = params['fast'] + random.randint(5, 20)
            inds.append(IndicatorConfig(indicator_id=iid, params=params))

        min_agreement = max(1, round(n * self.min_agreement_ratio))
        return StrategyConfig(indicators=inds, min_agreement=min_agreement)

    def _update_best(self, result: StrategyResult):
        self.best.append(result)
        self.best.sort(key=lambda r: (-r.win_rate, -r.total_trades))
        if len(self.best) > self.top_n:
            self.best = self.best[:self.top_n]

    def run(self, progress_cb: Optional[Callable] = None, max_iterations: Optional[int] = None):
        self.running = True
        self.start_time = time.time()

        while self.running:
            if max_iterations and self.iterations >= max_iterations:
                break

            try:
                strategy = self._random_strategy()
                result = backtest_strategy(self.candles, strategy, self.trading)
                if result is not None:
                    self._update_best(result)
            except Exception as ex:
                logger.debug(f"Generator iter error: {ex}")

            self.iterations += 1

            if progress_cb and self.iterations % 10 == 0:
                elapsed = time.time() - self.start_time
                rate = self.iterations / elapsed if elapsed > 0 else 0
                best_wr = self.best[0].win_rate if self.best else 0
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
                    'id': ind.indicator_id,
                    'label': cat_info.get('label', ind.indicator_id),
                    'category': cat_info.get('category', ''),
                    'params': ind.params,
                })
            out.append({
                'win_rate': r.win_rate,
                'total_trades': r.total_trades,
                'wins': r.wins,
                'losses': r.losses,
                'net_pnl': r.net_pnl,
                'max_consec_loss': r.max_consec_loss,
                'max_consec_win': r.max_consec_win,
                'score': r.score,
                'indicators_desc': r.indicators_desc,
                'sim_profit': r.sim_profit,
                'sim_final_balance': r.sim_final_balance,
                'sim_max_drawdown': r.sim_max_drawdown,
                'indicators': indicators,
                'min_agreement': r.config.min_agreement,
            })
        return out
