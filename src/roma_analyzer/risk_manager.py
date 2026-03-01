# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Risk Manager

Implements 4-layer risk management system.
"""

from typing import Dict, List, Optional
from loguru import logger


class RiskManager:
    """
    Risk management system with 4-layer protection.
    
    Layers:
    1. Single trade limits
    2. Total position limit
    3. Per-position limits
    4. Daily limits
    """
    
    def __init__(self, strategy_config: Dict):
        """
        Initialize risk manager.
        
        Args:
            strategy_config: Strategy configuration with risk_management section
        """
        risk_config = strategy_config.get("risk_management", {})
        
        self.max_positions = risk_config.get("max_positions", 3)
        self.max_leverage = risk_config.get("max_leverage", 10)
        self.max_position_size_pct = risk_config.get("max_position_size_pct", 30)
        self.max_total_position_pct = risk_config.get("max_total_position_pct", 80)
        self.max_single_trade_pct = risk_config.get("max_single_trade_pct", 50)
        self.max_single_trade_with_positions_pct = risk_config.get(
            "max_single_trade_with_positions_pct", 30
        )
        self.max_daily_loss_pct = risk_config.get("max_daily_loss_pct", 15)
        self.stop_loss_pct = risk_config.get("stop_loss_pct", 3)
        self.take_profit_pct = risk_config.get("take_profit_pct", 10)
        
        logger.info("Initialized RiskManager with 4-layer protection")
    
    def check_single_trade_limit(
        self,
        position_size_usd: float,
        available_balance: float,
        has_positions: bool,
    ) -> tuple:
        """
        Check single trade limit (Layer 1).
        
        Args:
            position_size_usd: Proposed position size in USD
            available_balance: Available balance
            has_positions: Whether account has existing positions
            
        Returns:
            (allowed: bool, adjusted_size: float, reason: str)
        """
        if has_positions:
            max_pct = self.max_single_trade_with_positions_pct
        else:
            max_pct = self.max_single_trade_pct
        
        max_amount = available_balance * (max_pct / 100)
        
        if position_size_usd > max_amount:
            logger.warning(
                f"Position size ${position_size_usd:.2f} exceeds {max_pct}% limit "
                f"(${max_amount:.2f}). Adjusting to limit."
            )
            return False, max_amount, f"Exceeds {max_pct}% single trade limit"
        
        return True, position_size_usd, "OK"
    
    def check_total_position_limit(
        self,
        current_margin_used: float,
        new_position_margin: float,
        total_balance: float,
    ) -> tuple:
        """
        Check total position limit (Layer 2).
        
        Args:
            current_margin_used: Current total margin used
            new_position_margin: New position margin
            total_balance: Total account balance
            
        Returns:
            (allowed: bool, reason: str)
        """
        total_margin_after = current_margin_used + new_position_margin
        max_total_margin = total_balance * (self.max_total_position_pct / 100)
        
        if total_margin_after > max_total_margin:
            remaining = max_total_margin - current_margin_used
            if remaining < 0.1:
                return False, f"Total position limit reached ({self.max_total_position_pct}%)"
            
            logger.warning(
                f"Total position would exceed {self.max_total_position_pct}% limit. "
                f"Reducing from ${new_position_margin:.2f} to ${remaining:.2f}"
            )
            return False, f"Reduced to stay within {self.max_total_position_pct}% limit"
        
        return True, "OK"
    
    def check_position_limits(
        self,
        position_size_pct: float,
        leverage: int,
        num_positions: int,
    ) -> tuple:
        """
        Check per-position limits (Layer 3).
        
        Args:
            position_size_pct: Position size as percentage of account
            leverage: Proposed leverage
            num_positions: Current number of positions
            
        Returns:
            (allowed: bool, reason: str)
        """
        # Check position count
        if num_positions >= self.max_positions:
            return False, f"Max positions ({self.max_positions}) reached"
        
        # Check position size
        if position_size_pct > self.max_position_size_pct:
            return False, f"Position size exceeds {self.max_position_size_pct}%"
        
        # Check leverage
        if leverage > self.max_leverage:
            return False, f"Leverage exceeds max {self.max_leverage}x"
        
        return True, "OK"
    
    def check_daily_loss(
        self,
        daily_pnl: float,
        total_balance: float,
    ) -> tuple:
        """
        Check daily loss limit (Layer 4).
        
        Args:
            daily_pnl: Daily P/L (negative = loss)
            total_balance: Total account balance
            
        Returns:
            (allowed: bool, reason: str)
        """
        if daily_pnl >= 0:
            return True, "OK"
        
        daily_loss_pct = abs(daily_pnl) / total_balance * 100
        
        if daily_loss_pct >= self.max_daily_loss_pct:
            return False, f"Daily loss limit reached ({self.max_daily_loss_pct}%)"
        
        return True, "OK"
    
    def validate_trade(
        self,
        position_size_usd: float,
        leverage: int,
        available_balance: float,
        total_balance: float,
        current_positions: List[Dict],
        daily_pnl: float = 0.0,
    ) -> tuple:
        """
        Validate a trade against all risk layers.
        
        Args:
            position_size_usd: Proposed position size
            leverage: Proposed leverage
            available_balance: Available balance
            total_balance: Total balance
            current_positions: List of current positions
            daily_pnl: Daily P/L
            
        Returns:
            (valid: bool, adjusted_size: float, reasons: List[str])
        """
        reasons = []
        adjusted_size = position_size_usd
        has_positions = len(current_positions) > 0
        
        # Layer 1: Single trade limit
        allowed, adjusted_size, reason = self.check_single_trade_limit(
            position_size_usd, available_balance, has_positions
        )
        if not allowed:
            reasons.append(reason)
        
        # Layer 2: Total position limit
        current_margin = sum(
            abs(p.get("position_amt", 0)) * p.get("entry_price", 0) / p.get("leverage", 1)
            for p in current_positions
        )
        allowed, reason = self.check_total_position_limit(
            current_margin, adjusted_size, total_balance
        )
        if not allowed:
            reasons.append(reason)
            # Adjust size to fit
            max_allowed = current_margin * (self.max_total_position_pct / 100) - current_margin
            adjusted_size = max(0, max_allowed)
        
        # Layer 3: Per-position limits
        position_size_pct = (adjusted_size / total_balance) * 100
        allowed, reason = self.check_position_limits(
            position_size_pct, leverage, len(current_positions)
        )
        if not allowed:
            reasons.append(reason)
        
        # Layer 4: Daily loss limit
        allowed, reason = self.check_daily_loss(daily_pnl, total_balance)
        if not allowed:
            reasons.append(reason)
        
        valid = len(reasons) == 0 or adjusted_size > 0
        
        return valid, adjusted_size, reasons
    
    def calculate_position_size(
        self,
        symbol: str,
        price: float,
        balance: float,
        leverage: int,
        confidence: float,
    ) -> float:
        """
        Calculate optimal position size based on confidence and risk parameters.
        
        Args:
            symbol: Trading pair
            price: Current price
            balance: Available balance
            leverage: Leverage to use
            confidence: AI confidence score (0-100)
            
        Returns:
            Position size in USD
        """
        # Base size: percentage of balance
        base_pct = self.max_position_size_pct
        
        # Adjust based on confidence
        confidence_factor = confidence / 100.0
        adjusted_pct = base_pct * confidence_factor
        
        # Ensure within limits
        adjusted_pct = min(adjusted_pct, self.max_position_size_pct)
        adjusted_pct = max(adjusted_pct, 5.0)  # Minimum 5%
        
        position_size = balance * (adjusted_pct / 100)
        
        logger.debug(
            f"Calculated position size for {symbol}: ${position_size:.2f} "
            f"({adjusted_pct:.1f}% of balance, confidence: {confidence:.0f}%)"
        )
        
        return position_size
