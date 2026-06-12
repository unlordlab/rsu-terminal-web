import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
import requests

CFG = {
    "phase_drops": [0.15, 0.10, 0.07, 0.10, 0.10, 0.10],
    "phase_alloc": [0.20, 0.15, 0.20, 0.20, 0.15, 0.10],
    "reserve_pct": 0.10,
    "sell_a_tp": 0.20, "sell_a_keep": 0.05,
    "sell_a_runner_tp": 0.17, "sell_a_trail_stop": 0.11,
    "sell_b_tp": 0.10, "sell_b_keep": 0.20,
    "sell_b_trail_be": 0.00, "sell_b_trail_act": 0.14,
    "sell_b_trail_stop": 0.11, "sell_b_close_from": 0.10,
    "sell_c_trim1_pct": 0.65, "sell_c_trim1_tp": 0.05,
    "sell_c_trail_be": 0.00, "sell_c_trim2_pct": 0.15,
    "sell_c_trim2_tp": 0.10, "sell_c_final_tp": 0.20,
    "dd_phase_map": [
        (15, "STAND BY", "#333"),
        (24, "FASE 1",   "#00ffad"),
        (29, "FASE 2",   "#00ffad"),
        (36, "FASE 3",   "#ff9800"),
        (43, "FASE 4",   "#ff9800"),
        (49, "FASE 5",   "#f23645"),
        (999,"FASE 6",   "#f23645"),
    ],
}

PHASE_DROPS = CFG["phase_drops"]
PHASE_ALLOC = CFG["phase_alloc"]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _is_market_open() -> bool:
    try:
        import pytz
        et     = pytz.timezone("America/New_York")
        now_et = datetime.now(pytz.utc).astimezone(et)
        if now_et.weekday() >= 5: return False
        t = now_et.hour * 60 + now_et.minute
        return 9*60+30 <= t < 16*60
    except Exception:
        now_utc = datetime.now(timezone.utc)
        if now_utc.weekday() >= 5: return False
        t = now_utc.hour * 60 + now_utc.minute
        return 13*60+30 <= t < 20*60

def _phase_state(current_price: float, spxl_high: float) -> tuple:
    dd = abs((current_price - spxl_high) / spxl_high * 100)
    for threshold, label, color in CFG["dd_phase_map"]:
        if dd < threshold:
            return label, color
    return "FASE 6", "#f23645"

def _fetch_cds() -> float | None:
    try:
        r = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2",
            timeout=8
        )
        if r.status_code != 200: return None
        for line in reversed(r.text.strip().splitlines()):
            if line.startswith("DATE"): continue
            parts = line.split(",")
            if len(parts) == 2 and parts[1].strip() not in ("", "."):
                return float(parts[1].strip())
    except Exception:
        pass
    return None

# ── LIVE DATA ─────────────────────────────────────────────────────────────────

