"""TheMealDB random recipe plugin."""

from __future__ import annotations

import html

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import section


RECIPE_URL = "https://www.themealdb.com/api/json/v1/1/random.php"


def _ingredients(meal: dict) -> list[str]:
    result = []
    for index in range(1, 21):
        ingredient = str(meal.get(f"strIngredient{index}") or "").strip()
        measure = str(meal.get(f"strMeasure{index}") or "").strip()
        if ingredient:
            result.append(f"{measure} {ingredient}".strip())
    return result


class RecipePlugin(BasePlugin):
    name = "recipe"
    display_name = "Recipe"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(RECIPE_URL, context.max_retries, context.retry_delay)
            meal = (payload.get("meals") or [])[0]
            data = {
                "name": html.unescape(str(meal["strMeal"])),
                "category": html.unescape(str(meal.get("strCategory") or "")),
                "area": html.unescape(str(meal.get("strArea") or "")),
                "ingredients": _ingredients(meal),
                "instructions": html.unescape(str(meal.get("strInstructions") or "")).strip(),
                "link": str(meal.get("strSource") or meal.get("strYoutube") or "").strip(),
            }
            if not data["name"] or not data["ingredients"] or not data["instructions"]:
                raise ValueError("recipe provider returned incomplete data")
            return FetchResult(ok=True, data=data)
        except Exception as error:
            print(f"  ⚠ Recipe unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict) -> str:
        lines = [data["name"]]
        if data["category"] or data["area"]:
            lines.append(" · ".join(value for value in (data["category"], data["area"]) if value))
        lines.append("Ingredients:")
        lines.extend(f"  - {ingredient}" for ingredient in data["ingredients"])
        lines.append("Instructions:")
        lines.append(data["instructions"])
        if data["link"]:
            lines.append(f"Source: {data['link']}")
        else:
            lines.append(f"Source: {RECIPE_URL}")
        return section("🍽️  RECIPE", "\n".join(lines))
