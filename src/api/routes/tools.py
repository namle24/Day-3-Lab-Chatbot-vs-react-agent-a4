from fastapi import APIRouter, Query

from src.tools import calculator, vehicle_lookup, reviews_search
from src.tools.registry import get_tool_specs

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.get("/specs")
def list_tool_specs():
    return {"tools": get_tool_specs()}


@router.get("/lookup")
def tool_lookup(query: str = Query(...), top_k: int = 4):
    return vehicle_lookup.lookup_vehicle(query, top_k=top_k)


@router.get("/compare")
def tool_compare(model_a: str = "VF5", model_b: str = "VF6"):
    return vehicle_lookup.compare_vehicles(model_a, model_b)


@router.get("/calculate")
def tool_calculate(expression: str):
    return calculator.calculate(expression)


@router.get("/reviews")
def tool_reviews(query: str, car_model: str | None = None):
    return reviews_search.search_reviews(query, car_model)
