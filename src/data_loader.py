"""Load and validate portfolio holdings from JSON or CSV."""

from pathlib import Path
import json
import pandas as pd
from typing import Any, Dict


def load_portfolio_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_portfolio_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)
