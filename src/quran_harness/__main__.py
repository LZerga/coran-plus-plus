"""Command line of the harness.

    python -m quran_harness sources verify|fetch
    python -m quran_harness counts
    python -m quran_harness build            # ingest, index, units, segment, then riwayat
    python -m quran_harness lectures
    python -m quran_harness variantes <sourate:verset>
    python -m quran_harness racine <racine>
    python -m quran_harness forme <forme>    # avec ou sans voyelles
    python -m quran_harness identite <racine>  # niveau 0 : هوية الجذر
    python -m quran_harness paire <passage A> <passage B> --pivot <forme>   # niveau 1
    python -m quran_harness familles <forme> [--pause strict|souple|verset]  # niveaux 1 et 2
    python -m quran_harness decoupages
    python -m quran_harness verset <sourate:verset>
    python -m quran_harness exemples
    python -m quran_harness fiche <forme>    [--niveau ...] [--pause strict|souple|verset] [--sortie fichier]
    python -m quran_harness comparer <passage A> <passage B>   # passage = sourate:verset:début-fin
    python -m quran_harness comparer-formes <forme 1> <forme 2>
    python -m quran_harness web              # interface web sur http://127.0.0.1:8000
    python -m quran_harness resume <forme>   [--ia] [--racine] [--sans-stats]
    python -m quran_harness note <forme> <texte> --auteur <nom>
"""

from __future__ import annotations

import argparse
import sqlite3
import sys

from . import __version__
from .config import NIVEAUX, default_choices, load_config, pause_choices, with_choices
from .raw_counts import COUNTERS
from .sources import check, fetch, load_manifest


def _sources(args: argparse.Namespace) -> int:
    failures = 0
    for source in load_manifest():
        if args.action == "fetch":
            status = fetch(source, accept_terms=args.accept_terms)
        else:
            status = check(source)
        failures += status != "ok"
        print(f"{status:<20} {source.id}")
    return 1 if failures else 0


def _counts(args: argparse.Namespace) -> int:
    print(f"{'source':<28} {'sourates':>8} {'versets':>8} {'mots':>8}")
    for source in load_manifest():
        counter = COUNTERS.get(source.id)
        if counter is None or not source.path.is_file():
            continue
        c = counter(source.path)
        words = "-" if c.words is None else c.words
        print(f"{source.id:<28} {c.suras:>8} {c.ayas:>8} {words:>8}")
    return 0


def _print_report(report: dict[str, int]) -> None:
    for label, value in report.items():
        print(f"{value:>8}  {label}")


def _build(args: argparse.Namespace) -> int:
    from . import index, ingest, readings, segmentation, units

    if args.command in ("build", "ingest"):
        _print_report(ingest.build())
    if args.command in ("build", "index"):
        _print_report(index.build())
    if args.command in ("build", "units"):
        _print_report(units.build())
    if args.command in ("build", "segment"):
        _print_report(segmentation.build())
    if args.command in ("build", "riwayat"):
        _print_report(readings.build())
    print(f"Base : {ingest.DB_PATH}")
    return 0


def _lectures(args: argparse.Namespace) -> int:
    from . import readings

    connection, meta = _open_database()
    print(f"Riwāyāt comparées au texte de base | lecture de base : {meta['reading']} | code {meta['code_version']}")
    print("Seuls les écarts de lettres et de mots sont relevés (pas les voyelles ni la prononciation).")
    kinds = [readings.LETTRES, readings.MOTS, readings.EN_PLUS, readings.EN_MOINS, readings.VERSET_ABSENT]
    print(f"\n{'riwāya':<10} {'rôle':<12} {'versets':>8} {'mots':>8} " + " ".join(f"{kind:>13}" for kind in kinds))
    for riwaya, role, ayas, words in connection.execute("SELECT id, role, ayas, words FROM riwayat ORDER BY rowid"):
        counts = dict(connection.execute("SELECT kind, count(*) FROM variants WHERE riwaya = ? GROUP BY kind", (riwaya,)))
        role = "étalonnage" if role == "calibration" else "étudiée"
        print(f"{riwaya:<10} {role:<12} {ayas:>8} {words:>8} " + " ".join(f"{counts.get(kind, 0):>13}" for kind in kinds))
    return 0


