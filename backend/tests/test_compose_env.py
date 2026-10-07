"""docker-compose must give containers container-correct service URLs (Defect 8).

Resolves the EFFECTIVE environment of each service from the real docker-compose.yml using compose's
precedence rule (`environment:` overrides `env_file:`), against a host-style .env. Needs no Docker.
"""

import os
import re
from urllib.parse import urlparse

import pytest
import yaml

COMPOSE = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")

# What a developer's host-side .env looks like (project Postgres published on 5433 because a native
# Postgres owns 5432). Correct for processes on the host; wrong inside a container.
HOST_DOTENV = {
    "DATABASE_URL": "postgresql+asyncpg://injury_user:changeme_in_production@localhost:5433/injury_detection",
    "DATABASE_URL_SYNC": "postgresql+psycopg2://injury_user:changeme_in_production@localhost:5433/injury_detection",
    "REDIS_URL": "redis://localhost:6379/0",
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


@pytest.mark.parametrize("service", ["backend", "arq_worker"])
def test_containers_reach_postgres_and_redis_by_service_name(compose, service, monkeypatch):
    for var in ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"):
        monkeypatch.delenv(var, raising=False)
    env = effective_env(compose["services"][service], HOST_DOTENV)

    for key in ("DATABASE_URL", "DATABASE_URL_SYNC"):
        url = urlparse(env[key].replace("+asyncpg", "").replace("+psycopg2", ""))
        assert (url.hostname, url.port) == ("postgres", 5432), f"{service}.{key} -> {env[key]}"
        assert url.path == "/injury_detection" and url.username == "injury_user"
    redis = urlparse(env["REDIS_URL"])
    assert (redis.hostname, redis.port) == ("redis", 6379)
    assert env["JWT_SECRET_KEY"] == "from-dotenv", "everything else must still come from .env"


@pytest.mark.parametrize("service", ["backend", "arq_worker"])
def test_container_url_follows_the_postgres_settings_used_by_the_database_service(compose, service, monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "u2")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p2")
    monkeypatch.setenv("POSTGRES_DB", "d2")
    url = urlparse(effective_env(compose["services"][service], HOST_DOTENV)["DATABASE_URL"].replace("+asyncpg", ""))
    assert (url.username, url.password, url.path, url.hostname) == ("u2", "p2", "/d2", "postgres")


def test_the_host_side_env_value_is_left_alone(compose):
    """Non-Docker runs read .env directly and must keep localhost:5433."""
    assert urlparse(HOST_DOTENV["DATABASE_URL"].replace("+asyncpg", "")).hostname == "localhost"
    assert "DATABASE_URL" not in (compose["services"]["postgres"].get("environment") or {})


def test_helper_reproduces_the_original_bug_when_no_override_exists():
    """Guards the guard: with only env_file (the old compose), the container sees the host URL."""
    old_style = {"env_file": [".env"]}
    assert urlparse(effective_env(old_style, HOST_DOTENV)["DATABASE_URL"].replace("+asyncpg", "")).hostname == "localhost"


def test_host_run_settings_need_only_database_url_and_redis_url():
    """Host runs read .env, not os.environ: the sync URL is derived and arq gets REDIS_URL from Settings."""
    from app.config import Settings
    from app.modules.pose.worker_settings import redis_settings_from_env

    s = Settings(database_url="postgresql+asyncpg://u:p@localhost:5433/d", database_url_sync="")
    assert s.database_url_sync == "postgresql+psycopg2://u:p@localhost:5433/d"
    assert redis_settings_from_env().host == urlparse(os.environ["REDIS_URL"]).hostname
