"""Normalizzazione direzionale: un solo modello per long e short (spec §6)."""
from __future__ import annotations


def up(side: str) -> int:
    return 1 if side == "long" else -1


def toward_target(side: str, a: float, b: float) -> float:
    """Positivo se b sta oltre a nella direzione del target (su per long, giù per short)."""
    return up(side) * (b - a)


def broken_edge(side: str, vah: float, val: float) -> float:
    return val if side == "long" else vah


def far_edge(side: str, vah: float, val: float) -> float:
    return vah if side == "long" else val
