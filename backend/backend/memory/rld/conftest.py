from __future__ import annotations

import sys
from pathlib import Path

# Prepend memory/rld/src to sys.path so RLD tests resolve to RLD's dsm package
rld_src = Path(__file__).resolve().parent / "src"
if str(rld_src) not in sys.path:
    sys.path.insert(0, str(rld_src))


def pytest_ignore_collect(collection_path: Path, config: object) -> bool:
    return collection_path.name == "__init__.py" and collection_path.parent == Path(__file__).parent

