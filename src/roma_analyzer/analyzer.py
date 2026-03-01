# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Core Module

Provides AI-powered market analysis and trading suggestions.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger
import dspy

from .config import load_config, Config
from .dex_clients.factory import DEXClientFactory
from .llm_clients.factory import LLMClientFactory
from .technical_analysis import TechnicalAnalyzer
from .risk_manager import RiskManager
from .decision_logger import DecisionLogger


class TradingSuggestion(dspy.Signature):
    """AI Trading Suggestion Signature."""
    
    system_prompt: str = dspy.InputField(desc="Trading rules and constraints")
    market_context: str = dspy.InputField(desc="Current market state, account, positions")
    
    chain_of_thought: str = dspy.OutputField(desc="Reasoning process and analysis")
    action: str = dspy.OutputField(desc="Trading action: OPEN_LONG, OPEN_SHORT, CLOSE_LONG, CLOSE_SHORT, HOLD, WAIT")
    confidence: float = dspy.OutputField(desc="Confidence score 0-100")
    key_levels: str = dspy.OutputField(desc="JSON object with support/resistance levels")
    risk_warning: str = dspy.OutputField(desc="Risk warning or important notes")


class TradingAnalyzer:
    """
    AI-powered trading analyzer.
    
    Simplified version of ROMA TradingAgent, focused on analysis
    rather than automatic execution.
    """
    
    def __init__(self, config: Config):
        """
        Initialize trading analyzer.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.agent_config = config.get("agents", [{}])[0] if config.get("agents") else {}
        
        # Initialize DEX client
        self.dex_factory = DEXClientFactory()
        self.dex = self._init_dex_client()
        
        # Initialize technical analyzer
        self.ta = TechnicalAnalyzer()
        
        # Initialize risk manager
        self.risk_manager = RiskManager(self.agent_config.get("strategy", {}))
        
        # Initialize decision logger
        self.logger = DecisionLogger()
        
        # Initialize LLM client
        self.llm_factory = LLMClientFactory()
        llm_config = self.agent_config.get("llm", {})
        self.lm = self.llm_factory.create_client(llm_config)
        
        # Initialize DSPy module
        self.suggestion_module = dspy.ChainOfThought(TradingSuggestion)
        
        logger.info(f"Initialized TradingAnalyzer with {self.agent_config.get('llm', {}).get('provider', 'unknown')} model")
    
    def _init_dex_client(self):
        """Initialize DEX client based on configuration."""
        exchange_config = self.agent_config.get("exchange", {})
        dex_type = exchange_config.get("type", "aster").lower()
        
        try:
            return self.dex_factory.create_client(dex_type, exchange_config)
        except Exception as e:
            logger.warning(f"Failed to initialize DEX client: {e}. Analysis features will be limited.")
            return None
    
    async def analyze_market(self, symbol: str) -> Dict:
        """
        Analyze market conditions for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            
        Returns:
            Dictionary with market analysis results
        """
        if not self.dex:
            return {"error": "DEX client not initialized", "symbol": symbol}
        
        try:
            # Fetch market data
            klines_3m = await self.dex.get_klines(symbol, interval="3m", limit=100)
            klines_15m = await self.dex.get_klines(symbol, interval="15m", limit=100)
            klines_1h = await self.dex.get_klines(symbol, interval="1h", limit=100)
            klines_4h = await self.dex.get_klines(symbol, interval="4h", limit=100)
            
            # Get current price
            current_price = await self.dex.get_market_price(symbol)
            
            # Technical analysis
            ta_3m = self.ta.analyze_klines(klines_3m, interval="3m")
            ta_15m = self.ta.analyze_klines(klines_15m, interval="15m")
            ta_1h = self.ta.analyze_klines(klines_1h, interval="1h")
            ta_4h = self.ta.analyze_klines(klines_4h, interval="4h")
            
            # Get funding rate if available
            funding_rate = None
            try:
                if hasattr(self.dex, "get_funding_rate"):
                    funding_rate = await self.dex.get_funding_rate(symbol)
            except Exception as e:
                logger.debug(f"Failed to fetch funding rate: {e}")
            
            # Build analysis result
            analysis = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "price": {
                    "current": current_price,
                    "change_24h": self._calculate_24h_change(klines_4h),
                    "high_24h": max([k["high"] for k in klines_4h[-24:]]),
                    "low_24h": min([k["low"] for k in klines_4h[-24:]]),
                },
                "technical": {
                    "rsi": ta_3m.get("rsi", 0),
                    "macd_signal": ta_3m.get("macd_signal", "Neutral"),
                    "ema_20": ta_3m.get("ema_20", 0),
                    "ema_50": ta_1h.get("ema_50", 0),
                    "bb_upper": ta_3m.get("bb_upper", 0),
                    "bb_lower": ta_3m.get("bb_lower", 0),
                    "adx": ta_4h.get("adx", 0),
                },
                "multi_timeframe": {
                    "3m": ta_3m,
                    "15m": ta_15m,
                    "1h": ta_1h,
                    "4h": ta_4h,
                },
                "funding_rate": funding_rate,
            }
            
            logger.info(f"Market analysis complete for {symbol}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze market: {e}", exc_info=True)
            return {"error": str(e), "symbol": symbol}
    
    async def get_suggestion(self, symbol: str, language: str = "zh") -> Dict:
        """
        Get AI trading suggestion for a symbol.
        
        Args:
            symbol: Trading pair symbol
            language: Language for prompts ("zh" or "en")
            
        Returns:
            Dictionary with AI suggestion
        """
        try:
            # Get market analysis
            analysis = await self.analyze_market(symbol)
            if "error" in analysis:
                return analysis
            
            # Get account state
            balance = await self.get_balance() if self.dex else {}
            positions = await self.get_positions() if self.dex else []
            
            # Build prompts
            system_prompt = self._build_system_prompt(language=language)
            market_context = self._build_market_context(
                symbol=symbol,
                analysis=analysis,
                balance=balance,
                positions=positions,
                language=language,
            )
            
            # Get AI suggestion
            logger.info(f"Getting AI suggestion for {symbol}")
            with dspy.context(lm=self.lm):
                result = await asyncio.to_thread(
                    self.suggestion_module,
                    system_prompt=system_prompt,
                    market_context=market_context,
                )
            
            # Parse result
            try:
                key_levels = json.loads(result.key_levels)
            except:
                key_levels = {}
            
            suggestion = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "action": result.action,
                "confidence": float(result.confidence),
                "chain_of_thought": result.chain_of_thought,
                "key_levels": key_levels,
                "risk_warning": result.risk_warning,
            }
            
            # Log decision
            self.logger.log_suggestion(suggestion)
            
            logger.info(f"AI suggestion: {result.action} (confidence: {result.confidence:.0f}%)")
            return suggestion
            
        except Exception as e:
            logger.error(f"Failed to get AI suggestion: {e}", exc_info=True)
            return {"error": str(e), "symbol": symbol}
    
    async def get_positions(self) -> List[Dict]:
        """Get current open positions."""
        if not self.dex:
            return []
        
        try:
            positions = await self.dex.get_positions()
            
            # Add P/L calculations
            for pos in positions:
                entry = pos.get("entry_price", 0)
                mark = pos.get("mark_price", 0)
                amt = pos.get("position_amt", 0)
                side = pos.get("side", "long")
                
                if side == "long":
                    pnl_pct = (mark - entry) / entry * 100 if entry > 0 else 0
                else:
                    pnl_pct = (entry - mark) / entry * 100 if entry > 0 else 0
                
                pnl_usd = amt * (mark - entry) if side == "long" else amt * (entry - mark)
                
                pos["pnl_pct"] = pnl_pct
                pos["pnl_usd"] = pnl_usd
            
            return positions
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def get_balance(self) -> Dict:
        """Get account balance."""
        if not self.dex:
            return {}
        
        try:
            balance = await self.dex.get_account_balance()
            
            # Add risk limits
            risk_config = self.agent_config.get("strategy", {}).get("risk_management", {})
            balance["max_total_position_pct"] = risk_config.get("max_total_position_pct", 80)
            
            # Calculate margin usage
            positions = await self.get_positions()
            total_margin = sum(
                abs(p.get("position_amt", 0)) * p.get("entry_price", 0) / p.get("leverage", 1)
                for p in positions
            )
            balance["total_margin_used"] = total_margin
            
            return balance
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return {}
    
    async def get_history(self, limit: int = 10) -> List[Dict]:
        """Get decision history."""
        return self.logger.get_history(limit=limit)
    
    def _build_system_prompt(self, language: str = "zh") -> str:
        """Build system prompt with trading rules."""
        risk = self.agent_config.get("strategy", {}).get("risk_management", {})
        
        if language == "zh":
            return f"""你是一个专业的加密货币交易分析师。请根据提供的市场数据给出交易建议。

