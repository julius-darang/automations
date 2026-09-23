"""TheCocktailDB random cocktail plugin."""

from __future__ import annotations

import html

from .base import BasePlugin, FetchResult, PluginContext
from .formatting import section


COCKTAIL_URL = "https://www.thecocktaildb.com/api/json/v1/1/random.php"


def _ingredients(drink: dict) -> list[str]:
    result = []
    for index in range(1, 16):
        ingredient = str(drink.get(f"strIngredient{index}") or "").strip()
        measure = str(drink.get(f"strMeasure{index}") or "").strip()
        if ingredient:
            result.append(f"{measure} {ingredient}".strip())
    return result


class CocktailPlugin(BasePlugin):
    name = "cocktail"
    display_name = "Cocktail"

    def fetch(self, context: PluginContext) -> FetchResult:
        try:
            payload = context.fetch_json(COCKTAIL_URL, context.max_retries, context.retry_delay)
            drink = (payload.get("drinks") or [])[0]
            data = {
                "name": html.unescape(str(drink["strDrink"])),
                "category": html.unescape(str(drink.get("strCategory") or "")),
                "glass": html.unescape(str(drink.get("strGlass") or "")),
                "alcoholic": html.unescape(str(drink.get("strAlcoholic") or "")),
                "ingredients": _ingredients(drink),
                "instructions": html.unescape(str(drink.get("strInstructions") or "")).strip(),
            }
            if not data["name"] or not data["ingredients"] or not data["instructions"]:
                raise ValueError("cocktail provider returned incomplete data")
            return FetchResult(ok=True, data=data)
        except Exception as error:
            print(f"  ⚠ Cocktail unavailable: {error}")
            return FetchResult(ok=False, error=str(error))

    def render(self, data: dict) -> str:
        lines = [data["name"]]
        metadata = [value for value in (data["category"], data["alcoholic"], data["glass"]) if value]
        if metadata:
            lines.append(" · ".join(metadata))
        lines.append("Ingredients:")
        lines.extend(f"  - {ingredient}" for ingredient in data["ingredients"])
        lines.append("Instructions:")
        lines.append(data["instructions"])
        lines.append(f"Source: {COCKTAIL_URL}")
        return section("🍸  COCKTAIL", "\n".join(lines))
