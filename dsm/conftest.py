from __future__ import annotations

from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config: object) -> bool:
    return collection_path.name == "__init__.py" and collection_path.parent == Path(__file__).parent
