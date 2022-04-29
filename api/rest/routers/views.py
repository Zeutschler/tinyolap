import random
from typing import Optional
from pydantic import BaseModel, parse_obj_as

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from ..dependencies import lock
from ..dependencies import get_token_header
from ..tiny.initialization import server
from ..tiny.initialization import *
from ..tiny.api import random_read, random_write, create_view


view_counter = 0

router = APIRouter(prefix="/views", tags=["views"],
                   # dependencies=[Depends(get_token_header)],
                   responses={404: {"description": "Not found"}},
                   )


@router.get("/", response_class=JSONResponse)
async def resolve_read():
    database = server["TinyCorp"]
    try:
        with lock[database].gen_rlock():
            view = create_view(database.cubes["pnl"], random_view=True)
            view.refresh()
            return JSONResponse(
                content=view.to_dict(), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Error. " + str(e))


@router.get("/random", response_class=JSONResponse)
async def resolve_random_view():
    """Returns a random view (report) from the supplied sample database in JSON format.
    You can also view the result as a simple static HTML representation by using .../views/random/html"""
    database = server["TinyCorp"]
    try:
        with lock[database].gen_rlock():
            random_cube = random.choice(database.cubes)
            view = create_view(database.cubes[random_cube], random_view=True).refresh()
            view.zero_suppression_on_rows = True
            return JSONResponse(content=view.to_dict(), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Error. " + str(e))

@router.get("/random/html", response_class=HTMLResponse)
async def resolve_random_html_view():
    """Returns a random view (report) from the supplied sample database in simple static HTML format.
    You can also view the result as a JSON representation by using .../views/random"""
    database = server["TinyCorp"]
    try:
        with lock[database].gen_rlock():
            random_cube = random.choice(database.cubes)
            view = create_view(database.cubes[random_cube], random_view=True).refresh()
            view.zero_suppression_on_rows = True
            return HTMLResponse(content=view.to_html(), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Error. " + str(e))

@router.get("/random/html/endless", response_class=HTMLResponse)
async def resolve_random_html_endless_view():
    """FOR TESTING PURPOSES ONLY - Returns a random view (report) from the supplied sample database
    in simple static HTML format. Directly after loading the report will reload."""
    database = server["TinyCorp"]
    global view_counter
    try:
        with lock[database].gen_rlock():
            view_counter += 1
            random_cube = random.choice(database.cubes)
            view = create_view(database.cubes[random_cube], random_view=True,
                               title=f"Random view #{view_counter:,} (endless loop) ").refresh()
            view.zero_suppression_on_rows = True
            return HTMLResponse(content=view.to_html(endless_loop=True), status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal Error. " + str(e))


@router.get("/{view_id}")
async def read_item(view_id: str):
    return {"name": view_id, "view_id": view_id}


@router.post("/{view_id}")
async def read_item(view_id: str):
    return {"name": view_id, "view_id": view_id}
