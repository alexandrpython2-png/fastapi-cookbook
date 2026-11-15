"""
API кулинарной книги

uvicorn cookbook.main:app --reload
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from cookbook.database import DATABASE_URL, Base
from cookbook.routes import router

DESCRIPTION: str = """
Бэкенд приложения «Кулинарная книга».

## Экраны и запросы

| Экран | Запрос |
|---|---|
| Таблица всех рецептов: название, количество просмотров, время готовки | `GET /recipes` |
| Рецепт: название, время готовки, ингредиенты, описание | `GET /recipes/{recipe_id}` |
| Добавление рецепта | `POST /recipes` |

## Популярность

Популярность рецепта — количество его просмотров, то есть сколько раз открыли его детальную информацию.
Каждый успешный `GET /recipes/{recipe_id}` увеличивает количество просмотров на 1. Список рецептов отсортирован
по убыванию просмотров, при равенстве — по возрастанию времени готовки.

## Форматы

* Время готовки — целое число минут.
* Запросы и ответы — JSON в кодировке UTF-8.

## Ошибки

У всех ошибок в ответе есть поле `detail`:

* `404` — рецепта с таким id нет, в `detail` строка с описанием;
* `422` — данные запроса не прошли проверку, в `detail` список ошибок: `loc` — где ошибка
  (например, `["body", "cooking_time"]`), `msg` — что не так.
"""

TAGS = [{'name': 'recipes', 'description': 'Рецепты: список, детальная информация и добавление'}]


def create_app(database_url: str = DATABASE_URL) -> FastAPI:
    """
    Создаёт приложение со своей базой данных: тесты передают сюда адрес временной базы
    """
    engine = create_async_engine(database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(
        title='Кулинарная книга',
        version='1.0.0',
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
        # operationId в документации — имя функции: list_recipes, get_recipe, create_recipe.
        # По нему генераторы клиентов называют методы
        generate_unique_id_function=lambda route: route.name,
    )
    # expire_on_commit=False: после коммита атрибуты объекта остаются загруженными, и его можно вернуть в ответе
    app.state.session_maker = async_sessionmaker(engine, expire_on_commit=False)
    app.include_router(router)

    @app.get('/', include_in_schema=False)
    async def index() -> RedirectResponse:
        return RedirectResponse('/docs')

    return app


app: FastAPI = create_app()
