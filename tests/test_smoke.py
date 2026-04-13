"""Smoke tests — verify the app boots and core endpoints respond."""


def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "SAPA" in r.text


def test_openapi_spec_exposed(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["openapi"].startswith("3.")
    assert "paths" in spec
    assert "/api/status" in spec["paths"]


def test_swagger_ui_available(client):
    r = client.get("/docs")
    assert r.status_code == 200
    assert "swagger" in r.text.lower()


def test_api_status(client):
    r = client.get("/api/status")
    assert r.status_code == 200


def test_profiles_seeded(client):
    r = client.get("/api/profiles")
    assert r.status_code == 200
    profiles = r.json()
    assert isinstance(profiles, list)
    assert len(profiles) >= 2
    names = {p.get("name") for p in profiles}
    assert {"john", "jane"}.issubset(names)


def test_current_profile(client):
    r = client.get("/api/profiles/current")
    assert r.status_code == 200


def test_sessions_endpoint(client):
    r = client.get("/api/sessions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_topics_endpoint(client):
    r = client.get("/api/topics")
    assert r.status_code == 200


def test_health_gap_analysis(client):
    r = client.get("/api/gap-analysis")
    assert r.status_code == 200


def test_homestead_gap_analysis(client):
    r = client.get("/api/homestead/gap-analysis")
    assert r.status_code == 200


def test_cors_headers_on_preflight(client):
    r = client.options(
        "/api/status",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_demo_inbox_seeded_on_startup(client, tmp_config_dir):
    john_dir = tmp_config_dir / "plugins" / "health" / "inbox" / "john"
    jane_dir = tmp_config_dir / "plugins" / "health" / "inbox" / "jane"
    assert john_dir.exists()
    assert jane_dir.exists()
    assert any(john_dir.glob("*.md")), "John's inbox should be seeded with demo content"
    assert any(jane_dir.glob("*.md")), "Jane's inbox should be seeded with demo content"
