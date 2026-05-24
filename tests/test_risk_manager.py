"""RiskManager 4 层风控测试。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from roma_analyzer.risk_manager import RiskManager


@pytest.fixture
def default_config() -> dict:
    return {
        "risk_management": {
            "max_positions": 3,
            "max_leverage": 10,
            "max_position_size_pct": 30,
            "max_total_position_pct": 80,
            "max_single_trade_pct": 50,
            "max_single_trade_with_positions_pct": 30,
            "max_daily_loss_pct": 15,
            "stop_loss_pct": 3,
            "take_profit_pct": 10,
        }
    }


@pytest.fixture
def rm(default_config):
    return RiskManager(default_config)


# --- 初始化 -----------------------------------------------------------------

def test_initialization_reads_config(rm):
    assert rm.max_positions == 3
    assert rm.max_leverage == 10
    assert rm.max_position_size_pct == 30


def test_initialization_with_empty_config_uses_defaults():
    rm = RiskManager({})
    assert rm.max_positions == 3
    assert rm.max_leverage == 10


# --- Layer 1: 单笔交易限额 -------------------------------------------------

def test_single_trade_within_limit_when_no_positions(rm):
    """无持仓 → 50% 限制；$200 在 $1000 上不超 50%。"""
    allowed, adjusted, reason = rm.check_single_trade_limit(
        position_size_usd=200, available_balance=1000, has_positions=False)
    assert allowed is True
    assert adjusted == 200


def test_single_trade_over_limit_when_no_positions(rm):
    """$600 在 $1000 上 = 60% > 50% → 被截到 $500。"""
    allowed, adjusted, reason = rm.check_single_trade_limit(
        position_size_usd=600, available_balance=1000, has_positions=False)
    assert allowed is False
    assert adjusted == 500
    assert "50%" in reason


def test_single_trade_stricter_limit_with_positions(rm):
    """有持仓 → 30% 限制；$400 > 30% × $1000 = $300 → 截到 $300。"""
    allowed, adjusted, reason = rm.check_single_trade_limit(
        position_size_usd=400, available_balance=1000, has_positions=True)
    assert allowed is False
    assert adjusted == 300


# --- Layer 2: 总持仓限额 ---------------------------------------------------

def test_total_position_within_limit(rm):
    """已用 $300，新 $200，总 $500 < 80% × $1000 = $800 → OK。"""
    allowed, reason = rm.check_total_position_limit(
        current_margin_used=300, new_position_margin=200, total_balance=1000)
    assert allowed is True


def test_total_position_over_limit(rm):
    """已用 $700，新 $200，总 $900 > $800 → 不允许。"""
    allowed, reason = rm.check_total_position_limit(
        current_margin_used=700, new_position_margin=200, total_balance=1000)
    assert allowed is False


# --- Layer 3: 单仓限额 -----------------------------------------------------

def test_per_position_within_limits(rm):
    allowed, reason = rm.check_position_limits(
        position_size_pct=20, leverage=5, num_positions=1)
    assert allowed is True


def test_per_position_too_many_positions(rm):
    """已有 max_positions 个持仓 → 不允许再开。"""
    allowed, reason = rm.check_position_limits(
        position_size_pct=20, leverage=5, num_positions=3)
    assert allowed is False
    assert "Max positions" in reason


def test_per_position_size_exceeds_limit(rm):
    allowed, reason = rm.check_position_limits(
        position_size_pct=50, leverage=5, num_positions=0)
    assert allowed is False
    assert "Position size" in reason


def test_per_position_leverage_exceeds(rm):
    allowed, reason = rm.check_position_limits(
        position_size_pct=20, leverage=20, num_positions=0)
    assert allowed is False
    assert "Leverage" in reason


# --- Layer 4: 日亏损限额 ---------------------------------------------------

def test_daily_pnl_positive_ok(rm):
    """日盈利 → 永远 OK。"""
    allowed, reason = rm.check_daily_loss(daily_pnl=50, total_balance=1000)
    assert allowed is True


def test_daily_loss_within_limit(rm):
    """亏 10% < 15% → OK。"""
    allowed, reason = rm.check_daily_loss(daily_pnl=-100, total_balance=1000)
    assert allowed is True


def test_daily_loss_exceeds_limit(rm):
    """亏 20% > 15% → 不允许。"""
    allowed, reason = rm.check_daily_loss(daily_pnl=-200, total_balance=1000)
    assert allowed is False
    assert "Daily loss" in reason


# --- validate_trade（综合 4 层）-------------------------------------------

def test_validate_trade_passes_all_layers(rm):
    valid, adjusted, reasons = rm.validate_trade(
        position_size_usd=200, leverage=5,
        available_balance=1000, total_balance=1000,
        current_positions=[], daily_pnl=0,
    )
    assert valid is True
    assert adjusted == 200
    assert reasons == []


def test_validate_trade_caught_by_single_trade_limit(rm):
    """无持仓 → 50% 限制 → 截掉超出部分。"""
    valid, adjusted, reasons = rm.validate_trade(
        position_size_usd=800, leverage=5,
        available_balance=1000, total_balance=1000,
        current_positions=[], daily_pnl=0,
    )
    assert adjusted == 500
    assert len(reasons) > 0


def test_validate_trade_blocked_by_max_positions(rm):
    """已有 3 个持仓 → 不允许再开。"""
    positions = [{"position_amt": 1, "entry_price": 100, "leverage": 1}] * 3
    valid, adjusted, reasons = rm.validate_trade(
        position_size_usd=100, leverage=5,
        available_balance=1000, total_balance=1000,
        current_positions=positions, daily_pnl=0,
    )
    assert any("Max positions" in r for r in reasons)


def test_validate_trade_blocked_by_daily_loss(rm):
    valid, adjusted, reasons = rm.validate_trade(
        position_size_usd=100, leverage=5,
        available_balance=1000, total_balance=1000,
        current_positions=[], daily_pnl=-200,    # 亏 20% > 15%
    )
    assert any("Daily loss" in r for r in reasons)


# --- calculate_position_size -----------------------------------------------

def test_calculate_position_size_scales_with_confidence(rm):
    """置信度越高 → 仓位越大。"""
    low = rm.calculate_position_size("BTC", 50000, 10000, leverage=5, confidence=20)
    high = rm.calculate_position_size("BTC", 50000, 10000, leverage=5, confidence=80)
    assert high > low


def test_calculate_position_size_caps_at_max(rm):
    """置信度 100% → 不超过 max_position_size_pct（30%）。"""
    size = rm.calculate_position_size("BTC", 50000, 10000,
                                       leverage=5, confidence=100)
    assert size <= 10000 * 0.30   # 30%


def test_calculate_position_size_min_5pct(rm):
    """置信度 0% → 最小 5%。"""
    size = rm.calculate_position_size("BTC", 50000, 10000,
                                       leverage=5, confidence=0)
    assert size >= 10000 * 0.05
