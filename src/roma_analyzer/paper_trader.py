# -*- coding: utf-8 -*-
"""ROMA-01 Paper Trading Simulator.

把历史 K 线灌进 TechnicalAnalyzer，按简单规则（RSI 超卖买、超买卖；可叠加
EMA 趋势过滤）出信号，再用模拟账户（cash + position）跑一遍，输出 PnL 曲线
和交易记录。

为什么不直接用真 ``analyzer.py`` 走 LLM 决策？
LLM 决策每条 K 线就要一次 LLM 调用 —— 跑一年日线就是 365 次，太贵 + 太慢。
本模块用纯规则信号，给"风控逻辑 + 技术指标 + 仓位管理"三层做端到端 sanity
check，验证整套系统在历史数据上不会爆账户。

要换成 LLM 决策的话，把 ``rule_signal`` 替换成调 LLM 的回调即可。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from loguru import logger

from .technical_analysis import TechnicalAnalyzer


# --- 数据结构 ---------------------------------------------------------------

@dataclass
class Trade:
    timestamp_idx: int        # K 线序号
    action: str               # "BUY" / "SELL"
    price: float
    size: float
    cash_after: float
    position_after: float
    reason: str

    def to_dict(self) -> dict:
        return {
            "timestamp_idx": int(self.timestamp_idx),
            "action": self.action,
            "price": float(self.price),
            "size": float(self.size),
            "cash_after": float(self.cash_after),
            "position_after": float(self.position_after),
            "reason": self.reason,
        }


@dataclass
class PaperTradeResult:
    initial_cash: float
    final_equity: float
    cash: float
    position: float
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    signals: List[str] = field(default_factory=list)    # "BUY" / "SELL" / "HOLD"

    @property
    def total_return(self) -> float:
        if self.initial_cash <= 0:
            return 0.0
        return self.final_equity / self.initial_cash - 1

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for v in self.equity_curve:
            if v > peak:
                peak = v
            if peak > 0:
                dd = v / peak - 1
                if dd < max_dd:
                    max_dd = dd
        return max_dd

    def to_dict(self) -> dict:
        return {
            "initial_cash": float(self.initial_cash),
            "final_equity": float(self.final_equity),
            "total_return": float(self.total_return),
            "max_drawdown": float(self.max_drawdown),
            "n_trades": int(self.n_trades),
            "cash_remaining": float(self.cash),
            "position_remaining": float(self.position),
            "trades": [t.to_dict() for t in self.trades],
        }


# --- 简单规则信号 -----------------------------------------------------------

def rule_signal(indicators: Dict, has_position: bool,
                rsi_buy: float = 30, rsi_sell: float = 70,
                use_trend: bool = True) -> Tuple[str, str]:
    """基于技术指标的规则信号生成器。

    返回 (action, reason)：action ∈ {"BUY", "SELL", "HOLD"}.

    - RSI < rsi_buy 且趋势不向下 → BUY
    - RSI > rsi_sell → SELL（已有持仓时）
    """
    rsi = indicators.get("rsi", 50)
    trend = indicators.get("trend", "Unknown")

    if has_position:
        if rsi > rsi_sell:
            return "SELL", f"RSI={rsi:.1f} > {rsi_sell}（超买，止盈）"
        if use_trend and trend in ("Strong Downtrend", "Downtrend"):
            return "SELL", f"趋势 {trend}（止损）"
        return "HOLD", "持仓中，无卖出信号"

    if rsi < rsi_buy:
        if use_trend and trend == "Strong Downtrend":
            return "HOLD", f"RSI={rsi:.1f} 但趋势强空，等右侧"
        return "BUY", f"RSI={rsi:.1f} < {rsi_buy}（超卖）"
    return "HOLD", "无入场信号"


# --- 模拟器 ---------------------------------------------------------------

def run(
    klines: List[Dict],
    initial_cash: float = 10_000.0,
    allocation: float = 0.95,
    commission: float = 0.001,
    warmup: int = 50,
    signal_fn: Optional[Callable[[Dict, bool], Tuple[str, str]]] = None,
    analyzer: Optional[TechnicalAnalyzer] = None,
) -> PaperTradeResult:
    """走一遍历史 K 线，按规则信号交易。

    Parameters
    ----------
    klines : 每个含 open/high/low/close/volume 的 dict
    initial_cash : 初始现金
    allocation : 单次建仓使用资金比例（剩 5% 作为缓冲）
    commission : 单边费率
    warmup : 前 warmup 根 K 线只看不交易（指标没算稳定）
    signal_fn : 信号函数 (indicators, has_position) -> (action, reason)
    """
    if signal_fn is None:
        signal_fn = lambda ind, hp: rule_signal(ind, hp)
    if analyzer is None:
        analyzer = TechnicalAnalyzer()

    cash = initial_cash
    position = 0.0
    trades: List[Trade] = []
    equity_curve: List[float] = []
    signals: List[str] = []

    for i, kline in enumerate(klines):
        current_price = kline["close"]
        # 先记 equity（按收盘价）
        equity = cash + position * current_price
        equity_curve.append(equity)

        if i < warmup:
            signals.append("HOLD")
            continue

        # 用历史 K 线算指标
        window = klines[: i + 1]
        indicators = analyzer.analyze_klines(window)

        has_position = position > 0
        action, reason = signal_fn(indicators, has_position)
        signals.append(action)

        if action == "BUY" and not has_position:
            buy_cash = cash * allocation
            size = buy_cash / (current_price * (1 + commission))
            cost = size * current_price * (1 + commission)
            if cost <= cash and size > 0:
                cash -= cost
                position += size
                trades.append(Trade(
                    timestamp_idx=i, action="BUY", price=current_price,
                    size=size, cash_after=cash, position_after=position,
                    reason=reason,
                ))
        elif action == "SELL" and has_position:
            proceeds = position * current_price * (1 - commission)
            cash += proceeds
            trades.append(Trade(
                timestamp_idx=i, action="SELL", price=current_price,
                size=position, cash_after=cash, position_after=0,
                reason=reason,
            ))
            position = 0

    # 终值（按最后一根收盘价 mark-to-market）
    final_price = klines[-1]["close"] if klines else 0
    final_equity = cash + position * final_price

    return PaperTradeResult(
        initial_cash=initial_cash,
        final_equity=final_equity,
        cash=cash,
        position=position,
        trades=trades,
        equity_curve=equity_curve,
        signals=signals,
    )
