"""Load the demo panel or a Statista XLS export."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED = [
    "country",
    "region",
    "market_size_musd",
    "cagr",
    "competition_index",
    "fixed_cost_musd",
    "min_spend_musd",
    "max_spend_musd",
    "risk_weight",
]

ROOT = Path(__file__).resolve().parents[1]
DEMO_PATH = ROOT / "data" / "ev_charging_markets.csv"


def load_demo() -> pd.DataFrame:
    frame = pd.read_csv(DEMO_PATH)
    return _validate(frame)


def load_statista_xls(path: str | Path | object, sheet: int | str = 0) -> pd.DataFrame:
    """Read a Statista XLS/XLSX export or a cleaned CSV with the project schema.

    Statista chart exports are not a stable schema. Rename columns to REQUIRED
    before calling this, or pass a file that already matches the demo CSV.
    Accepts a path or a file-like object (Streamlit uploader).
    """
    name = getattr(path, "name", "")
    suffix = Path(name).suffix.lower() if name else Path(str(path)).suffix.lower()
    if hasattr(path, "read") and not isinstance(path, (str, Path)):
        if suffix in {".xls", ".xlsx"}:
            frame = pd.read_excel(path, sheet_name=sheet)
        else:
            frame = pd.read_csv(path)
    else:
        path = Path(path)
        if path.suffix.lower() in {".xls", ".xlsx"}:
            frame = pd.read_excel(path, sheet_name=sheet)
        else:
            frame = pd.read_csv(path)
    frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
    return _validate(frame)


def _validate(frame: pd.DataFrame) -> pd.DataFrame:
    missing = [col for col in REQUIRED if col not in frame.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    out = frame[REQUIRED].copy()
    out["country"] = out["country"].astype(str)
    for col in REQUIRED[2:]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out[REQUIRED[2:]].isna().any().any():
        raise ValueError("Numeric columns contain non-numeric values")
    if (out["competition_index"] <= 0).any():
        raise ValueError("competition_index must be positive")
    if (out["min_spend_musd"] > out["max_spend_musd"]).any():
        raise ValueError("min_spend_musd exceeds max_spend_musd")
    return out.reset_index(drop=True)
