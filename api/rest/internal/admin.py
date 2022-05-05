from fastapi import APIRouter


router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)


@router.post("/")
async def update_admin():
    return {"message": "Admin getting schwifty"}