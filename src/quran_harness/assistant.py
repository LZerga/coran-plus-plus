"""Step 9 (optional): a plain-language summary of a fiche, and forms worth comparing.

Everything said comes from a list of *facts*: sentences written by this module from
the numbers of a fiche. Three kinds of statement are kept apart in every output:

    calculé             computed by the harness (always tied to fact identifiers)
    cité d'une source   provenance of the data, read from the database
    note humaine        a note written by a person, read from data/notes.yaml

Without a model, the summary is the list of facts. With one, the model may only
rephrase and shorten: it is given the facts and nothing else, must cite the facts
behind each sentence, and every sentence is then checked. A sentence is thrown
away when it cites no fact, holds a number or an Arabic word absent from the facts
it cites, or uses a word of interpretation (CLAUDE.md rule 4). The model never
writes a result; if it is unavailable, the summary falls back to the facts.
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from . import compare
from .fiche import Fiche
from .index import forms_of_root, search_key
from .sources import PROJECT_ROOT

CALCULE, SOURCE, NOTE = "calculé", "cité d'une source", "note humaine"
NOTES_PATH = PROJECT_ROOT / "data" / "notes.yaml"
WITHOUT_MODEL = "sans modèle"

# Words that announce an interpretation. A sentence holding one is rejected.
INTERPRETATION = re.compile(
    r"\b(signifi\w*|veut dire|veulent dire|sens\b|symbolis\w*|exprim\w*|désign\w*|évoqu\w*|suggèr\w*|"
    r"impliqu\w*|prouv\w*|démontr\w*|révèl\w*|miracl\w*|intention\w*|parce que|car\b|donc\b)",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_ARABIC = re.compile(r"[ء-ٰٟ-ۭ]+")

SYSTEM_PROMPT = """Tu reformules en français simple des faits déjà calculés par un programme d'étude du texte coranique.

Le lecteur est un chercheur qui veut lire en quelques phrases ce que montre une fiche, sans parcourir ses tableaux.

Ce que tu reçois : une liste de faits numérotés (F1, F2…) et une liste de formes candidates à la comparaison (S1, S2…). Ces deux listes sont tout ce que tu sais ; n'utilise aucune autre connaissance, ni sur la langue arabe ni sur le texte.

Ce que tu rends :
- `summary` : de trois à sept phrases courtes qui disent l'essentiel des faits. Chaque phrase cite, dans `facts`, les identifiants des faits qu'elle reprend.
- `suggestions` : au plus le nombre demandé de candidats, choisis parmi la liste S, chacun avec une raison d'une phrase tirée des faits et les identifiants qui la fondent.

