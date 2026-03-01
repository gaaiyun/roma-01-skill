# ROMA-01 Trading Analyzer Skill

基于 ROMA (Recursive Open Meta-Agents) 框架的简化版加密货币交易分析工具。

## 功能

提供 AI 驱动的加密货币交易分析和建议：
- 📊 多 DEX 支持（Aster, Hyperliquid, Binance）
- 🤖 多 LLM 模型（DeepSeek, Qwen, Claude, GPT, Grok, Gemini）
- 📈 技术指标分析（RSI, MACD, EMA, ATR, 布林带）
- 💡 AI 交易决策建议
- 🔒 风险管理检查
- 📝 历史决策分析

## 用法

### 基本命令

```bash
# 分析特定代币的市场状况
python scripts/roma_analyzer.py --symbol BTCUSDT --analyze

# 获取 AI 交易建议（建议/做多/做空/等待）
python scripts/roma_analyzer.py --symbol ETHUSDT --suggest

# 查看当前所有持仓
python scripts/roma_analyzer.py --positions

# 查看历史交易决策
python scripts/roma_analyzer.py --history --limit 10

# 查看账户余额
python scripts/roma_analyzer.py --balance

# 运行完整分析（市场 + 建议 + 风险）
python scripts/roma_analyzer.py --symbol SOLUSDT --full
```

### 配置文件

1. 首次使用时复制配置模板：
```bash
cp config/roma_config.yaml.example config/roma_config.yaml
```

2. 编辑 `config/roma_config.yaml` 添加：
   - DEX API 密钥（Aster/Hyperliquid/Binance）
   - LLM API 密钥（DeepSeek/Qwen/Claude 等）
   - 交易对列表
   - 风险管理参数

### 环境变量

也可以通过环境变量配置：

```bash
# DEX 配置
export ASTER_USER=your_user
export ASTER_SIGNER=your_signer
export ASTER_PRIVATE_KEY=your_private_key

export HL_SECRET_KEY=your_hyperliquid_secret
export HL_ACCOUNT_ADDRESS=your_account_address

export BINANCE_API_KEY=your_binance_key
export BINANCE_API_SECRET=your_binance_secret

# LLM 配置
export DEEPSEEK_API_KEY=your_deepseek_key
export QWEN_API_KEY=your_qwen_key
export ANTHROPIC_API_KEY=your_anthropic_key
export OPENAI_API_KEY=your_openai_key
export XAI_API_KEY=your_xai_key
export GOOGLE_API_KEY=your_google_key
```

## 输出示例

### 市场分析 (--analyze)

```
📊 BTCUSDT 市场分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前价格：$95,234.50
24h 变化：+2.34%

技术指标:
  RSI(14): 62.3 (中性偏多)
  MACD: 金叉
  EMA(20): $93,450 (支撑位)
  布林带：中轨上方

资金费率：0.0123% (中性)
```

### AI 建议 (--suggest)

```
💡 AI 交易建议
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
建议：等待 (WAIT)
置信度：75%

推理链:
1. RSI 处于中性区域，无明显超买/超卖
2. 价格在布林带中轨附近震荡
3. 等待突破确认信号

关键价位:
  支撑：$93,500
  阻力：$97,000
```

### 持仓查看 (--positions)

```
📈 当前持仓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. ETHUSDT 多单
   入场：$3,450.00
   当前：$3,520.00
   盈亏：+2.03% (+$140.00)
   杠杆：5x

2. SOLUSDT 空单
   入场：$210.50
   当前：$208.30
   盈亏：+1.05% (+$44.00)
   杠杆：3x

总未实现盈亏：+$184.00
```

## 配置选项

### 交易对配置

```yaml
default_coins:
  - BTCUSDT     # 比特币
  - ETHUSDT     # 以太坊
  - SOLUSDT     # Solana
  - BNBUSDT     # 币安币
  - DOGEUSDT    # 狗狗币
  - XRPUSDT     # 瑞波币
```

### 风险管理参数

