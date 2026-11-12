from fastapi import FastAPI

from routes import api_v1_router

app = FastAPI()

app.include_router(api_v1_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
