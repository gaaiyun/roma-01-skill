# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Base DEX Client

Abstract base class for all DEX implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any


class BaseDEXClient(ABC):
    """Abstract base class for DEX clients."""
    
    @abstractmethod
    async def get_account_balance(self) -> Dict:
        """Get account balance."""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Get open positions."""
        pass
    
    @abstractmethod
    async def get_market_price(self, symbol: str) -> float:
        """Get current market price."""
        pass
    
    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        interval: str = "3m",
        limit: int = 100,
    ) -> List[Dict]:
        """Get kline/candlestick data."""
        pass
    
    @abstractmethod
    async def close(self):
        """Close client connections."""
        pass
