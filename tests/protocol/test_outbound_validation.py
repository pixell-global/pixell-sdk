import pytest

from pixell.protocol import validate_outbound_if_dev


def test_validate_outbound_dev_pass(monkeypatch):
    monkeypatch.setenv("PIXELL_ENV", "development")
    envelope = {"type": "action.result", "status": "ok"}
    validate_outbound_if_dev(envelope)  # should not raise


def test_validate_outbound_dev_fail(monkeypatch):
    monkeypatch.setenv("PIXELL_ENV", "development")
    bad = {"type": "action.result", "status": "wat"}
    with pytest.raises(Exception):
        validate_outbound_if_dev(bad) 