"""
Таблицы базы данных
"""
from typing import List

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cookbook.database import Base


class Recipe(Base):
    __tablename__ = 'recipes'

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    cooking_time: Mapped[int]  # в минутах
    description: Mapped[str] = mapped_column(Text)
    views: Mapped[int] = mapped_column(default=0, server_default='0')  # сколько раз открыли детальный рецепт
    # lazy='raise': в асинхронной сессии ингредиенты нельзя подгрузить незаметно при обращении к атрибуту,
    # их нужно загрузить в запросе явно, иначе будет понятная ошибка
    ingredients: Mapped[List['Ingredient']] = relationship(
        cascade='all, delete-orphan', order_by='Ingredient.id', lazy='raise'
    )


class Ingredient(Base):
    __tablename__ = 'ingredients'

    id: Mapped[int] = mapped_column(primary_key=True)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    amount: Mapped[str] = mapped_column(String(50))
