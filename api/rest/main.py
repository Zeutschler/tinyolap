# -*- coding: utf-8 -*-
# TinyOlap, copyright (c) 2022 Thomas Zeutschler
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# The TinyOlap api file & folder structure follows the recommendations from fastapi:
# https://fastapi.tiangolo.com/tutorial/bigger-applications/

import uvicorn
from fastapi import Depends, FastAPI

from api.rest.documentation import api_description, tags_metadata

from api.rest.dependencies import get_query_token, get_token_header
from api.rest.internal import admin
from api.rest.routers import databases, cells, users

app = FastAPI(title="TinyOlap api",
              # , dependencies=[Depends(get_query_token)
              description=api_description,
              openapi_tags=tags_metadata,
              version="0.0.1",
              license_info={
                  "name": "MIT",
                  "url": "https://tinyolap.com/docs/license.html",
              })

app.include_router(users.router)
app.include_router(databases.router)
app.include_router(cells.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {"message": "TinyOlap api 1.0"}


if __name__ == "__main__":
    # Note: reload 'true' will allow to reflect changes to Python scripts without restart. Cool!
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
