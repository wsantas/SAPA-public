"""Backend API coverage for the health plugin's recipe endpoints.

These tests exercise the Python routes that back the recipe, favorites,
cook-log, and meal-planner UI. They are intentionally thin — verifying the
endpoints respond and return plausibly-shaped data, not deep business logic.
"""


def test_recipes_list_endpoint(client):
    r = client.get("/api/recipes")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # The repo ships with 15 recipe JSON files seeding many recipes.
    assert len(data) > 0, "Recipe library should not be empty on fresh install"


def test_recipe_detail_endpoint(client):
    # Fetch the list, then request the first recipe's detail.
    list_resp = client.get("/api/recipes")
    assert list_resp.status_code == 200
    recipes = list_resp.json()
    assert recipes, "Need at least one recipe for detail test"
    recipe_id = recipes[0].get("id")
    assert recipe_id, f"First recipe has no id: {recipes[0]}"

    detail = client.get(f"/api/recipes/{recipe_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body.get("id") == recipe_id


def test_recipe_favorites_endpoint(client):
    r = client.get("/api/recipes/favorites")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_recipe_cook_log_endpoint(client):
    r = client.get("/api/recipes/cook-log")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_meal_plans_endpoint(client):
    r = client.get("/api/meal-plans")
    assert r.status_code == 200


def test_meal_requests_endpoint(client):
    r = client.get("/api/meal-requests")
    assert r.status_code == 200


def test_meals_today_endpoint(client):
    r = client.get("/api/meals/today")
    assert r.status_code == 200


def test_recipe_library_size(client):
    r = client.get("/api/recipes")
    assert r.status_code == 200
    recipes = r.json()
    assert len(recipes) > 10, f"Recipe loader returned suspiciously few: {len(recipes)}"
