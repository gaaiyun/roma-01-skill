#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Main Script

A simplified trading analysis tool based on the ROMA framework.
Provides AI-powered market analysis and trading suggestions.

Usage:
    python scripts/roma_analyzer.py --symbol BTCUSDT --analyze
    python scripts/roma_analyzer.py --symbol ETHUSDT --suggest
    python scripts/roma_analyzer.py --positions
    python scripts/roma_analyzer.py --history --limit 10
"""

import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from roma_analyzer.analyzer import TradingAnalyzer
from roma_analyzer.config import load_config


def setup_logging():
    """Configure logging."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO",
    )
    logger.add(
        "logs/roma_analyzer_{time:YYYY-MM-DD}.log",
        rotation="00:00",
        retention="7 days",
        level="DEBUG",
    )


def print_market_analysis(analysis: dict):
    """Print market analysis results."""
    symbol = analysis.get("symbol", "UNKNOWN")
    print("\n" + "="*60)
    print(f"📊 {symbol} 市场分析")
    print("="*60)
    
    # Price info
    price_data = analysis.get("price", {})
    print(f"\n当前价格：${price_data.get('current', 0):,.2f}")
    print(f"24h 变化：{price_data.get('change_24h', 0):+.2f}%")
    print(f"24h 最高：${price_data.get('high_24h', 0):,.2f}")
    print(f"24h 最低：${price_data.get('low_24h', 0):,.2f}")
    
    # Technical indicators
    tech = analysis.get("technical", {})
    print("\n技术指标:")
    print(f"  RSI(14): {tech.get('rsi', 0):.1f} ({get_rsi_status(tech.get('rsi', 0))})")
    print(f"  MACD: {tech.get('macd_signal', 'Neutral')}")
    print(f"  EMA(20): ${tech.get('ema_20', 0):,.2f}")
    print(f"  EMA(50): ${tech.get('ema_50', 0):,.2f}")
    print(f"  布林带上轨：${tech.get('bb_upper', 0):,.2f}")
    print(f"  布林带下轨：${tech.get('bb_lower', 0):,.2f}")
    
    # Funding rate
    funding = analysis.get("funding_rate")
    if funding is not None:
        funding_status = "偏多拥挤" if funding > 0.03 else "偏空拥挤" if funding < -0.03 else "中性"
        print(f"\n资金费率：{funding:.4f}% ({funding_status})")
    
    print("="*60)


def print_ai_suggestion(suggestion: dict):
    """Print AI trading suggestion."""
    print("\n" + "="*60)
    print("💡 AI 交易建议")
    print("="*60)
    
    action = suggestion.get("action", "WAIT")
    action_map = {
        "OPEN_LONG": "🟢 做多 (LONG)",
        "OPEN_SHORT": "🔴 做空 (SHORT)",
        "CLOSE_LONG": "⚫ 平多单",
        "CLOSE_SHORT": "⚫ 平空单",
        "HOLD": "✋ 持有",
        "WAIT": "⏳ 等待",
    }
    
    print(f"\n建议：{action_map.get(action, action)}")
    print(f"置信度：{suggestion.get('confidence', 0):.0f}%")
    
    # Chain of thought
    cot = suggestion.get("chain_of_thought", "")
    if cot:
        print("\n推理链:")
        for i, line in enumerate(cot.split("\n"), 1):
            if line.strip():
                print(f"  {i}. {line.strip()}")
    
    # Key levels
    levels = suggestion.get("key_levels", {})
    if levels:
        print("\n关键价位:")
        if levels.get("support"):
            print(f"  支撑：${levels['support']:,.2f}")
        if levels.get("resistance"):
            print(f"  阻力：${levels['resistance']:,.2f}")
    
    # Risk warning
    risk = suggestion.get("risk_warning")
    if risk:
        print(f"\n⚠️ 风险提醒：{risk}")
    
    print("="*60)


def print_positions(positions: list):
    """Print current positions."""
    print("\n" + "="*60)
    print("📈 当前持仓")
    print("="*60)
    
    if not positions:
        print("\n暂无持仓")
    else:
        total_pnl = 0
        for i, pos in enumerate(positions, 1):
            side = "多" if pos.get("side") == "long" else "空"
            pnl_pct = pos.get("pnl_pct", 0)
            pnl_usd = pos.get("pnl_usd", 0)
            total_pnl += pnl_usd
            
            print(f"\n{i}. {pos['symbol']} {side}单")
            print(f"   入场：${pos['entry_price']:,.2f}")
            print(f"   当前：${pos['mark_price']:,.2f}")
            print(f"   杠杆：{pos['leverage']}x")
            print(f"   数量：{pos['position_amt']:.6f}")
            print(f"   盈亏：{pnl_pct:+.2f}% ({pnl_usd:+.2f} USDT)")
        
        print(f"\n总未实现盈亏：{total_pnl:+.2f} USDT")
    
    print("="*60)