交易规则：
- 最大持仓数：{risk.get('max_positions', 3)}
- 最大杠杆：{risk.get('max_leverage', 10)}x
- 单笔仓位上限：{risk.get('max_position_size_pct', 30)}%
- 总仓位上限：{risk.get('max_total_position_pct', 80)}%
- 止损：{risk.get('stop_loss_pct', 3)}%
- 止盈：{risk.get('take_profit_pct', 10)}%

可用操作：
- OPEN_LONG: 开多单
- OPEN_SHORT: 开空单
- CLOSE_LONG: 平多单
- CLOSE_SHORT: 平空单
- HOLD: 持有现有仓位
- WAIT: 等待更好机会

请谨慎分析，优先考虑风险控制。"""
        else:
            return f"""You are a professional crypto trading analyst. Provide trading suggestions based on market data.

Trading Rules:
- Max positions: {risk.get('max_positions', 3)}
- Max leverage: {risk.get('max_leverage', 10)}x
- Single position limit: {risk.get('max_position_size_pct', 30)}%
- Total position limit: {risk.get('max_total_position_pct', 80)}%
- Stop loss: {risk.get('stop_loss_pct', 3)}%
- Take profit: {risk.get('take_profit_pct', 10)}%

Available Actions:
- OPEN_LONG: Open long position
- OPEN_SHORT: Open short position
- CLOSE_LONG: Close long position
- CLOSE_SHORT: Close short position
- HOLD: Hold current positions
- WAIT: Wait for better opportunity

