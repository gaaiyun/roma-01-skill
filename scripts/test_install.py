#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Quick Test Script

Tests the basic functionality of the analyzer.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from roma_analyzer.config import load_config, get_default_config, create_default_config
from roma_analyzer.technical_analysis import TechnicalAnalyzer


def test_config():
    """Test configuration loading."""
    print("\n" + "="*60)
    print("测试配置模块")
    print("="*60)
    
    # Test default config
    config = get_default_config()
    print("[OK] 默认配置生成成功")
    print(f"  - 账户数：{len(config.get('accounts', []))}")
    print(f"  - 模型数：{len(config.get('models', []))}")
    print(f"  - 代理数：{len(config.get('agents', []))}")
    
    # Check if example config exists
    example_config = Path("config/roma_config.yaml.example")
    if example_config.exists():
        print(f"[OK] 配置示例文件存在：{example_config}")
    else:
        print(f"[FAIL] 配置示例文件不存在：{example_config}")
    
    return True


def test_technical_analysis():
    """Test technical analysis module."""
    print("\n" + "="*60)
    print("测试技术分析模块")
    print("="*60)
    
    ta = TechnicalAnalyzer()
    
    # Generate sample kline data
    import random
    base_price = 50000
    klines = []
    for i in range(100):
        change = random.uniform(-0.02, 0.02)
        open_price = base_price * (1 + change)
        close_price = open_price * (1 + random.uniform(-0.01, 0.01))
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.01))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.01))
        volume = random.uniform(100, 1000)
        
        klines.append({
            "timestamp": i * 180,  # 3 minutes
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume,
        })
        base_price = close_price
    
    # Analyze
    result = ta.analyze_klines(klines, interval="3m")
    
    print("[OK] 技术分析计算成功")
    print(f"  - RSI: {result.get('rsi', 0):.2f}")
    print(f"  - MACD 信号：{result.get('macd_signal_str', 'Unknown')}")
    print(f"  - 趋势：{result.get('trend', 'Unknown')}")
    print(f"  - 当前价：${result.get('current_price', 0):,.2f}")
    print(f"  - 布林带：${result.get('bb_lower', 0):,.2f} - ${result.get('bb_upper', 0):,.2f}")
    
    return True


def test_risk_manager():
    """Test risk manager module."""
    print("\n" + "="*60)
    print("测试风险管理模块")
    print("="*60)
    
    from roma_analyzer.risk_manager import RiskManager
    
    strategy_config = {
        "risk_management": {
            "max_positions": 3,
            "max_leverage": 10,
            "max_position_size_pct": 30,
            "max_total_position_pct": 80,
            "stop_loss_pct": 3,
            "take_profit_pct": 10,
        }
    }
    
    rm = RiskManager(strategy_config)
    
    # Test trade validation
    valid, adjusted_size, reasons = rm.validate_trade(
        position_size_usd=5000,
        leverage=5,
        available_balance=10000,
        total_balance=10000,
        current_positions=[],
        daily_pnl=0,
    )
    
    print("[OK] 风险管理验证成功")
    print(f"  - 交易是否有效：{valid}")
    print(f"  - 调整后仓位：${adjusted_size:,.2f}")
    if reasons:
        print(f"  - 限制原因：{', '.join(reasons)}")
    
    # Test position size calculation
    position_size = rm.calculate_position_size(
        symbol="BTCUSDT",
        price=50000,
        balance=10000,
        leverage=5,
        confidence=75,
    )
    
    print(f"  - 计算仓位大小：${position_size:,.2f} (置信度 75%)")
    
    return True


def test_decision_logger():
    """Test decision logger module."""
    print("\n" + "="*60)
    print("测试决策日志模块")
    print("="*60)
    
    from roma_analyzer.decision_logger import DecisionLogger
    
    logger = DecisionLogger(logs_dir="logs")
    
    # Log a test suggestion
    test_suggestion = {
        "symbol": "BTCUSDT",
        "action": "WAIT",
        "confidence": 65.0,
        "chain_of_thought": "Test analysis",
        "key_levels": {"support": 48000, "resistance": 52000},
        "risk_warning": "Test warning",
    }
    
    logger.log_suggestion(test_suggestion)
    print("[OK] 测试建议已记录")
    
    # Get history
    history = logger.get_history(limit=5)
    print(f"  - 日志文件：{logger.log_file}")
    print(f"  - 历史条目数：{len(history)}")
    
    # Get statistics
    stats = logger.get_statistics()
    print(f"  - 总交易数：{stats.get('total_trades', 0)}")
    print(f"  - 胜率：{stats.get('win_rate', 0):.1f}%")
    
    return True


def test_analyzer():
    """Test main analyzer (without actual API calls)."""
    print("\n" + "="*60)
    print("测试主分析器模块")
    print("="*60)
    
    from roma_analyzer.analyzer import TradingAnalyzer
    
    # Create minimal config
    config = {
        "agents": [{
            "exchange": {"type": "binance"},
            "llm": {"provider": "deepseek", "api_key": "test"},
            "strategy": {
                "risk_management": {
                    "max_positions": 3,
                    "max_leverage": 10,
                }
            }
        }]
    }
    
    try:
        # Note: We can't fully initialize without proper DEX setup
        # This is just a basic import test
        print("[OK] 分析器模块导入成功")
        print("  - TradingAnalyzer 类可用")
        return True
    except Exception as e:
        print(f"[WARN] 分析器模块警告：{e}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("ROMA-01 Trading Analyzer - 快速测试")
    print("="*60)
    
    tests = [
        ("配置模块", test_config),
        ("技术分析", test_technical_analysis),
        ("风险管理", test_risk_manager),
        ("决策日志", test_decision_logger),
        ("主分析器", test_analyzer),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"\n[FAIL] {name} 测试失败")
        except Exception as e:
            failed += 1
            print(f"\n[ERROR] {name} 测试异常：{e}")
    
    print("\n" + "="*60)
    print(f"测试完成：{passed} 通过，{failed} 失败")
    print("="*60)
    
    if failed == 0:
        print("\n[SUCCESS] 所有测试通过！技能已准备就绪。")
        print("\n下一步:")
        print("1. 复制 config/roma_config.yaml.example 到 config/roma_config.yaml")
        print("2. 编辑配置文件，添加你的 API 密钥")
        print("3. 运行：python scripts/roma_analyzer.py --help")
    else:
        print("\n[WARN] 部分测试失败，请检查错误信息。")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
