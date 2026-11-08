"""Checkout-relative runtime locations; no dependency on a parent workspace."""
from pathlib import Path
DEMO = Path(__file__).resolve().parents[1]
ROOT = DEMO.parent
