"""Record the golden output. Run only when a change to generated values is intended.

    uv run python tests/golden/record.py

A changed golden file is a breaking change for every user who relies on a seed, so the diff
belongs in the pull request and the changelog.
"""

from pathlib import Path

import dataspecter

HERE = Path(__file__).parent
FORMATS = ("csv", "json", "jsonl")


def record(spec_name: str = "spec") -> None:
    spec = dataspecter.load_spec(HERE / f"{spec_name}.yaml")
    for fmt in FORMATS:
        dataspecter.write(spec, out_dir=HERE / "expected" / spec_name / fmt, format=fmt)


if __name__ == "__main__":
    for path in sorted(HERE.glob("*.yaml")):
        record(path.stem)
        print(f"recorded {path.stem}")
