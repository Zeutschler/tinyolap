import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from fastapi.responses import FileResponse
from api.rest.tiny.initialization import TINYOLAP_API_VERSION

router = APIRouter()


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root():
    return root_page(TINYOLAP_API_VERSION)


@router.get("/logo.png", response_class=FileResponse, include_in_schema=False)
async def tinyolap_logo():
    file_name = os.path.join(Path(__file__).resolve().parents[1], "static", "logo.png")
    return FileResponse(file_name)


@router.get("/icon.png", response_class=FileResponse, include_in_schema=False)
async def tinyolap_logo():
    file_name = os.path.join(Path(__file__).resolve().parents[1], "static", "icon.png")
    return FileResponse(file_name)


def root_page(version: str):
    return '<!DOCTYPE html><html><head><title>TinyOlap API</title>' \
           '<link href="icon.png" rel="icon" type="image/x-icon">' \
           '<style>' \
           'div { overflow: hidden; }' \
           '#parent {width: 336px;height: 96px; position:absolute; flex-direction: column; display: flex; ' \
           'justify-content: center;align-items: center;height: 90%;width: 95%;}' \
           '#logo{width: 336;height: 64px;}' \
           '#version{position:relative;font-family: Arial;font-size: 20px;}' \
           '#links{position:relative;font-family: Arial;font-size: 14px;justify-content: center;align-items: center;}' \
           '</style></head><body>' \
           '<div id="parent"><div id="logo"><img src="logo.png" alt="TinyOlap logo"></div>' \
           '<div id="version">Version ' + version + '<div>' \
           '<div id="links">...view <a href="/docs">TinyOlap OpenAPI documentation</a><div>' \
           '<div id="links"><a href="/views/random">random view (json)</a>, <a href="/views/random/html">random view (html)</a><div>' \
           '</div></body></html>'
