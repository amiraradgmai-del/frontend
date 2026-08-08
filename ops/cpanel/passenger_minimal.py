from a2wsgi import ASGIMiddleware
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok"}


application = ASGIMiddleware(app, wait_time=2.0)
