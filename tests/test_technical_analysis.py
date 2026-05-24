"""TechnicalAnalyzer 单元测试 —— 验证技术指标计算正确性。"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from roma_analyzer.technical_analysis import TechnicalAnalyzer


@pytest.fixture
def analyzer():
    return TechnicalAnalyzer()


def _make_kline(close: float, high: float = None, low: float = None,
                volume: float = 1000) -> dict:
    return {
        "open": close,
        "high": high or close,
        "low": low or close,
        "close": close,
        "volume": volume,
    }


# --- analyze_klines ----------------------------------------------------------

def test_analyze_klines_insufficient_data_returns_empty(analyzer):
    """少于 20 根 K 线应返回 empty analysis。"""
    klines = [_make_kline(100.0) for _ in range(10)]
    result = analyzer.analyze_klines(klines)
    assert result["rsi"] == 50.0       # empty_analysis 默认值
    assert result["trend"] == "Unknown"


def test_analyze_klines_returns_all_fields(analyzer):
    """正常输入应包含所有字段。"""
    klines = [_make_kline(100 + i * 0.5, high=101 + i * 0.5,
                          low=99 + i * 0.5, volume=1000)
              for i in range(60)]
    result = analyzer.analyze_klines(klines)
    expected = {"rsi", "ema_20", "ema_50", "macd", "macd_signal",
                "macd_hist", "macd_signal_str", "bb_upper", "bb_middle",
                "bb_lower", "atr", "adx", "volume_ratio", "trend",
                "current_price"}
    assert expected.issubset(set(result.keys()))


def test_analyze_klines_ema_50_none_when_too_short(analyzer):
    """30 根 K 线 → 算得出 EMA20 但 EMA50 应为 None。"""
    klines = [_make_kline(100 + i * 0.5) for i in range(30)]
    result = analyzer.analyze_klines(klines)
    assert result["ema_50"] is None


# --- RSI --------------------------------------------------------------------

def test_rsi_all_gains_returns_100(analyzer):
    """单调上涨：无下跌 → RSI = 100"""
    prices = [100 + i for i in range(30)]
    rsi = analyzer._calculate_rsi(prices, period=14)
    assert rsi == 100.0


def test_rsi_too_few_returns_neutral(analyzer):
    """数据不足：返回中性 50."""
    rsi = analyzer._calculate_rsi([100, 101, 102], period=14)
    assert rsi == 50.0


def test_rsi_oscillating_in_range(analyzer):
    """震荡：RSI 应在 (0, 100) 区间。"""
    import random
    rng = random.Random(0)
    prices = [100 + rng.gauss(0, 1) for _ in range(50)]
    rsi = analyzer._calculate_rsi(prices, period=14)
    assert 0 < rsi < 100


def test_rsi_monotone_down_low(analyzer):
    """单调下跌 → RSI 应很低（≤ 5）。"""
    prices = [200 - i for i in range(30)]
    rsi = analyzer._calculate_rsi(prices, period=14)
    assert rsi <= 5.0


# --- EMA --------------------------------------------------------------------

def test_ema_constant_prices_equals_price(analyzer):
    """常数价格 → EMA = 价格。"""
    prices = [100.0] * 50
    assert analyzer._calculate_ema(prices, period=20) == 100.0


def test_ema_too_short_returns_last_price(analyzer):
    """数据少于 period → 返回最后价。"""
    prices = [100, 101, 102]
    assert analyzer._calculate_ema(prices, period=20) == 102


def test_ema_empty_returns_zero(analyzer):
    assert analyzer._calculate_ema([], period=20) == 0.0


def test_ema_trending_up(analyzer):
    """单调上涨 → EMA 应高于初始价。"""
    prices = list(range(100, 200))
    ema = analyzer._calculate_ema(prices, period=20)
    assert ema > 100


# --- MACD -------------------------------------------------------------------

def test_macd_returns_three_values(analyzer):
    prices = list(range(100, 150))
    macd, signal, hist = analyzer._calculate_macd(prices)
    assert isinstance(macd, float)
    assert isinstance(signal, float)
    assert isinstance(hist, float)


def test_macd_short_data_returns_zeros(analyzer):
    """数据少于 26 → 返回 (0, 0, 0)。"""
    macd, signal, hist = analyzer._calculate_macd([100] * 10)
    assert (macd, signal, hist) == (0.0, 0.0, 0.0)


def test_macd_uptrend_positive(analyzer):
    """上涨趋势：EMA12 > EMA26 → MACD > 0。"""
    prices = list(range(100, 200))
    macd, _, _ = analyzer._calculate_macd(prices)
    assert macd > 0


def test_macd_downtrend_negative(analyzer):
    prices = list(range(200, 100, -1))
    macd, _, _ = analyzer._calculate_macd(prices)
    assert macd < 0


# --- Bollinger Bands --------------------------------------------------------

def test_bollinger_middle_equals_sma(analyzer):
    prices = [100 + i for i in range(20)]
    upper, mid, lower = analyzer._calculate_bollinger_bands(prices, period=20)
    expected_mid = sum(prices) / 20
    assert mid == pytest.approx(expected_mid)


def test_bollinger_upper_above_lower(analyzer):
    prices = [100 + (i % 7) for i in range(30)]
    upper, mid, lower = analyzer._calculate_bollinger_bands(prices, period=20)
    assert upper > mid > lower


def test_bollinger_constant_prices_collapsed_bands(analyzer):
    """常数价格 → 上下轨与中轨重合。"""
    prices = [100.0] * 20
    upper, mid, lower = analyzer._calculate_bollinger_bands(prices, period=20)
    assert upper == mid == lower == 100.0


def test_bollinger_short_data_returns_constant(analyzer):
    upper, mid, lower = analyzer._calculate_bollinger_bands([100, 101], period=20)
    assert upper == mid == lower


# --- ATR --------------------------------------------------------------------

def test_atr_constant_prices_zero(analyzer):
    """常数 H/L/C → True Range 全 0 → ATR 0。"""
    highs = [100] * 20
    lows = [100] * 20
    closes = [100] * 20
    assert analyzer._calculate_atr(highs, lows, closes, period=14) == 0.0


def test_atr_short_data_returns_zero(analyzer):
    assert analyzer._calculate_atr([100, 101], [99, 100], [100, 101]) == 0.0


def test_atr_positive_when_volatile(analyzer):
    """有波动 → ATR > 0。"""
    highs = [100 + i * 2 for i in range(20)]
    lows = [99 + i * 2 for i in range(20)]
    closes = [99.5 + i * 2 for i in range(20)]
    atr = analyzer._calculate_atr(highs, lows, closes, period=14)
    assert atr > 0


# --- ADX --------------------------------------------------------------------

def test_adx_capped_at_100(analyzer):
    """ADX 上限 100。"""
    highs = [100 + i * 10 for i in range(20)]
    lows = [100 + i * 10 for i in range(20)]
    closes = [100 + i * 10 for i in range(20)]
    adx = analyzer._calculate_adx(highs, lows, closes)
    assert adx <= 100


def test_adx_returns_zero_for_short_data(analyzer):
    assert analyzer._calculate_adx([100], [99], [99.5]) == 0.0


# --- 趋势检测 ---------------------------------------------------------------

def test_detect_strong_uptrend(analyzer):
    """当前价 > EMA20 > EMA50 → Strong Uptrend"""
    prices = [120]
    assert analyzer._detect_trend(prices, ema_20=110, ema_50=100) == "Strong Uptrend"


def test_detect_strong_downtrend(analyzer):
    prices = [80]
    assert analyzer._detect_trend(prices, ema_20=90, ema_50=100) == "Strong Downtrend"


def test_detect_uptrend_no_ema50(analyzer):
    prices = [110]
    assert analyzer._detect_trend(prices, ema_20=100, ema_50=None) == "Uptrend"


def test_detect_downtrend_no_ema50(analyzer):
    prices = [90]
    assert analyzer._detect_trend(prices, ema_20=100, ema_50=None) == "Downtrend"


def test_detect_unknown_empty_prices(analyzer):
    assert analyzer._detect_trend([], 100, 100) == "Unknown"


# --- format_market_data -----------------------------------------------------

def test_format_market_data_chinese(analyzer):
    data = {"current_price": 50000, "rsi": 60, "macd_signal_str": "Bullish",
            "trend": "Uptrend"}
    out = analyzer.format_market_data("BTC", data, language="zh")
    assert "当前价" in out
    assert "BTC" in out
    assert "RSI" in out


def test_format_market_data_english(analyzer):
    data = {"current_price": 50000, "rsi": 60, "macd_signal_str": "Bullish",
            "trend": "Uptrend"}
    out = analyzer.format_market_data("BTC", data, language="en")
    assert "Price" in out
    assert "Trend" in out


def test_format_market_data_includes_4h(analyzer):
    data_3m = {"current_price": 50000, "rsi": 60}
    data_4h = {"rsi": 55, "trend": "Sideways"}
    out = analyzer.format_market_data("BTC", data_3m, data_4h, language="en")
    assert "4h" in out
