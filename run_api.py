#!/usr/bin/env python3
"""Start VinFast backend API: uvicorn run_api:app --reload"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
