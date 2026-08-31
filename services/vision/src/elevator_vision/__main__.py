import uvicorn
from elevator_vision import config

if __name__ == "__main__":
    uvicorn.run("elevator_vision.api:app", host=config.API_HOST, port=config.API_PORT, reload=False)
