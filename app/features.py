from __future__ import annotations

from typing import Any


CORE_ROUTES = [
    "home",
    "panel",
    "login",
    "register",
    "logout",
    "forgot",
    "dashboard",
    "servers",
    "createServer",
    "editServer",
    "account",
    "admin",
    "theme",
    "discord_oauth",
    "banned",
    "HTTPError",
    "api",
]

OPTIONAL_ROUTES = {
    "afkpage": lambda cfg: bool(cfg.get("afk", {}).get("enable", False)),
    "afk_ws": lambda cfg: bool(cfg.get("afk", {}).get("enable", False)),
    "store": lambda cfg: bool(cfg.get("store", {}).get("enable", False)),
    "verify": lambda cfg: bool(cfg.get("mail", {}).get("verifyUser", False)),
}


def enabled_route_modules(config: dict[str, Any]) -> list[str]:
    modules = list(CORE_ROUTES)
    for module_name, is_enabled in OPTIONAL_ROUTES.items():
        if is_enabled(config):
            modules.append(module_name)
    return modules
