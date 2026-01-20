from __future__ import annotations

import json
from pathlib import Path


def _load_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _write_list(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def load_customers(data_dir: str | Path) -> list[dict]:
    path = Path(data_dir) / "customers.json"
    return _load_list(path)


def upsert_customer(data_dir: str | Path, customer: dict) -> None:
    path = Path(data_dir) / "customers.json"
    customers = _load_list(path)
    name = (customer.get("name") or "").strip()
    if not name:
        return
    for entry in customers:
        if (entry.get("name") or "").strip() == name:
            entry.update(customer)
            _write_list(path, customers)
            return
    customers.append(customer)
    _write_list(path, customers)


def load_products(data_dir: str | Path) -> list[dict]:
    path = Path(data_dir) / "products.json"
    return _load_list(path)
