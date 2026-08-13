from __future__ import annotations
import time
from pathlib import Path
from typing import Dict, Iterable
from .util import sha256_file, stable_id
from .ledger import upsert_source

def register_file(path: Path, source_type: str = "local_file") -> Dict:
    path = Path(path).expanduser()
    sha = sha256_file(path)
    src = {
        "id": stable_id({"path": str(path), "sha256": sha}, "src_"),
        "path": str(path),
        "url": None,
        "title": path.name,
        "sha256": sha,
        "source_type": source_type,
        "created_at": time.time(),
        "metadata": {"size": path.stat().st_size}
    }
    upsert_source(src)
    return src
