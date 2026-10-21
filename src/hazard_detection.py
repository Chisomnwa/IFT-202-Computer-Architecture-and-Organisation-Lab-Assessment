"""RAW hazard detection for the assessment's five-stage pipeline."""

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class Instruction:
    name: str
    src1: Optional[str] = None
    src2: Optional[str] = None
    dest_reg: Optional[str] = None

    @property
    def source_registers(self) -> tuple[str, ...]:
        return tuple(reg for reg in (self.src1, self.src2) if reg is not None)


@dataclass(frozen=True)
class PipelineEntry:
    instruction: Optional[Instruction] = None
    valid: bool = False

    @property
    def dest_reg(self) -> Optional[str]:
        if not self.valid or self.instruction is None:
            return None
        return self.instruction.dest_reg


def detect_raw_hazard(
    decoded_instr: Instruction,
    id_ex: PipelineEntry,
    ex_mem: PipelineEntry,
    mem_wb: PipelineEntry,
) -> bool:
    """Return True for a source/destination match in any valid later stage.

    This detects an outstanding RAW dependency; it does not by itself decide
    whether, or how long, the pipeline must stall.
    """
    sources = set(decoded_instr.source_registers)
    return any(
        entry.valid
        and entry.dest_reg is not None
        and entry.dest_reg in sources
        for entry in (id_ex, ex_mem, mem_wb)
    )


def matching_hazard_registers(
    decoded_instr: Instruction,
    later_stages: Sequence[PipelineEntry],
) -> tuple[str, ...]:
    """Return matching source registers, in source order, without duplicates."""
    destinations = {
        entry.dest_reg
        for entry in later_stages
        if entry.valid and entry.dest_reg is not None
    }
    return tuple(dict.fromkeys(reg for reg in decoded_instr.source_registers if reg in destinations))
