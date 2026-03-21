"""Shared analysis utilities."""

import json
from pathlib import Path

import pandas as pd

# Display names for disclosure modes (shared across tests that use them)
MODE_LABELS = {
    "random": "Random Subset",
    "all": "All Tools (no disclosure)",
    "disclosed": "Late Disclosure",
    "noisy": "Noisy Disclosure",
}


def load_results(paths: list[Path]) -> pd.DataFrame:
    """Load one or more result JSON files into a DataFrame."""
    frames = []
    for path in paths:
        with open(path) as f:
            data = json.load(f)
        df = pd.DataFrame(data["results"])
        df["provider"] = data["provider"]
        if "mode" not in df.columns:
            df["mode"] = data.get("mode", "random")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)