def _variantes(args: argparse.Namespace) -> int:
    connection, meta = _open_database()
    sura, aya = (int(n) for n in args.verset.split(":"))
    span = connection.execute("SELECT min(id), max(id) FROM words WHERE sura = ? AND aya = ?", (sura, aya)).fetchone()
    if span[0] is None:
        print(f"Verset {args.verset} introuvable.")
        return 1
    rows = connection.execute(
        """SELECT v.riwaya, v.kind, coalesce(w.ref, '—'), v.riwaya_aya, v.base_text, v.variant_text
           FROM variants v LEFT JOIN words w ON w.id = v.first_word_id
           WHERE v.first_word_id BETWEEN ? AND ? ORDER BY v.first_word_id, v.id""",
        span,
    ).fetchall()
    print(f"Écarts des riwāyāt sur le verset {sura}:{aya} (numérotation Hafs) | code {meta['code_version']}")
    if not rows:
        print("Aucun écart de lettres ni de mots.")
    for riwaya, kind, ref, riwaya_aya, base_text, variant_text in rows:
        print(f"  {riwaya:<8} {kind:<13} {ref:<10} (verset {riwaya_aya} chez {riwaya})  {base_text or '—'}  →  {variant_text or '—'}")
    return 0


def _decoupages(args: argparse.Namespace) -> int:
    from .segmentation import scheme_names, selected_scheme, summary

    connection, meta = _open_database()
    chosen = selected_scheme(load_config())
    print(f"Découpages en segments | lecture : {meta['reading']} | code {meta['code_version']}")
    print("Basmala de tête de sourate non comptée.")
    for scheme in scheme_names(connection):
        params = connection.execute("SELECT params FROM segmentations WHERE name = ?", (scheme,)).fetchone()[0]
        print(f"\n{scheme}{'  (retenu par config.yaml)' if scheme == chosen else ''}  {params}")
        _print_report(summary(connection, scheme))
    return 0


def _verset(args: argparse.Namespace) -> int:
    from .segmentation import scheme_names, segments_of_aya

    connection, meta = _open_database()
    sura, aya = (int(n) for n in args.verset.split(":"))
    words = dict(
        connection.execute("SELECT pos, text_raw FROM words WHERE sura = ? AND aya = ? ORDER BY pos", (sura, aya))
    )
    if not words:
        print(f"Verset {args.verset} introuvable.")
        return 1
    print(f"Verset {sura}:{aya} | lecture : {meta['reading']} | code {meta['code_version']}")
    for scheme in scheme_names(connection):
        segments = segments_of_aya(connection, scheme, sura, aya)
        print(f"\n{scheme} : {len(segments)} segment(s)")
        for segment in segments:
            text = " ".join(words[pos] for pos in range(segment.start_pos, segment.end_pos + 1))
            print(f"  {segment.ref:<14} {text} {segment.closing_mark}".rstrip())
    return 0


def _exemples(args: argparse.Namespace) -> int:
    from .examples import load_examples, locate

    connection, meta = _open_database()
    found, missing = locate(connection, load_examples())
    print(f"Phrases du SPEC §2 dans le texte | lecture : {meta['reading']} | code {meta['code_version']}")
    for location in found:
        print(f"\n{location.example.id}  {location.example.text}")
        print(f"    trouvée en {location.ref} ({location.end_pos - location.start_pos + 1} mots)")
        for scheme, (relation, refs) in location.fits.items():
            print(f"    {scheme:<12} {relation} : {', '.join(refs)}")
    for example, reason in missing:
        print(f"\n{example.id}  {example.text}\n    {reason}")
    return 0


FORM_LABEL = "mot écrit, واو de conjonction à part, sans voyelle finale"


def _open_database() -> tuple[sqlite3.Connection, dict[str, str]]:
    from .ingest import DB_PATH

    if not DB_PATH.is_file():
        raise SystemExit("Base absente : lancer d'abord `python -m quran_harness build`.")
    connection = sqlite3.connect(DB_PATH)
    return connection, dict(connection.execute("SELECT key, value FROM meta"))


def _racine(args: argparse.Namespace) -> int:
    from .units import forms_of_root

    connection, meta = _open_database()
    rows = forms_of_root(connection, args.racine)
    print(f"Racine {args.racine}")
    print(f"lecture : {meta['reading']} | forme : {FORM_LABEL} | code {meta['code_version']}")
    if not rows:
        print("Aucune forme trouvée pour cette racine.")
        return 1
    print(f"{'occurrences':>11} {'versets':>8}  forme")
    for row in rows:
        print(f"{row.occurrences:>11} {row.ayas:>8}  {row.form}")
    print(f"{sum(r.occurrences for r in rows):>11}           total, {len(rows)} formes")
    return 0


