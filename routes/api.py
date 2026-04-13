# type: ignore
from app.runtime import *

import db
import ende
import sendmail
import time
import random

from flask import jsonify

_chr = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0987654321"


def _json_error(message, code=400):
    return jsonify({"ok": False, "error": message}), code


def _payload():
    data = request.get_json(silent=True)
    if isinstance(data, dict):
        return data
    return request.form.to_dict()


def _public_eggs(raw_eggs):
    safe = {}
    if not isinstance(raw_eggs, dict):
        return safe
    for key, value in raw_eggs.items():
        if not isinstance(value, dict):
            continue
        name_value = value.get("name")
        if not isinstance(name_value, str):
            continue
        safe[str(key)] = {"name": name_value}
    return safe


def _public_nodes(raw_nodes):
    safe = {}
    if not isinstance(raw_nodes, dict):
        return safe
    for key, value in raw_nodes.items():
        if not isinstance(value, dict):
            continue
        name_value = value.get("name")
        if not isinstance(name_value, str):
            continue
        safe[str(key)] = {"name": name_value}
    return safe


def _require_auth():
    check = helper.chSID(request.cookies.get("sid"))
    if not check[0]:
        return (False, _json_error("Unauthorized.", 401))
    return (True, check[1])


def _require_admin(user):
    u_dt = helper.checkPteroUser(user)
    if (not u_dt[0]) or (not u_dt[1].get("root_admin", False)):
        return (False, _json_error("Forbidden.", 403))
    return (True, u_dt[1])


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"ok": True, "name": name, "version": ver, "codename": codename})


@app.route("/api/public/config", methods=["GET"])
def api_public_config():
    return jsonify(
        {
            "ok": True,
            "name": name,
            "features": {
                "store": bool(store.get("enable", False)),
                "afk": bool(afk.get("enable", False)),
                "verifyUser": bool(config.get("mail", {}).get("verifyUser", False)),
            },
            "turnstile": {
                "enable": bool(config.get("cf_turnstile", {}).get("enable", False)),
                "site_key": config.get("cf_turnstile", {}).get("site_key", ""),
            },
            "menu": menuItems,
        }
    )


@app.route("/api/auth/session", methods=["GET"])
def api_auth_session():
    check = helper.chSID(request.cookies.get("sid"))
    if not check[0]:
        return jsonify({"ok": True, "authenticated": False})

    u_dt = helper.checkPteroUser(check[1]["user"])
    is_admin = bool(u_dt[0] and u_dt[1].get("root_admin", False))

    return jsonify(
        {
            "ok": True,
            "authenticated": True,
            "user": {
                "user": check[1]["user"],
                "email": check[1]["email"],
                "coin": check[1]["coin"],
                "slot": check[1]["slot"],
                "cpu": check[1]["cpu"],
                "ram": check[1]["ram"],
                "disk": check[1]["disk"],
                "isAdmin": is_admin,
            },
        }
    )


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = _payload()
    user = str(data.get("user", "")).strip()
    passwd = data.get("passwd")

    if (not user) or (not passwd):
        return _json_error("Missing data.")

    cf_token = data.get("cf-turnstile-response") or data.get("cf_token")
    cf_ip = request.headers.get("CF-Connecting-IP")
    e = helper.cf_check(cf_token, cf_ip)
    if not e[0]:
        return _json_error("Invalid captcha.")

    check = helper.login(user, passwd)
    if check[0]:
        resp = jsonify({"ok": True})
        helper.set_auth_cookie(resp, check[1], request)
        return resp

    if check[1] == "verify":
        return jsonify({"ok": False, "error": "verify", "user": check[2]}), 403
    if check[1] == "banned":
        return jsonify({"ok": False, "error": "banned"}), 403
    return _json_error(str(check[1]), 403)


@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    data = _payload()
    user = str(data.get("user", "")).replace(" ", "")
    passwd = data.get("passwd")
    cpasswd = data.get("cpasswd")
    email = data.get("email")

    if (not user) or (not passwd) or (not cpasswd) or (not email):
        return _json_error("Missing data.")

    cf_token = data.get("cf-turnstile-response") or data.get("cf_token")
    cf_ip = request.headers.get("CF-Connecting-IP")
    e = helper.cf_check(cf_token, cf_ip)
    if not e[0]:
        return _json_error("Invalid captcha.")

    if (not helper.chMX(email.split("@")[::-1][0])) and (config["mail"]["verifyUser"]):
        return _json_error("Invalid email domain.")

    if passwd != cpasswd:
        return _json_error("Password confirmation failed.")

    created = helper.register(user, passwd, email, dft["cpu"], dft["ram"], dft["disk"], dft["slot"], dft["coin"])
    if not created[0]:
        return _json_error(str(created[1]))

    return jsonify({"ok": True})


