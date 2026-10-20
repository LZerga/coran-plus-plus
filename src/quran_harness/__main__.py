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
    python -m quran_harness comparer <forme 1> <forme 2> [--pause] [--stats] [--detail]  # niveau 5
    python -m quran_harness cadres <racine> [--pause] [--detail]   # القوالب والخانات
    python -m quran_harness etude <racine> [<racine> …] [--pause] [--sans-stats] [--protocole fichier.yaml]
    python -m quran_harness decoupages
    python -m quran_harness verset <sourate:verset>
    python -m quran_harness exemples
    python -m quran_harness fiche <forme>    [--pause strict|souple|verset] [--detail] [--sortie fichier]
    python -m quran_harness web              # interface web sur http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse

import yaml
import sqlite3
import sys

from . import __version__
from .config import default_pause, load_config, pause_choices, with_pause
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
    from .labels import meta_line, t
    from .units import forms_of_root

    connection, meta = _open_database()
    rows = forms_of_root(connection, args.racine)
    print(f"{t('root')} : {args.racine}")
    print(meta_line(meta, t("form_rule")))
    if not rows:
        print(t("no_root_form"))
        return 1
    print(f"\n{t('occurrences'):>12} {t('ayas'):>6}  {t('form')}")
    for row in rows:
        print(f"{row.occurrences:>12} {row.ayas:>6}  {row.form}")
    print(f"\n{t('total')} : {sum(r.occurrences for r in rows)} ؛ {t('forms')} : {len(rows)}")
    return 0


def _identite(args: argparse.Namespace) -> int:
    from . import root_identity
    from .labels import t

    connection, meta = _open_database()
    found = root_identity.identity(connection, args.racine)
    if found is None:
        print(t("no_root"))
        return 1
    _write(root_identity.render(found, meta), args.sortie)
    return 0


def _paire(args: argparse.Namespace) -> int:
    from . import pairs
    from .labels import t

    connection, meta = _open_database()
    a, b = (pairs.cells_of_span(connection, *pairs.parse_span(span)) for span in (args.a, args.b))
    indexes = [pairs.pivot_index(cells, args.pivot) for cells in (a, b)]
    for cells, index in zip((a, b), indexes):
        if index is None:
            raise SystemExit(t("not_in_span", form=args.pivot, text=" ".join(c.text for c in cells)))
    signature = pairs.compare(a, indexes[0], b, indexes[1], pairs.PairSettings.from_config(load_config()))
    _write(pairs.render_pair(a, b, signature, args.a, args.b, args.pivot, meta), args.sortie)
    return 0


def _familles(args: argparse.Namespace) -> int:
    from . import families, matrix, pairs
    from .labels import t
    from .segmentation import selected_scheme
    from .units import FormSettings

    connection, meta = _open_database()
    config = with_pause(load_config(), args.pause)
    candidates = families.forms_for(connection, args.forme, FormSettings.from_config(config))
    if not candidates:
        print(t("no_occurrence"))
        return 1
    form = next(iter(candidates))
    if len(candidates) > 1:
        others = "، ".join(f"{f} ({n})" for f, n in list(candidates.items())[1:])
        print(t("retained", typed=args.forme, form=form, n=candidates[form], others=others) + "\n")
    settings = families.FamilySettings.from_config(config)
    analysis = families.analyse(connection, form, selected_scheme(config), pairs.PairSettings.from_config(config), settings)
    matrices = matrix.build_all(analysis, config["matrix"]["relative_min"])
    _write(families.render(analysis, meta, settings, matrices), args.sortie)
    return 0


def _fiche_new(args: argparse.Namespace) -> int:
    from . import sheet
    from .labels import t
    from .segmentation import selected_scheme
    from .units import FormSettings

    from .families import forms_for

    connection, meta = _open_database()
    config = with_pause(load_config(), args.pause)
    candidates = forms_for(connection, args.forme, FormSettings.from_config(config))
    if not candidates:
        print(t("no_occurrence"))
        return 1
    form = next(iter(candidates))
    if len(candidates) > 1:
        others = "، ".join(f"{f} ({n})" for f, n in list(candidates.items())[1:])
        print(t("retained", typed=args.forme, form=form, n=candidates[form], others=others) + "\n")
    found = sheet.build(connection, form, selected_scheme(config), config, with_stats=args.stats)
    _write(sheet.render(found, meta, config, detail=args.detail), args.sortie)
    return 0


def _comparer(args: argparse.Namespace) -> int:
    from . import comparison
    from .families import forms_for
    from .labels import t
    from .segmentation import selected_scheme
    from .units import FormSettings

    connection, meta = _open_database()
    config = with_pause(load_config(), args.pause)
    chosen = []
    for typed in (args.forme1, args.forme2):
        candidates = forms_for(connection, typed, FormSettings.from_config(config))
        if not candidates:
            print(t("no_occurrence") + f" ({typed})")
            return 1
        form = next(iter(candidates))
        if len(candidates) > 1:
            others = "، ".join(f"{f} ({n})" for f, n in list(candidates.items())[1:])
            print(t("retained", typed=typed, form=form, n=candidates[form], others=others))
        chosen.append(form)
    try:
        found = comparison.compare_forms(connection, *chosen, selected_scheme(config), config, with_stats=args.stats)
    except ValueError:
        print(t("not_same_root"))
        return 1
    _write(comparison.render(found, meta, detail=args.detail), args.sortie)
    return 0


