"""docker-compose must give containers container-correct service URLs (Defect 8) and stay light by default.

Resolves the EFFECTIVE environment of the backend from the real docker-compose.yml using compose's precedence rule
(`environment:` overrides `env_file:`), against a host-style .env. Needs no Docker.
"""

import os
import re
from urllib.parse import urlparse

import pytest
import yaml

COMPOSE = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")

# What a developer's host-side .env looks like. Correct for processes on the host; wrong inside a container.
HOST_DOTENV = {
    "DATABASE_URL": "postgresql+asyncpg://injury_user:changeme_in_production@localhost:5433/injury_detection",
    "DATABASE_URL_SYNC": "postgresql+psycopg2://injury_user:changeme_in_production@localhost:5433/injury_detection",
    "JWT_SECRET_KEY": "from-dotenv",
}


def interpolate(value: str) -> str:
    return re.sub(r"\$\{([A-Z_]+)(?::-([^}]*))?\}", lambda m: os.environ.get(m.group(1), m.group(2) or ""), str(value))


def effective_env(service: dict, dotenv: dict) -> dict:
    env = dict(dotenv) if service.get("env_file") else {}
    declared = service.get("environment") or {}
    if isinstance(declared, list):
        declared = dict(item.split("=", 1) for item in declared)
    env.update({k: interpolate(v) for k, v in declared.items()})
    return env


@pytest.fixture(scope="module")
def compose():
    with open(COMPOSE) as f:
        return yaml.safe_load(f)


def test_the_backend_container_reaches_postgres_by_service_name(compose, monkeypatch):
    for var in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        monkeypatch.delenv(var, raising=False)
    env = effective_env(compose["services"]["backend"], HOST_DOTENV)

    for key in ("DATABASE_URL", "DATABASE_URL_SYNC"):
        url = urlparse(env[key].replace("+asyncpg", "").replace("+psycopg2", ""))
        assert (url.hostname, url.port) == ("postgres", 5432), f"backend.{key} -> {env[key]}"
        assert url.path == "/injury_detection" and url.username == "injury_user"
    assert env["JWT_SECRET_KEY"] == "from-dotenv", "everything else must still come from .env"


def test_container_url_follows_the_postgres_settings_used_by_the_database_service(compose, monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "u2")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p2")
    monkeypatch.setenv("POSTGRES_DB", "d2")
    url = urlparse(effective_env(compose["services"]["backend"], HOST_DOTENV)["DATABASE_URL"].replace("+asyncpg", ""))
    assert (url.username, url.password, url.path, url.hostname) == ("u2", "p2", "/d2", "postgres")


def test_the_host_side_env_value_is_left_alone(compose):
    """Non-Docker runs read .env directly and must keep localhost."""
    assert urlparse(HOST_DOTENV["DATABASE_URL"].replace("+asyncpg", "")).hostname == "localhost"
    assert "DATABASE_URL" not in (compose["services"]["postgres"].get("environment") or {})


def test_helper_reproduces_the_original_bug_when_no_override_exists():
    """Guards the guard: with only env_file (the old compose), the container sees the host URL."""
    old_style = {"env_file": [".env"]}
    assert urlparse(effective_env(old_style, HOST_DOTENV)["DATABASE_URL"].replace("+asyncpg", "")).hostname == "localhost"


def test_plain_compose_up_starts_only_the_database(compose):
    """`docker compose up -d` must stay light (Docker is what made this unusable on a 16 GB laptop): no torch image, no Redis."""
    default = [name for name, svc in compose["services"].items() if not svc.get("profiles")]
    assert default == ["postgres"]
    assert "redis" not in compose["services"] and "arq_worker" not in compose["services"]


def test_host_run_settings_need_only_database_url():
    """Host runs read .env, not os.environ: the sync URL is derived."""
    from app.config import Settings

    s = Settings(database_url="postgresql+asyncpg://u:p@localhost:5433/d", database_url_sync="")
    assert s.database_url_sync == "postgresql+psycopg2://u:p@localhost:5433/d"
