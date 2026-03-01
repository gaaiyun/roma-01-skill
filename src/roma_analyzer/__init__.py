# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer

AI-powered cryptocurrency trading analysis tool based on the ROMA framework.
"""

__version__ = "1.0.0"
__author__ = "Based on ROMA-01 by lukema95"

from .analyzer import TradingAnalyzer
from .config import load_config, Config

__all__ = ["TradingAnalyzer", "load_config", "Config"]
