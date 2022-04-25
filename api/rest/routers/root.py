from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root():
    return {"message": "TinyOlap REST API 1.0"}