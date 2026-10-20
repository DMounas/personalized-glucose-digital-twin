"""Unit tests for DashboardDataLoader.

Verifies that the dashboard data loader extracts strictly canonical,
validated metrics without exposing raw participant data or leaking paths.
"""

from __future__ import annotations

import pytest

from dtwin.dashboard_data import (
    RUNG_METADATA,
    WINDOW_METADATA,
    DashboardDataLoader,
    GlobalRungMetric,
    PersonalizationWindowMetric,
)


@pytest.fixture
def loader() -> DashboardDataLoader:
    """Fixture providing initialized data loader."""
    return DashboardDataLoader()


def test_loader_global_ladder_structure(loader: DashboardDataLoader) -> None:
    """Verify global ladder loads all 8 rungs for +30m and +60m."""
    for h in ["h30", "h60"]:
        ladder = loader.get_global_ladder(h)
        assert len(ladder) == len(RUNG_METADATA) == 8
        for item in ladder:
            assert isinstance(item, GlobalRungMetric)
            assert item.total_participants == 45
            assert item.mean_rmse > 0
            assert item.ci_95_rmse[0] < item.mean_rmse < item.ci_95_rmse[1]
            assert 0.0 <= item.fraction_improved <= 1.0


def test_loader_global_ladder_canonical_values(loader: DashboardDataLoader) -> None:
    """Verify ladder values match canonical numbers."""
    ladder_30 = {m.rung_label: m for m in loader.get_global_ladder("h30")}
    assert ladder_30["Rung 0"].mean_rmse == pytest.approx(21.554, abs=0.01)
    assert ladder_30["Rung 2"].mean_rmse == pytest.approx(19.866, abs=0.01)
    assert ladder_30["Rung 5"].mean_rmse == pytest.approx(18.853, abs=0.01)
    assert ladder_30["Rung 6"].mean_rmse == pytest.approx(19.146, abs=0.01)
    assert ladder_30["Rung 5"].mean_skill_pct == pytest.approx(11.82, abs=0.05)

    ladder_60 = {m.rung_label: m for m in loader.get_global_ladder("h60")}
    assert ladder_60["Rung 0"].mean_rmse == pytest.approx(29.321, abs=0.01)
    assert ladder_60["Rung 2"].mean_rmse == pytest.approx(26.966, abs=0.01)
    assert ladder_60["Rung 5"].mean_rmse == pytest.approx(25.452, abs=0.01)
    assert ladder_60["Rung 6"].mean_rmse == pytest.approx(25.642, abs=0.01)
    assert ladder_60["Rung 5"].mean_skill_pct == pytest.approx(11.85, abs=0.05)


def test_loader_personalization_metrics(loader: DashboardDataLoader) -> None:
    """Verify personalization window loading and statistical significance classification."""
    # +30m: ALL windows MUST NOT be statistically significant (CIs bracket zero)
    for w in WINDOW_METADATA:
        m = loader.get_personalization_metric("h30", str(w["key"]))
        assert isinstance(m, PersonalizationWindowMetric)
        assert not m.is_statistically_significant, f"h30 {w['key']} should not be significant"
        assert m.ci_95_delta_rmse[0] < 0 < m.ci_95_delta_rmse[1]

    # +60m: 2d must not be significant; 4d and 6d must be statistically significant
    m_2d_60 = loader.get_personalization_metric("h60", "window_2d")
    assert not m_2d_60.is_statistically_significant
    assert m_2d_60.ci_95_delta_rmse[0] < 0 < m_2d_60.ci_95_delta_rmse[1]

    m_4d_60 = loader.get_personalization_metric("h60", "window_4d")
    assert m_4d_60.is_statistically_significant
    assert m_4d_60.mean_delta_rmse == pytest.approx(-1.146, abs=0.01)
    assert m_4d_60.ci_95_delta_rmse[1] < 0.0

    m_6d_60 = loader.get_personalization_metric("h60", "window_6d")
    assert m_6d_60.is_statistically_significant
    assert m_6d_60.mean_delta_rmse == pytest.approx(-1.811, abs=0.01)
    assert m_6d_60.ci_95_delta_rmse[1] < 0.0
    assert m_6d_60.n_improved == 40


def test_loader_trajectory_length(loader: DashboardDataLoader) -> None:
    """Verify trajectory returns exactly 3 window metrics (2d, 4d, 6d)."""
    traj = loader.get_personalization_trajectory("h60")
    assert len(traj) == 3
    assert [m.window_key for m in traj] == ["window_2d", "window_4d", "window_6d"]


def test_loader_missing_file_raises() -> None:
    """Verify loader raises FileNotFoundError when given non-existent paths."""
    bad_loader = DashboardDataLoader(stage2_path="/nonexistent/path/stage2.json")
    with pytest.raises(FileNotFoundError):
        bad_loader.get_global_ladder("h30")
