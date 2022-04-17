# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2021 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import os
import random
import sys
import time
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from tinyolap.slice import Slice
from tinyolap.server import Server

from samples.tutor import load_tutor


# Configure the database and cube to show here...
caching = False  # Switch True / False to enable / disable caching in cubes
db = load_tutor()
cube = db.cubes["Verkauf"]
# ... the following code does not need to be touched. Just run and enjoy...

# TinyOlap setup
sys.path.append('')
db_name = db.name
server = Server()
server.add_database(db)
server[db_name].caching = caching
cube.caching = caching
report_def = None


def render_report(refresh_only: bool = False) -> str:
    # Renders a random report based on the configures database and cube
    cube.reset_counters()
    global report_def
    if not report_def or not refresh_only:
        dims = [{"dimension": dim} for dim in cube.dimension_names]
        random.shuffle(dims)
        for d in range(len(dims)):
            members = db.dimensions[dims[d]["dimension"]].get_members()
            dims[d]["member"] = members[random.randrange(0, len(members))]
        nested_dims_in_rows = random.randrange(1, 2)  # change the 2 to 3 for nested row dimensions
        header_dims = dims[: cube.dimensions_count - 1 - nested_dims_in_rows]
        next_dim = len(header_dims)
        col_members_count = len(cube.get_dimension(dims[next_dim]["dimension"]))
        row_members_count = len(cube.get_dimension(dims[next_dim + 1]["dimension"]))
        column_dims = [{"dimension": dims[len(header_dims)]["dimension"]}]
        row_dims = [{"dimension": d["dimension"]} for d in dims[len(header_dims) + 1:]]
        if (nested_dims_in_rows < 2) and (col_members_count > row_members_count):
            column_dims, row_dims = row_dims, column_dims  # put the dim with more member_defs into the rows]
        report_def = {"title": f"Random report on cube <strong>{cube.name}</strong> "
                               f"from database <strong>{db.name}</strong>",
                      "header": header_dims, "columns": column_dims, "rows": row_dims}
    # Execute the report
    start = time.time()
    random_report = Slice(cube, report_def)
    duration = time.time() - start

    footer = f"\tReport with caching {'ON' if cube.caching else 'OFF'} refreshed in {duration:.6} sec. " \
             f"{cube.counter_cell_requests:,}x cell requests, " \
             f"{cube.counter_aggregations:,}x aggregations calculated and " \
             f"{cube.counter_rule_requests:,}x rules executed."
    return random_report.as_html(footer=footer)


# FastAPI
app = FastAPI(title="TinyOlap API")


@app.get("/", response_class=HTMLResponse)
async def report():
    return render_report(True)


@app.get("/report", response_class=HTMLResponse)
async def report():
    return render_report(True)


@app.get("/nextreport", response_class=HTMLResponse)
async def report():
    return render_report(False)


@app.get("/tinylogo.png")
async def tinyolap_logo():
    file_name = os.path.join(Path(__file__).resolve().parents[1], "doc", "source", "_logos", "logo_white_512.png")
    return FileResponse(file_name)


@app.get("/info", response_class=JSONResponse)
async def root():
    db_list = list({"name": name} for name, db in server._databases.items())
    return {"service": "TinyOlap",
            "version": str(server.Settings.version),
            "databases": db_list,
            }


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
