from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from ..dependencies import lock
from ..tiny.catalog import catalog
from ..tiny.initialization import server


router = APIRouter(
    prefix="/databases",
    tags=["databases"],
    responses={404: {"description": "Not found"}},
)


@router.get("/", response_class=JSONResponse)
async def get_databases():
    """Returns the list of databases provided through the current TinyOlap API instance."""
    try:
        return JSONResponse(content={"databases": [{"id": server.databases[db].name,
                               "description": server.databases[db].description,
                               "in_memory": server.databases[db].in_memory} for db in server.databases]},
                             status_code=200)

    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))


@router.get("/{database_id}", response_class=JSONResponse)
async def get_database_info(database_id: str):
    """Returns the list of cubes and dimensions defined in a specific database.
     :param database_id: id (the name) of the database to return.
    """
    try:
        if database_id in server.databases:
            database = server[database_id]
            with lock[database].gen_rlock():
                return JSONResponse(catalog(db=server.databases[database_id], full_catalog=False),
                                    status_code=200)
        else:
            raise HTTPException(status_code=404, detail=f"TinyOlap database_id '{database_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))


@router.get("/{database_id}/catalog", response_class=JSONResponse)
async def get_database_catalog(database_id: str):
    """Returns the catalog of a specific database, containing all relevant meta and
    master data, including members of dimension and rules."""
    try:
        if database_id in server.databases:
            database = server[database_id]
            with lock["db"].gen_rlock():
                return JSONResponse(content=catalog(db=server.databases[database_id], full_catalog=True),
                                    status_code=200)
        else:
            raise HTTPException(status_code=404, detail=f"TinyOlap database_id '{database_id}' not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error. " + str(e))
