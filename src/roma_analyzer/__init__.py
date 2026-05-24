# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer

AI-powered cryptocurrency trading analysis tool based on the ROMA framework.
"""

__version__ = "1.0.0"
__author__ = "Based on ROMA-01 by lukema95"

# 配置模块零依赖，可以直接 eager 加载
from .config import load_config, Config

# analyzer 依赖 dspy（重）。允许仅装 stdlib + loguru 的用户做技术分析 /
# 风控 / paper trading，不强制装 dspy。需要 TradingAnalyzer 时用 lazy import：
#     from roma_analyzer.analyzer import TradingAnalyzer

__all__ = ["load_config", "Config"]