def get_spxl_live() -> dict:
    try:
        spxl = yf.Ticker("SPXL")
        hist = spxl.history(period="2y")
        if hist.empty:
            return {"ok": False, "error": "Sin datos SPXL"}

        current   = float(hist['Close'].iloc[-1])
        prev      = float(hist['Close'].iloc[-2])
        chg_pct   = (current - prev) / prev * 100
        spxl_high = float(hist['Close'].max())
        dd_pct    = (current - spxl_high) / spxl_high * 100
        phase_lbl, phase_color = _phase_state(current, spxl_high)

        # SPX
        spx_hist  = yf.Ticker("^GSPC").history(period="2d")
        spx_price = float(spx_hist['Close'].iloc[-1]) if not spx_hist.empty else None
        spx_chg   = None
        if spx_hist is not None and len(spx_hist) >= 2:
            spx_chg = float((spx_hist['Close'].iloc[-1] - spx_hist['Close'].iloc[-2]) / spx_hist['Close'].iloc[-2] * 100)

        # VIX + 10Y
        vix_val, vix_chg, bond_val, bond_chg = None, None, None, None
        try:
            vix  = yf.Ticker("^VIX").history(period="2d")
            if len(vix) >= 2:
                vix_val = round(float(vix['Close'].iloc[-1]), 2)
                vix_chg = round(float(vix['Close'].iloc[-1]) - float(vix['Close'].iloc[-2]), 2)
        except Exception: pass
        try:
            tnx = yf.Ticker("^TNX").history(period="2d")
            if len(tnx) >= 2:
                bond_val = round(float(tnx['Close'].iloc[-1]), 2)
                bond_chg = round(float(tnx['Close'].iloc[-1]) - float(tnx['Close'].iloc[-2]), 2)
        except Exception: pass

        # CDS
        cds = _fetch_cds()

        # Fases — precio objetivo de entrada por fase
        phases = []
        ref    = current
        for i, (drop, alloc) in enumerate(zip(PHASE_DROPS, PHASE_ALLOC)):
            target = ref * (1 - drop)
            phases.append({
                "phase":  i + 1,
                "drop":   drop * 100,
                "alloc":  alloc * 100,
                "target": round(target, 2),
                "active": phase_lbl == f"FASE {i+1}",
            })
            ref = target

        # Chart sparkline 90d
        chart_data = hist['Close'].tail(90)
        chart = {
            "dates":  [d.strftime('%Y-%m-%d') for d in chart_data.index],
            "closes": [round(float(c), 2) for c in chart_data.values],
        }

        return {
            "ok":           True,
            "price":        round(current, 2),
            "chg_pct":      round(chg_pct, 2),
            "spxl_high":    round(spxl_high, 2),
            "dd_pct":       round(dd_pct, 2),
            "phase":        phase_lbl,
            "phase_color":  phase_color,
            "market_open":  _is_market_open(),
            "spx_price":    round(spx_price, 2) if spx_price else None,
            "spx_chg":      round(spx_chg, 2) if spx_chg else None,
            "vix":          vix_val,
            "vix_chg":      vix_chg,
            "bond10y":      bond_val,
            "bond10y_chg":  bond_chg,
            "cds":          round(cds, 2) if cds else None,
            "phases":       phases,
            "chart":        chart,
            "timestamp":    datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── BACKTEST ──────────────────────────────────────────────────────────────────

def _make_trade(date, exit_price, avg_cost, qty, phases_used, scenario, entry_date=None, ref_price=None):
    gross    = qty * exit_price
    cost     = qty * avg_cost
    pnl      = gross - cost
    pnl_pct  = pnl / cost * 100 if cost > 0 else 0
    hold_days = (date - entry_date).days if entry_date else 0
    return {
        "date": str(date)[:10], "exit_price": round(exit_price, 2),
        "avg_cost": round(avg_cost, 2), "qty": round(qty, 4),
        "gross": round(gross, 2), "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 2), "phases": phases_used,
        "scenario": scenario, "hold_days": hold_days,
    }

def run_backtest(df, initial_capital=100_000):
    initial_capital = float(initial_capital)
    prices   = df['price'].values
    dates    = df.index
    cash     = initial_capital
    shares   = 0.0
    avg_cost = 0.0
    phase_high   = prices[0]
    phase_idx    = -1
    phases_spent = []
    entry_date   = None
    trades       = []
    equity_curve = []
    bnh_curve    = []
    bnh_shares   = (initial_capital * (1 - CFG["reserve_pct"])) / prices[0]
    bnh_cash     = initial_capital * CFG["reserve_pct"]
    peak_equity  = initial_capital
    max_dd       = 0.0
    cycle_equity = initial_capital
    runner_shares   = 0.0
    runner_peak     = 0.0
    first_sell_px   = None
    trail_stop_px   = None
    in_runner       = False
    sold_trim1      = False
    sold_trim2      = False

    for i, (price, date) in enumerate(zip(prices, dates)):
        cur_equity = cash + (shares + runner_shares) * price
        bnh_val    = bnh_cash + bnh_shares * price
        equity_curve.append({"date": str(date)[:10], "equity": round(cur_equity, 2)})
        bnh_curve.append({"date": str(date)[:10], "equity": round(bnh_val, 2)})

        if cur_equity > peak_equity: peak_equity = cur_equity
        dd = (peak_equity - cur_equity) / peak_equity * 100
        if dd > max_dd: max_dd = dd

        dd_from_high = (price - phase_high) / phase_high * 100

        # BUY logic
        next_phase = phase_idx + 1
        if next_phase < len(PHASE_DROPS):
            threshold = -PHASE_DROPS[next_phase] * 100
            if dd_from_high <= threshold:
                alloc_frac = PHASE_ALLOC[next_phase]
                buy_cash   = cycle_equity * alloc_frac
                if buy_cash > cash: buy_cash = cash
                if buy_cash > 0:
                    new_shares  = buy_cash / price
                    total_cost  = avg_cost * shares + buy_cash
                    shares     += new_shares
                    avg_cost    = total_cost / shares if shares > 0 else price
                    cash       -= buy_cash
                    phase_idx   = next_phase
                    phases_spent.append(next_phase)
                    if entry_date is None: entry_date = date
                    phase_high = price

        # SELL logic
        if shares > 0 and avg_cost > 0:
            gain = (price - avg_cost) / avg_cost
            n_phases = len(phases_spent)

            if n_phases >= 6:  # Scenario C
                if not sold_trim1 and gain >= CFG["sell_c_trim1_tp"]:
                    trim_qty = shares * CFG["sell_c_trim1_pct"]
                    trades.append(_make_trade(date, price, avg_cost, trim_qty, n_phases, "C-trim1", entry_date))
                    shares   -= trim_qty
                    sold_trim1 = True
                    first_sell_px = price
                elif sold_trim1 and not sold_trim2:
                    rg = (price - first_sell_px) / first_sell_px if first_sell_px else 0
                    if rg >= CFG["sell_c_trim2_tp"]:
                        trim2_qty = shares * (CFG["sell_c_trim2_pct"] / (1 - CFG["sell_c_trim1_pct"]))
                        trades.append(_make_trade(date, price, avg_cost, trim2_qty, n_phases, "C-trim2", entry_date))
                        shares   -= trim2_qty
                        sold_trim2 = True
                elif sold_trim2:
                    rg = (price - first_sell_px) / first_sell_px if first_sell_px else 0
                    if rg >= CFG["sell_c_final_tp"]:
                        trades.append(_make_trade(date, price, avg_cost, shares, n_phases, "C-final", entry_date))
                        cash += shares * price
                        shares = avg_cost = 0; phase_idx = -1
                        phases_spent = []; entry_date = None
                        sold_trim1 = sold_trim2 = False; first_sell_px = None
                        phase_high   = price
                        cycle_equity = cash + runner_shares * price

            elif n_phases >= 4:  # Scenario B
                if not in_runner and gain >= CFG["sell_b_tp"]:
                    main_qty = shares * (1 - CFG["sell_b_keep"])
                    trades.append(_make_trade(date, price, avg_cost, main_qty, n_phases, "B-main", entry_date))
                    cash          += main_qty * price
                    runner_shares += shares * CFG["sell_b_keep"]
                    shares         = 0
                    in_runner      = True
                    runner_peak    = price
                    first_sell_px  = price
                elif in_runner:
                    if price > runner_peak: runner_peak = price
                    rg = (price - avg_cost) / avg_cost if avg_cost > 0 else 0
                    close_target = first_sell_px * (1 + CFG["sell_b_close_from"]) if first_sell_px else 0
                    trail_cond   = rg >= CFG["sell_b_trail_act"]
                    stop_px      = runner_peak * (1 - CFG["sell_b_trail_stop"]) if trail_cond else avg_cost
                    if price >= close_target or price <= stop_px:
                        trades.append(_make_trade(date, price, avg_cost, runner_shares, n_phases, "B-runner", entry_date))
                        cash += runner_shares * price
                        runner_shares = 0; in_runner = False; first_sell_px = None
                        shares = avg_cost = 0; phase_idx = -1
                        phases_spent = []; entry_date = None
                        phase_high   = price
                        cycle_equity = cash

            else:  # Scenario A
                if not in_runner and gain >= CFG["sell_a_tp"]:
                    main_qty = shares * (1 - CFG["sell_a_keep"])
                    trades.append(_make_trade(date, price, avg_cost, main_qty, n_phases, "A-main", entry_date))
                    cash          += main_qty * price
                    runner_shares += shares * CFG["sell_a_keep"]
                    shares         = 0
                    in_runner      = True
                    runner_peak    = price
                elif in_runner:
                    if price > runner_peak: runner_peak = price
                    runner_target = first_sell_px * (1 + CFG["sell_a_runner_tp"]) if first_sell_px else price * 1.17
                    stop_px       = runner_peak * (1 - CFG["sell_a_trail_stop"])
                    if price >= runner_target or price <= stop_px:
                        trades.append(_make_trade(date, price, avg_cost, runner_shares, n_phases, "A-runner", entry_date))
                        cash += runner_shares * price
                        runner_shares = 0; in_runner = False
                        shares = avg_cost = 0; phase_idx = -1
                        phases_spent = []; entry_date = None
                        phase_high   = price
                        cycle_equity = cash

    return {
        "trades":       trades,
        "equity_curve": equity_curve,
        "bnh_curve":    bnh_curve,
        "max_dd":       round(max_dd, 2),
    }

def compute_stats(trades, eq_curve, bnh_curve, initial_capital):
    if not trades or not eq_curve:
        return {}
    final_equity = eq_curve[-1]['equity']
    final_bnh    = bnh_curve[-1]['equity']
    start_date   = datetime.strptime(eq_curve[0]['date'], '%Y-%m-%d')
    end_date     = datetime.strptime(eq_curve[-1]['date'], '%Y-%m-%d')
    years        = max((end_date - start_date).days / 365.25, 0.01)
    cagr         = ((final_equity / initial_capital) ** (1/years) - 1) * 100
    bnh_cagr     = ((final_bnh / initial_capital) ** (1/years) - 1) * 100
    wins         = [t for t in trades if t['pnl'] > 0]
    losses       = [t for t in trades if t['pnl'] <= 0]
    win_rate     = len(wins) / len(trades) * 100 if trades else 0
    avg_win      = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
    avg_loss     = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
    peak         = initial_capital
    max_dd       = 0.0
    for pt in eq_curve:
        if pt['equity'] > peak: peak = pt['equity']
        dd = (peak - pt['equity']) / peak * 100
        if dd > max_dd: max_dd = dd

    return {
        "total_trades":  len(trades),
        "win_rate":      round(win_rate, 1),
        "avg_win":       round(avg_win, 2),
        "avg_loss":      round(avg_loss, 2),
        "final_equity":  round(final_equity, 2),
        "total_return":  round((final_equity - initial_capital) / initial_capital * 100, 2),
        "cagr":          round(cagr, 2),
        "max_dd":        round(max_dd, 2),
        "final_bnh":     round(final_bnh, 2),
        "bnh_return":    round((final_bnh - initial_capital) / initial_capital * 100, 2),
        "bnh_cagr":      round(bnh_cagr, 2),
        "years":         round(years, 1),
    }

def get_backtest(initial_capital: float = 100_000) -> dict:
    try:
        spxl    = yf.Ticker("SPXL")
        df_raw  = spxl.history(start="2008-11-05")[["Close"]].copy()
        df_raw.index = df_raw.index.tz_localize(None)
        df_raw.columns = ["price"]
        df_raw = df_raw[~df_raw.index.duplicated(keep="last")].sort_index().dropna()

        result = run_backtest(df_raw, initial_capital)
        stats  = compute_stats(result['trades'], result['equity_curve'], result['bnh_curve'], initial_capital)

        # Reducir tamaño — solo últimos 500 puntos para el chart
        eq_chart  = result['equity_curve'][-500:]
        bnh_chart = result['bnh_curve'][-500:]

        return {
            "ok":           True,
            "stats":        stats,
            "trades":       result['trades'][-50:],
            "equity_chart": eq_chart,
            "bnh_chart":    bnh_chart,
            "timestamp":    datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}