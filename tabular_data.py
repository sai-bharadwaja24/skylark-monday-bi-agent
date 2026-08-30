"""
Tabular Data Engine (Zero Dependency / Pure Python)
Provides lightweight tabular manipulation, filtering, aggregation, and grouping
with 100% standard library compliance, plus pandas interoperability.
"""

from typing import List, Dict, Any, Callable, Optional
import json

class Table:
    """Lightweight, resilient tabular data structure."""

    def __init__(self, records: Optional[List[Dict[str, Any]]] = None):
        self.records: List[Dict[str, Any]] = [dict(r) for r in records] if records else []

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)

    def __getitem__(self, idx):
        return self.records[idx]

    @property
    def empty(self) -> bool:
        return len(self.records) == 0

    @property
    def columns(self) -> List[str]:
        if not self.records:
            return []
        keys = []
        for r in self.records:
            for k in r.keys():
                if k not in keys:
                    keys.append(k)
        return keys

    def copy(self) -> "Table":
        return Table(self.records)

    def append(self, row: Dict[str, Any]):
        self.records.append(dict(row))

    def head(self, n: int = 5) -> "Table":
        return Table(self.records[:n])

    def filter(self, predicate: Callable[[Dict[str, Any]], bool]) -> "Table":
        return Table([r for r in self.records if predicate(r)])

    def select(self, cols: List[str]) -> "Table":
        res = []
        for r in self.records:
            res.append({c: r.get(c) for c in cols if c in r})
        return Table(res)

    def sort_by(self, key: str, ascending: bool = True) -> "Table":
        def sort_key(row):
            val = row.get(key)
            if val is None:
                return (1, 0) if ascending else (0, 0)
            return (0, val)
        sorted_rows = sorted(self.records, key=sort_key, reverse=not ascending)
        return Table(sorted_rows)

    def groupby(self, key: str) -> Dict[Any, "Table"]:
        groups: Dict[Any, List[Dict[str, Any]]] = {}
        for r in self.records:
            g_val = r.get(key)
            if g_val not in groups:
                groups[g_val] = []
            groups[g_val].append(r)
        return {k: Table(v) for k, v in groups.items()}

    def sum(self, col: str) -> float:
        total = 0.0
        for r in self.records:
            val = r.get(col, 0)
            try:
                total += float(val) if val is not None else 0.0
            except (ValueError, TypeError):
                pass
        return total

    def mean(self, col: str) -> float:
        vals = []
        for r in self.records:
            val = r.get(col)
            if val is not None:
                try:
                    vals.append(float(val))
                except (ValueError, TypeError):
                    pass
        return sum(vals) / len(vals) if vals else 0.0

    def unique(self, col: str) -> List[Any]:
        seen = []
        for r in self.records:
            v = r.get(col)
            if v is not None and v not in seen:
                seen.append(v)
        return seen

    def to_records(self) -> List[Dict[str, Any]]:
        return [dict(r) for r in self.records]

    def to_markdown(self, max_rows: int = 50) -> str:
        if not self.records:
            return "_No records available_"
        cols = self.columns
        lines = []
        lines.append("| " + " | ".join(str(c) for c in cols) + " |")
        lines.append("| " + " | ".join(["---"] * len(cols)) + " |")
        for r in self.records[:max_rows]:
            row_vals = [str(r.get(c, "")).replace("\n", " ").replace("|", "/") for c in cols]
            lines.append("| " + " | ".join(row_vals) + " |")
        return "\n".join(lines)

    def to_dict(self) -> List[Dict[str, Any]]:
        return self.to_records()
