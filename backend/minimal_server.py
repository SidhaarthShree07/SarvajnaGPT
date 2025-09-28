from fastapi import FastAPI
import uvicorn

from automation_router import router as automation_router

app = FastAPI()
app.include_router(automation_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)