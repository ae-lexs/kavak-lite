from fastapi import FastAPI

app = FastAPI(title="kavak-lite")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