@app.route("/api/auth/verify", methods=["POST"])
def api_auth_verify():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    data = _payload()
    code = data.get("code")
    user = data.get("user")
    if (not code) or (not user):
        return _json_error("Missing data.")

    check = helper.checkVcode(user, code)
    if not check[0]:
        return _json_error(str(check[1]))

    resp = jsonify({"ok": True})
    helper.set_auth_cookie(resp, check[1], request)
    return resp


@app.route("/api/auth/forgot", methods=["POST"])
def api_auth_forgot():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    data = _payload()
    email = str(data.get("email", "")).strip()
    if (not email) or ("@" not in email):
        return jsonify({"ok": True})

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("select lastSend from user where email=?", (email,))
    e = cursor.fetchall()
    if len(e) == 0:
        conn.close()
        return jsonify({"ok": True})

    if e[0][0] > time.time() - 3600:
        conn.close()
        return jsonify({"ok": True})

    nw = "".join(random.choice(_chr) for _ in range(random.randint(10, 15)))
    sent = sendmail.sendrspwd(email, nw)
    if sent[0]:
        cursor.execute("update user set password=?, lastSend=? where email=?", (ende.encode(nw), int(time.time()), email))
        conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    helper.logout(request.cookies.get("sid"))
    resp = jsonify({"ok": True})
    helper.clear_auth_cookie(resp, request)
    return resp


@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    ok, auth = _require_auth()
    if not ok:
        return auth

    u_sv = helper.listPteroServer(auth["user"])
    u_dt = helper.checkPteroUser(auth["user"])
    if (not u_sv[0]) or (not u_dt[0]):
        return _json_error("Cannot load dashboard.", 502)

    return jsonify(
        {
            "ok": True,
            "isAdmin": u_dt[1].get("root_admin", False),
            "user": auth["user"],
            "coin": auth["coin"],
            "resources": {
                "cpu": {"available": auth["cpu"] - u_sv[2], "total": auth["cpu"]},
                "ram": {"available": auth["ram"] - u_sv[4], "total": auth["ram"]},
                "disk": {"available": auth["disk"] - u_sv[3], "total": auth["disk"]},
                "slot": {"available": auth["slot"] - len(u_sv[1]), "total": auth["slot"]},
            },
            "servers": u_sv[1],
        }
    )


@app.route("/api/servers", methods=["GET", "POST"])
def api_servers():
    ok, auth = _require_auth()
    if not ok:
        return auth

    if request.method == "GET":
        # Auto-heal missing panel account for users that exist locally but not in Calagopus yet.
        ensured = helper.ensurePteroUser(auth["user"])
        if not ensured[0]:
            return _json_error(str(ensured[1]), 502)

        u_sv = helper.listPteroServer(auth["user"])
        u_dt = helper.checkPteroUser(auth["user"])
        if (not u_sv[0]) or (not u_dt[0]):
            return _json_error("Cannot load servers.", 502)
        r_nodes = helper.get_runtime_nodes()
        r_eggs = helper.get_runtime_eggs()
        nodes_payload = r_nodes[1] if r_nodes[0] else nodeList
        eggs_payload = r_eggs[1] if r_eggs[0] else eggsList
        return jsonify(
            {
                "ok": True,
                "servers": u_sv[1],
                "eggs": _public_eggs(eggs_payload),
                "nodes": _public_nodes(nodes_payload),
                "isAdmin": u_dt[1].get("root_admin", False),
            }
        )

    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    data = _payload()
    name_value = str(data.get("name", "")).strip()
    cpu = str(data.get("cpu", ""))
    ram = str(data.get("ram", ""))
    disk = str(data.get("disk", ""))
    node = str(data.get("node", ""))
    egg = str(data.get("egg", ""))

    if not name_value:
        return _json_error("Missing name.")
    if (not cpu.isdigit()) or (not ram.isdigit()) or (not disk.isdigit()):
        return _json_error("Invalid data type.")
    if (int(cpu) == 0) or (int(ram) == 0) or (int(disk) == 0):
        return _json_error("Invalid limits.")

    created = helper.createPteroServer(name_value, auth["user"], node, egg, int(cpu), int(ram), int(disk))
    if not created[0]:
        return _json_error(str(created[1]))
    return jsonify({"ok": True})