def _identite(args: argparse.Namespace) -> int:
    from . import root_identity

    connection, meta = _open_database()
    found = root_identity.identity(connection, args.racine)
    if found is None:
        print(f"Aucune occurrence pour la racine {args.racine}.")
        return 1
    _write(root_identity.render(found, meta), args.sortie)
    return 0


def _pivot(cells, typed: str) -> int:
    from .index import search_key
    from .normalize import Level, normalize

    key = search_key(typed)
    found = next((i for i, cell in enumerate(cells) if normalize(cell.form, Level.NO_VOWELS).replace("ٱ", "ا") == key), None)
    if found is None:
        raise SystemExit(f"La forme {typed} n'est pas dans le passage {' '.join(c.text for c in cells)}.")
    return found


def _paire(args: argparse.Namespace) -> int:
    from . import pairs
    from .elements import parse_span

    connection, meta = _open_database()
    a, b = (pairs.cells_of_span(connection, *parse_span(span)) for span in (args.a, args.b))
    signature = pairs.compare(a, _pivot(a, args.pivot), b, _pivot(b, args.pivot), pairs.PairSettings.from_config(load_config()))
    lines = [
        f"Paire | lecture : {meta['reading']} | forme de référence : {args.pivot} | code {meta['code_version']}",
        f"A  {args.a}  {' '.join(c.text for c in a)}",
        f"B  {args.b}  {' '.join(c.text for c in b)}",
        *(f"{label:<12} {value}" for label, value in pairs.describe(a, b, signature).items()),
    ]
    _write("\n".join(lines), args.sortie)
    return 0


def _familles(args: argparse.Namespace) -> int:
    from . import families, pairs
    from .segmentation import selected_scheme
    from .units import FormSettings

    connection, meta = _open_database()
    config = with_choices(load_config(), None, args.pause)
    candidates = families.forms_for(connection, args.forme, FormSettings.from_config(config))
    if not candidates:
        print(f"Aucune occurrence pour la forme {args.forme}.")
        return 1
    form = next(iter(candidates))
    if len(candidates) > 1:
        others = ", ".join(f"{f} ({n})" for f, n in list(candidates.items())[1:])
        print(f"{args.forme} recouvre plusieurs formes ; retenue : {form} ({candidates[form]}) ; "
              f"les autres ({others}) se demandent avec leurs voyelles.\n")  # fmt: skip
    settings = families.FamilySettings.from_config(config)
    analysis = families.analyse(connection, form, selected_scheme(config), pairs.PairSettings.from_config(config), settings)
    _write(families.render(analysis, meta, settings), args.sortie)
    return 0


def _forme(args: argparse.Namespace) -> int:
    from .units import FormSettings, by_form, occurrences_of_form

    connection, meta = _open_database()
    groups = by_form(occurrences_of_form(connection, args.forme, FormSettings.from_config(load_config())))
    print(f"Forme {args.forme}")
    print(f"lecture : {meta['reading']} | forme : {FORM_LABEL} | code {meta['code_version']}")
    if not groups:
        print("Aucune occurrence.")
        return 1
    if len(groups) > 1:
        print(f"\nLa saisie recouvre {len(groups)} formes, gardées séparées :")
    for form, group in groups.items():
        ayas = {occurrence.aya_ref for occurrence in group}
        roots = sorted({occurrence.roots for occurrence in group if occurrence.roots})
        print(f"\n{form} | racine {', '.join(roots) or '—'} : {len(group)} occurrences dans {len(ayas)} versets")
        for occurrence in group:
            print(f"  {occurrence.word_ref:<12} {occurrence.text}")
    return 0


def _method_config(args: argparse.Namespace) -> dict:
    """config.yaml, with the choices made on the command line."""
    return with_choices(load_config(), args.niveau, getattr(args, "pause", None))


def _web(args: argparse.Namespace) -> int:
    import uvicorn

    from .ingest import DB_PATH
    from .web import create_app

    print(f"Interface : http://{args.host}:{args.port}   (Ctrl+C pour arrêter)")
    uvicorn.run(create_app(DB_PATH), host=args.host, port=args.port, log_level="warning")
    return 0


def _write(text: str, path: str | None) -> None:
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Écrit : {path}")
    else:
        print(text)


def _fiche(args: argparse.Namespace) -> int:
    from . import fiche

    connection, _ = _open_database()
    fiches = fiche.build(connection, args.forme, _method_config(args), with_stats=not args.sans_stats)
    if not fiches:
        print(f"Aucune occurrence portant une racine pour la forme {args.forme} au niveau {args.niveau}.")
        return 1
    _write("\n---\n\n".join(fiche.render(f, args.paires) for f in fiches), args.sortie)
    return 0


