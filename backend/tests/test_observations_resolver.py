"""Observations resolver — the unpinned, faithful bulk read behind /api/observations
(ADR 0004). Co-locating labelled rows across Conventions is NOT merging: this path
must NEVER raise AmbiguousConvention, never dedupe Millésimes, and carry the
Convention + traceability on every row.
"""

from app.data import resolve_observations


def test_returns_rows_spanning_more_than_one_convention_without_raising(con, relation):
    # DGFiP spans two Concepts (total ≤2017, immobilier ≥2018) across the 2018
    # Rupture. resolve_series would raise AmbiguousConvention here; the bulk path
    # co-locates both, each row self-describing (ADR 0004).
    rows, total = resolve_observations(
        con,
        relation,
        source=["DGFiP"],
        indicateur=["impot_moyen"],
        groupe=["redevables"],
    )
    concepts = {r["concept_patrimoine"] for r in rows}
    assert concepts == {"total", "immobilier"}
    assert total == len([r for r in rows])
    # Every row carries its Convention + traceability (never dropped).
    assert all(r["unite"] == "foyer_fiscal" for r in rows)
    assert all(
        r["source"] == "DGFiP" and r["millesime_source"] and r["date_extraction"] for r in rows
    )


def test_multi_value_filter_selects_the_union_and_omitted_filter_is_unconstrained(con, relation):
    # A comma-list of sources selects the union of both; the omitted indicateur,
    # groupe, concept… filters place no constraint.
    rows, total = resolve_observations(con, relation, source=["WID", "INSEE"])
    sources = {r["source"] for r in rows}
    assert sources == {"WID", "INSEE"}  # union of the two, and only those
    assert total == len(rows)
    # No indicateur filter → more than one indicateur comes back unconstrained.
    assert len({r["indicateur"] for r in rows}) > 1


def test_all_millesimes_of_a_revision_are_returned_labelled_not_deduped(con, relation):
    # The fixture revises WID's 2015 top1 share: 26.0 in WID 2024, 26.5 in WID 2026.
    # Append-only historisation: both Millésimes coexist, each labelled, never
    # collapsed to the latest (unlike resolve_series).
    rows, _ = resolve_observations(
        con,
        relation,
        source=["WID"],
        indicateur=["part_patrimoine"],
        groupe=["top1"],
        annee_min=2015,
        annee_max=2015,
    )
    by_millesime = {r["millesime_source"]: r["valeur"] for r in rows}
    assert by_millesime == {"WID 2024": 26.0, "WID 2026": 26.5}


def test_both_nominal_and_euros_constants_rows_returned_then_narrowed(con, relation):
    # The level indicator carries both a nominal (euros) and a deflated
    # (euros_constants_2021) row. Unnarrowed, both come back, each labelled.
    both, _ = resolve_observations(
        con,
        relation,
        source=["WID"],
        indicateur=["patrimoine_moyen"],
        groupe=["top1"],
    )
    assert {r["unite_valeur"] for r in both} == {"euros", "euros_constants_2021"}
    # euros_constants=False narrows to the nominal row only.
    nominal, _ = resolve_observations(
        con,
        relation,
        source=["WID"],
        indicateur=["patrimoine_moyen"],
        groupe=["top1"],
        euros_constants=False,
    )
    assert {r["unite_valeur"] for r in nominal} == {"euros"}


def test_total_reflects_full_match_while_limit_offset_slice_it(con, relation):
    full, total = resolve_observations(con, relation, source=["WID"])
    assert total == len(full) > 2  # WID has several rows in the fixture

    page, page_total = resolve_observations(con, relation, source=["WID"], limit=2, offset=0)
    assert page_total == total  # total is the full match, independent of the page
    assert len(page) == 2  # but the page is sliced

    rest, _ = resolve_observations(con, relation, source=["WID"], limit=2, offset=2)
    # offset advances past the first page; no overlap on a stable ORDER BY.
    assert [r for r in page] != [r for r in rest]


def test_paging_across_a_tie_group_is_lossless_total_order(con, relation):
    # The ORDER BY must be a TOTAL order. WID's 2021 patrimoine_moyen carries two
    # rows — nominal (euros) and deflated (euros_constants_2021) — that tie on
    # every HIST_KEYS column AND on millesime_source/date_extraction; only
    # euros_constants + unite_valeur distinguish them. Paging with a page boundary
    # STRADDLING that tied pair must drop nothing and duplicate nothing.
    full, total = resolve_observations(con, relation, source=["WID"])

    # Sanity: the tie group really is in the fixture and adjacent under the order.
    tie = [r for r in full if r["indicateur"] == "patrimoine_moyen" and r["annee"] == 2021]
    assert {r["unite_valeur"] for r in tie} == {"euros", "euros_constants_2021"}

    # Walk the whole result one row at a time, so every offset (including the ones
    # landing inside the tie pair) is exercised as a page boundary.
    paged: list[dict] = []
    for off in range(total + 1):
        page, page_total = resolve_observations(con, relation, source=["WID"], limit=1, offset=off)
        assert page_total == total
        paged.extend(page)

    assert len(paged) == total  # no duplicate, no drop
    assert paged == full  # the concatenation of pages equals the full result
