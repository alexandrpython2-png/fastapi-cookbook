"""
Запросы к рецептам
"""
from typing import Annotated, List, Sequence

from fastapi import APIRouter, HTTPException, Path, status
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from cookbook import models, schemas
from cookbook.database import SessionDep

MAX_ID: int = 2 ** 63 - 1  # наибольшее число, которое помещается в INTEGER базы

router = APIRouter(prefix='/recipes', tags=['recipes'])


@router.get(
    '',
    response_model=List[schemas.RecipeShort],
    summary='Список рецептов',
    response_description='Все рецепты, от самых популярных к наименее популярным',
)
async def list_recipes(session: SessionDep) -> Sequence[models.Recipe]:
    """
    Все рецепты для экрана с таблицей: название, количество просмотров и время готовки.

    Рецепты отсортированы по популярности, то есть по убыванию количества просмотров. При равном количестве
    просмотров первым идёт рецепт с меньшим временем готовки, а при равном времени — тот, что добавлен раньше.

    Сам этот запрос просмотром не считается.
    """
    recipes = await session.scalars(
        select(models.Recipe).order_by(models.Recipe.views.desc(), models.Recipe.cooking_time, models.Recipe.id)
    )
    return recipes.all()


@router.get(
    '/{recipe_id}',
    response_model=schemas.RecipeDetail,
    summary='Детальная информация о рецепте',
    response_description='Рецепт с ингредиентами и описанием',
    responses={status.HTTP_404_NOT_FOUND: {'model': schemas.HTTPError, 'description': 'Рецепта с таким id нет'}},
)
async def get_recipe(
    recipe_id: Annotated[int, Path(ge=1, le=MAX_ID, description='Идентификатор рецепта из списка рецептов')],
    session: SessionDep,
) -> models.Recipe:
    """
    Название, время готовки, ингредиенты и описание рецепта для экрана с рецептом.

    Каждый успешный запрос — это просмотр: количество просмотров рецепта увеличивается на 1,
    и рецепт поднимается в списке. Запрос несуществующего рецепта просмотром не считается.
    """
    # Счётчик увеличивает сама база одним UPDATE, поэтому при одновременных просмотрах ни один не потеряется
    result = await session.execute(
        update(models.Recipe)
        .where(models.Recipe.id == recipe_id)
        .values(views=models.Recipe.views + 1)
        .execution_options(synchronize_session=False)
    )
    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Рецепт не найден')
    recipe: models.Recipe = await session.scalar(
        select(models.Recipe).options(selectinload(models.Recipe.ingredients)).where(models.Recipe.id == recipe_id)
    )
    await session.commit()
    return recipe


@router.post(
    '',
    response_model=schemas.RecipeDetail,
    status_code=status.HTTP_201_CREATED,
    summary='Добавить рецепт',
    response_description='Созданный рецепт вместе с его id',
)
async def create_recipe(recipe_in: schemas.RecipeCreate, session: SessionDep) -> models.Recipe:
    """
    Добавляет рецепт. У нового рецепта 0 просмотров, поэтому в списке он оказывается среди наименее популярных.
    """
    recipe = models.Recipe(
        title=recipe_in.title,
        cooking_time=recipe_in.cooking_time,
        description=recipe_in.description,
        ingredients=[models.Ingredient(**ingredient.model_dump()) for ingredient in recipe_in.ingredients],
    )
    session.add(recipe)
    await session.commit()
    return recipe
