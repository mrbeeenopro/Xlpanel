from __future__ import annotations

from flask import *  # noqa: F401,F403
from werkzeug.exceptions import HTTPException

import datetime

import helper
import sendmail


app = None
sock = None
config = {}
name = ""
ver = ""
codename = ""
dft = {}
eggsList = {}
nodeList = {}
menuItems = {}
afk = {}
store = {}

def _sanitize_eggs(raw_eggs):
    cleaned = {}
    if not isinstance(raw_eggs, dict):
        return cleaned
    for key, value in raw_eggs.items():
        if not isinstance(value, dict):
            continue
        name_value = value.get("name")
        info_value = value.get("info")
        if not isinstance(name_value, str):
            continue
        if not isinstance(info_value, dict):
            continue
        cleaned[str(key)] = value
    return cleaned

def _sanitize_nodes(raw_nodes):
    cleaned = {}
    if not isinstance(raw_nodes, dict):
        return cleaned
    for key, value in raw_nodes.items():
        if not isinstance(value, dict):
            continue
        if not isinstance(value.get("name"), str):
            continue
        cleaned[str(key)] = value
    return cleaned


def configure_runtime(
    *,
    flask_app,
    socket,
    loaded_config,
    app_name,
    version,
    app_codename,
    defaults,
    eggs,
    nodes,
    menu,
    afk_config,
    store_config,
):
    global app, sock, config, name, ver, codename, dft, eggsList, nodeList, menuItems, afk, store

    app = flask_app
    sock = socket
    config = loaded_config
    name = app_name
    ver = version
    codename = app_codename
    dft = defaults
    eggsList = _sanitize_eggs(eggs)
    nodeList = _sanitize_nodes(nodes)
    menuItems = menu
    afk = afk_config
    store = store_config
