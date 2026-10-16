"""Provenance of the raw data files: manifest, integrity check, download.

The manifest (data/sources.yaml) is the machine-readable twin of data/SOURCES.md.
Raw files are never modified: they are written once, then set read-only.
"""

from __future__ import annotations

import hashlib
import stat
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = PROJECT_ROOT / "data" / "sources.yaml"
RAW_DIR = PROJECT_ROOT / "data" / "raw"


@dataclass(frozen=True)
class Source:
    id: str
    path: Path
    url: str
    sha256: str
    size: int
    license: str
    retrieved: str
    requires_terms_acceptance: bool = False


def load_manifest(manifest_path: Path = MANIFEST_PATH, root: Path = PROJECT_ROOT) -> list[Source]:
    with open(manifest_path, encoding="utf-8") as f:
        entries = yaml.safe_load(f)["sources"]
    return [
        Source(
            id=e["id"],
            path=root / e["path"],
            url=e["url"],
            sha256=e["sha256"],
            size=e["size"],
            license=e["license"],
            retrieved=str(e["retrieved"]),
            requires_terms_acceptance=e.get("requires_terms_acceptance", False),
        )
        for e in entries
    ]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(source: Source) -> str:
    """Return "ok", or the reason the local file does not match the manifest."""
    if not source.path.is_file():
        return "absent"
    if source.path.stat().st_size != source.size:
        return "taille différente"
    if sha256_of(source.path) != source.sha256:
        return "SHA-256 différent"
    return "ok"


def is_read_only(path: Path) -> bool:
    return not path.stat().st_mode & stat.S_IWRITE


def fetch(source: Source, accept_terms: bool = False) -> str:
    """Download a missing source. Nothing is kept if the hash does not match."""
    if source.path.is_file():
        return check(source)
    if source.requires_terms_acceptance and not accept_terms:
        return "conditions d'utilisation à accepter (--accept-terms)"
    with urllib.request.urlopen(source.url) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != source.sha256:
        return "SHA-256 différent, fichier non conservé"
    source.path.parent.mkdir(parents=True, exist_ok=True)
    source.path.write_bytes(content)
    source.path.chmod(stat.S_IREAD)
    return "ok"
