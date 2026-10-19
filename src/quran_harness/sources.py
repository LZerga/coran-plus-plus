"""Provenance of the raw data files: manifest, integrity check, download.

The manifest (data/sources.yaml) is the machine-readable twin of data/SOURCES.md.
Raw files are never modified: they are written once, then set read-only.
"""

from __future__ import annotations

import hashlib
import io
import stat
import time
import urllib.request
import zipfile
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
    # Path of the file inside the ZIP archive at `url` (OpenITI); None for a plain file.
    archive_member: str | None = None


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
            archive_member=e.get("archive_member"),
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
    if source.archive_member:
        content = read_archive_member(source.url, source.archive_member)
    else:
        with urllib.request.urlopen(source.url) as response:
            content = response.read()
    if hashlib.sha256(content).hexdigest() != source.sha256:
        return "SHA-256 différent, fichier non conservé"
    source.path.parent.mkdir(parents=True, exist_ok=True)
    source.path.write_bytes(content)
    source.path.chmod(stat.S_IREAD)
    return "ok"


class RemoteFile(io.RawIOBase):
    """Read-only, seekable view of a remote file through HTTP range requests.

    Lets zipfile read one member of a large archive (OpenITI: 5.9 GB) without
    downloading the whole archive.
    """

    def __init__(self, url: str, retries: int = 5):
        self.url = url
        self.retries = retries
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD")) as response:
            self.size = int(response.headers["Content-Length"])
        self.pos = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.pos, io.SEEK_END: self.size}[whence]
        self.pos = base + offset
        return self.pos

    def readinto(self, buffer) -> int:
        if self.pos >= self.size:
            return 0
        end = min(self.pos + len(buffer), self.size) - 1
        request = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{end}"})
        for attempt in range(self.retries):
            try:
                with urllib.request.urlopen(request, timeout=120) as response:
                    if response.status != 206:
                        raise OSError(f"le serveur ignore la lecture partielle (HTTP {response.status})")
                    data = response.read()
                break
            except OSError:
                if attempt == self.retries - 1:
                    raise
                time.sleep(3)
        buffer[: len(data)] = data
        self.pos += len(data)
        return len(data)


def open_remote(url: str):
    return io.BufferedReader(RemoteFile(url), buffer_size=1 << 20)


def read_archive_member(url: str, member: str, opener=open_remote) -> bytes:
    """Return one member of a remote ZIP archive; zipfile checks its CRC-32."""
    with opener(url) as handle, zipfile.ZipFile(handle) as archive:
        return archive.read(member)
