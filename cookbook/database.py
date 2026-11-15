"""
Подключение к базе данных. Адрес базы берётся из переменной окружения DATABASE_URL,
по умолчанию это файл cookbook.db в папке, из которой запущен сервер
"""
import os
from typing import Annotated, AsyncIterator

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL: str = os.environ.get('DATABASE_URL', 'sqlite+aiosqlite:///./cookbook.db')


class Base(DeclarativeBase):
    """Базовый класс таблиц"""


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """
    Отдельная сессия на каждый запрос: одну сессию нельзя использовать из нескольких запросов одновременно
    """
    async with request.app.state.session_maker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
