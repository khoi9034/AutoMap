import pytest

from app import ports


def test_reserved_ports_are_blocked(monkeypatch):
    monkeypatch.setattr(ports, "is_port_busy", lambda port, host="127.0.0.1": False)

    with pytest.raises(ValueError, match="reserved for Cabarrus FutureScape"):
        ports.validate_automap_port(3000, service_name="frontend")

    with pytest.raises(ValueError, match="reserved for Cabarrus FutureScape"):
        ports.validate_automap_port(8000, service_name="backend/API")


def test_busy_automap_port_is_blocked(monkeypatch):
    monkeypatch.setattr(ports, "is_port_busy", lambda port, host="127.0.0.1": port == 8010)

    with pytest.raises(ValueError, match="8010 is already in use"):
        ports.validate_automap_port(8010, service_name="backend/API")


def test_reserved_busy_ports_warn_but_do_not_block_automap_port(monkeypatch):
    monkeypatch.setattr(ports, "is_port_busy", lambda port, host="127.0.0.1": port in {3000, 8000})

    warnings = ports.validate_automap_port(8010, service_name="backend/API")

    assert len(warnings) == 2
    assert all("reserved for Cabarrus FutureScape" in warning for warning in warnings)
