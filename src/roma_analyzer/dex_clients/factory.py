# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - DEX Client Factory

Provides unified interface for multiple DEX implementations.
"""

from typing import Dict, Any, Optional
from loguru import logger


class DEXClientFactory:
    """Factory for creating DEX clients."""
    
    def __init__(self):
        """Initialize factory."""
        self._clients = {}
    
    def create_client(self, dex_type: str, config: Dict[str, Any]):
        """
        Create DEX client based on type.
        
        Args:
            dex_type: DEX type ("aster", "hyperliquid", "binance")
            config: DEX configuration
            
        Returns:
            DEX client instance
        """
        dex_type = dex_type.lower()
        
        if dex_type == "aster":
            return self._create_aster_client(config)
        elif dex_type == "hyperliquid":
            return self._create_hyperliquid_client(config)
        elif dex_type == "binance":
            return self._create_binance_client(config)
        else:
            raise ValueError(f"Unsupported DEX type: {dex_type}")
    
    def _create_aster_client(self, config: Dict[str, Any]):
        """Create Aster DEX client."""
        try:
            from .dex_clients.aster import AsterClient
            return AsterClient(
                user=config.get("user", ""),
                signer=config.get("signer", ""),
                private_key=config.get("private_key", ""),
                testnet=config.get("testnet", False),
            )
        except ImportError as e:
            logger.error(f"Failed to import Aster client: {e}")
            raise
    
    def _create_hyperliquid_client(self, config: Dict[str, Any]):
        """Create Hyperliquid DEX client."""
        try:
            from .dex_clients.hyperliquid import HyperliquidClient
            return HyperliquidClient(
                api_secret=config.get("api_secret", ""),
                account_id=config.get("account_id", ""),
                testnet=config.get("testnet", False),
            )
        except ImportError as e:
            logger.error(f"Failed to import Hyperliquid client: {e}")
            raise
    
    def _create_binance_client(self, config: Dict[str, Any]):
        """Create Binance client."""
        try:
            from .dex_clients.binance import BinanceClient
            return BinanceClient(
                api_key=config.get("api_key", ""),
                api_secret=config.get("api_secret", ""),
                testnet=config.get("testnet", False),
            )
        except ImportError as e:
            logger.error(f"Failed to import Binance client: {e}")
            raise
