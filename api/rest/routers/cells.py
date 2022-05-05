from typing import Optional
from pydantic import BaseModel, parse_obj_as

from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import lock
from ..dependencies import get_token_header
from ..tiny.initialization import server
from ..tiny.api import random_read, random_write


class CellAddress(BaseModel):
    database: str
    cube: str
    members: list[str]


router = APIRouter(
    prefix="/cells",
    tags=["cells"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def resolve_read():
    database = server["db"]
    try:
        with lock["db"].gen_rlock():
            db, cube, address, value = random_read(database)
            result = {"db": db,
                      "cube": cube,
                      "address": address,
                      "value": value
                      }
            return result
    except Exception as e:
        raise HTTPException(status_code=404, detail="Item not found. " + str(e))



@router.put("/")
async def resolve_write():
    database = server["db"]
    try:
        with lock["db"].gen_wlock():
            db, cube, address, value = random_write(database)
            result = {"db": db,
                      "cube": cube,
                      "address": address,
                      "value": value
                      }
            return result
    except Exception as e:
        raise HTTPException(status_code=404, detail="Item not found. " + str(e))


@router.get("/{item_id}")
async def read_item(item_id: str):
    return {"name": item_id, "item_id": item_id}
