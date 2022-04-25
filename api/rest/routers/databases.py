from typing import Optional
from pydantic import BaseModel, parse_obj_as

from fastapi import APIRouter, Depends, HTTPException
from ..dependencies import lock
from ..tiny.catalog import catalog
from ..tiny.initialization import server

from tinyolap.database import Database

router = APIRouter(
    prefix="/databases",
    tags=["databases"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def get_databases():
    """Returns the list of available databases."""
    try:
        # Locking on server (hopefully) not required. >>>  with lock["@"].gen_rlock():
        return {"databases": [{"id": server.databases[db].name,
                               "description": server.databases[db].description,
                               "in_memory": server.databases[db].in_memory} for db in server.databases]}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))


@router.get("/{database_id}")
async def get_database_info(database_id: str):
    """Returns the list of cubes and dimensions available in a specific database."""
    try:
        with lock["db"].gen_rlock():
            if database_id not in server.databases:
                HTTPException(status_code=404, detail="Database not found")
            return catalog(db=server.databases[database_id], full_catalog=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))

@router.get("/{database_id}/catalog}")
async def get_database_catalog(database_id: str):
    """Returns the catalog of a specific database, containing all relevant meta and
    master data, including members of dimension and rules."""
    try:
        with lock["db"].gen_rlock():
            if database_id not in server.databases:
                HTTPException(status_code=404, detail="Database not found")
            return catalog(db=server.databases[database_id], full_catalog=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))