def _etude(args: argparse.Namespace) -> int:
    from pathlib import Path

    from . import study
    from .labels import t
    from .sources import PROJECT_ROOT

    connection, _ = _open_database()
    protocol = {}
    if args.protocole:
        with open(args.protocole, encoding="utf-8") as f:
            protocol = yaml.safe_load(f) or {}
    roots = args.racines or protocol.get("racines", [])
    if not roots:
        print(t("empty_query"))
        return 1
    pause = args.pause or protocol.get("pause")
    with_stats = not args.sans_stats and protocol.get("statistiques", True)
    out = Path(args.sortie or protocol.get("sortie") or PROJECT_ROOT / "sorties")
    status = 0
    for root in roots:
        config = with_pause(load_config(), pause)
        try:
            study.run(connection, root, config, out, with_stats=with_stats)
        except ValueError:
            print(f"{t('no_root')} ({root})")
            status = 1
    return status


def _cadres(args: argparse.Namespace) -> int:
    from . import frames
    from .index import search_key
    from .labels import t
    from .segmentation import selected_scheme
    from . import alt_roots

    connection, meta = _open_database()
    config = with_pause(load_config(), args.pause)
    root = alt_roots.fold_hamza(search_key(args.racine))
    found = frames.build(connection, root, selected_scheme(config), config["statistics"]["alpha"])
    if not found.occurrences:
        print(t("no_root"))
        return 1
    _write(frames.render(found, meta, detail=args.detail), args.sortie)
    return 0


def _forme(args: argparse.Namespace) -> int:
    from .labels import meta_line, t
    from .units import FormSettings, by_form, occurrences_of_form

    connection, meta = _open_database()
    groups = by_form(occurrences_of_form(connection, args.forme, FormSettings.from_config(load_config())))
    print(f"{t('form')} : {args.forme}")
    print(meta_line(meta, t("form_rule")))
    if not groups:
        print(t("no_occurrence"))
        return 1
    if len(groups) > 1:
        print("\n" + t("covers", n=len(groups)))
    for form, group in groups.items():
        ayas = {occurrence.aya_ref for occurrence in group}
        roots = sorted({occurrence.roots for occurrence in group if occurrence.roots})
        print(f"\n{form} ؛ {t('root')} : {'، '.join(roots) or '—'} ؛ {t('occurrences')} : {len(group)} ؛ {t('ayas')} : {len(ayas)}")
        for occurrence in group:
            print(f"  {occurrence.word_ref:<12} {occurrence.text}")
    return 0


def _web(args: argparse.Namespace) -> int:
    import uvicorn

    from .ingest import DB_PATH
    from .web import create_app

    print(f"Interface : http://{args.host}:{args.port}   (Ctrl+C pour arrêter)")
    uvicorn.run(create_app(DB_PATH), host=args.host, port=args.port, log_level="warning")
    return 0


def _write(text: str, path: str | None) -> None:
    from .labels import t

    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print(t("written", path=path))
    else:
        print(text)


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
    pauses, pause_default = pause_choices(config), default_pause(config)
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
    p_familles.add_argument("--pause", choices=pauses, default=pause_default, help="découpage en segments")
    p_familles.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")
    p_familles.set_defaults(func=_familles)

    p_web = sub.add_parser("web", help="lancer l'interface web")
    p_web.add_argument("--host", default="127.0.0.1")
    p_web.add_argument("--port", type=int, default=8000)
    p_web.set_defaults(func=_web)

    p_fiche = sub.add_parser("fiche", help="بطاقة الصيغة : الهوية، الارتباطات، المقارنات، أنواع الاستعمال، المصفوفات")
    p_fiche.add_argument("forme")
    p_fiche.add_argument("--pause", choices=pauses, default=pause_default, help="découpage en segments")
    p_fiche.add_argument("--stats", action="store_true", help="contrôle aléatoire (environ 30 s)")
    p_fiche.add_argument("--detail", action="store_true", help="tout afficher : références, paires, colonnes masquées")
    p_fiche.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")
    p_fiche.set_defaults(func=_fiche_new)

    p_comparer = sub.add_parser("comparer", help="مقارنة صيغتين من نفس الجذر (المستوى 5)")
    p_comparer.add_argument("forme1")
    p_comparer.add_argument("forme2")
    p_comparer.add_argument("--pause", choices=pauses, default=pause_default, help="découpage en segments")
    p_comparer.add_argument("--stats", action="store_true", help="contrôle aléatoire (environ 30 s)")
    p_comparer.add_argument("--detail", action="store_true", help="tout afficher")
    p_comparer.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")
    p_comparer.set_defaults(func=_comparer)

    p_cadres = sub.add_parser("cadres", help="القوالب والخانات : ما يأتي قبل صيغ الجذر وبعدها مباشرة")
    p_cadres.add_argument("racine")
    p_cadres.add_argument("--pause", choices=pauses, default=pause_default, help="découpage en segments")
    p_cadres.add_argument("--detail", action="store_true", help="tout afficher")
    p_cadres.add_argument("--sortie", help="fichier où écrire le résultat (UTF-8)")
    p_cadres.set_defaults(func=_cadres)

    p_etude = sub.add_parser("etude", help="دراسة كاملة لجذر أو أكثر : كل المراحل، ثم تقرير في مجلد")
    p_etude.add_argument("racines", nargs="*", help="un ou plusieurs racines (une étude par racine)")
    p_etude.add_argument("--pause", choices=pauses, default=None, help="découpage en segments")
    p_etude.add_argument("--sans-stats", action="store_true", help="sans contrôle aléatoire (plus rapide)")
    p_etude.add_argument("--protocole", help="fichier YAML : racines, pause, statistiques, sortie")
    p_etude.add_argument("--sortie", help="dossier des résultats (par défaut : sorties/)")
    p_etude.set_defaults(func=_etude)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