@app.route("/api/servers/<identity>", methods=["GET", "PATCH", "DELETE"])
def api_server_detail(identity: str):
    ok, auth = _require_auth()
    if not ok:
        return auth

    u_sv = helper.listPteroServer(auth["user"])
    if not u_sv[0]:
        return _json_error("Cannot load servers.", 502)

    current = None
    for item in u_sv[1]:
        if item["identifier"] == identity:
            current = item
            break

    if current is None:
        return _json_error("Server not found or no permission.", 404)

    if request.method == "GET":
        return jsonify({"ok": True, "server": current})

    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    if request.method == "DELETE":
        if current.get("status") == "suspended":
            return _json_error("This server has been suspended.")
        deleted = helper.delPteroServer(current["id"])
        if not deleted[0]:
            return _json_error(str(deleted[1]))
        return jsonify({"ok": True})

    data = _payload()
    cpu = str(data.get("cpu", ""))
    ram = str(data.get("ram", ""))
    disk = str(data.get("disk", ""))

    if (not cpu.isdigit()) or (not ram.isdigit()) or (not disk.isdigit()):
        return _json_error("Invalid data type.")
    if (int(cpu) == 0) or (int(ram) == 0) or (int(disk) == 0):
        return _json_error("Invalid limits.")

    edited = helper.editPteroServer(auth["user"], identity, int(cpu), int(ram), int(disk))
    if not edited[0]:
        return _json_error(str(edited[1]))
    return jsonify({"ok": True})


@app.route("/api/servers/<identity>/power", methods=["POST"])
def api_server_power(identity: str):
    ok, auth = _require_auth()
    if not ok:
        return auth
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    u_sv = helper.listPteroServer(auth["user"])
    if not u_sv[0]:
        return _json_error("Cannot load servers.", 502)

    current = None
    for item in u_sv[1]:
        if item["identifier"] == identity:
            current = item
            break
    if current is None:
        return _json_error("Server not found or no permission.", 404)

    data = _payload()
    action = str(data.get("action", "")).strip().lower()
    if action not in ("start", "stop", "restart", "kill"):
        return _json_error("Invalid power action.")

    server_ref = str(current.get("uuid") or current.get("id") or "")
    if not server_ref:
        return _json_error("Server reference not found.", 400)

    powered = helper.powerPteroServer(server_ref, action)
    if not powered[0]:
        return _json_error(str(powered[1]))

    latest = helper.getPteroServerStatus(server_ref)
    return jsonify({"ok": True, "status": latest[1] if latest[0] else current.get("status", "unknown")})


@app.route("/api/servers/<identity>/status", methods=["GET"])
def api_server_status(identity: str):
    ok, auth = _require_auth()
    if not ok:
        return auth

    u_sv = helper.listPteroServer(auth["user"])
    if not u_sv[0]:
        return _json_error("Cannot load servers.", 502)

    current = None
    for item in u_sv[1]:
        if item["identifier"] == identity:
            current = item
            break
    if current is None:
        return _json_error("Server not found or no permission.", 404)

    server_ref = str(current.get("uuid") or current.get("id") or "")
    if not server_ref:
        return _json_error("Server reference not found.", 400)

    latest = helper.getPteroServerStatus(server_ref)
    if not latest[0]:
        return jsonify({"ok": True, "status": current.get("status", "unknown")})
    return jsonify({"ok": True, "status": latest[1]})


@app.route("/api/account", methods=["GET"])
def api_account():
    ok, auth = _require_auth()
    if not ok:
        return auth

    u_dt = helper.checkPteroUser(auth["user"])
    if not u_dt[0]:
        return _json_error("Cannot load account.", 502)

    return jsonify(
        {
            "ok": True,
            "user": auth["user"],
            "email": auth["email"],
            "coin": auth["coin"],
            "discord_link": helper.get_site_settings().get("discord_link", ""),
            "isAdmin": u_dt[1].get("root_admin", False),
        }
    )


