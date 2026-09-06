"""Living memory subsystems for Aether."""

try:
    from aia_canvas.src.memory.event_ledger import EventLedger
except ModuleNotFoundError:
    from memory.event_ledger import EventLedger

__all__ = ["EventLedger"]

