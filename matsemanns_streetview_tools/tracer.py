from contextlib import contextmanager
import time
from typing import TypedDict


class TraceEntry(TypedDict):
    invocations: int
    total_time: float

_traces: dict[str, TraceEntry] = {}

def clear():
    _traces.clear()

def add(trace: str, time_used: float, invocations):
    value = _traces.setdefault(trace, {"invocations": 0, "total_time": 0})
    value["invocations"] += 1
    value["total_time"] += time_used

def out() -> str:

    def render(name: str, trace_entry: TraceEntry) -> str:
        invocations = str(trace_entry["invocations"]).rjust(4)
        total_time=f"{trace_entry["total_time"]:.2f}".rjust(9)
        avg = f"{(trace_entry["total_time"] / trace_entry["invocations"]):.2f}"
        return f"{name.ljust(20)} invocations: {invocations},    total_time: {total_time}s ({avg}s avg)"

    traces = "\n".join([render(k,v) for k,v in _traces.items()])
    return f"Traces:\n{traces}"

@contextmanager
def trace(trace: str, invocations: int = 1):
    start = time.time()
    yield
    time_used = time.time() - start
    add(trace, time_used, invocations)

