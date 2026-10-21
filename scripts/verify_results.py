"""Independent arithmetic, execution, pipeline, RAW and stall checks."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hazard_detection import Instruction, PipelineEntry, detect_raw_hazard, matching_hazard_registers  # noqa: E402


@dataclass(frozen=True)
class Op:
    name: str
    kind: str
    dest: str | None = None
    srcs: tuple[str, ...] = ()
    value: int | None = None
    address: int | None = None


def sequential_cycles(instructions: int, stages: int = 5) -> int:
    return instructions * stages


def execute(ops: list[Op]) -> tuple[dict[str, int], dict[int, int]]:
    regs = {f"R{i}": 0 for i in range(32)}
    memory: dict[int, int] = {}
    for op in ops:
        if op.kind == "loadi":
            regs[op.dest] = int(op.value)
        elif op.kind == "add":
            regs[op.dest] = regs[op.srcs[0]] + regs[op.srcs[1]]
        elif op.kind == "sub":
            regs[op.dest] = regs[op.srcs[0]] - regs[op.srcs[1]]
        elif op.kind == "store":
            memory[int(op.address)] = regs[op.srcs[0]]
        elif op.kind == "load":
            regs[op.dest] = memory.get(int(op.address), 0)
        else:
            raise ValueError(f"Unsupported operation: {op.kind}")
    return regs, memory


def raw_dependencies(ops: list[Op]) -> list[tuple[int, int, str]]:
    dependencies = []
    for reader, op in enumerate(ops):
        for src in op.srcs:
            writer = next(
                (idx for idx in range(reader - 1, -1, -1) if ops[idx].dest == src),
                None,
            )
            if writer is not None:
                dependencies.append((writer + 1, reader + 1, src))
    return dependencies


def simulate_no_forwarding(ops: list[Op]) -> tuple[int, int, list[tuple[int, str | None, str | None, str | None, str | None, str | None]]]:
    """Cycle-simulate IF/ID/EX/MEM/WB with ID reads and WB write-first timing."""
    if_id = id_ex = ex_mem = mem_wb = None
    next_fetch = 0
    cycles = 0
    stalls = 0
    rows = []

    while next_fetch < len(ops) or any(x is not None for x in (if_id, id_ex, ex_mem, mem_wb)):
        cycles += 1
        old_if, old_id, old_ex, old_wb = if_id, id_ex, ex_mem, mem_wb
        blocked = False
        if old_if is not None:
            sources = set(ops[old_if].srcs)
            # An EX/MEM writer is not yet in WB; an old WB write is
            # visible to an ID read in this same cycle under our assumption.
            for producer in (old_id, old_ex):
                if producer is not None and ops[producer].dest in sources:
                    blocked = True
                    break

        fetched = next_fetch if next_fetch < len(ops) else None
        if blocked:
            stalls += 1
            fetch_stage = old_if  # PC and IF/ID are held during the stall.
            id_label = f"I{old_if + 1} (S)"
        else:
            fetch_stage = fetched
            id_label = f"I{old_if + 1}" if old_if is not None else None

        rows.append((
            cycles,
            f"I{fetch_stage + 1}" if fetch_stage is not None else None,
            id_label,
            f"I{old_id + 1}" if old_id is not None else None,
            f"I{old_ex + 1}" if old_ex is not None else None,
            f"I{old_wb + 1}" if old_wb is not None else None,
        ))

        if blocked:
            if_id = old_if
            id_ex = None
        else:
            id_ex = old_if
            if_id = fetched
            if fetched is not None:
                next_fetch += 1
        ex_mem = old_id
        mem_wb = old_ex
    return cycles, stalls, rows


def ideal_pipeline_cycles(instructions: int, stages: int = 5) -> int:
    return instructions + stages - 1


def ideal_pipeline_schedule(names: list[str], stages: tuple[str, ...] = ("IF", "ID", "EX", "MEM", "WB")) -> list[dict[str, str | None]]:
    schedule = []
    for cycle in range(1, len(names) + len(stages)):
        row = {}
        for stage_index, stage in enumerate(stages):
            instruction_index = cycle - stage_index - 1
            row[stage] = names[instruction_index] if 0 <= instruction_index < len(names) else None
        schedule.append(row)
    return schedule


def snapshot_stalls_no_forwarding(source_regs: tuple[str, ...], stage_destinations: dict[str, str | None]) -> tuple[int, list[dict[str, str | None]]]:
    """Advance EX/MEM/WB writers each cycle while the decoded instruction waits in ID."""
    stages = dict(stage_destinations)
    stalls = 0
    trace = []
    while any(stages[s] in source_regs for s in ("EX", "MEM")):
        trace.append(dict(stages))
        stalls += 1
        stages = {"EX": None, "MEM": stages["EX"], "WB": stages["MEM"]}
    trace.append(dict(stages))
    return stalls, trace


def stalls_until_wb_visible(producer_stage: str) -> int:
    """Simulate one producer advancing toward WB while a consumer waits in ID."""
    stage_number = {"EX": 2, "MEM": 3, "WB": 4}[producer_stage]
    stalls = 0
    while stage_number in (2, 3):
        stalls += 1
        stage_number += 1
    return stalls


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS: {label}")


def main() -> None:
    a1 = [
        Op("I1", "loadi", "R1", value=10),
        Op("I2", "loadi", "R2", value=20),
        Op("I3", "add", "R3", ("R1", "R2")),
        Op("I4", "sub", "R4", ("R3", "R1")),
        Op("I5", "store", srcs=("R4",), address=100),
        Op("I6", "load", "R5", address=100),
    ]
    regs, memory = execute(a1)
    check(sequential_cycles(6) == 30, "Assessment 1 sequential cycle count is 30")
    check([regs[f"R{i}"] for i in range(1, 6)] == [10, 20, 30, 20, 20], "Assessment 1 final R1-R5 values are 10, 20, 30, 20, 20")
    check(memory.get(100) == 20, "Assessment 1 memory[100] is 20")
    check(30 / 6 == 5, "Assessment 1 CPI is 5")

    ideal4 = ideal_pipeline_cycles(4)
    check(ideal4 == 8, "Assessment 2 ideal four-instruction pipeline completes in 8 cycles")
    a2_schedule = ideal_pipeline_schedule(["I1", "I2", "I3", "I4"])
    check(a2_schedule[3] == {"IF": "I4", "ID": "I3", "EX": "I2", "MEM": "I1", "WB": None}, "Assessment 2 cycle 4 stage assignment matches the ideal schedule")
    check(a2_schedule[-1]["WB"] == "I4" and len(a2_schedule) == 8, "Assessment 2 stage progression completes I4 in WB in cycle 8")
    check([ideal_pipeline_cycles(n) for n in (4, 8, 12, 20, 100)] == [8, 12, 16, 24, 104], "Assessments 2-3 ideal pipeline schedules follow N+4")

    sequential = [20, 40, 60, 100, 500]
    pipelined = [8, 12, 16, 24, 104]
    speedups = [s / p for s, p in zip(sequential, pipelined)]
    check(abs(speedups[0] - 2.5) < 1e-12 and abs(speedups[-1] - 500 / 104) < 1e-12, "Assessment 3 speedups calculate from sequential/pipelined cycles")

    seq1 = [
        Op("I1", "add", "R1", ("R2", "R3")),
        Op("I2", "sub", "R4", ("R1", "R5")),
        Op("I3", "add", "R6", ("R4", "R7")),
    ]
    seq2 = [
        Op("I1", "loadi", "R1", value=10),
        Op("I2", "loadi", "R2", value=20),
        Op("I3", "add", "R3", ("R1", "R2")),
        Op("I4", "store", srcs=("R3",), address=100),
        Op("I5", "load", "R4", address=100),
    ]
    seq3 = [
        Op("I1", "loadi", "R1", value=5),
        Op("I2", "add", "R2", ("R1", "R3")),
        Op("I3", "sub", "R4", ("R2", "R1")),
        Op("I4", "add", "R5", ("R4", "R6")),
    ]
    expected = [
        [(1, 2, "R1"), (2, 3, "R4")],
        [(1, 3, "R1"), (2, 3, "R2"), (3, 4, "R3")],
        [(1, 2, "R1"), (2, 3, "R2"), (1, 3, "R1"), (3, 4, "R4")],
    ]
    actual = [raw_dependencies(seq) for seq in (seq1, seq2, seq3)]
    check(actual == expected, "Assessment 4 RAW dependency lists include all earlier writers")
    cycle_result = [simulate_no_forwarding(seq) for seq in (seq1, seq2, seq3)]
    check([item[1] for item in cycle_result] == [4, 4, 6], "Assessment 4 no-forwarding cycle simulation gives 4, 4, and 6 stalls")
    check([item[0] for item in cycle_result] == [11, 13, 14], "Assessment 4 simulated completion cycles are 11, 13, and 14")
    stage_stalls = [stalls_until_wb_visible(stage) for stage in ("EX", "MEM", "WB")]
    check(stage_stalls == [2, 1, 0], "Assessment 4 EX/MEM/WB producer cases require 2/1/0 simulated stalls")

    decoded = Instruction("ADD R5, R1, R2", "R1", "R2", "R5")
    id_ex = PipelineEntry(Instruction("SUB R4, R3, R1", "R3", "R1", "R4"), True)
    ex_mem = PipelineEntry(Instruction("LOADI R1, 10", dest_reg="R1"), True)
    mem_wb = PipelineEntry(Instruction("ADD R2, R6, R7", "R6", "R7", "R2"), True)
    invalid_match = PipelineEntry(Instruction("LOADI R1, 99", dest_reg="R1"), False)
    check(detect_raw_hazard(decoded, id_ex, ex_mem, mem_wb), "Assessment 5 detector finds a valid RAW match")
    check(matching_hazard_registers(decoded, (id_ex, ex_mem, mem_wb)) == ("R1", "R2"), "Assessment 5 matches R1 in EX/MEM and R2 in MEM/WB")
    check(not detect_raw_hazard(decoded, PipelineEntry(), PipelineEntry(), PipelineEntry()), "Assessment 5 detector returns false when there are no valid matches")
    check(not detect_raw_hazard(decoded, id_ex, invalid_match, PipelineEntry()), "Assessment 5 detector ignores invalid pipeline entries")
    snapshot_stalls, snapshot_trace = snapshot_stalls_no_forwarding(
        decoded.source_registers, {"EX": "R4", "MEM": "R1", "WB": "R2"}
    )
    check(snapshot_stalls == 1, "Assessment 5 cycle-level snapshot progression inserts exactly one stall")
    check(snapshot_trace[0]["MEM"] == "R1" and snapshot_trace[1]["WB"] == "R1", "Assessment 5 R1 advances from MEM to WB before the ID read proceeds")

    print("\nSpeedups:", ", ".join(f"{x:.4f}" for x in speedups))
    print("Assessment 4 simulated (cycles, stalls):", [(c, s) for c, s, _ in cycle_result])
    print("Assessment 5 snapshot stall trace:", snapshot_trace)
    print("All verification checks passed.")


if __name__ == "__main__":
    main()
