from typing import Optional
from pydantic import BaseModel, parse_obj_as

from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import lock
from ..dependencies import get_token_header
from ..tiny.setup import server
from ..tiny.setup import random_read, random_write


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
fake_items_db = {"plumbus": {"name": "Plumbus"}, "gun": {"name": "Portal Gun"}}


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
    if item_id not in fake_items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"name": fake_items_db[item_id]["name"], "item_id": item_id}


@router.put("/{item_id}", tags=["custom"], responses={403: {"description": "Operation forbidden"}})
async def update_item(item_id: str):
    if item_id != "plumbus":
        raise HTTPException(
            status_code=403, detail="You can only update the item: plumbus"
        )
    return {"item_id": item_id, "name": "The great Plumbus"}
