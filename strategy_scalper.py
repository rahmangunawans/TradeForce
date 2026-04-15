"""
ATV Aggressive Scalper M1
=========================
Strategi scalping agresif untuk IQ Option binary options.
Timeframe : M1 (1 menit)
Expiry    : 1 menit
Target    : Win rate > 75%

Logika sinyal (Triple-Confluence):
  1. Triple EMA Trend  : EMA3 > EMA8 > EMA50 (CALL) / EMA3 < EMA8 < EMA50 (PUT)
  2. RSI(7) Zone       : momentum di zona aktif, bukan ekstrem overbought/oversold
  3. Stochastic Cross  : %K memotong %D — konfirmasi momentum jangka pendek
  4. EMA8 Bounce       : harga baru saja memantul dari EMA8 searah tren

Sinyal hanya diambil saat SEMUA 4 kondisi terpenuhi → filter ketat = win rate tinggi.
"""

import time
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ─── Pure-Python indicator calculations (no pandas/numpy needed) ───────────────

def _calc_ema(values: list, period: int) -> list:
    """Exponential Moving Average. Returns list same length as values, None for warm-up."""
    if len(values) < period:
        return [None] * len(values)
    result = [None] * (period - 1)
    sma = sum(values[:period]) / period
    result.append(sma)
    k = 2.0 / (period + 1)
    for v in values[period:]:
        result.append(result[-1] * (1 - k) + v * k)
    return result


def _calc_rsi(closes: list, period: int = 14) -> list:
    """RSI. Returns list same length as closes, None for warm-up."""
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
        l = max(-d, 0.0)
        avg_g = (avg_g * (period - 1) + g) / period
        avg_l = (avg_l * (period - 1) + l) / period
        result.append(100.0 if avg_l == 0 else 100 - 100 / (1 + avg_g / avg_l))
    return result


def _smooth_sma(arr: list, period: int) -> list:
    """Simple rolling average, ignoring None."""
    result = [None] * (period - 1)
    buf = []
    for v in arr[period - 1:]:
        buf.append(v)
        if len(buf) > period:
            buf.pop(0)
        valid = [x for x in buf if x is not None]
        result.append(sum(valid) / len(valid) if valid else None)
    # align: arr[period-1:] is len(arr)-(period-1) elements
    return result


def _calc_stoch(highs, lows, closes, k_period=14, k_smooth=3, d_smooth=3):
    """Stochastic %K and %D. Returns (stk, std) same length as closes."""
    raw_k = []
    for i in range(len(closes)):
        if i < k_period - 1:
            raw_k.append(None)
            continue
        h = max(highs[i - k_period + 1: i + 1])
        l = min(lows[i - k_period + 1: i + 1])
        raw_k.append(50.0 if h == l else 100 * (closes[i] - l) / (h - l))

    # Smooth %K
    k_smooth_vals = []
    for i in range(len(raw_k)):
        if i < k_period + k_smooth - 2:
            k_smooth_vals.append(None)
            continue
        window = [raw_k[j] for j in range(i - k_smooth + 1, i + 1) if raw_k[j] is not None]
        k_smooth_vals.append(sum(window) / len(window) if window else None)

    # Smooth %D
    d_smooth_vals = []
    for i in range(len(k_smooth_vals)):
        if i < k_period + k_smooth + d_smooth - 3:
            d_smooth_vals.append(None)
            continue
        window = [k_smooth_vals[j] for j in range(i - d_smooth + 1, i + 1) if k_smooth_vals[j] is not None]
        d_smooth_vals.append(sum(window) / len(window) if window else None)

    return k_smooth_vals, d_smooth_vals


# ─── Strategy class ────────────────────────────────────────────────────────────

