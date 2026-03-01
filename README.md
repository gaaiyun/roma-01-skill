# ROMA-01 Trading Analyzer Skill

基于 ROMA 框架的简化版加密货币交易分析工具，专为 OpenClaw 设计。

## 功能特性

- 📊 **多 DEX 支持**: Aster Finance, Hyperliquid, Binance
- 🤖 **多 LLM 模型**: DeepSeek, Qwen, Claude, GPT, Grok, Gemini
- 📈 **技术分析**: RSI, MACD, EMA, ATR, 布林带
- 💡 **AI 决策分析**: 基于 DSPy 框架的交易决策
- 🔒 **风险管理**: 4 层风险控制体系
- 📝 **决策日志**: 完整的 AI 推理链记录

## 核心架构

### 账户 - 模型解耦

```yaml
accounts:  # DEX 交易账户
  - id: "aster-acc-01"
    dex_type: "aster"
    credentials: ...
  
models:    # LLM 模型配置
  - id: "deepseek-v3.1"
    provider: "deepseek"
    model: "deepseek-chat"

agents:    # 绑定账户和模型
  - id: "deepseek-aster-01"
    account_id: "aster-acc-01"
    model_id: "deepseek-v3.1"
```

### 交易决策流程

```
1. 扫描市场 → 获取价格、指标、持仓
2. AI 决策 (DSPy) → 分析市场条件，评估风险/收益
3. 风险验证 → 检查仓位限制
4. 执行交易 → 下单并记录
5. 监控日志 → 更新指标和决策历史
```

## 使用方法

### 基本用法

```bash
# 分析特定代币
python scripts/roma_analyzer.py --symbol BTCUSDT --analyze

# 获取 AI 交易建议
python scripts/roma_analyzer.py --symbol ETHUSDT --suggest

# 查看当前持仓
python scripts/roma_analyzer.py --positions

# 查看历史决策
python scripts/roma_analyzer.py --history --limit 10
```

### 配置

1. 复制配置模板：
```bash
cp config/roma_config.yaml.example config/roma_config.yaml
```

2. 编辑配置文件，添加 API 密钥和账户信息

3. 运行分析工具

## 与完整 ROMA 平台的区别

| 功能 | 完整 ROMA 平台 | OpenClaw Skill |
|------|---------------|----------------|
| Web 界面 | ✅ Next.js 仪表板 | ❌ 命令行工具 |
| 实时交易 | ✅ 自动执行 | ⚠️ 仅建议，需确认 |
| 多 Agent 并行 | ✅ 支持 | ✅ 支持 |
| 技术分析 | ✅ 完整 | ✅ 完整 |
| AI 决策 | ✅ DSPy | ✅ DSPy |
| 风险管理 | ✅ 4 层系统 | ✅ 4 层系统 |
| 决策日志 | ✅ SQLite | ✅ JSONL 文件 |
| WebSocket | ✅ 实时更新 | ❌ 轮询 |

## 依赖

- Python 3.12+
- dspy-ai
- httpx
- pyyaml
- loguru
- ta-lib (可选)

## 安全提示

⚠️ **重要**: 
- 本工具提供交易分析和建议，不自动执行交易
- 所有交易决策需要人工确认
- 请在测试网或小资金环境下先测试
- 妥善保管 API 密钥和私钥

## 许可证

MIT License
