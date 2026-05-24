# roma-01-skill

ROMA-01 加密货币交易分析工具：技术指标 + 风控 + DSPy/LLM AI 决策。基于
[ROMA](https://github.com/sentient-agi/ROMA) 框架简化版。

v1 已经把分析、风控、DEX 客户端、LLM 客户端、决策日志做齐了（~2500 LOC，
src/ 布局规范）。v2 在不动 v1 现有代码的前提下补两件实用的东西：

1. **完整单元测试** — v1 之前只有 `scripts/test_install.py` 安装冒烟，技术指标
   和风控这种**钱有关的代码无单测**直接上生产很危险。v2 加 82 个 pytest 覆盖
   TechnicalAnalyzer 全部指标 + RiskManager 4 层风控 + DecisionLogger JSONL 读写
   + PaperTrader 模拟器。
2. **Paper trading 模拟器** — v1 走 `analyze → suggest → 人工确认 → 执行` 流程，
   单点测试 LLM 输出。v2 加 `paper_trader.run(klines)` 让你把整年历史 K 线一次
   性灌进去走一遍简单规则（RSI 超卖买 + EMA 趋势过滤），出 PnL 曲线和交易日志。
   验证整套系统在历史数据上**不爆账户**，再考虑真上线。

## v2 新增

| 文件 | 干什么 |
|---|---|
| `src/roma_analyzer/paper_trader.py` | `rule_signal` + `run(klines)` + `PaperTradeResult`：模拟器主入口 |
| `tests/test_technical_analysis.py` | 32 个测试：RSI / EMA / MACD / Bollinger / ATR / ADX / 趋势检测 |
| `tests/test_risk_manager.py` | 21 个测试：4 层风控限额 + `validate_trade` + `calculate_position_size` |
| `tests/test_decision_logger.py` | 9 个测试：JSONL 读写 + filter + 时间戳 + Unicode |
| `tests/test_paper_trader.py` | 20 个测试：规则信号 + 模拟器端到端 + 边界 |
| `__main__.py` | CLI：`paper-trade` / `list-indicators` / `analyze` |

总测试 82 个，260ms 跑完，全部 stdlib + loguru 即可（不需要 dspy）。

## v1 仍保留

| 模块 | 干什么 |
|---|---|
| `src/roma_analyzer/analyzer.py` | TradingAnalyzer 主入口，用 DSPy 做 LLM 决策 |
| `src/roma_analyzer/technical_analysis.py` | RSI/EMA/MACD/Bollinger/ATR/ADX |
| `src/roma_analyzer/risk_manager.py` | 4 层风控（单笔 / 总仓 / 单仓 / 日亏损）|
| `src/roma_analyzer/decision_logger.py` | JSONL 决策记录 |
| `src/roma_analyzer/dex_clients/` | Aster / Hyperliquid / Binance 客户端 |
| `src/roma_analyzer/llm_clients/` | LLM provider factory |
| `scripts/roma_analyzer.py` | v1 CLI |
| `scripts/test_install.py` | v1 安装冒烟 |

## 安装

```bash
pip install -r requirements.txt
# v2 paper-trade + tests 只需要 loguru
# v1 真 LLM 决策需要：pip install dspy-ai httpx pyyaml
```

## 快速开始

### v2 入口：paper-trading（无网络、无 API key）

```bash
# 合成 K 线 demo
python __main__.py paper-trade --synthetic --n-bars 300 --seed 42

# 用本地 OHLCV CSV
python __main__.py paper-trade --csv data/btc_daily.csv \
    --initial-cash 10000 --commission 0.001 -o report.json

# 列内置技术指标
python __main__.py list-indicators
```

输出示例：

```
[ok] 加载 300 根 K 线（synthetic）

Initial cash : $10,000.00
Final equity : $9,984.32
Total return : -0.16%
Max drawdown : -2.17%
# trades     : 2
Cash left    : $9,984.32
Position left: 0.000000
```

### v1 入口：真 LLM 决策（要装 dspy + 配置 API key）

```bash
cp config/roma_config.yaml.example config/roma_config.yaml
# 编辑 config，填 DEX 账户 + LLM API key

python scripts/roma_analyzer.py --symbol BTCUSDT --analyze
python scripts/roma_analyzer.py --symbol ETHUSDT --suggest
python scripts/roma_analyzer.py --positions
python scripts/roma_analyzer.py --history --limit 10
```

### 库调用

```python
# 不需要 dspy / 真 API key
from roma_analyzer.technical_analysis import TechnicalAnalyzer
from roma_analyzer.risk_manager import RiskManager
from roma_analyzer.paper_trader import run, rule_signal

ta = TechnicalAnalyzer()
indicators = ta.analyze_klines(klines)
# {'rsi': 28.5, 'macd_signal_str': 'Bullish', 'trend': 'Uptrend', ...}

rm = RiskManager({"risk_management": {"max_positions": 3, ...}})
ok, adj, reasons = rm.validate_trade(
    position_size_usd=500, leverage=5,
    available_balance=10000, total_balance=10000,
    current_positions=[], daily_pnl=0,
)

result = run(klines, initial_cash=10_000, warmup=50)
print(result.total_return, result.max_drawdown)
for trade in result.trades:
    print(trade.action, trade.price, trade.reason)
```

## paper_trader 默认规则

```python
def rule_signal(indicators, has_position, rsi_buy=30, rsi_sell=70):
    rsi = indicators["rsi"]
    trend = indicators["trend"]
    if has_position:
        if rsi > rsi_sell:                # 超买 → 止盈
            return "SELL", "RSI overbought"
        if trend in ("Strong Downtrend", "Downtrend"):
            return "SELL", "trend break"
        return "HOLD", "在场"
    if rsi < rsi_buy:
        if trend == "Strong Downtrend":   # 抄底过滤：强空不接
            return "HOLD", "等右侧"
        return "BUY", "RSI oversold"
    return "HOLD", "无入场信号"
```

要换 LLM 决策、自定义信号：传 `signal_fn=` 给 `run()`，签名是
`(indicators, has_position) -> (action, reason)`。

## 风控测试覆盖

`tests/test_risk_manager.py` 把 4 层都覆盖了：

- Layer 1（单笔交易）：无持仓 50% 限制 / 有持仓 30% 限制 / 超出自动截到上限
- Layer 2（总持仓）：累计仓位不超 80%；超出报错
- Layer 3（单仓限额）：最大持仓数 / 单仓最大占比 / 杠杆上限
- Layer 4（日亏损）：超过 15% 日亏损暂停交易

`validate_trade` 综合 4 层走一遍，输出 `(valid, adjusted_size, reasons)`。

## 设计取舍

- **paper_trader 默认走规则而非 LLM**：跑一年日线 365 次 LLM 调用太贵 + 太慢。
  规则模拟器主要验证"风控逻辑 + 技术指标 + 仓位管理"端到端不爆账户，验过后
  再换 LLM 上线。
- **`roma_analyzer/__init__.py` 改 lazy import**：原版 `from .analyzer import
  TradingAnalyzer` 强制 import dspy，导致只想用技术指标的用户也得装 dspy。
  v2 改成：用 TradingAnalyzer 时显式 `from roma_analyzer.analyzer import ...`。
- **测试用 stdlib + pytest + loguru**：不依赖 dspy / httpx / pyyaml，CI 友好。
- **commission 默认 0.1%**：贴近 Binance / Aster 永续合约的实际费率。

## 项目结构

```
roma-01-skill/
├── __main__.py                       # v2 CLI 统一入口
├── README.md / SKILL.md / requirements.txt
├── src/roma_analyzer/
│   ├── analyzer.py                   # v1 TradingAnalyzer（DSPy + LLM）
│   ├── technical_analysis.py         # v1 技术指标库
│   ├── risk_manager.py               # v1 4 层风控
│   ├── decision_logger.py            # v1 JSONL 决策日志
│   ├── paper_trader.py               # v2 模拟器（新）
│   ├── config.py
│   ├── dex_clients/                  # Aster / Hyperliquid / Binance
│   └── llm_clients/                  # LLM provider factory
├── scripts/
│   ├── roma_analyzer.py              # v1 CLI
│   └── test_install.py               # v1 安装冒烟
├── tests/                            # v2 单元测试（82 个）
│   ├── test_technical_analysis.py
│   ├── test_risk_manager.py
│   ├── test_decision_logger.py
│   └── test_paper_trader.py
├── config/                           # 配置模板
└── logs/                             # 决策日志输出目录
```

## 测试

```bash
pip install pytest loguru
pytest tests/
```

82 个测试，260ms 跑完，无网络 / 无 dspy / 无 LLM key。

## 已知限制

- 技术指标里 ADX 是简化实现（用价格变动 / ATR 做代理），不是 Wilder 的完整
  +DI / -DI 计算，对盘整市判断会偏弱。
- paper_trader 不模拟滑点 / 部分成交 / 市价 vs 限价的区别 —— 实盘前要乘个
  额外的费用 buffer。
- 风控的 daily_pnl 需要外部传入，本仓库不持久化日盈亏，调用方自己跟踪。

## 安全提示

本工具提供分析和建议，所有真实交易决策需要人工确认。请在测试网或小资金环境
下先验证，妥善保管 API 密钥和私钥。

## 许可

MIT
