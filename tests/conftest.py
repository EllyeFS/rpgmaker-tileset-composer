"""Pytest configuration for Qt tests."""

import pytest


@pytest.fixture(scope="session")
def qapp_args():
    """Arguments to pass to QApplication."""
    return ["-platform", "offscreen"]


# Tell pytest-qt to use PySide6
def pytest_configure(config):
    config.addinivalue_line(
        "markers", "qt: mark test as requiring Qt"
    )
