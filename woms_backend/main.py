from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend_core import init_db
from api_routes import router

app = FastAPI(title="WOMS Weather Observation Portal Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()
app.include_router(router)