Règles, chacune vérifiée automatiquement après ta réponse ; une phrase qui en enfreint une est écartée :
- Écris les nombres en chiffres, et seulement des nombres présents dans les faits cités.
- Recopie les mots arabes exactement comme dans les faits cités, sans les traduire ni les translittérer.
- Décris, n'interprète pas : ne dis jamais ce qu'un mot signifie, ce qu'un passage veut dire, ni pourquoi une association existe. Le programme observe des comptages ; il ne connaît pas le sens.
- Quand un fait dit qu'une association est « au-dessus du hasard », « attendue par la seule fréquence » ou « trop rare pour conclure », garde cette formule telle quelle. Si aucun contrôle aléatoire n'a été lancé, ne parle pas de hasard.
- Si un fait te paraît surprenant ou douteux, reprends-le tel quel plutôt que de le corriger."""

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text": {"type": "string"}, "facts": {"type": "array", "items": {"type": "string"}}},
                "required": ["text", "facts"],
                "additionalProperties": False,
            },
        },
        "suggestions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate": {"type": "string"},
                    "reason": {"type": "string"},
                    "facts": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["candidate", "reason", "facts"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "suggestions"],
    "additionalProperties": False,
}


class AssistantUnavailable(RuntimeError):
    """The model could not be reached or declined; the caller falls back to the facts."""


@dataclass(frozen=True)
class Fact:
    id: str
    text: str


@dataclass(frozen=True)
class Statement:
    kind: str  # CALCULE | SOURCE | NOTE
    text: str
    basis: tuple[str, ...]  # fact identifiers, source identifiers, or author and date of a note


@dataclass(frozen=True)
class Summary:
    statements: list[Statement]
    suggestions: list[Statement]
    engine: str  # WITHOUT_MODEL, or the name of the model that rephrased
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (sentence, why it was thrown away)
    notice: str = ""  # why the model was not used, when it was asked for


# A completer sends the instructions and the facts to a model and returns its JSON answer.
Completer = Callable[[str, str, dict], dict]


# --- Facts --------------------------------------------------------------------


def _fr(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _subject(fiche: Fiche) -> str:
    if fiche.form.startswith("racine "):
        return f"La racine {fiche.root} ({fiche.lemma})"
    return f"La forme {fiche.form} (lemme {fiche.lemma}, racine {fiche.root})"


def facts_of(fiche: Fiche, max_companions: int) -> list[Fact]:
    """The fiche as sentences. Every number in them is a number of the fiche."""
    texts: list[str] = []
    ayas = len({ref.rsplit(":", 1)[0] for ref in fiche.occurrences})
    texts.append(
        f"{_subject(fiche)} a {len(fiche.occurrences)} occurrences, dans {ayas} versets et {len(fiche.uses)} segments "
        f"(lecture {fiche.parameters['lecture']}, forme prise {fiche.parameters['forme']}, découpage {fiche.parameters['découpage']})."
    )
    writings = fiche.writings.most_common(6)
    texts.append("Graphies rencontrées : " + ", ".join(f"{text} {count} fois" for text, count in writings) + ".")
    positions = Counter(use.position for use in fiche.uses)
    texts.append("Position dans le segment : " + ", ".join(f"{name} {count} fois" for name, count in positions.most_common()) + ".")
    if fiche.attached:
        attached = sorted(fiche.attached.items(), key=lambda item: -len(item[1]))
        texts.append("Collé à la forme : " + ", ".join(f"{form} {len(refs)} fois" for (form, _), refs in attached) + ".")

    statistics = fiche.statistics
    if statistics:
        texts.append(
            f"Un contrôle aléatoire a été lancé : {statistics['permutations']} mélanges des mots entre les segments, "
            f"seuil {_fr(statistics['alpha'], 2)} après correction pour {len(fiche.companions)} compagnons testés."
        )
    else:
        texts.append("Aucun contrôle aléatoire n'a été lancé : les comptages ne disent pas s'ils dépassent le hasard.")

    kinds = {"a": "de la même racine", "b": "d'une autre racine", "c": "lettre ou pronom"}
    for companion in sorted(fiche.companions, key=lambda c: (-len(c.segments), -len(c.refs), c.form))[:max_companions]:
        described = f"lemme {companion.lemma}" if companion.lemma else "sans lemme"
        text = (
            f"Le mot {companion.form} ({described}, {kinds[companion.kind]}) est dans {len(companion.segments)} "
            f"des {len(fiche.uses)} segments de la forme : {companion.before} fois avant elle, {companion.after} fois après."
        )
        if statistics and companion.stats:
            control = next(iter(companion.stats.controls.values()))
            text += (
                f" Il est dans {companion.stats.n_y} segments du texte ; attendu au hasard {_fr(control.expected, 2)} ; "
                f"p corrigée {_fr(control.q_value, 3)} ; lecture du contrôle : "
                f"{companion.stats.reading(statistics['alpha'], statistics['min_cooccurrence'])}."
            )
        texts.append(text)

    if fiche.pairs:
        relations = Counter(pair.comparison.relation for pair in fiche.pairs)
        counts = ", ".join(f"{compare.LABELS[r]} {relations[r]}" for r in compare.LABELS if relations[r])
        texts.append(f"Comparés deux à deux, les segments donnent {len(fiche.pairs)} paires : {counts}.")
    elif fiche.pairs_skipped:
        texts.append(f"Les segments n'ont pas été comparés deux à deux : {fiche.pairs_skipped} paires, au-delà de la limite.")
    if fiche.groups:
        sizes = ", ".join(str(len(group.members)) for group in fiche.groups[:8])
        text = f"Regroupés par ressemblance, les segments forment {len(fiche.groups)} groupes, de tailles {sizes}."
        largest = fiche.groups[0]
        if largest.shared_block:
            text += f" Le plus grand partage le bloc {largest.shared_block} dans {largest.shared_in} de ses {largest.pairs} paires."
        texts.append(text)
    if fiche.readings:
        block = fiche.readings
        unchanged = len(fiche.companions) - len(block.touched)
        texts.append(
            f"Dans les {len(block.riwayat)} autres riwāyāt comparées, au niveau des lettres seulement, "
            f"{len(block.on_reference)} écarts touchent la forme, et {unchanged} compagnons sur {len(fiche.companions)} "
            f"gardent leur association inchangée."
        )
    return [Fact(f"F{number}", text) for number, text in enumerate(texts, start=1)]


def candidates_of(connection: sqlite3.Connection, fiche: Fiche, level: str, limit: int) -> list[Fact]:
    """Forms worth comparing with the form of the fiche, all taken from the index of its root."""
    rows = forms_of_root(connection, fiche.root, level)
    own = search_key(fiche.form.removeprefix("racine "))
    same = [r for r in rows if r.lemma == fiche.lemma and search_key(r.form) != own]
    other = [r for r in rows if r.lemma != fiche.lemma]
    by_count = lambda r: (-r.occurrences, r.form)  # noqa: E731
    chosen = sorted(same, key=by_count)[:limit] + sorted(other, key=by_count)[:limit]
    return [
        Fact(
            f"S{number}",
            f"La forme {row.form} (lemme {row.lemma}, "
            f"{'même lemme' if row.lemma == fiche.lemma else 'autre lemme de la même racine'}) "
            f"a {row.occurrences} occurrences dans {row.ayas} versets.",
        )
        for number, row in enumerate(chosen, start=1)
    ]


# --- Sources and human notes --------------------------------------------------


def source_statements(connection: sqlite3.Connection) -> list[Statement]:
    """Where the data comes from, as recorded in the database when it was built."""
    meta = dict(connection.execute("SELECT key, value FROM meta"))
    labels = {
        "tanzil-uthmani": "Texte de base",
        "qac-morphology": "Racines, lemmes et clitiques",
        "masaq": "Contrôle des pronoms attachés",
        "quran-morphology-mustafa0x": "Comparaison des racines",
    }
    return [
        Statement(SOURCE, f"{label} : source {source}, empreinte SHA-256 {meta[f'sha256:{source}'][:12]}… (data/SOURCES.md).", (source,))
        for source, label in labels.items()
        if f"sha256:{source}" in meta
    ]


def load_notes(path: Path | None = None) -> list[dict]:
    path = path or NOTES_PATH
    if not path.is_file():
        return []
    with open(path, encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("notes", [])


def add_note(form: str, text: str, author: str, lemma: str = "", path: Path | None = None, today: date | None = None) -> dict:
    """Record a note written by a person about a form. Notes are never produced by the program."""
    path = path or NOTES_PATH
    if not text.strip() or not author.strip():
        raise ValueError("une note a besoin d'un texte et d'un auteur")
    note = {"form": form, "lemma": lemma, "author": author.strip(), "date": (today or date.today()).isoformat(), "text": text.strip()}
    notes = load_notes(path) + [note]
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Notes humaines sur des formes. Écrites par des personnes, jamais par le programme.\n")
        yaml.safe_dump({"notes": notes}, f, allow_unicode=True, sort_keys=False)
    return note


def note_statements(fiche: Fiche, notes: list[dict]) -> list[Statement]:
    own = search_key(fiche.form.removeprefix("racine "))
    return [
        Statement(NOTE, note["text"], (note["author"], str(note["date"])))
        for note in notes
        if search_key(note["form"]) == own and note.get("lemma") in ("", None, fiche.lemma)
    ]


# --- Checking what a model wrote ----------------------------------------------


def check(text: str, cited: list[str], known: dict[str, str]) -> str | None:
    """Why a sentence must be thrown away, or None when it only says what its facts say."""
    if not cited:
        return "ne cite aucun fait"
    unknown = [fact for fact in cited if fact not in known]
    if unknown:
        return f"cite un fait inexistant ({', '.join(unknown)})"
    found = INTERPRETATION.search(text)
    if found:
        return f"mot d'interprétation « {found.group(0)} »"
    basis = " ".join(known[fact] for fact in cited)
    allowed_numbers = {n.replace(",", ".") for n in _NUMBER.findall(basis)}
    for number in _NUMBER.findall(text):
        if number.replace(",", ".") not in allowed_numbers:
            return f"nombre absent des faits cités ({number})"
    allowed_words = set(_ARABIC.findall(basis))
    for word in _ARABIC.findall(text):
        if word not in allowed_words:
            return f"mot arabe absent des faits cités ({word})"
    return None


# --- Summary ------------------------------------------------------------------


def summarise(
    connection: sqlite3.Connection,
    fiche: Fiche,
    config: dict,
    level: str,
    completer: Completer | None = None,
    notes: list[dict] | None = None,
) -> Summary:
    settings = config["assistant"]
    facts = facts_of(fiche, settings["max_companions"])
    candidates = candidates_of(connection, fiche, level, settings["max_suggestions"])
    extras = source_statements(connection) + note_statements(fiche, load_notes() if notes is None else notes)

    plain = [Statement(CALCULE, fact.text, (fact.id,)) for fact in facts]
    plain_suggestions = [Statement(CALCULE, c.text, (c.id,)) for c in candidates[: settings["max_suggestions"]]]
    if completer is None:
        return Summary(plain + extras, plain_suggestions, WITHOUT_MODEL)

    request = {
        "faits": [{"id": f.id, "texte": f.text} for f in facts],
        "candidats": [{"id": c.id, "texte": c.text} for c in candidates],
        "nombre_de_suggestions": settings["max_suggestions"],
    }
    try:
        answer = completer(SYSTEM_PROMPT, json.dumps(request, ensure_ascii=False, indent=1), OUTPUT_SCHEMA)
    except AssistantUnavailable as error:
        return Summary(plain + extras, plain_suggestions, WITHOUT_MODEL, notice=str(error))

    known = {item.id: item.text for item in facts + candidates}
    candidate_ids = {c.id for c in candidates}
    statements, suggestions, rejected = [], [], []
    for sentence in answer.get("summary", []):
        reason = check(sentence["text"], sentence["facts"], known)
        if reason:
            rejected.append((sentence["text"], reason))
        else:
            statements.append(Statement(CALCULE, sentence["text"], tuple(sentence["facts"])))
    for suggestion in answer.get("suggestions", [])[: settings["max_suggestions"]]:
        cited = list(dict.fromkeys([suggestion["candidate"], *suggestion["facts"]]))
        reason = (
            "candidat hors de la liste proposée"
            if suggestion["candidate"] not in candidate_ids
            else check(suggestion["reason"], cited, known)
        )
        if reason:
            rejected.append((suggestion["reason"], reason))
        else:
            text = f"{known[suggestion['candidate']]} {suggestion['reason']}"
            suggestions.append(Statement(CALCULE, text, tuple(cited)))
    if not statements:  # nothing the model wrote survived: the facts speak for themselves
        return Summary(plain + extras, plain_suggestions, WITHOUT_MODEL, rejected, "aucune phrase du modèle n'a passé la vérification")
    return Summary(statements + extras, suggestions or plain_suggestions, settings["model"], rejected)


def anthropic_completer(config: dict) -> Completer:
    """A completer that calls Claude. Needs the `ia` extra and credentials in the environment."""
    settings = config["assistant"]

    def complete(system: str, user: str, schema: dict) -> dict:
        try:
            import anthropic
        except ImportError:
            raise AssistantUnavailable("le paquet `anthropic` n'est pas installé (uv sync --extra ia)") from None
        try:
            response = anthropic.Anthropic().beta.messages.create(
                model=settings["model"],
                max_tokens=settings["max_tokens"],
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",  # a request declined by a safety classifier is re-run on another model
                system=system,
                output_config={"effort": settings["effort"], "format": {"type": "json_schema", "schema": schema}},
                messages=[{"role": "user", "content": user}],
            )
        except anthropic.AuthenticationError:
            raise AssistantUnavailable("identifiants Anthropic absents ou refusés (variable ANTHROPIC_API_KEY)") from None
        except anthropic.RateLimitError:
            raise AssistantUnavailable("limite de débit atteinte ; réessayer plus tard") from None
        except anthropic.APIStatusError as error:
            raise AssistantUnavailable(f"erreur de l'API ({error.status_code}) : {error.message}") from None
        except anthropic.APIConnectionError:
            raise AssistantUnavailable("l'API Anthropic est injoignable") from None
        except anthropic.AnthropicError as error:  # for instance a credentials profile that cannot be read
            raise AssistantUnavailable(f"appel au modèle impossible : {error}") from None
        except TypeError as error:  # the SDK raises this when it finds no credentials at all
            if "authentication" not in str(error):
                raise
            raise AssistantUnavailable(
                "aucun identifiant Anthropic configuré (variable d'environnement ANTHROPIC_API_KEY)"
            ) from None
        if response.stop_reason == "refusal":
            raise AssistantUnavailable("le modèle a décliné la demande")
        if response.stop_reason == "max_tokens":
            raise AssistantUnavailable("réponse du modèle coupée avant la fin")
        text = next((block.text for block in response.content if block.type == "text"), None)
        if text is None:
            raise AssistantUnavailable("réponse du modèle sans texte")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise AssistantUnavailable("réponse du modèle illisible") from None

    return complete


# --- Rendering ----------------------------------------------------------------


def render(fiche: Fiche, summary: Summary) -> str:
    title = fiche.form if fiche.form.startswith("racine ") else f"forme {fiche.form}, lemme {fiche.lemma}"
    lines = [
        f"# Résumé — {title}",
        "",
        " · ".join(f"{key} : {value}" for key, value in fiche.parameters.items()),
        f"Rédaction : {summary.engine}. Chaque ligne dit d'où elle vient.",
    ]
    if summary.notice:
        lines.append(f"Modèle non utilisé : {summary.notice}. Le résumé reprend les faits tels quels.")
    lines += ["", "## Ce que montre la fiche", ""]
    lines += [f"- [{s.kind} · {', '.join(s.basis)}] {s.text}" for s in summary.statements]
    lines += ["", "## Formes à comparer", ""]
    lines += [f"- [{s.kind} · {', '.join(s.basis)}] {s.text}" for s in summary.suggestions] or ["Aucune autre forme pour cette racine."]
    if summary.rejected:
        lines += ["", f"## Phrases du modèle écartées par la vérification ({len(summary.rejected)})", ""]
        lines += [f"- {reason} : « {text} »" for text, reason in summary.rejected]
    return "\n".join(lines) + "\n"


def to_dict(summary: Summary) -> dict:
    as_dict = lambda s: {"kind": s.kind, "text": s.text, "basis": list(s.basis)}  # noqa: E731
    return {
        "engine": summary.engine,
        "notice": summary.notice,
        "statements": [as_dict(s) for s in summary.statements],
        "suggestions": [as_dict(s) for s in summary.suggestions],
        "rejected": [{"text": text, "reason": reason} for text, reason in summary.rejected],
    }