```yaml
risk_management:
  max_positions: 3              # 最大同时持仓数
  max_leverage: 10              # 最大杠杆倍数
  max_position_size_pct: 30     # 单笔仓位上限 (%)
  max_total_position_pct: 80    # 总仓位上限 (%)
  max_single_trade_pct: 50      # 无持仓时单笔交易上限 (%)
  max_single_trade_with_positions_pct: 30  # 有持仓时单笔交易上限 (%)
  max_daily_loss_pct: 15        # 每日最大亏损 (%)
  stop_loss_pct: 3              # 自动止损 (%)
  take_profit_pct: 10           # 自动止盈 (%)
```

### LLM 模型配置

```yaml
models:
  - id: "deepseek-v3.1"
    provider: "deepseek"
    api_key: ${DEEPSEEK_API_KEY}
    model: "deepseek-chat"
    temperature: 0.15
    max_tokens: 4000
  
  - id: "qwen3-max"
    provider: "qwen"
    api_key: ${QWEN_API_KEY}
    model: "qwen-max"
    temperature: 0.15
    max_tokens: 4000
```

## 安全提示

⚠️ **重要警告**:

1. **本工具仅提供信息和分析，不自动执行交易**
2. 所有交易决策需要人工确认和执行
3. 加密货币交易风险极高，可能导致本金全部损失
4. 请先在测试网或小资金环境下充分测试
5. 妥善保管 API 密钥和私钥，不要提交到版本控制
6. 定期备份决策日志和配置文件

## 文件结构

```
roma-01-skill/
├── SKILL.md                 # 本文件
├── README.md                # 详细说明
├── scripts/
│   └── roma_analyzer.py     # 主脚本
├── src/
│   └── roma_analyzer/
│       ├── __init__.py
│       ├── analyzer.py      # 核心分析模块
│       ├── dex_clients/     # DEX 客户端
│       │   ├── base.py
│       │   ├── aster.py
│       │   ├── hyperliquid.py
│       │   └── binance.py
│       ├── llm_clients/     # LLM 客户端
│       │   ├── factory.py
│       │   ├── deepseek.py
│       │   ├── qwen.py
│       │   └── ...
│       ├── technical_analysis.py  # 技术分析
│       └── risk_manager.py  # 风险管理
├── config/
│   ├── roma_config.yaml.example
│   └── prompts/
│       ├── system_en.md
│       ├── system_zh.md
│       ├── analysis_en.md
│       └── analysis_zh.md
├── logs/                    # 决策日志
│   └── decisions_YYYY-MM-DD.jsonl
└── requirements.txt         # Python 依赖
```

## 依赖安装

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 可选：安装 TA-Lib 技术指标库
# Windows: 下载预编译包
# macOS: brew install ta-lib
# Linux: apt-get install ta-lib
```

## 常见问题

### Q: 支持哪些 DEX？
A: 目前支持 Aster Finance, Hyperliquid, 和 Binance。可以通过扩展 `dex_clients` 模块添加更多。

### Q: 可以自动交易吗？
A: 不可以。本技能专注于提供分析和建议，所有交易需要人工确认。这是为了安全考虑。

### Q: 如何查看历史决策？
A: 使用 `--history` 参数，或通过 `logs/decisions_*.jsonl` 文件查看原始日志。

### Q: 支持中文吗？
A: 支持！在配置文件中设置 `prompt_language: zh` 即可使用中文提示词。

### Q: 如何切换 LLM 模型？
A: 在配置文件的 `agents` 部分修改 `model_id`，或在命令行使用 `--model` 参数。

## 版本历史

- **v1.0.0** (2026-03-01): 初始版本
  - 基于 ROMA-01 框架简化
  - 支持多 DEX 和多 LLM
  - 完整的技术分析和风险管理
  - 决策日志和历史分析

## 许可证

MIT License - 详见原 ROMA-01 项目

## 致谢

- **ROMA Framework**: 分层多智能体架构
- **DSPy**: 结构化 AI 提示和智能体编排
- **Aster Finance**: DEX 集成和 Web3 交易基础设施
- **DeepSeek**: 快速且经济的 LLM API
