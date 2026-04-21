import uvicorn

from app import config


if __name__ == "__main__":
    uvicorn.run("app.api:app", host=config.API_HOST, port=config.API_PORT, reload=False)
