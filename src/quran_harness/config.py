"""Method choices are read from config.yaml, never hard-coded (CLAUDE.md)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .sources import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
VERSET = "verset"  # the pause choice that keeps each aya whole


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def pause_choices(config: dict) -> list[str]:
    return [*config["segmentation"]["pause_levels"], VERSET]


def default_pause(config: dict) -> str:
    """The pause choice config.yaml asks for."""
    segmentation = config["segmentation"]
    return VERSET if segmentation["scheme"] == "aya" else segmentation["pause_level"]


def with_pause(config: dict, pause: str | None = None) -> dict:
    """The configuration with the pause level chosen for one request."""
    if pause is not None:
        if pause not in pause_choices(config):
            raise ValueError(f"pause inconnue : {pause!r} (attendu : {', '.join(pause_choices(config))})")
        config["segmentation"]["scheme"] = "aya" if pause == VERSET else "waqf"
        if pause != VERSET:
            config["segmentation"]["pause_level"] = pause
    return config