@app.route("/api/account/password", methods=["POST"])
def api_account_password():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    ok, auth = _require_auth()
    if not ok:
        return auth

    data = _payload()
    crpwd = str(data.get("crpasswd", ""))
    nwpwd = str(data.get("nwpasswd", ""))
    cnwpwd = str(data.get("cnwpasswd", ""))

    if (not crpwd) or (not nwpwd) or (not cnwpwd):
        return _json_error("Missing data.")
    if nwpwd != cnwpwd:
        return _json_error("Please confirm your new password.")
    if not ende.checkpw(auth["pwd"], crpwd):
        return _json_error("Invalid current password.")
    if crpwd == nwpwd:
        return _json_error("New password must be different.")
    if len(nwpwd) < 8:
        return _json_error("Password too short.")

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("update user set password=? where user=?", (ende.encode(nwpwd), auth["user"]))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/account/ptero/reset", methods=["POST"])
def api_account_ptero_reset():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    ok, auth = _require_auth()
    if not ok:
        return auth

    e = helper.checkPteroUser(auth["user"])
    e = helper.getPteroPasswd(e)
    if e[0]:
        return jsonify({"ok": True, "passwd": e[1]})
    return _json_error(str(e[1]))


@app.route("/api/store", methods=["GET", "POST"])
def api_store():
    if not store.get("enable", False):
        return _json_error("Store is disabled.", 404)

    ok, auth = _require_auth()
    if not ok:
        return auth

    if request.method == "GET":
        return jsonify({"ok": True, "coin": auth["coin"], "store": store})

    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    data = _payload()
    item = data.get("item")
    amount = str(data.get("amount", ""))

    if item not in ["cpu", "ram", "disk", "slot"]:
        return _json_error("Invalid item.")
    if not amount.isdigit():
        return _json_error("Invalid data type.")

    amount_i = int(amount)
    if amount_i <= 0 or amount_i > 1000:
        return _json_error("Invalid amount.")
    if (store[item][0] * amount_i) > auth["coin"]:
        return _json_error("Not enough coins.")

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute(f"update user set {item}={item}+? where user=?", (store[item][1] * amount_i, auth["user"]))
    cursor.execute("update user set coin=coin-? where user=?", (store[item][0] * amount_i, auth["user"]))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/admin/users", methods=["GET"])
def api_admin_users():
    ok, auth = _require_auth()
    if not ok:
        return auth

    admin_ok, admin_result = _require_admin(auth["user"])
    if not admin_ok:
        return admin_result

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("select user, coin, cpu, disk, ram, banned, email, verified from user")
    users = cursor.fetchall()
    conn.close()

    return jsonify({"ok": True, "users": users, "isAdmin": admin_result.get("root_admin", False)})


@app.route("/api/admin/add", methods=["POST"])
def api_admin_add():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    ok, auth = _require_auth()
    if not ok:
        return auth

    admin_ok, admin_result = _require_admin(auth["user"])
    if not admin_ok:
        return admin_result

    data = _payload()
    user = str(data.get("user", ""))

    def _to_int(name):
        try:
            return int(data.get(name, 0) or 0)
        except Exception:
            return 0

    cpu = _to_int("cpu")
    ram = _to_int("ram")
    disk = _to_int("disk")
    slot = _to_int("slot")
    coin = _to_int("coin")

    u = helper.getUser(user)
    if not u[0]:
        return _json_error("User not found.", 404)

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("update user set cpu=cpu+?, ram=ram+?, disk=disk+?, slot=slot+?, coin=coin+? where user=?", (cpu, ram, disk, slot, coin, user))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/admin/ban", methods=["POST"])
def api_admin_ban():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    ok, auth = _require_auth()
    if not ok:
        return auth

    admin_ok, admin_result = _require_admin(auth["user"])
    if not admin_ok:
        return admin_result

    data = _payload()
    user = str(data.get("user", ""))
    if not user:
        return _json_error("Missing user.")
    if auth["user"] == user:
        return _json_error("You cannot ban yourself.")

    u = helper.getUser(user)
    if not u[0]:
        return _json_error("User not found.", 404)

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("update user set banned = ? where user=?", (int(not u[1]["banned"]), user))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


@app.route("/api/admin/create-ptero", methods=["POST"])
def api_admin_create_ptero():
    if not helper.is_same_origin(request):
        return _json_error("Forbidden.", 403)

    ok, auth = _require_auth()
    if not ok:
        return auth

    admin_ok, admin_result = _require_admin(auth["user"])
    if not admin_ok:
        return admin_result

    data = _payload()
    user = str(data.get("user", ""))
    email = str(data.get("email", ""))
    if (not user) or (not email):
        return _json_error("Missing data.")

    e = helper.createPteroUser(user, email)
    if e.get("errors"):
        return _json_error(str(e["errors"][0]))
    if e.get("error"):
        return _json_error(str(e["error"]))

    return jsonify({"ok": True})
