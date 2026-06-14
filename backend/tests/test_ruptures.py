"""Ruptures lookup — a pure function over the backend's known-ruptures table."""

from app.data import ruptures_in


def test_dgfip_rupture_surfaces_when_2018_in_range():
    ruptures = ruptures_in("DGFiP", 2015, 2020)
    assert [(r.annee, r.label) for r in ruptures] == [(2018, "ISF (total) → IFI (immobilier)")]


def test_no_rupture_when_2018_outside_range():
    assert ruptures_in("DGFiP", 2000, 2017) == []


def test_sources_without_a_break_have_no_ruptures():
    assert ruptures_in("WID", 2000, 2030) == []
    assert ruptures_in("INSEE", 2000, 2030) == []
