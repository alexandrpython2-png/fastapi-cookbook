"""
Схемы запросов и ответов. По ним FastAPI проверяет данные и строит документацию:
описания полей и примеры отсюда видны фронтендерам в /docs
"""
from typing import Annotated, List

from pydantic import BaseModel, ConfigDict, Field

MAX_COOKING_TIME: int = 7 * 24 * 60  # неделя в минутах

RecipeId = Annotated[int, Field(description='Идентификатор рецепта', examples=[1])]
Title = Annotated[str, Field(min_length=1, max_length=200, description='Название рецепта', examples=['Блины на молоке'])]
CookingTime = Annotated[int, Field(
    ge=1,
    le=MAX_COOKING_TIME,
    description='Время готовки в минутах, от 1 минуты до недели',
    examples=[40],
)]
Description = Annotated[str, Field(
    min_length=1,
    max_length=10_000,
    description='Текстовое описание: как готовить',
    examples=['Смешайте яйца с сахаром и солью, влейте молоко и всыпьте муку. Жарьте на разогретой сковороде '
              'по минуте с каждой стороны.'],
)]


class Ingredient(BaseModel):
    """
    Ингредиент рецепта и его количество
    """
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100, description='Название ингредиента', examples=['Мука пшеничная'])
    amount: str = Field(
        min_length=1,
        max_length=50,
        description='Количество в свободной форме, например «200 г», «2 шт.» или «по вкусу»',
        examples=['200 г'],
    )


class RecipeCreate(BaseModel):
    """
    Новый рецепт. Пробелы в начале и в конце строк отбрасываются, пустые строки не принимаются
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Title
    cooking_time: CookingTime
    ingredients: List[Ingredient] = Field(
        min_length=1,
        max_length=100,
        description='Ингредиенты, от 1 до 100, в том порядке, в котором их нужно показывать',
    )
    description: Description


class RecipeShort(BaseModel):
    """
    Строка таблицы на экране списка рецептов
    """
    model_config = ConfigDict(from_attributes=True)

    id: RecipeId
    title: Title
    views: int = Field(
        ge=0,
        description='Количество просмотров: сколько раз открыли детальную информацию о рецепте',
        examples=[42],
    )
    cooking_time: CookingTime


class RecipeDetail(BaseModel):
    """
    Детальная информация о рецепте
    """
    model_config = ConfigDict(from_attributes=True)

    id: RecipeId
    title: Title
    cooking_time: CookingTime
    ingredients: List[Ingredient] = Field(description='Ингредиенты в том порядке, в котором их добавили')
    description: Description


class HTTPError(BaseModel):
    """
    Ошибка запроса
    """
    detail: str = Field(description='Что пошло не так', examples=['Рецепт не найден'])
