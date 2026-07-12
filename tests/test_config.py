"""Smoke tests for configuration and project structure."""
import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "src" / "trading_bot" / "src" / "config" / "trading_config.yaml"


def test_trading_config_exists():
    assert CONFIG_PATH.exists(), "Active trading config must exist"


def test_trading_config_has_required_sections():
    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    assert "trading" in config
    assert "pairs" in config["trading"]
    assert len(config["trading"]["pairs"]) >= 1


def test_run_py_exists():
    assert (ROOT / "run.py").exists()


def test_env_example_exists():
    assert (ROOT / ".env.example").exists()


def test_no_secrets_in_env_example():
    content = (ROOT / ".env.example").read_text()
    assert "sk-proj-" not in content
    assert "mongodb+srv://kairee" not in content


def test_strategy_modules_importable():
    """Verify core strategy package structure is intact."""
    strategies_dir = ROOT / "src" / "trading_bot" / "src" / "strategies"
    assert strategies_dir.exists()
    assert (strategies_dir / "strategy_manager.py").exists()
    assert (strategies_dir / "swing").is_dir()
