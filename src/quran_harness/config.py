"""Method choices are read from config.yaml, never hard-coded (CLAUDE.md)."""

from __future__ import annotations

from pathlib import Path

import yaml

from .sources import PROJECT_ROOT

CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# Names the user chooses a form level by, with the index level and what it means.
NIVEAUX = {
    "ecrit": ("written", "mot écrit, clitiques collés"),
    "noyau": ("core", "sans clitiques, article gardé"),
    "nu": ("bare", "sans clitiques ni article"),
}
VERSET = "verset"  # the pause choice that keeps each aya whole


def pause_choices(config: dict) -> list[str]:
    return [*config["segmentation"]["pause_levels"], VERSET]


def default_choices(config: dict) -> tuple[str, str]:
    """(niveau, pause) that config.yaml asks for."""
    level = form_level(config)
    niveau = next(name for name, (key, _) in NIVEAUX.items() if key == level)
    segmentation = config["segmentation"]
    return niveau, VERSET if segmentation["scheme"] == "aya" else segmentation["pause_level"]


def with_choices(config: dict, niveau: str | None = None, pause: str | None = None) -> dict:
    """The configuration with the form level and the pause level chosen for one request."""
    if niveau is not None:
        if niveau not in NIVEAUX:
            raise ValueError(f"niveau inconnu : {niveau!r} (attendu : {', '.join(NIVEAUX)})")
        level = NIVEAUX[niveau][0]
        config["reference_form"]["match_level"] = 0 if level == "written" else 1
        config["reference_form"]["article_is_clitic"] = level == "bare"
    if pause is not None:
        if pause not in pause_choices(config):
            raise ValueError(f"pause inconnue : {pause!r} (attendu : {', '.join(pause_choices(config))})")
        config["segmentation"]["scheme"] = "aya" if pause == VERSET else "waqf"
        if pause != VERSET:
            config["segmentation"]["pause_level"] = pause
    return config


def form_level(config: dict) -> str:
    """Index level ("written", "core" or "bare") that the configuration calls the reference form."""
    reference = config["reference_form"]
    if reference["match_level"] == 0:
        return "written"
    return "bare" if reference["article_is_clitic"] else "core"
