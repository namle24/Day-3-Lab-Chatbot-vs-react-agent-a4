import sys
import os
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.tools.vehicle_lookup import lookup_vehicle
import json

res1 = lookup_vehicle("giá xe VF3 ?")
print("--- QUERY: giá xe VF3 ? ---")
for r in res1.get("results", []):
    print(f"Score: {r['score']}, Title: {r['title']}, Models: {r['models']}, Snippet: {r['snippet'][:150]}")

