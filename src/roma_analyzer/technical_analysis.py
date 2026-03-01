# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Technical Analysis Module

Provides technical indicators and market analysis.
"""

from typing import Dict, List, Optional
from loguru import logger


class TechnicalAnalyzer:
    """Technical analysis toolkit."""
    
    def analyze_klines(self, klines: List[Dict], interval: str = "3m") -> Dict:
        """
        Analyze kline data and calculate technical indicators.
        
        Args:
            klines: List of kline dicts with OHLCV data
            interval: Timeframe interval
            
        Returns:
            Dictionary with technical indicators
        """
        if not klines or len(klines) < 20:
            return self._empty_analysis()
        
        # Extract prices
        closes = [k["close"] for k in klines]
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        volumes = [k["volume"] for k in klines]
        
        # Calculate indicators
        rsi = self._calculate_rsi(closes, period=14)
        ema_20 = self._calculate_ema(closes, period=20)
        ema_50 = self._calculate_ema(closes, period=50) if len(closes) >= 50 else None
        macd, macd_signal, macd_hist = self._calculate_macd(closes)
        bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes)
        atr = self._calculate_atr(highs, lows, closes, period=14)
        adx = self._calculate_adx(highs, lows, closes, period=14)
        
        # Volume analysis
        avg_volume = sum(volumes[-20:]) / min(len(volumes), 20)
        current_volume = volumes[-1] if volumes else 0
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        # Trend detection
        trend = self._detect_trend(closes, ema_20, ema_50)
        
        # MACD signal
        macd_signal_str = "Bullish" if macd_hist > 0 else "Bearish" if macd_hist < 0 else "Neutral"
        
        return {
            "interval": interval,
            "rsi": rsi,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "macd": macd,
            "macd_signal": macd_signal,
            "macd_hist": macd_hist,
            "macd_signal_str": macd_signal_str,
            "bb_upper": bb_upper,
            "bb_middle": bb_middle,
            "bb_lower": bb_lower,
            "atr": atr,
            "adx": adx,
            "volume_ratio": volume_ratio,
            "trend": trend,
            "current_price": closes[-1] if closes else 0,
        }
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis when insufficient data."""
        return {
            "rsi": 50.0,
            "ema_20": 0.0,
            "ema_50": None,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_hist": 0.0,
            "macd_signal_str": "Neutral",
            "bb_upper": 0.0,
            "bb_middle": 0.0,
            "bb_lower": 0.0,
            "atr": 0.0,
            "adx": 0.0,
            "volume_ratio": 1.0,
            "trend": "Unknown",
        }
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return prices[-1] if prices else 0.0
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema
    
    def _calculate_macd(self, prices: List[float]) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < 26:
            return 0.0, 0.0, 0.0
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        macd = ema_12 - ema_26
        
        # Calculate signal line (9-period EMA of MACD)
        # Simplified: use last 9 MACD values
        macd_line = [macd]  # Simplified for demo
        signal = self._calculate_ema(macd_line, 9) if len(macd_line) >= 9 else macd
        
        hist = macd - signal
        
        return macd, signal, hist
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20) -> tuple:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            mid = prices[-1] if prices else 0.0
            return mid, mid, mid
        
        mid = sum(prices[-period:]) / period
        
        variance = sum((p - mid) ** 2 for p in prices[-period:]) / period
        std_dev = variance ** 0.5
        
        upper = mid + (2 * std_dev)
        lower = mid - (2 * std_dev)
        
        return upper, mid, lower
    
    def _calculate_atr(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(highs) < period + 1:
            return 0.0
        
        true_ranges = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1]),
            )
            true_ranges.append(tr)
        
        return sum(true_ranges[-period:]) / period
    
    def _calculate_adx(self, highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Calculate Average Directional Index (simplified)."""
        if len(highs) < period + 1:
            return 0.0
        
        # Simplified ADX calculation
        # Full implementation would require +DI and -DI calculations
        tr_sum = 0
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1]),
            )
            tr_sum += tr
        
        avg_tr = tr_sum / (len(highs) - 1)
        
        # Simplified: use price movement as proxy
        price_change = abs(closes[-1] - closes[-period]) if len(closes) > period else 0
        adx = (price_change / avg_tr * 100) if avg_tr > 0 else 0
        
        return min(adx, 100.0)  # Cap at 100
    
    def _detect_trend(self, prices: List[float], ema_20: float, ema_50: Optional[float]) -> str:
        """Detect trend direction."""
        if not prices:
            return "Unknown"
        
        current_price = prices[-1]
        
        if ema_50:
            if current_price > ema_20 > ema_50:
                return "Strong Uptrend"
            elif current_price < ema_20 < ema_50:
                return "Strong Downtrend"
            elif ema_20 > ema_50:
                return "Uptrend"
            elif ema_20 < ema_50:
                return "Downtrend"
            else:
                return "Sideways"
        else:
            if current_price > ema_20:
                return "Uptrend"
            elif current_price < ema_20:
                return "Downtrend"
            else:
                return "Sideways"
    
    def format_market_data(
        self,
        symbol: str,
        data_3m: Dict,
        data_4h: Optional[Dict] = None,
        language: str = "en",
    ) -> str:
        """Format market data for display."""
        if language == "zh":
            lines = [
                f"{symbol}:",
                f"  当前价：${data_3m.get('current_price', 0):,.2f}",
                f"  RSI: {data_3m.get('rsi', 0):.1f}",
                f"  MACD: {data_3m.get('macd_signal_str', 'Neutral')}",
                f"  趋势：{data_3m.get('trend', 'Unknown')}",
            ]
            if data_4h:
                lines.append(f"  4h RSI: {data_4h.get('rsi', 0):.1f}")
                lines.append(f"  4h 趋势：{data_4h.get('trend', 'Unknown')}")
        else:
            lines = [
                f"{symbol}:",
                f"  Price: ${data_3m.get('current_price', 0):,.2f}",
                f"  RSI: {data_3m.get('rsi', 0):.1f}",
                f"  MACD: {data_3m.get('macd_signal_str', 'Neutral')}",
                f"  Trend: {data_3m.get('trend', 'Unknown')}",
            ]
            if data_4h:
                lines.append(f"  4h RSI: {data_4h.get('rsi', 0):.1f}")
                lines.append(f"  4h Trend: {data_4h.get('trend', 'Unknown')}")
        
        return "\n".join(lines)
