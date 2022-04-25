from typing import Optional
from pydantic import BaseModel, parse_obj_as

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from ..dependencies import lock
from ..dependencies import get_token_header
from ..tiny.initialization import server
from ..tiny.api import random_read, random_write, create_view

router = APIRouter(prefix="/views", tags=["views"],
                   # dependencies=[Depends(get_token_header)],
                   responses={404: {"description": "Not found"}},
                   )


@router.get("/", response_class=JSONResponse)
async def resolve_read():
    database = server["TinyCorp"]
    try:
        with lock[database].gen_rlock():
            view = create_view(database.cubes["pnl"])
            view.refresh()
            return JSONResponse(
                content=view.to_dict(),  #.to_json(indent=4),
                status_code=200)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Item not found. " + str(e))


@router.get("/{view_id}")
async def read_item(view_id: str):
    return {"name": view_id, "view_id": view_id}


@router.post("/{view_id}")
async def read_item(view_id: str):
    return {"name": view_id, "view_id": view_id}