def _resume(args: argparse.Namespace) -> int:
    from . import assistant, fiche
    from .config import form_level

    connection, _ = _open_database()
    config = _method_config(args)
    if args.racine:
        fiches = fiche.build_root(connection, args.forme, config, with_stats=not args.sans_stats)
    else:
        fiches = fiche.build(connection, args.forme, config, with_stats=not args.sans_stats)
    if not fiches:
        print(f"Aucune occurrence portant une racine pour {args.forme} au niveau {args.niveau}.")
        return 1
    completer = assistant.anthropic_completer(config) if args.ia else None
    texts = [
        assistant.render(f, assistant.summarise(connection, f, config, form_level(config), completer)) for f in fiches
    ]
    _write("\n---\n\n".join(texts), args.sortie)
    return 0


def _note(args: argparse.Namespace) -> int:
    from . import assistant

    note = assistant.add_note(args.forme, args.texte, args.auteur, args.lemme)
    print(f"Note enregistrée dans {assistant.NOTES_PATH} : {note['author']}, {note['date']}.")
    return 0


def _comparer_formes(args: argparse.Namespace) -> int:
    from . import fiche

    connection, _ = _open_database()
    config = _method_config(args)
    chosen = []
    for form in (args.forme1, args.forme2):
        fiches = fiche.build(connection, form, config, with_stats=False)
        if not fiches:
            print(f"Aucune occurrence portant une racine pour la forme {form} au niveau {args.niveau}.")
            return 1
        best = max(fiches, key=lambda f: len(f.occurrences))
        if len(fiches) > 1:
            others = ", ".join(f.lemma for f in fiches if f is not best)
            print(f"{form} : plusieurs lemmes ; retenu {best.lemma}, laissé de côté {others}.")
        chosen.append(best)
    _write(fiche.render_companion_comparison(*chosen), args.sortie)
    return 0


