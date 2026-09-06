"""Living memory subsystems for Aether."""

try:
    from aia_canvas.src.memory.event_ledger import EventLedger
    from aia_canvas.src.memory.profile_manager import ProfileManager
    from aia_canvas.src.memory.prompt_assembler import PromptAssembler
    from aia_canvas.src.memory.synthesizer import MemorySynthesizer
except ModuleNotFoundError:
    from memory.event_ledger import EventLedger
    from memory.profile_manager import ProfileManager
    from memory.prompt_assembler import PromptAssembler
    from memory.synthesizer import MemorySynthesizer

__all__ = ["EventLedger", "ProfileManager", "PromptAssembler", "MemorySynthesizer"]



