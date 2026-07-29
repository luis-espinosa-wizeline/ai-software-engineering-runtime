from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from app.github.api import router as github_router


class RuntimeInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str


app = FastAPI(
    title="AI Software Engineering Runtime",
    version="0.1.0",
)
app.include_router(github_router)


@app.get("/", response_model=RuntimeInfo)
def read_runtime_info() -> RuntimeInfo:
    return RuntimeInfo(
        name="AI Software Engineering Runtime",
        version="0.1.0",
    )