def _comparer(args: argparse.Namespace) -> int:
    from . import compare, fiche
    from .elements import ElementLoader, parse_span

    connection, meta = _open_database()
    config = _method_config(args)
    loader = ElementLoader(connection, config)
    a, b = (loader.span(*parse_span(text)) for text in (args.a, args.b))
    parts = fiche.describe(a, b, compare.compare(a, b, compare.Settings.from_config(config)))
    lines = [
        f"Comparaison | lecture : {meta['reading']} | forme : {args.niveau} | code {meta['code_version']}",
        f"A  {args.a}  {' '.join(e.text for e in a)}",
        f"B  {args.b}  {' '.join(e.text for e in b)}",
        *(f"{label:<28} {value}" for label, value in parts.items()),
    ]
    _write("\n".join(lines), args.sortie)
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(prog="quran_harness")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_sources = sub.add_parser("sources", help="vérifier ou télécharger les fichiers bruts")
    p_sources.add_argument("action", choices=["verify", "fetch"])
    p_sources.add_argument(
        "--accept-terms",
        action="store_true",
        help="accepter les conditions d'utilisation des sources qui l'exigent (Tanzil)",
    )
    p_sources.set_defaults(func=_sources)

    p_counts = sub.add_parser("counts", help="compter sourates, versets et mots par source")
    p_counts.set_defaults(func=_counts)

    for name, text in [
        ("build", "reconstruire toute la base depuis les fichiers bruts"),
        ("ingest", "étape 2 seule : texte et annotation"),
        ("index", "étape 3 seule : index des racines et des formes"),
        ("units", "étapes 2 et 3 : cases (واو de conjonction à part) et formes"),
        ("segment", "étape 4 seule : découpage en segments"),
        ("riwayat", "étape 7 seule : écarts des autres riwāyāt"),
    ]:
        sub.add_parser(name, help=text).set_defaults(func=_build)

    sub.add_parser("lectures", help="riwāyāt comparées et nombre d'écarts").set_defaults(func=_lectures)
    p_variantes = sub.add_parser("variantes", help="écarts des riwāyāt sur un verset")
    p_variantes.add_argument("verset", help="sourate:verset dans la numérotation Hafs, par exemple 2:259")
    p_variantes.set_defaults(func=_variantes)

    sub.add_parser("decoupages", help="taille des segments pour chaque découpage").set_defaults(func=_decoupages)
    sub.add_parser("exemples", help="place des phrases du SPEC dans les segments").set_defaults(func=_exemples)
    p_verset = sub.add_parser("verset", help="segments d'un verset, pour chaque découpage")
    p_verset.add_argument("verset", help="sourate:verset, par exemple 34:39")
    p_verset.set_defaults(func=_verset)

    config = load_config()
    default_niveau, default_pause = default_choices(config)
    pauses = pause_choices(config)
    for name, func, text in [
        ("racine", _racine, "formes attestées d'une racine"),
        ("forme", _forme, "occurrences d'une forme ; sans voyelles, toutes les formes qu'elle recouvre"),
    ]:
        p = sub.add_parser(name, help=text)
        p.add_argument(name)
        p.set_defaults(func=func)

    p_identite = sub.add_parser("identite", help="niveau 0 : formes de la racine employées dans le Coran, par catégorie")
    p_identite.add_argument("racine")
    p_identite.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")
    p_identite.set_defaults(func=_identite)

    p_paire = sub.add_parser("paire", help="niveau 1 : comparer deux passages autour d'une forme de référence")
    p_paire.add_argument("a", help="sourate:verset:début-fin (positions des mots), par exemple 34:36:1-8")
    p_paire.add_argument("b")
    p_paire.add_argument("--pivot", required=True, help="la forme de référence, présente dans les deux passages")
    p_paire.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")
    p_paire.set_defaults(func=_paire)

    p_familles = sub.add_parser("familles", help="niveaux 1 et 2 : paires de segments d'une forme et familles")
    p_familles.add_argument("forme")
    p_familles.add_argument("--pause", choices=pauses, default=default_pause, help="découpage en segments")
    p_familles.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")
    p_familles.set_defaults(func=_familles)

    p_web = sub.add_parser("web", help="lancer l'interface web")
    p_web.add_argument("--host", default="127.0.0.1")
    p_web.add_argument("--port", type=int, default=8000)
    p_web.set_defaults(func=_web)

    def method_options(p: argparse.ArgumentParser) -> None:
        p.add_argument("--niveau", choices=list(NIVEAUX), default=default_niveau, help="ce qu'on appelle « la même forme »")
        p.add_argument("--lecture", choices=["hafs"], default="hafs")
        p.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")

    p_fiche = sub.add_parser("fiche", help="carte d'identité, compagnons et comparaisons d'une forme")
    p_fiche.add_argument("forme")
    p_fiche.add_argument("--pause", choices=pauses, default=default_pause, help="découpage en segments")
    p_fiche.add_argument("--paires", type=int, default=100, help="nombre de comparaisons affichées")
    p_fiche.add_argument("--sans-stats", action="store_true", help="ne pas lancer le contrôle aléatoire")
    method_options(p_fiche)
    p_fiche.set_defaults(func=_fiche)

    p_resume = sub.add_parser("resume", help="résumé d'une fiche en langage simple, et formes à comparer")
    p_resume.add_argument("forme")
    p_resume.add_argument("--racine", action="store_true", help="la demande est une racine, pas une forme")
    p_resume.add_argument("--ia", action="store_true", help="faire reformuler le résumé par un modèle (envoie les faits à l'API Anthropic)")
    p_resume.add_argument("--pause", choices=pauses, default=default_pause, help="découpage en segments")
    p_resume.add_argument("--sans-stats", action="store_true", help="ne pas lancer le contrôle aléatoire")
    method_options(p_resume)
    p_resume.set_defaults(func=_resume)

    p_note = sub.add_parser("note", help="enregistrer une note humaine sur une forme")
    p_note.add_argument("forme")
    p_note.add_argument("texte")
    p_note.add_argument("--auteur", required=True)
    p_note.add_argument("--lemme", default="", help="limiter la note à un lemme, quand deux mots s'écrivent pareil")
    p_note.set_defaults(func=_note)

    p_formes = sub.add_parser("comparer-formes", help="compagnons communs à deux formes")
    p_formes.add_argument("forme1")
    p_formes.add_argument("forme2")
    p_formes.add_argument("--pause", choices=pauses, default=default_pause, help="découpage en segments")
    method_options(p_formes)
    p_formes.set_defaults(func=_comparer_formes)

    p_comparer = sub.add_parser("comparer", help="comparer deux passages donnés par leurs références")
    p_comparer.add_argument("a", help="sourate:verset:début-fin, par exemple 34:36:1-8")
    p_comparer.add_argument("b")
    method_options(p_comparer)
    p_comparer.set_defaults(func=_comparer)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
