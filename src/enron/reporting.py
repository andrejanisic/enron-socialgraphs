"""Turning results into Markdown tables and summary files."""

import numpy as np
import pandas as pd


def fmt_number(x, digits: int = 3) -> str:
    if isinstance(x, (float, np.floating)):
        return "" if np.isnan(x) else f"{x:.{digits}f}"
    return str(x)


def fmt_p(p: float, n: int) -> str:
    """p-value from n shuffles. When no shuffle reached the observed value, write '< 1/n'."""
    if p <= 1 / (n + 1) + 1e-12:
        return f"< {1 / n:g}"
    return f"{p:.2g}" if p < 0.01 else f"{p:.3f}"


def md_table(df: pd.DataFrame, digits: int = 3) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(fmt_number(x, digits) for x in row) + " |")
    return "\n".join(lines)
