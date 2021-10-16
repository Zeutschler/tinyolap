# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import random
import sys
import time
from pathlib import Path

sys.path.append('..')

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import FileResponse

from tinyolap.slice import Slice
from tinyolap.server import Server

from samples.tutor import load_tutor
from samples.tiny import load_tiny

server = Server()
server.add_database(load_tutor())
server.add_database(load_tiny())

app = FastAPI(title="TinyOlap API")

@app.get("/report", response_class=HTMLResponse)
async def root():
    cube = server["tutor"].cubes["Verkauf"]

    dims = [{"dimension": "datenart", "member": "Ist"},
                          {"dimension": "jahre", "member": "1995"},
                          {"dimension": "monate", "member": "März"},
                          {"dimension": "regionen", "member": "Mitteleuropa"},
                          {"dimension": "produkte", "member": "Produkte gesamt"},
                          {"dimension": "wertart", "member": "Umsatz"}]
    random.shuffle(dims)
    report_definition = {"title": "Random report from Tutor",
                         "header": [dims[0], dims[1], dims[2], dims[3]],
                         "columns": [{"dimension": dims[4]["dimension"]}],
                         "rows": [{"dimension": dims[5]["dimension"]}]}
    start = time.time()
    report = Slice(cube, report_definition)
    duration = time.time() - start
    footer = f"\tReport updated in {duration:.3} sec."
    return report.as_html(footer=footer)


@app.get("/logo.png")
async def tinyolap_logo():
    file_name = os.path.join(Path(__file__).resolve().parents[1], "doc", "source", "_logos", "cube256.png")
    return FileResponse(file_name)


@app.get("/", response_class=JSONResponse)
async def root():
    db_list = list({"name": name} for name, db in server._databases.items())
    return {"service": "TinyOlap",
            "version": str(server.Settings.version),
            "databases": db_list,
            }

@app.get("/databases/{database_id}/cubes")
async def get_cubes(database_id):
    try:
        cube_list = list({"name": cube.name} for cube in server[database_id].cubes.values())
        return {"service": "TinyOlap",
                "version": str(server.Settings.version),
                "database": database_id,
                "cubes": cube_list,
                }
    except Exception as err:
        return {"service": "TinyOlap",
                "version": str(server.Settings.version),
                "error": str(err)
                }

@app.get("/databases/{database_id}/dimensions")
async def get_dimensions(database_id):
    try:
        dim_list = list({"name": dim.name} for dim in server[database_id].dimensions.values())
        return {"service": "TinyOlap",
                "version": str(server.Settings.version),
                "database": database_id,
                "dimensions": dim_list,
                }
    except Exception as err:
        return {"service": "TinyOlap",
                "version": str(server.Settings.version),
                "error": str(err)
                }

@app.get("/databases/{database_id}/dimensions/{dimension_id}")
async def get_dimension(database_id, dimension_id):
    try:
        dim_list = list({"name": dim.name} for dim in server[database_id].dimensions.values())
        return server[database_id].dimensions[dimension_id].to_json()
    except Exception as err:
        return {"service": "TinyOlap",
                "version": str(server.Settings.version),
                "error": str(err)
                }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)