# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# Note: The TinyOlap REST API file & folder structure follows the recommendations from fastapi:
# see https://fastapi.tiangolo.com/tutorial/bigger-applications/ for further details.

import uvicorn
from fastapi import Depends, FastAPI
from api.rest.documentation import api_description, tags_metadata
from api.rest.dependencies import get_query_token, get_token_header
from api.rest.internal import admin
from api.rest.routers import root, databases, views, cells, users
from api.rest.tiny.initialization import setup, TINYOLAP_API_VERSION


# FastAPI initialization
app = FastAPI(title="TinyOlap API",
              # , dependencies=[Depends(get_query_token)
              description=api_description,
              terms_of_service="https://tinyolap.com/terms.html",
              openapi_tags=tags_metadata,
              version=TINYOLAP_API_VERSION,
              license_info={"name": "MIT License", "url": "https://tinyolap.com/docs/license.html",}
              )

app.include_router(root.router)
app.include_router(users.router)
app.include_router(databases.router)
app.include_router(cells.router)
app.include_router(views.router)
app.include_router(admin.router)


@app.on_event("startup")
async def startup_event():
    # TinyOlap server initialization
    setup("medium")  # "large", "medium", "small"


if __name__ == "__main__":

    # Note: reload 'true' will allows real-time changes to the running Python scripts. Very Cool!
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

