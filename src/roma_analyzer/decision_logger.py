# -*- coding: utf-8 -*-
"""
ROMA-01 Trading Analyzer - Decision Logger

Logs trading decisions and suggestions to JSONL files.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger


class DecisionLogger:
    """Logger for trading decisions and suggestions."""
    
    def __init__(self, logs_dir: str = "logs"):
        """
        Initialize decision logger.
        
        Args:
            logs_dir: Directory to store log files
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file = self.logs_dir / f"decisions_{today}.jsonl"
        
        logger.info(f"DecisionLogger initialized: {self.log_file}")
    
    def log_suggestion(self, suggestion: Dict):
        """
        Log AI trading suggestion.
        
        Args:
            suggestion: Suggestion dictionary
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "suggestion",
            **suggestion,
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logger.debug(f"Logged suggestion for {suggestion.get('symbol', 'UNKNOWN')}")
        except Exception as e:
            logger.error(f"Failed to log suggestion: {e}")
    
    def log_trade(self, trade: Dict):
        """
        Log executed trade.
        
        Args:
            trade: Trade dictionary
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": "trade",
            **trade,
        }
        
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            logger.info(f"Logged trade: {trade.get('action')} {trade.get('symbol')}")
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
    
    def get_history(self, limit: int = 10, filter_type: Optional[str] = None) -> List[Dict]:
        """
        Get decision history.
        
        Args:
            limit: Maximum number of entries to return
            filter_type: Filter by type ("suggestion" or "trade")
            
        Returns:
            List of log entries
        """
        entries = []
        
        # Read from current log file
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        
                        try:
                            entry = json.loads(line)
                            
                            # Filter by type if specified
                            if filter_type and entry.get("type") != filter_type:
                                continue
                            
                            entries.append(entry)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"Failed to read log file: {e}")
        
        # Read from previous days if needed
        if len(entries) < limit:
            # Find previous log files
            try:
                log_files = sorted(
                    self.logs_dir.glob("decisions_*.jsonl"),
                    reverse=True,
                )
                
                for log_file in log_files[1:]:  # Skip current file
                    if len(entries) >= limit:
                        break
                    
                    try:
                        with open(log_file, "r", encoding="utf-8") as f:
                            for line in f:
                                if len(entries) >= limit:
                                    break
                                
                                line = line.strip()
                                if not line:
                                    continue
                                
                                try:
                                    entry = json.loads(line)
                                    
                                    if filter_type and entry.get("type") != filter_type:
                                        continue
                                    
                                    entries.append(entry)
                                except json.JSONDecodeError:
                                    continue
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Failed to scan for old log files: {e}")
        
        # Sort by timestamp (newest first) and limit
        entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return entries[:limit]
    
    def get_suggestions(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get AI suggestions.
        
        Args:
            symbol: Filter by symbol
            limit: Maximum entries
            
        Returns:
            List of suggestions
        """
        all_suggestions = self.get_history(limit=100, filter_type="suggestion")
        
        if symbol:
            filtered = [s for s in all_suggestions if s.get("symbol") == symbol]
        else:
            filtered = all_suggestions
        
        return filtered[:limit]
    
    def get_trades(self, symbol: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        Get trade history.
        
        Args:
            symbol: Filter by symbol
            limit: Maximum entries
            
        Returns:
            List of trades
        """
        all_trades = self.get_history(limit=100, filter_type="trade")
        
        if symbol:
            filtered = [t for t in all_trades if t.get("symbol") == symbol]
        else:
            filtered = all_trades
        
        return filtered[:limit]
    
    def get_statistics(self) -> Dict:
        """
        Get trading statistics from logs.
        
        Returns:
            Statistics dictionary
        """
        trades = self.get_trades(limit=1000)
        
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
            }
        
        total_pnl = sum(t.get("realized_pnl", 0) for t in trades)
        winning = [t for t in trades if t.get("realized_pnl", 0) > 0]
        losing = [t for t in trades if t.get("realized_pnl", 0) <= 0]
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": len(winning) / len(trades) * 100 if trades else 0,
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(trades) if trades else 0,
            "best_trade": max((t.get("realized_pnl", 0) for t in trades), default=0),
            "worst_trade": min((t.get("realized_pnl", 0) for t in trades), default=0),
        }
