import os
import random
import sys
import time
from pathlib import Path

sys.path.append('..')

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse

from tinyolap.samples.tutor import load
from tinyolap.slice import Slice

db = load()  # load Tutor database

app = FastAPI(title="TinyOlap API")


@app.get("/report", response_class=HTMLResponse)
async def root():
    cube = db.cubes["verkauf"]

    dims = [{"dimension": "datenart", "member": "Ist"},
                          {"dimension": "jahre", "member": "1994"},
                          {"dimension": "monate", "member": "Januar"},
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
async def tinyolaplogo():
    file_name = os.path.join(Path(__file__).resolve().parents[1], "doc", "source", "_logos", "cube256.png")
    return FileResponse(file_name)


@app.get("/")
async def root():
    cubes = list(db.cubes.keys(), )
    dimensions = list(db.dimensions.keys(), )
    return {"message": "TinyOlap",
            "database": db.name,
            "cubes": cubes,
            "dimension": dimensions,
            }