class AtvScalperM1:
    """ATV Aggressive Scalper M1 — Triple-Confluence binary options strategy."""

    NAME       = "ATV Aggressive Scalper M1"
    TIMEFRAME  = "M1"
    EXPIRY_MIN = 1

    # Indicator params
    EMA_FAST   = 3
    EMA_MID    = 8
    EMA_SLOW   = 50
    RSI_PERIOD = 7
    STOCH_K    = 14
    STOCH_KS   = 3
    STOCH_DS   = 3

    # RSI zones
    RSI_CALL_LO, RSI_CALL_HI = 45, 67
    RSI_PUT_LO,  RSI_PUT_HI  = 33, 55

    # Stochastic limits
    STOCH_CALL_MAX = 72   # not overbought
    STOCH_PUT_MIN  = 28   # not oversold

    # EMA bounce tolerance (0.05%)
    BOUNCE_TOL = 0.0005

    def _indicators(self, candles: list) -> dict:
        closes = [c['close'] for c in candles]
        highs  = [c['high']  for c in candles]
        lows   = [c['low']   for c in candles]
        opens  = [c['open']  for c in candles]
        return {
            'opens':  opens,
            'closes': closes,
            'highs':  highs,
            'lows':   lows,
            'ema3':   _calc_ema(closes, self.EMA_FAST),
            'ema8':   _calc_ema(closes, self.EMA_MID),
            'ema50':  _calc_ema(closes, self.EMA_SLOW),
            'rsi':    _calc_rsi(closes, self.RSI_PERIOD),
            'stk':    _calc_stoch(highs, lows, closes,
                                  self.STOCH_K, self.STOCH_KS, self.STOCH_DS)[0],
            'std':    _calc_stoch(highs, lows, closes,
                                  self.STOCH_K, self.STOCH_KS, self.STOCH_DS)[1],
        }

    def _signal_at(self, i: int, ind: dict) -> str | None:
        """Return 'call', 'put', or None for candle at index i."""
        e3, e8, e50 = ind['ema3'], ind['ema8'], ind['ema50']
        rsi         = ind['rsi']
        stk, std    = ind['stk'], ind['std']
        cls, opn    = ind['closes'], ind['opens']

        # Require both current and previous bar to have all indicators
        if any(v is None for v in [
            e3[i], e8[i], e50[i], rsi[i], stk[i], std[i],
            e3[i-1], e8[i-1], stk[i-1], std[i-1]
        ]):
            return None

        is_bull = cls[i] > opn[i]
        is_bear = cls[i] < opn[i]

        # ── CALL ──────────────────────────────────────────────────────────────
        ema_up        = e3[i] > e8[i] > e50[i]
        rsi_call      = self.RSI_CALL_LO <= rsi[i] <= self.RSI_CALL_HI
        stoch_up_x    = (stk[i] > std[i] and stk[i-1] <= std[i-1]   # fresh cross-up
                         and stk[i] < self.STOCH_CALL_MAX)
        bounce_call   = (cls[i-1] <= e8[i-1] * (1 + self.BOUNCE_TOL) and
                         cls[i]   >  e8[i])                           # bounced above EMA8

        if ema_up and rsi_call and stoch_up_x and is_bull and bounce_call:
            return 'call'

        # ── PUT ───────────────────────────────────────────────────────────────
        ema_dn        = e3[i] < e8[i] < e50[i]
        rsi_put       = self.RSI_PUT_LO <= rsi[i] <= self.RSI_PUT_HI
        stoch_dn_x    = (stk[i] < std[i] and stk[i-1] >= std[i-1]   # fresh cross-down
                         and stk[i] > self.STOCH_PUT_MIN)
        bounce_put    = (cls[i-1] >= e8[i-1] * (1 - self.BOUNCE_TOL) and
                         cls[i]   <  e8[i])                           # bounced below EMA8

        if ema_dn and rsi_put and stoch_dn_x and is_bear and bounce_put:
            return 'put'

        return None

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_signals(self, candles: list) -> list:
        """Return list of signal dicts for all candles."""
        ind     = self._indicators(candles)
        signals = []
        start   = self.EMA_SLOW + 10          # warm-up buffer
        for i in range(start, len(candles) - 1):
            direction = self._signal_at(i, ind)
            if direction:
                signals.append({
                    'i':          i,
                    'time':       candles[i]['time'],
                    'direction':  direction,
                    'open':       round(candles[i]['open'],  5),
                    'close':      round(candles[i]['close'], 5),
                    'next_open':  round(candles[i + 1]['open'],  5),
                    'next_close': round(candles[i + 1]['close'], 5),
                })
        return signals

    def backtest(self, candles: list, payout: float = 0.82) -> dict:
        """
        Run backtest on candles list.
        payout: broker payout (e.g. 0.82 = 82%). IQ Option typical: 75-92%.
        Returns a stats dict with full trade log (last 200 trades).
        """
        signals = self.generate_signals(candles)

        wins = losses = 0
        consec_w = consec_l = max_cw = max_cl = 0
        trade_log = []

        for sig in signals:
            i         = sig['i']
            direction = sig['direction']
            entry     = candles[i + 1]['open']
            exit_px   = candles[i + 1]['close']

            won = ((direction == 'call' and exit_px > entry) or
                   (direction == 'put'  and exit_px < entry))

            if won:
                wins += 1; consec_w += 1; consec_l = 0
                max_cw = max(max_cw, consec_w)
            else:
                losses += 1; consec_l += 1; consec_w = 0
                max_cl = max(max_cl, consec_l)

            trade_log.append({
                'time':      datetime.fromtimestamp(sig['time'],
                             tz=timezone.utc).strftime('%Y-%m-%d %H:%M'),
                'direction': direction.upper(),
                'entry':     round(entry,   5),
                'exit':      round(exit_px, 5),
                'result':    'WIN' if won else 'LOSS',
                'pnl':       round(payout if won else -1.0, 2),
            })

        total    = wins + losses
        win_rate = round(wins / total * 100, 2) if total else 0
        net_pnl  = round(wins * payout - losses, 2)

        # Monthly breakdown
        monthly: dict = {}
        for t in trade_log:
            ym = t['time'][:7]
            if ym not in monthly:
                monthly[ym] = {'wins': 0, 'losses': 0}
            if t['result'] == 'WIN':
                monthly[ym]['wins'] += 1
            else:
                monthly[ym]['losses'] += 1
        monthly_stats = []
        for ym, v in sorted(monthly.items()):
            tot = v['wins'] + v['losses']
            monthly_stats.append({
                'month':    ym,
                'wins':     v['wins'],
                'losses':   v['losses'],
                'total':    tot,
                'win_rate': round(v['wins'] / tot * 100, 1) if tot else 0,
            })

        return {
            'strategy':         self.NAME,
            'timeframe':        self.TIMEFRAME,
            'expiry':           self.EXPIRY_MIN,
            'payout_used':      payout,
            'total_signals':    total,
            'wins':             wins,
            'losses':           losses,
            'win_rate':         win_rate,
            'net_pnl_units':    net_pnl,
            'max_consec_win':   max_cw,
            'max_consec_loss':  max_cl,
            'avg_signals_day':  0,       # filled by fetch function
            'monthly':          monthly_stats,
            'trade_log':        trade_log[-200:],  # last 200 for UI
        }


