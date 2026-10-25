from __future__ import annotations

import csv
import importlib.util
from io import StringIO
from pathlib import Path
from types import ModuleType

import pytest

from tradecat_sources.registry import DatasetSpec, list_datasets

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github/scripts/validate_data_contract.py"
ACTIVE_DATASETS = list_datasets()


@pytest.fixture
def validator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("tradecat_data_contract_validation_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Literal public source headers observed independently from the registry on
# 2026-10-24. Deriving them from DatasetSpec would let a wrong registry pass.
PUBLIC_SOURCE_HEADERS = {
    "market_snapshot": ("排名", "交易对"),
    "anomaly_panel": ("排名", "交易对"),
    "market_stats": ("窗口", "覆盖合约数"),
    "signal_flow": ("时间(北京)", "交易对", "周期", "信号类型", "内容"),
    "event_stream": ("时间(北京)", "内容"),
}


def _fixture_csv(dataset: DatasetSpec, *, exclude: tuple[str, ...] = ()) -> str:
    columns = [*PUBLIC_SOURCE_HEADERS[dataset.key], "fixture_value", "fixture_extra"]
    columns = [column for column in columns if column not in exclude]
    stream = StringIO()
    writer = csv.writer(stream)
    writer.writerow(columns)
    writer.writerow([f"synthetic-{index}" for index in range(len(columns))])
    return stream.getvalue()


def test_data_validator_uses_relocated_registry(validator: ModuleType) -> None:
    assert validator.REGISTRY_PATH == ROOT / ".github/src/tradecat_sources/dataset_registry.json"
    assert validator.REGISTRY_PATH.is_file()
    assert validator.validate_registry_file() == []


@pytest.mark.parametrize("dataset", ACTIVE_DATASETS, ids=lambda dataset: dataset.key)
def test_remote_shape_validator_accepts_offline_csv_fixture(
    validator: ModuleType, monkeypatch: pytest.MonkeyPatch, dataset: DatasetSpec
) -> None:
    calls = []

    def fake_fetch(url: str, *, timeout: float) -> str:
        calls.append((url, timeout))
        return _fixture_csv(dataset)

    monkeypatch.setattr(validator, "fetch_csv_body", fake_fetch)

    assert validator.validate_remote_csv(dataset.key, timeout=2.0) == []
    assert calls == [(dataset.export_url(), 2.0)]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("", "remote CSV is empty"),
        ("only_one_column\nsynthetic\n", "header must contain at least 2 columns"),
        ("fixture_a,fixture_b\n", "must contain at least one data row"),
    ],
)
def test_remote_shape_validator_rejects_bad_offline_csv(
    validator: ModuleType, monkeypatch: pytest.MonkeyPatch, body: str, expected: str
) -> None:
    monkeypatch.setattr(validator, "fetch_csv_body", lambda *args, **kwargs: body)

    errors = validator.validate_remote_csv(ACTIVE_DATASETS[0].key, timeout=2.0)

    assert any(expected in error for error in errors)


def test_remote_shape_validator_requires_configured_event_keys(
    validator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = next(dataset for dataset in ACTIVE_DATASETS if dataset.event_key_columns)
    monkeypatch.setattr(
        validator, "fetch_csv_body", lambda *args, **kwargs: _fixture_csv(dataset, exclude=dataset.event_key_columns)
    )

    errors = validator.validate_remote_csv(dataset.key, timeout=2.0)

    assert any("lacks event key columns" in error for error in errors)


def test_remote_shape_validator_requires_configured_index_column(
    validator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset = next(dataset for dataset in ACTIVE_DATASETS if dataset.index_columns)
    monkeypatch.setattr(
        validator, "fetch_csv_body", lambda *args, **kwargs: _fixture_csv(dataset, exclude=dataset.index_columns)
    )

    errors = validator.validate_remote_csv(dataset.key, timeout=2.0)

    assert any("lacks any configured index column" in error for error in errors)


def test_remote_shape_validator_records_offline_transport_failure(
    validator: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_timeout(*args, **kwargs) -> str:
        raise TimeoutError("synthetic offline timeout; no request sent")

    monkeypatch.setattr(validator, "fetch_csv_body", fake_timeout)

    errors = validator.validate_remote_csv(ACTIVE_DATASETS[0].key, timeout=2.0)

    assert any("remote CSV fetch failed" in error and "synthetic offline timeout" in error for error in errors)


def test_remote_cli_dispatch_with_offline_fixtures_does_not_validate_inactive_sources(
    validator: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen = []

    def fake_validate(key: str, *, timeout: float) -> list[str]:
        seen.append(key)
        return []

    monkeypatch.setattr(validator, "validate_remote_csv", fake_validate)

    assert validator.main(["--remote", "--include-inactive"]) == 0
    assert set(seen) == {dataset.key for dataset in ACTIVE_DATASETS}
    assert "data contract ok: mode=registry+remote" in capsys.readouterr().out
