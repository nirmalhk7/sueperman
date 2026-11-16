"""Developer sponsor flags must not turn ordinary regression tests into live calls."""

from fastapi.testclient import TestClient


def test_ordinary_suite_refuses_band_even_when_developer_environment_enables_it(tmp_path, monkeypatch):
    from app.diwali import band_bridge
    from app.main import create_app

    monkeypatch.setenv("DIWALI_ENABLED", "true")

    def unexpected_provider(*args, **kwargs):
        raise AssertionError("Ordinary tests reached the credentialed BAND transport")

    monkeypatch.setattr(band_bridge, "BandTransport", unexpected_provider)
    with TestClient(create_app(f"sqlite:///{tmp_path}/offline.db")) as client:
        seed = client.post("/api/demo/reset").json()
        response = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"],
            "collaboration_mode": "band", "idempotency_key": "ordinary-tests-offline"})
        assert response.status_code == 503
