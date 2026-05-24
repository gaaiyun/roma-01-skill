"""DecisionLogger 测试 —— JSONL 读写。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from roma_analyzer.decision_logger import DecisionLogger


@pytest.fixture
def logger_instance(tmp_path):
    return DecisionLogger(logs_dir=str(tmp_path))


def test_creates_logs_dir(tmp_path):
    logs_dir = tmp_path / "nested" / "logs"
    DecisionLogger(logs_dir=str(logs_dir))
    assert logs_dir.exists()


def test_log_suggestion_appends_jsonl(logger_instance, tmp_path):
    logger_instance.log_suggestion({
        "symbol": "BTCUSDT",
        "action": "BUY",
        "confidence": 75,
    })
    # 读回
    assert logger_instance.log_file.exists()
    content = logger_instance.log_file.read_text(encoding="utf-8")
    obj = json.loads(content.strip())
    assert obj["type"] == "suggestion"
    assert obj["symbol"] == "BTCUSDT"
    assert obj["confidence"] == 75


def test_log_trade_appends_jsonl(logger_instance):
    logger_instance.log_trade({
        "symbol": "ETHUSDT",
        "action": "SELL",
        "size": 0.5,
        "price": 3000,
    })
    content = logger_instance.log_file.read_text(encoding="utf-8")
    obj = json.loads(content.strip())
    assert obj["type"] == "trade"
    assert obj["action"] == "SELL"


def test_multiple_entries_one_per_line(logger_instance):
    logger_instance.log_suggestion({"symbol": "BTC", "action": "BUY"})
    logger_instance.log_trade({"symbol": "BTC", "action": "BUY", "size": 1})
    logger_instance.log_suggestion({"symbol": "ETH", "action": "SELL"})

    lines = logger_instance.log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    objs = [json.loads(l) for l in lines]
    assert objs[0]["type"] == "suggestion"
    assert objs[1]["type"] == "trade"
    assert objs[2]["type"] == "suggestion"


def test_entries_include_timestamp(logger_instance):
    logger_instance.log_suggestion({"symbol": "BTC"})
    obj = json.loads(logger_instance.log_file.read_text(encoding="utf-8"))
    assert "timestamp" in obj
    # ISO 格式应该可被 datetime 解析
    from datetime import datetime
    datetime.fromisoformat(obj["timestamp"])


def test_get_history_returns_recent(logger_instance):
    for i in range(5):
        logger_instance.log_suggestion({"symbol": f"COIN{i}", "action": "BUY"})
    history = logger_instance.get_history(limit=3)
    assert len(history) == 3
    # 应该是最新的 3 条
    symbols = [h["symbol"] for h in history]
    assert "COIN4" in symbols


def test_get_history_filter_by_type(logger_instance):
    logger_instance.log_suggestion({"symbol": "BTC", "action": "BUY"})
    logger_instance.log_trade({"symbol": "BTC", "action": "BUY"})
    logger_instance.log_suggestion({"symbol": "ETH", "action": "SELL"})

    suggestions = logger_instance.get_history(limit=10, filter_type="suggestion")
    assert all(s["type"] == "suggestion" for s in suggestions)
    assert len(suggestions) == 2

    trades = logger_instance.get_history(limit=10, filter_type="trade")
    assert all(t["type"] == "trade" for t in trades)
    assert len(trades) == 1


def test_get_history_empty_when_no_log_file(tmp_path):
    """日志文件不存在时不应崩。"""
    logger_instance = DecisionLogger(logs_dir=str(tmp_path))
    # 直接调 get_history，不写任何东西
    history = logger_instance.get_history(limit=10)
    assert history == []


def test_log_handles_unicode(logger_instance):
    """中文字符应正常存。"""
    logger_instance.log_suggestion({
        "symbol": "BTCUSDT",
        "reasoning": "看涨突破，建议买入",
    })
    content = logger_instance.log_file.read_text(encoding="utf-8")
    assert "看涨突破" in content
