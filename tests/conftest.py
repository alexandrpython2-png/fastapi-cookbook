from pathlib import Path
from typing import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cookbook.main import create_app


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    """
    У каждого теста своя пустая база во временной папке
    """
    return f'sqlite+aiosqlite:///{(tmp_path / "test.db").as_posix()}'


@pytest.fixture
def app(database_url: str) -> FastAPI:
    return create_app(database_url)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:  # with запускает lifespan: создание таблиц и закрытие подключений
        yield client


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'
