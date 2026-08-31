import os
import uvicorn
if __name__ == "__main__":
    uvicorn.run("elevator_gateway.app:app",host=os.getenv("API_HOST","0.0.0.0"),port=int(os.getenv("API_PORT","8000")),reload=False)
