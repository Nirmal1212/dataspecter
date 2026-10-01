"""Throughput and memory benchmark.

    uv run python benchmarks/bench.py flat 1000000
    uv run python benchmarks/bench.py flat 1000000 --memory

Each scenario writes one entity to CSV in a temporary directory. Timing takes the best of three
runs; `--memory` reports peak traced memory from a single run instead, which is much slower.
Compare numbers only between runs on the same machine.
"""

import shutil
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

import dataspecter

SCENARIOS = {
    "flat": {
        "id": {"type": "sequence"},
        "user_id": {"type": "integer", "min": 1, "max": 100000},
        "amount": {
            "type": "float",
            "distribution": "normal",
            "mean": 40,
            "stddev": 15,
            "min": 0,
            "precision": 2,
        },
        "kind": {"type": "choice", "values": ["view", "click", "buy"], "weights": [80, 15, 5]},
        "at": {"type": "datetime", "min": "2025-01-01T00:00:00", "max": "2025-12-31T23:59:59"},
    },
    # The built-in realistic types.
    "realistic": {
        "id": {"type": "sequence"},
        "name": {"type": "full_name"},
        "email": {"type": "email"},
        "phone": {"type": "phone", "locale": "en_IN"},
        "home": {"type": "address"},
    },
    # One Faker provider, for comparison with the built-in types. Needs Faker installed.
    "faker": {
        "id": {"type": "sequence"},
        "company": {"type": "faker", "provider": "company"},
    },
    # A pattern, a unique pattern, hidden inputs and a template over them.
    "text": {
        "id": {"type": "sequence"},
        "code": {"type": "pattern", "pattern": "??-####-####", "unique": True},
        "phone": {"type": "pattern", "pattern": "+91-%#########"},
        "first": {"type": "choice", "values": ["Asha", "Ravi", "Meera", "Tom"], "hidden": True},
        "last": {"type": "choice", "values": ["Rao", "Nair", "Smith"], "hidden": True},
        "email": {"type": "template", "template": "{first|slug}.{last|slug}.{id}@example.com"},
        "amount": {"type": "float", "min": 0, "max": 500, "precision": 2},
    },
    # An object, an object inside it, and references that copy an object and read a nested path.
    "nested": {
        "entities": {
            "customer": {
                "count": 1000,
                "fields": {
                    "id": {"type": "sequence"},
                    "address": {
                        "type": "object",
                        "fields": {
                            "city": {"type": "choice", "values": ["Pune", "Austin", "Leeds"]},
                            "postcode": {"type": "integer", "min": 10000, "max": 99999},
                        },
                    },
                },
            }
        },
        "fields": {
            "id": {"type": "sequence"},
            "customer_id": "$customer.id",
            "ship_city": "$customer.address.city",
            "ship_to": "$customer.address",
            "home": {
                "type": "object",
                "fields": {
                    "amount": {"type": "float", "min": 0, "max": 500, "precision": 2},
                    "geo": {
                        "type": "object",
                        "fields": {
                            "lat": {"type": "float", "min": -90, "max": 90},
                            "lon": {"type": "float", "min": -180, "max": 180},
                        },
                    },
                },
            },
        },
    },
}


def spec_for(scenario: str, rows: int) -> dataspecter.spec.Spec:
    raw = {"version": 1, "seed": 1, "entities": {"event": {"count": rows, "fields": {}}}}
    definition = SCENARIOS[scenario]
    if "entities" in definition:  # a scenario may bring parent entities of its own
        raw["entities"].update(definition["entities"])
        raw["entities"]["event"] = {"count": rows, "fields": definition["fields"]}
        for key in ("types", "locale"):
            if key in definition:
                raw[key] = definition[key]
    else:
        raw["entities"]["event"]["fields"] = definition
    return dataspecter.load_spec(raw)


def run_once(scenario: str, rows: int) -> float:
    out = Path(tempfile.mkdtemp(prefix="dataspecter-bench-"))
    try:
        spec = spec_for(scenario, rows)
        start = time.perf_counter()
        dataspecter.write(spec, out_dir=out)
        return time.perf_counter() - start
    finally:
        shutil.rmtree(out, ignore_errors=True)


def main() -> None:
    scenario, rows = sys.argv[1], int(sys.argv[2])
    if "--memory" in sys.argv:
        tracemalloc.start()
        run_once(scenario, rows)
        peak = tracemalloc.get_traced_memory()[1] / 1e6
        print(f"{scenario:10} {rows:>9} rows  peak traced memory {peak:8.2f} MB")
        return
    best = min(run_once(scenario, rows) for _ in range(3))
    print(f"{scenario:10} {rows:>9} rows  {best:7.2f} s  {rows / best:>9,.0f} rows/s")


if __name__ == "__main__":
    main()
