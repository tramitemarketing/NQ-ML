"""Revisore di backtest - motore Pro.

Audit statistico della strategia di un cliente con i dati di mercato: bootstrap a blocchi per giorno,
Deflated Sharpe Ratio con N tentativi, beta per minuto del giorno, placebo con la stessa struttura,
audit meccanico del look-ahead, decadimento fuori campione, report HTML con verdetto A-F.
Strumento educativo, non consulenza finanziaria.
"""
__version__ = "0.1.0"

from .market import Market, load_market  # noqa: E402,F401
from .trades import load_trades, attach_market  # noqa: E402,F401
from .audit import AuditConfig, run_audit  # noqa: E402,F401
