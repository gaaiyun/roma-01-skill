"""roma-01-skill CLI（v2）。

子命令：
    paper-trade <csv>      历史 K 线 → 模拟交易 → 结果报告
    list-indicators        列内置技术指标
    analyze                v1 入口：调真 DEX + LLM 决策（要求装 dspy 等）
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))


def _read_klines_csv(path: str) -> list:
    """从 CSV 读 K 线：date, open, high, low, close, volume。"""
    rows = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                rows.append({
                    "open": float(row.get("open", row.get("Open", 0))),
                    "high": float(row.get("high", row.get("High", 0))),
                    "low": float(row.get("low", row.get("Low", 0))),
                    "close": float(row.get("close", row.get("Close", 0))),
                    "volume": float(row.get("volume", row.get("Volume", 0))),
                })
            except (ValueError, KeyError):
                continue
    return rows


def _synthetic_klines(n: int = 200, seed: int = 42) -> list:
    """合成 K 线，给离线 demo 用。"""
    import random
    rng = random.Random(seed)
    klines = []
    price = 50_000.0
    for i in range(n):
        change = rng.gauss(0.0005, 0.02)
        new_price = price * (1 + change)
        klines.append({
            "open": price,
            "high": max(price, new_price) * 1.005,
            "low": min(price, new_price) * 0.995,
            "close": new_price,
            "volume": rng.uniform(1e8, 5e8),
        })
        price = new_price
    return klines


def cmd_paper_trade(args) -> int:
    from roma_analyzer.paper_trader import run

    if args.synthetic:
        klines = _synthetic_klines(n=args.n_bars, seed=args.seed)
        source = "synthetic"
    else:
        if not args.csv:
            sys.stderr.write("[error] 需要 --csv 或 --synthetic\n")
            return 1
        klines = _read_klines_csv(args.csv)
        if not klines:
            sys.stderr.write(f"[error] {args.csv} 没读到任何有效 K 线\n")
            return 2
        source = args.csv

    sys.stderr.write(f"[ok] 加载 {len(klines)} 根 K 线（{source}）\n")

    result = run(
        klines, initial_cash=args.initial_cash,
        allocation=args.allocation, commission=args.commission,
        warmup=args.warmup,
    )

    print()
    print(f"Initial cash : ${result.initial_cash:,.2f}")
    print(f"Final equity : ${result.final_equity:,.2f}")
    print(f"Total return : {result.total_return:+.2%}")
    print(f"Max drawdown : {result.max_drawdown:+.2%}")
    print(f"# trades     : {result.n_trades}")
    print(f"Cash left    : ${result.cash:,.2f}")
    print(f"Position left: {result.position:.6f}")

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8")
        sys.stderr.write(f"[ok] 写入 {args.output}\n")
    return 0


def cmd_list_indicators(args) -> int:
    print("Built-in technical indicators (TechnicalAnalyzer):")
    print("  rsi          — RSI(14) 默认周期")
    print("  ema_20       — 20 周期 EMA")
    print("  ema_50       — 50 周期 EMA（数据足够时）")
    print("  macd         — 12/26 EMA 差值")
    print("  macd_signal  — MACD 信号线")
    print("  macd_hist    — MACD 直方图")
    print("  bb_upper/mid/lower — 布林带（20 周期 + 2σ）")
    print("  atr          — Average True Range(14)")
    print("  adx          — Average Directional Index（简化版）")
    print("  volume_ratio — 当前成交量 / 20 周期均量")
    print("  trend        — Strong Uptrend / Uptrend / Sideways / Downtrend / Strong Downtrend")
    return 0


def cmd_analyze(args) -> int:
    """v1 入口：转发到 scripts/roma_analyzer.py（需要 dspy + 真 API key）。"""
    sys.stderr.write(
        "[info] v1 真分析入口在 scripts/roma_analyzer.py，"
        "需要 dspy / loguru / httpx + 配置 config/roma_config.yaml。\n"
        "[info] 启动：python scripts/roma_analyzer.py --symbol BTCUSDT --analyze\n"
    )
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="roma-01",
        description="ROMA-01：加密交易分析 + paper-trading sanity check"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("paper-trade", help="历史 K 线模拟交易")
    sp.add_argument("--csv", help="OHLCV CSV 文件")
    sp.add_argument("--synthetic", action="store_true",
                    help="用合成 K 线（不需联网 / 不需文件）")
    sp.add_argument("--n-bars", type=int, default=200)
    sp.add_argument("--seed", type=int, default=42)
    sp.add_argument("--initial-cash", type=float, default=10_000.0)
    sp.add_argument("--allocation", type=float, default=0.95)
    sp.add_argument("--commission", type=float, default=0.001)
    sp.add_argument("--warmup", type=int, default=50)
    sp.add_argument("-o", "--output", help="结果写 JSON")
    sp.set_defaults(func=cmd_paper_trade)

    sp = sub.add_parser("list-indicators", help="列内置技术指标")
    sp.set_defaults(func=cmd_list_indicators)

    sp = sub.add_parser("analyze", help="v1 真 DEX + LLM 分析入口提示")
    sp.set_defaults(func=cmd_analyze)

    return p


def main(argv=None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
