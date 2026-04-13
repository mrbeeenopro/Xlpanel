from __future__ import annotations

import importlib
import os
import datetime
from typing import Any

from flask import Flask, request
from flask_sock import Sock
import helper

from .config_loader import load_config
from .features import enabled_route_modules
from .runtime import configure_runtime


def _build_menu_items(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    menu = {
        "Dashboard": {
            "link": "/dashboard",
            "icon": '<i class="fa-solid fa-house"></i>',
        },
        "Server": {
            "link": "/servers",
            "icon": '<i class="fa-solid fa-server"></i>',
        },
        "Store": {
            "link": "/store",
            "icon": '<i class="fa-solid fa-bag-shopping"></i>',
        },
        "Afk": {
            "link": "/afk",
            "icon": '<i class="fa-solid fa-bullseye"></i>',
        },
        "Account": {
            "link": "/account",
            "icon": '<i class="fa-solid fa-user"></i>',
        },
    }

    if not config.get("afk", {}).get("enable", False):
        menu.pop("Afk", None)
    if not config.get("store", {}).get("enable", False):
        menu.pop("Store", None)

    return menu


def _register_routes(config: dict[str, Any]) -> None:
    for module_name in enabled_route_modules(config):
        importlib.import_module(f"routes.{module_name}")


def create_app(config_path: str = "config.json") -> tuple[Flask, dict[str, Any]]:
    config = load_config(config_path)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_dir = os.path.join(project_root, "templates")
    static_dir = os.path.join(project_root, "assets")

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
        static_url_path="/assets",
    )
    sock = Sock(app)
    app.config["SOCK_SERVER_OPTIONS"] = {"ping_interval": 2}
    app.jinja_env.globals.update(list=list, datetime=datetime, request=request, min=min, max=max, int=int, len=len)

    allow_debug = os.environ.get("FLASK_DEBUG", "").strip() == "1"
    flask_debug = bool(config["flask"]["debug"] and allow_debug)

    defaults = {
        "cpu": config["default"]["cpu"],
        "ram": config["default"]["ram"],
        "disk": config["default"]["disk"],
        "slot": config["default"]["slot"],
        "coin": config["default"]["coin"],
    }

    configure_runtime(
        flask_app=app,
        socket=sock,
        loaded_config=config,
        app_name=config["name"],
        version=config["version"],
        app_codename=config["codename"],
        defaults=defaults,
        eggs=config.get("eggs", {}),
        nodes=config.get("locations", {}),
        menu=_build_menu_items(config),
        afk_config=config.get("afk", {}),
        store_config=config.get("store", {}),
    )

    _register_routes(config)

    @app.context_processor
    def inject_site_settings():
        site = helper.get_site_settings()
        return {"site": site, "name": site.get("site_name", config["name"])}

    @app.after_request
    def add_security_headers(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return resp

    runtime_options = {
        "host": config["flask"]["host"],
        "port": config["flask"]["port"],
        "debug": flask_debug,
    }

    return app, runtime_options
