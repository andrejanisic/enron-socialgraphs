"""Where the project's data, results and figures live."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"
GRAPH_PATH = DATA_DIR / "main_characters_graph.pkl"
MAIN_DB = DATA_DIR / "enron_main_characters.sqlite"
EXTERNAL_DB = DATA_DIR / "enron_external.sqlite"

RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = PROJECT_ROOT / "figures"
