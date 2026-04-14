"""Structural validation of the assembled health plugin JavaScript.

These tests guard against refactor regressions in how health.js is split,
concatenated, and rendered. They specifically cover the risk surface of the
recipe-extraction refactor: brace balance, single-declaration invariants,
declaration-before-use ordering, and absence of unsubstituted template
placeholders leaking into the browser.
"""

import re


def _rendered_health_js():
    from sapa.plugins.health.plugin import HealthPlugin
    return HealthPlugin().get_js()


def test_rendered_js_has_balanced_braces():
    js = _rendered_health_js()
    assert js.count("{") == js.count("}"), (
        f"Brace imbalance: {js.count('{')} open vs {js.count('}')} close"
    )


def test_rendered_js_has_balanced_parens():
    js = _rendered_health_js()
    # Parens can legitimately mismatch by a small count due to regex/string
    # literal contents. Keep this loose — we only care about gross imbalance.
    delta = abs(js.count("(") - js.count(")"))
    assert delta < 10, f"Paren imbalance too large: delta={delta}"


def test_allrecipes_declared_exactly_once():
    js = _rendered_health_js()
    # Match `let allRecipes =` at the start of a declaration, not accidental
    # substring occurrences.
    count = len(re.findall(r"\blet\s+allRecipes\s*=", js))
    assert count == 1, (
        f"`let allRecipes = ` should be declared exactly once, got {count}. "
        "A duplicate means the recipe file is being concatenated twice; a zero "
        "means the recipe file isn't in the output."
    )


def test_recipefavorites_declared_exactly_once():
    js = _rendered_health_js()
    count = len(re.findall(r"\blet\s+recipeFavorites\s*=", js))
    assert count == 1, f"`let recipeFavorites = ` should appear once, got {count}"


def test_recipecooklog_declared_exactly_once():
    js = _rendered_health_js()
    count = len(re.findall(r"\blet\s+recipeCookLog\s*=", js))
    assert count == 1, f"`let recipeCookLog = ` should appear once, got {count}"


def test_recipes_declared_before_meal_planner_uses():
    """Meal planner in health.js references allRecipes, which is declared
    in health-recipes.js. The concatenation order must put recipes first.
    """
    js = _rendered_health_js()
    decl_pos = js.find("let allRecipes =")
    # The meal planner sidebar builds a pool via `allRecipes.slice()`,
    # which is unique to the meal planner code path and doesn't appear in
    # health-recipes.js itself. Using this as the marker for "after the
    # recipe block we reference allRecipes unconditionally".
    use_pos = js.find("allRecipes.slice()")
    assert decl_pos >= 0, "allRecipes declaration not found in rendered JS"
    assert use_pos >= 0, "meal planner use of allRecipes not found in rendered JS"
    assert decl_pos < use_pos, (
        "allRecipes is used before it is declared. Check that "
        "health-recipes.js is concatenated before health.js in plugin.py."
    )


def test_key_recipe_functions_present():
    """All critical recipe functions must survive the split."""
    js = _rendered_health_js()
    required = [
        "function loadRecipes",
        "function showRecipe",
        "function closeRecipeModal",
        "function filterRecipes",
        "function renderRecipes",
        "function startCookingMode",
        "function exitCookingMode",
        "async function toggleRecipeFavorite",
        "async function addRecipeToGrocery",
        "async function logRecipeAsMeal",
    ]
    missing = [name for name in required if name not in js]
    assert not missing, f"Missing recipe functions: {missing}"


def test_key_meal_planner_functions_present():
    """Meal planner functions must still exist alongside the extracted recipes."""
    js = _rendered_health_js()
    required = [
        "function switchMealPlanView",
        "async function loadMealPlanner",
        "async function addMealPlan",
        "async function deleteMealPlan",
        "async function openMealSidebar",
    ]
    missing = [name for name in required if name not in js]
    assert not missing, f"Missing meal planner functions: {missing}"


def test_no_unsubstituted_placeholders():
    """The gap analysis template uses $PLACEHOLDER$ substitution. Any leaked
    placeholder in the rendered JS is a build-time bug.
    """
    js = _rendered_health_js()
    # These should all be substituted by generate_gap_js() in health plugin.
    leaked = re.findall(r"\$[A-Z_]+\$", js)
    # $TOPIC$ and $CATEGORY$ are intentional runtime placeholders inside the
    # gap prompt templates. Everything else is a leak.
    real_leaks = [p for p in leaked if p not in ("$TOPIC$", "$CATEGORY$")]
    assert not real_leaks, f"Unsubstituted placeholders in rendered JS: {set(real_leaks)}"


def test_no_duplicate_function_declarations():
    """If the split copied a function into both files by mistake, it would
    show up twice in the rendered output. Spot-check a few that should be
    unique to the recipe file.
    """
    js = _rendered_health_js()
    unique_recipe_fns = [
        "function loadRecipes",
        "function showRecipe",
        "function startCookingMode",
    ]
    for fn in unique_recipe_fns:
        count = js.count(fn)
        assert count == 1, f"`{fn}` appears {count} times in rendered JS, expected 1"


def test_rendered_html_includes_recipes_js(client):
    """Full integration check: the assembled HTML served at `/` must contain
    the recipe code path, confirming plugin.get_js() is actually wired into
    page assembly and concatenation order survives the shell template.
    """
    r = client.get("/")
    assert r.status_code == 200
    assert "function loadRecipes" in r.text
    assert "function showRecipe" in r.text
    # base.js has a *guarded* tab lazy-load hook that references allRecipes
    # via `typeof allRecipes !== 'undefined'` — that's safe regardless of
    # order. The unguarded meal planner use via `allRecipes.slice()` must
    # still come after the declaration.
    decl_pos = r.text.find("let allRecipes =")
    unguarded_use_pos = r.text.find("allRecipes.slice()")
    assert decl_pos >= 0, "let allRecipes = missing from assembled HTML"
    assert unguarded_use_pos >= 0, "meal planner unguarded use missing"
    assert decl_pos < unguarded_use_pos, (
        "allRecipes is used unguarded in health.js before it is declared "
        "in health-recipes.js. Concatenation order is broken."
    )