def print_balance(balance: dict):
    """Print account balance."""
    print("\n" + "="*60)
    print("💰 账户余额")
    print("="*60)
    
    print(f"\n总余额：${balance.get('total_wallet_balance', 0):,.2f}")
    print(f"可用余额：${balance.get('available_balance', 0):,.2f}")
    print(f"未实现盈亏：${balance.get('total_unrealized_profit', 0):,.2f}")
    
    # Position usage
    total_margin = balance.get('total_margin_used', 0)
    max_total_pct = balance.get('max_total_position_pct', 80)
    print(f"\n已用保证金：${total_margin:,.2f}")
    print(f"仓位使用率：{total_margin / balance.get('total_wallet_balance', 1) * 100:.1f}% (上限：{max_total_pct}%)")
    
    print("="*60)


def print_history(decisions: list):
    """Print decision history."""
    print("\n" + "="*60)
    print("📝 历史决策")
    print("="*60)
    
    if not decisions:
        print("\n暂无历史决策")
    else:
        for i, dec in enumerate(decisions, 1):
            timestamp = dec.get("timestamp", "Unknown")
            symbol = dec.get("symbol", "Unknown")
            action = dec.get("action", "Unknown")
            pnl = dec.get("realized_pnl")
            
            print(f"\n{i}. [{timestamp}] {symbol} - {action}")
            if pnl is not None:
                print(f"   实现盈亏：{pnl:+.2f} USDT")
    
    print("="*60)


def get_rsi_status(rsi: float) -> str:
    """Get RSI status string."""
    if rsi > 70:
        return "超买"
    elif rsi < 30:
        return "超卖"
    elif rsi > 60:
        return "中性偏多"
    elif rsi < 40:
        return "中性偏空"
    else:
        return "中性"


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ROMA-01 Trading Analyzer - AI-powered crypto trading analysis tool"
    )
    
    # Action arguments
    parser.add_argument("--symbol", type=str, help="Trading pair symbol (e.g., BTCUSDT)")
    parser.add_argument("--analyze", action="store_true", help="Analyze market conditions")
    parser.add_argument("--suggest", action="store_true", help="Get AI trading suggestion")
    parser.add_argument("--positions", action="store_true", help="Show current positions")
    parser.add_argument("--balance", action="store_true", help="Show account balance")
    parser.add_argument("--history", action="store_true", help="Show decision history")
    parser.add_argument("--full", action="store_true", help="Run full analysis (market + suggestion)")
    
    # Options
    parser.add_argument("--limit", type=int, default=10, help="Number of history items to show")
    parser.add_argument("--model", type=str, help="Override LLM model ID")
    parser.add_argument("--config", type=str, default="config/roma_config.yaml", help="Config file path")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error(f"Config file not found: {config_path}")
        logger.info("Please copy config/roma_config.yaml.example to config/roma_config.yaml and configure it")
        sys.exit(1)
    
    config = load_config(config_path)
    
    # Override model if specified
    if args.model and config.get("agents"):
        config["agents"][0]["model_id"] = args.model
    
    # Initialize analyzer
    analyzer = TradingAnalyzer(config)
    
    try:
        # No action specified - show help
        if not any([args.analyze, args.suggest, args.positions, args.balance, args.history, args.full]):
            parser.print_help()
            sys.exit(0)
        
        # Full analysis
        if args.full:
            if not args.symbol:
                logger.error("--symbol is required for --full analysis")
                sys.exit(1)
            
            logger.info(f"Running full analysis for {args.symbol}")
            
            # Market analysis
            analysis = await analyzer.analyze_market(args.symbol)
            print_market_analysis(analysis)
            
            # AI suggestion
            suggestion = await analyzer.get_suggestion(args.symbol)
            print_ai_suggestion(suggestion)
            
            return
        
        # Market analysis
        if args.analyze:
            if not args.symbol:
                logger.error("--symbol is required for --analyze")
                sys.exit(1)
            
            logger.info(f"Analyzing {args.symbol}")
            analysis = await analyzer.analyze_market(args.symbol)
            
            if args.json:
                import json
                print(json.dumps(analysis, indent=2))
            else:
                print_market_analysis(analysis)
            
            return
        
        # AI suggestion
        if args.suggest:
            if not args.symbol:
                logger.error("--symbol is required for --suggest")
                sys.exit(1)
            
            logger.info(f"Getting AI suggestion for {args.symbol}")
            suggestion = await analyzer.get_suggestion(args.symbol)
            
            if args.json:
                import json
                print(json.dumps(suggestion, indent=2))
            else:
                print_ai_suggestion(suggestion)
            
            return
        
        # Positions
        if args.positions:
            logger.info("Fetching positions")
            positions = await analyzer.get_positions()
            
            if args.json:
                import json
                print(json.dumps(positions, indent=2))
            else:
                print_positions(positions)
            
            return
        
        # Balance
        if args.balance:
            logger.info("Fetching balance")
            balance = await analyzer.get_balance()
            
            if args.json:
                import json
                print(json.dumps(balance, indent=2))
            else:
                print_balance(balance)
            
            return
        
        # History
        if args.history:
            logger.info(f"Fetching last {args.limit} decisions")
            decisions = await analyzer.get_history(limit=args.limit)
            
            if args.json:
                import json
                print(json.dumps(decisions, indent=2))
            else:
                print_history(decisions)
            
            return
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        await analyzer.close()


if __name__ == "__main__":
    asyncio.run(main())
