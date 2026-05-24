"""paper_trader.py 测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from roma_analyzer.paper_trader import (
    PaperTradeResult,
    Trade,
    rule_signal,
    run,
)


def _make_klines(prices, volume=1000):
    return [{"open": p, "high": p * 1.001, "low": p * 0.999,
             "close": p, "volume": volume} for p in prices]


# --- rule_signal ---------------------------------------------------------

def test_rule_signal_buys_on_oversold():
    indicators = {"rsi": 25, "trend": "Uptrend"}
    action, reason = rule_signal(indicators, has_position=False)
    assert action == "BUY"


def test_rule_signal_sells_on_overbought():
    indicators = {"rsi": 75, "trend": "Uptrend"}
    action, reason = rule_signal(indicators, has_position=True)
    assert action == "SELL"


def test_rule_signal_holds_when_neutral():
    indicators = {"rsi": 50, "trend": "Sideways"}
    action, _ = rule_signal(indicators, has_position=False)
    assert action == "HOLD"


def test_rule_signal_skip_buy_in_strong_downtrend():
    """RSI 超卖但强空趋势 → 不抄底。"""
    indicators = {"rsi": 20, "trend": "Strong Downtrend"}
    action, _ = rule_signal(indicators, has_position=False)
    assert action == "HOLD"


def test_rule_signal_exit_on_downtrend_with_position():
    """持仓中遇到下跌趋势 → 止损卖出。"""
    indicators = {"rsi": 50, "trend": "Strong Downtrend"}
    action, _ = rule_signal(indicators, has_position=True)
    assert action == "SELL"


def test_rule_signal_custom_thresholds():
    """rsi_buy=40, rsi_sell=60，更激进。"""
    indicators = {"rsi": 35, "trend": "Uptrend"}
    action, _ = rule_signal(indicators, has_position=False, rsi_buy=40)
    assert action == "BUY"


# --- run（端到端）-------------------------------------------------------

def test_run_returns_result_object():
    prices = [100 + i * 0.5 for i in range(80)]
    klines = _make_klines(prices)
    result = run(klines, initial_cash=10_000)
    assert isinstance(result, PaperTradeResult)
    assert result.initial_cash == 10_000


def test_run_equity_curve_length_matches_klines():
    prices = [100] * 60
    klines = _make_klines(prices)
    result = run(klines, warmup=20)
    assert len(result.equity_curve) == len(klines)


def test_run_no_trades_in_warmup():
    prices = [100] * 60
    klines = _make_klines(prices)
    result = run(klines, warmup=30)
    for t in result.trades:
        assert t.timestamp_idx >= 30


def test_run_uptrend_captures_some_pnl():
    """单调上涨 → buy-and-hold 类策略至少买一次（如果有信号）。"""
    # 制造一个让 RSI 偶尔下到买点的震荡上行趋势
    import math
    prices = [100 * math.exp(i * 0.005 + 0.05 * math.sin(i / 5))
              for i in range(120)]
    klines = _make_klines(prices)
    result = run(klines, initial_cash=10_000, warmup=50)
    # 不要求一定赢钱，但应该至少跑通
    assert result.final_equity > 0
    assert isinstance(result.total_return, float)


def test_run_handles_empty_klines():
    """空 K 线不崩。"""
    result = run([], initial_cash=10_000)
    assert result.final_equity == 10_000
    assert result.n_trades == 0


def test_run_max_drawdown_negative_or_zero():
    prices = [100 + (i % 10) - 5 for i in range(80)]
    klines = _make_klines(prices)
    result = run(klines, warmup=30)
    assert result.max_drawdown <= 0


def test_run_no_position_at_end_if_all_sold():
    """完整 buy → sell 循环后应没持仓。"""
    # 价格先跌（触发 BUY 时 RSI 超卖）然后涨（触发 SELL 时 RSI 超买）
    prices = ([100 - i * 0.5 for i in range(30)]   # 跌
              + [85 + i * 1.0 for i in range(50)])  # 反弹
    klines = _make_klines(prices)
    result = run(klines, warmup=20)
    # 至少应该有 1 笔买 + 1 笔卖
    actions = [t.action for t in result.trades]
    if "BUY" in actions and "SELL" in actions:
        # 最后一笔应该是 SELL（持仓清空）
        assert result.position == 0


def test_run_with_custom_signal_fn():
    """自定义 signal_fn 也能跑通。"""
    def always_hold(ind, hp):
        return "HOLD", "never trade"

    klines = _make_klines([100] * 80)
    result = run(klines, signal_fn=always_hold, warmup=30)
    assert result.n_trades == 0


def test_run_commission_reduces_final_value():
    """高佣金 → 终值更低（执行了交易的话）。"""
    prices = ([100 - i * 0.5 for i in range(30)]
              + [85 + i * 1.0 for i in range(50)])
    klines = _make_klines(prices)
    low_comm = run(klines, commission=0.0001, warmup=20)
    high_comm = run(klines, commission=0.005, warmup=20)
    if low_comm.n_trades > 0:
        assert low_comm.final_equity >= high_comm.final_equity


# --- PaperTradeResult --------------------------------------------------

def test_total_return_calculation():
    result = PaperTradeResult(initial_cash=1000, final_equity=1500,
                              cash=500, position=10)
    assert result.total_return == 0.5


def test_total_return_zero_initial_safe():
    result = PaperTradeResult(initial_cash=0, final_equity=100,
                              cash=0, position=0)
    assert result.total_return == 0.0


def test_max_drawdown_empty():
    result = PaperTradeResult(initial_cash=1000, final_equity=1000,
                              cash=1000, position=0)
    assert result.max_drawdown == 0.0


def test_to_dict_json_serializable():
    import json
    klines = _make_klines([100 + i * 0.3 for i in range(80)])
    result = run(klines, warmup=30)
    d = result.to_dict()
    assert json.dumps(d)


def test_trade_to_dict():
    t = Trade(timestamp_idx=10, action="BUY", price=100, size=1,
              cash_after=900, position_after=1, reason="test")
    d = t.to_dict()
    assert d["action"] == "BUY"
    assert d["price"] == 100.0
