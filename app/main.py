from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict


class RuntimeInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    version: str


app = FastAPI(
    title="AI Software Engineering Runtime",
    version="0.1.0",
)


@app.get("/", response_model=RuntimeInfo)
def read_runtime_info() -> RuntimeInfo:
    return RuntimeInfo(
        name="AI Software Engineering Runtime",
        version="0.1.0",
    )

