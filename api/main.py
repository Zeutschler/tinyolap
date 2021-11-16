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

# TinyOlap
server = Server()
server.add_database(load_tutor())
server.add_database(load_tiny())

caching = False  # Switch True / False to enable / disable caching in cubes
server["tutor"].caching = caching
server["tutor"].cubes["Verkauf"].caching = caching
report_def = None


def render_report(refresh_only: bool= False) -> str:
    # Renders a random report
    cube = server["tutor"].cubes["Verkauf"]
    cube.reset_counters()
    global report_def
    if not report_def or not refresh_only:
        dims = [{"dimension": "datenart"}, {"dimension": "jahre"}, {"dimension": "monate"},
                {"dimension": "regionen"}, {"dimension": "produkte"}, {"dimension": "wertart"}]
        random.shuffle(dims)
        for d in range(len(dims)):
            members = server["tutor"].dimensions[dims[d]["dimension"]].get_members()
            dims[d]["member"] = members[random.randrange(0, len(members))]
        nested_dims_in_rows = random.randrange(1, 2)  # change 2 to 3 for nested row dimensions
        header_dims = dims[: 6 - 1 - nested_dims_in_rows]
        column_dims = [{"dimension": dims[len(header_dims)]["dimension"]}]
        row_dims = [{"dimension": d["dimension"]} for d in dims[len(header_dims) + 1:]]
        report_def = {"title": f"Random Report from Tutor Database (caching is {str(cube.caching)})",
                             "header": header_dims, "columns": column_dims, "rows": row_dims}
    # Execute the report
    start = time.time()
    report = Slice(cube, report_def)
    duration = time.time() - start
    footer = f"\tReport refreshed in {duration:.6} sec. {cube.counter_cell_requests:,}x cell requests, " \
             f"{cube.counter_aggregations:,}x aggregations calculated and " \
             f"{cube.counter_rule_requests:,}x rules executed."
    return report.as_html(footer=footer)


# FastAPI
app = FastAPI(title="TinyOlap API")


@app.get("/report", response_class=HTMLResponse)
async def report():
    return render_report(True)

@app.get("/nextreport", response_class=HTMLResponse)
async def report():
    return render_report(False)


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
        return server[database_id].dimensions[dimension_id]._to_json()
    except Exception as err:
        return {"service": "TinyOlap",
                "version": str(server.Settings.version),
                "error": str(err)
                }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