# ─── Data-fetching helper ──────────────────────────────────────────────────────

def fetch_candles_range(robot, asset: str, interval: int,
                        start_ts: float, end_ts: float,
                        progress_cb=None) -> list:
    """
    Fetch all M1 candles between start_ts and end_ts using IQ Option API.
    Walks backwards in time in chunks of 1 000 candles.
    progress_cb(pct, msg) is called periodically.
    Returns sorted list of candle dicts.
    """
    CHUNK = 1000
    all_candles: list = []
    current_end = end_ts
    total_seconds = end_ts - start_ts
    fetched = 0

    logger.info(f"Fetching {asset} M{interval//60} from "
                f"{datetime.fromtimestamp(start_ts)} to {datetime.fromtimestamp(end_ts)}")

    while current_end > start_ts:
        try:
            raw = robot.api.get_candles(asset, interval, CHUNK, current_end)
        except Exception as ex:
            logger.warning(f"get_candles error (retrying): {ex}")
            time.sleep(2)
            try:
                raw = robot.api.get_candles(asset, interval, CHUNK, current_end)
            except Exception:
                break

        if not raw:
            break

        chunk = []
        for c in raw:
            t = int(c.get('from', c.get('id', 0)))
            if t < start_ts:
                continue
            chunk.append({
                'time':   t,
                'open':   float(c.get('open', 0)),
                'high':   float(c.get('max', c.get('high', 0))),
                'low':    float(c.get('min', c.get('low', 0))),
                'close':  float(c.get('close', 0)),
                'volume': int(c.get('volume', 0)),
            })

        if not chunk:
            break

        chunk.sort(key=lambda x: x['time'])
        oldest_in_chunk = chunk[0]['time']

        # Merge (avoid duplicates by timestamp)
        existing_times = {c['time'] for c in all_candles}
        for c in chunk:
            if c['time'] not in existing_times:
                all_candles.append(c)

        fetched += len(chunk)
        pct = min(99, int((end_ts - oldest_in_chunk) / total_seconds * 100))
        if progress_cb:
            progress_cb(pct, f"Fetched {fetched:,} candles… ({pct}%)")
        logger.info(f"  chunk oldest={datetime.fromtimestamp(oldest_in_chunk)} "
                    f"fetched={fetched}")

        if oldest_in_chunk <= start_ts:
            break

        current_end = oldest_in_chunk - 1
        time.sleep(0.35)   # be polite to the API

    all_candles.sort(key=lambda x: x['time'])

    # Filter to exact range
    all_candles = [c for c in all_candles if start_ts <= c['time'] <= end_ts]
    logger.info(f"Total candles after fetch: {len(all_candles)}")
    return all_candles