Prioritize risk management in your analysis."""
    
    def _build_market_context(
        self,
        symbol: str,
        analysis: Dict,
        balance: Dict,
        positions: List[Dict],
        language: str = "zh",
    ) -> str:
        """Build market context for AI."""
        lines = []
        
        if language == "zh":
            lines.append(f"**分析标的**: {symbol}")
            lines.append(f"\n**账户信息**:")
            lines.append(f"可用余额：${balance.get('available_balance', 0):,.2f}")
            lines.append(f"总余额：${balance.get('total_wallet_balance', 0):,.2f}")
            
            if positions:
                lines.append(f"\n**当前持仓 **({len(positions)}个):")
                for pos in positions:
                    side = "多" if pos.get("side") == "long" else "空"
                    pnl = pos.get("pnl_pct", 0)
                    lines.append(f"- {pos['symbol']} {side}单：盈亏 {pnl:+.2f}%")
            else:
                lines.append("\n**当前持仓**: 无")
            
            lines.append(f"\n**市场分析**:")
            price = analysis.get("price", {})
            lines.append(f"当前价格：${price.get('current', 0):,.2f} (24h: {price.get('change_24h', 0):+.2f}%)")
            
            tech = analysis.get("technical", {})
            lines.append(f"RSI: {tech.get('rsi', 0):.1f}")
            lines.append(f"MACD: {tech.get('macd_signal', 'Neutral')}")
            lines.append(f"布林带：${tech.get('bb_lower', 0):,.2f} - ${tech.get('bb_upper', 0):,.2f}")
            
        else:
            lines.append(f"**Symbol**: {symbol}")
            lines.append(f"\n**Account**:")
            lines.append(f"Available: ${balance.get('available_balance', 0):,.2f}")
            lines.append(f"Total: ${balance.get('total_wallet_balance', 0):,.2f}")
            
            if positions:
                lines.append(f"\n**Positions **({len(positions)}):")
                for pos in positions:
                    side = pos.get("side", "long").upper()
                    pnl = pos.get("pnl_pct", 0)
                    lines.append(f"- {pos['symbol']} {side}: P/L {pnl:+.2f}%")
            else:
                lines.append("\n**Positions**: None")
            
            lines.append(f"\n**Market Analysis**:")
            price = analysis.get("price", {})
            lines.append(f"Price: ${price.get('current', 0):,.2f} (24h: {price.get('change_24h', 0):+.2f}%)")
            
            tech = analysis.get("technical", {})
            lines.append(f"RSI: {tech.get('rsi', 0):.1f}")
            lines.append(f"MACD: {tech.get('macd_signal', 'Neutral')}")
            lines.append(f"Bollinger: ${tech.get('bb_lower', 0):,.2f} - ${tech.get('bb_upper', 0):,.2f}")
        
        return "\n".join(lines)
    
    def _calculate_24h_change(self, klines: List[Dict]) -> float:
        """Calculate 24h price change percentage."""
        if len(klines) < 2:
            return 0.0
        
        old_price = klines[-2]["close"]
        current_price = klines[-1]["close"]
        
        return (current_price - old_price) / old_price * 100 if old_price > 0 else 0.0
    
    async def close(self):
        """Close connections."""
        if self.dex and hasattr(self.dex, "close"):
            await self.dex.close()
        
        logger.info("TradingAnalyzer closed")
