"""Smoke and integration tests for the Streamlit research dashboard app.py.

Uses Streamlit's official AppTest framework to verify:
- Clean startup without exceptions.
- Correct rendering across all four navigation sections.
- Dynamic interaction with horizon and adaptation window controls.
- Safe headless execution without raw data requirements.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app() -> AppTest:
    """Fixture providing initialized AppTest instance for app.py."""
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    return at


def test_app_starts_without_exception(app: AppTest) -> None:
    """Verify app starts cleanly without unhandled exceptions."""
    assert not app.exception, f"App startup encountered exception: {app.exception}"


def test_app_navigation_overview(app: AppTest) -> None:
    """Verify Section A (Project Overview) renders expected core elements."""
    assert not app.exception
    # Check that sidebar radio contains all 4 sections
    radio = app.sidebar.radio[0]
    assert len(radio.options) == 4
    assert radio.value == "📌 Project Overview"


def test_app_navigation_global_explorer(app: AppTest) -> None:
    """Verify Section B (Global Forecasting Explorer) loads and responds to horizon toggles."""
    app.sidebar.radio[0].set_value("📈 Global Forecasting Explorer").run()
    assert not app.exception

    # Test toggling to +60m
    horizon_radio = app.radio[0]
    assert len(horizon_radio.options) == 2
    horizon_radio.set_value("+60-Minute Horizon").run()
    assert not app.exception


def test_app_navigation_personalization_lab(app: AppTest) -> None:
    """Verify Section C (Personalization Lab) loads and responds to horizon and window toggles."""
    app.sidebar.radio[0].set_value("🎯 Personalization Lab").run()
    assert not app.exception

    # Test toggling adaptation windows
    # Radios on page: horizon, window
    assert len(app.radio) >= 2
    app.radio[1].set_value("4 Study Days").run()
    assert not app.exception

    app.radio[1].set_value("2 Study Days").run()
    assert not app.exception


def test_app_navigation_methodology(app: AppTest) -> None:
    """Verify Section D (Methodology & Guard Band) loads without exception."""
    app.sidebar.radio[0].set_value("🔬 Methodology & Guard Band").run()
    assert not app.exception
