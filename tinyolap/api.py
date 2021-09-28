from fastapi import FastAPI
from settings import Settings

app = FastAPI()

@app.get("/")
async def root():
    return {"message": f"TinyOlap", "version": Settings.version}

@app.get("/")
async def root():
    pass