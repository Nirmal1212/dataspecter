"""Config-driven synthetic data simulator.

import dataspecter

spec = dataspecter.load_spec("shop.yaml")
for customer in dataspecter.generate(spec, seed=42).records("customer"):
    ...
dataspecter.write(spec, out_dir="out", format="jsonl")
"""

from dataspecter._version import __version__
from dataspecter.api import generate, write
from dataspecter.errors import ExportError, SpecError
from dataspecter.spec import load_spec

__all__ = ["ExportError", "SpecError", "__version__", "generate", "load_spec", "write"]
