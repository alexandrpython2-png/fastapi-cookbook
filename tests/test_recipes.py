import asyncio
from typing import Any, Dict

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import ASGITransport, AsyncClient

from cookbook.main import create_app


def make_recipe(**changes: Any) -> Dict[str, Any]:
    recipe: Dict[str, Any] = {
        "title": "Блины на молоке",
        "cooking_time": 40,
        "ingredients": [
            {"name": "Мука пшеничная", "amount": "200 г"},
            {"name": "Молоко", "amount": "500 мл"},
            {"name": "Яйца", "amount": "2 шт."},
            {"name": "Соль", "amount": "по вкусу"},
        ],
        "description": "Смешайте яйца с солью, влейте молоко и всыпьте муку. Жарьте по минуте с каждой стороны.",
    }
    recipe.update(changes)
    return recipe


def create(client: TestClient, **changes: Any) -> Dict[str, Any]:
    response = client.post("/recipes", json=make_recipe(**changes))
    assert response.status_code == 201, response.text
    created: Dict[str, Any] = response.json()
    return created


def open_recipe(client: TestClient, recipe_id: int, times: int = 1) -> None:
    for _ in range(times):
        assert client.get(f"/recipes/{recipe_id}").status_code == 200


def test_root_redirects_to_docs(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_list_is_empty_at_start(client: TestClient) -> None:
    response = client.get("/recipes")
    assert response.status_code == 200
    assert response.json() == []


def test_create_recipe_returns_detail(client: TestClient) -> None:
    recipe = make_recipe()
    response = client.post("/recipes", json=recipe)

    assert response.status_code == 201
    created = response.json()
    assert isinstance(created["id"], int)
    assert created == {"id": created["id"], **recipe}


def test_get_recipe_returns_detail_screen_fields(client: TestClient) -> None:
    created = create(client)
    response = client.get(f'/recipes/{created["id"]}')

    assert response.status_code == 200
    assert response.json() == created
    assert set(response.json()) == {"id", "title", "cooking_time", "ingredients", "description"}


def test_list_returns_table_fields(client: TestClient) -> None:
    created = create(client)
    assert client.get("/recipes").json() == [
        {"id": created["id"], "title": "Блины на молоке", "views": 0, "cooking_time": 40},
    ]


def test_detail_request_counts_as_view(client: TestClient) -> None:
    recipe_id = create(client)["id"]
    open_recipe(client, recipe_id, times=3)
    client.get("/recipes")  # список просмотром не считается

    assert client.get("/recipes").json()[0]["views"] == 3


def test_list_sorted_by_views_then_cooking_time(client: TestClient) -> None:
    ids = {
        title: create(client, title=title, cooking_time=cooking_time)["id"]
        for title, cooking_time in [
            ("Борщ", 120),
            ("Омлет", 15),
            ("Сырники", 30),
            ("Бутерброд", 5),
            ("Тост", 5),
            ("Каша", 20),
        ]
    }
    for title, views in [("Борщ", 1), ("Омлет", 3), ("Сырники", 1), ("Каша", 1)]:
        open_recipe(client, ids[title], times=views)

    table = [(row["title"], row["views"], row["cooking_time"]) for row in client.get("/recipes").json()]
    assert table == [
        ("Омлет", 3, 15),
        ("Каша", 1, 20),  # просмотров поровну, раньше тот, что готовится быстрее
        ("Сырники", 1, 30),
        ("Борщ", 1, 120),
        ("Бутерброд", 0, 5),  # и время поровну: раньше тот, что добавлен раньше
        ("Тост", 0, 5),
    ]


def test_ingredients_keep_order(client: TestClient) -> None:
    ingredients = [{"name": f"Ингредиент {number}", "amount": f"{number} г"} for number in range(20, 0, -1)]
    recipe_id = create(client, ingredients=ingredients)["id"]
    assert client.get(f"/recipes/{recipe_id}").json()["ingredients"] == ingredients


def test_missing_recipe_returns_404(client: TestClient) -> None:
    recipe_id = create(client)["id"]
    response = client.get(f"/recipes/{recipe_id + 1}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Рецепт не найден"}
    assert client.get("/recipes").json()[0]["views"] == 0


@pytest.mark.parametrize("recipe_id", ["abc", "1.5", "0", "-1", str(2**63)])
def test_invalid_recipe_id_returns_422(client: TestClient, recipe_id: str) -> None:
    response = client.get(f"/recipes/{recipe_id}")
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "recipe_id"]


@pytest.mark.parametrize(
    "changes, field",
    [
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"title": "Б" * 201}, "title"),
        ({"cooking_time": 0}, "cooking_time"),
        ({"cooking_time": -10}, "cooking_time"),
        ({"cooking_time": 1.5}, "cooking_time"),
        ({"cooking_time": "долго"}, "cooking_time"),
        ({"cooking_time": 10**20}, "cooking_time"),
        ({"ingredients": []}, "ingredients"),
        ({"ingredients": "мука, молоко"}, "ingredients"),
        ({"ingredients": [{"name": "Соль"}]}, "ingredients"),
        ({"ingredients": [{"name": " ", "amount": "1 г"}]}, "ingredients"),
        ({"description": ""}, "description"),
        ({"description": None}, "description"),
    ],
)
def test_invalid_recipe_is_rejected(client: TestClient, changes: Dict[str, Any], field: str) -> None:
    response = client.post("/recipes", json=make_recipe(**changes))

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][:2] == ["body", field]
    assert client.get("/recipes").json() == []


@pytest.mark.parametrize("field", ["title", "cooking_time", "ingredients", "description"])
def test_required_fields(client: TestClient, field: str) -> None:
    recipe = make_recipe()
    del recipe[field]
    response = client.post("/recipes", json=recipe)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]


def test_strings_are_stripped(client: TestClient) -> None:
    created = create(client, title="  Блины  ", ingredients=[{"name": " Мука ", "amount": " 200 г "}])
    assert created["title"] == "Блины"
    assert created["ingredients"] == [{"name": "Мука", "amount": "200 г"}]


def test_recipes_are_stored_in_database(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        recipe_id = create(client)["id"]
        open_recipe(client, recipe_id)

    with TestClient(create_app(database_url)) as client:  # новое приложение с той же базой
        assert client.get("/recipes").json()[0]["views"] == 1
        assert client.get(f"/recipes/{recipe_id}").json()["title"] == "Блины на молоке"


@pytest.mark.anyio
async def test_concurrent_views_are_not_lost(app: FastAPI) -> None:
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/recipes", json=make_recipe())
            recipe_id = response.json()["id"]

            responses = await asyncio.gather(*(client.get(f"/recipes/{recipe_id}") for _ in range(50)))
            assert all(response.status_code == 200 for response in responses)

            recipes = (await client.get("/recipes")).json()
            assert recipes[0]["views"] == 50


def test_documentation_describes_every_model_and_field(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    models = schema["components"]["schemas"]
    for name in ["Ingredient", "RecipeCreate", "RecipeShort", "RecipeDetail", "HTTPError"]:
        assert models[name].get("description"), name
        for field, field_schema in models[name]["properties"].items():
            assert field_schema.get("description"), f"{name}.{field}"

    operations = {
        operation["operationId"]: operation for path in schema["paths"].values() for operation in path.values()
    }
    assert set(operations) == {"list_recipes", "get_recipe", "create_recipe"}
    for operation in operations.values():
        assert operation["summary"] and operation["description"]
    assert operations["get_recipe"]["responses"]["404"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPError"
    }
