# type: ignore
from app.runtime import *
import time
import db

from flask import redirect, render_template

def _require_admin_user():
    check = helper.chSID(request.cookies.get("sid"))
    if not check[0]:
        return (False, redirect("/login"))
    uDt = helper.checkPteroUser(check[1]["user"])
    if (uDt[0] == False):
        return (False, f"""Something went wrong!\n\nuDt response:\n{uDt}""")
    if not uDt[1].get("root_admin", False):
        return (False, abort(403))
    return (True, check)

@app.route("/admin/", methods=["GET"])
def ad():
    if request.method == "GET":
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")
        return render_template(
            "admin.html",
            name=helper.get_site_settings().get("site_name", name),
            isAdmin=False,
            user=check[1]["user"],
            coin=check[1]["coin"],
            mIt=menuItems,
            ul=[],
            error=request.args.get("err"),
            version=ver,
            codename=codename,
            loadTime=int((time.time()-beginT)*100000)/100000
        )

@app.route("/admin/settings/", methods=["GET", "POST"])
def admin_settings():
    beginT = time.time()
    ok, check = _require_admin_user()
    if not ok:
        return check
    if request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        helper.update_site_settings({
            "site_name": request.form.get("site_name", "Xlpanel").strip() or "Xlpanel",
            "site_logo": request.form.get("site_logo", "").strip() or "/assets/img/logo.png",
            "discord_link": request.form.get("discord_link", "").strip(),
            "panel_link": request.form.get("panel_link", "").strip(),
            "theme_primary": request.form.get("theme_primary", "#0000aa").strip() or "#0000aa",
            "theme_accent": request.form.get("theme_accent", "#0000dd").strip() or "#0000dd",
            "theme_danger": request.form.get("theme_danger", "#aa0000").strip() or "#aa0000",
            "theme_bg": request.form.get("theme_bg", "#000010").strip() or "#000010",
            "discord_oauth_enable": request.form.get("discord_oauth_enable", "0"),
            "discord_client_id": request.form.get("discord_client_id", "").strip(),
            "discord_client_secret": request.form.get("discord_client_secret", "").strip(),
            "discord_redirect_uri": request.form.get("discord_redirect_uri", "").strip(),
        })
        return redirect("/admin/settings/?err=saved")

    settings = helper.get_site_settings()
    return render_template(
        "admin_settings.html",
        name=settings.get("site_name", name),
        isAdmin=True,
        user=check[1]["user"],
        coin=check[1]["coin"],
        mIt=menuItems,
        error=request.args.get("err"),
        settings=settings,
        loadTime=int((time.time()-beginT)*100000)/100000
    )

@app.route("/admin/add/", methods=["POST"])
def adr():
    if request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")
        uDt = helper.checkPteroUser(check[1]["user"])
        if (uDt[0] == False):
            return f"""Something went wrong!\n\nuDt response:\n{uDt}"""

        if (uDt[1].get("root_admin",False)):
            user = request.form.get("user", "")
            cpu = request.form.get("cpu", "0")
            ram = request.form.get("ram", "0")
            disk = request.form.get("disk", "0")
            slot = request.form.get("slot", '0')
            coin = request.form.get("coin", "0")

            if (not cpu): cpu = "0"
            if (not ram): ram = "0"
            if (not disk): disk = "0"
            if (not slot): slot = "0"
            if (not coin): coin = "0"
            try:
                cpu = int(cpu)
            except Exception: cpu = 0
            try:
                ram = int(ram)
            except Exception: ram = 0
            try:
                disk = int(disk)
            except Exception: disk = 0
            try:
                slot = int(slot)
            except Exception: slot = 0
            try:
                coin = int(coin)
            except Exception: coin = 0

            u = helper.getUser(user)
            if not u[0]:
                return redirect("/admin?err=User not found.")
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("update user set cpu=cpu+?, ram=ram+?, disk=disk+?, slot=slot+?, coin=coin+? where user=?",(cpu, ram, disk, slot, coin, user))
            conn.commit()
            conn.close()
            return redirect("/admin?err=none")
        else:
            abort(403)

@app.route("/admin/ban/", methods=["POST"])
def _adb():
    if request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")

        uDt = helper.checkPteroUser(check[1]["user"])
        if (uDt[0] == False):
            return f"""Something went wrong!\n\nuDt response:\n{uDt}"""

        if (uDt[1].get("root_admin",False)):
            user = request.form.get("user", "")
            if not user:
                return redirect("/admin?err=Missing user.")
            if check[1]["user"] == user:
                return redirect("/admin?err=You can't ban yourself.")
            u = helper.getUser(user)
            if not u[0]:
                return redirect("/admin?err=User not found.")
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("update user set banned = ? where user=?",(int(not u[1]["banned"]), user))
            conn.commit()
            conn.close()
            return redirect("/admin?err=none")
        else: abort(403)

@app.route("/admin/createPtero/", methods=["POST"])
def _pterocreate():
    if request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")

        uDt = helper.checkPteroUser(check[1]["user"])
        if (uDt[0] == False):
            return f"""Something went wrong!\n\nuDt response:\n{uDt}"""

        if (uDt[1].get("root_admin",False)):
            user = request.form.get("user", "")
            email = request.form.get("email", "")
            if (not user) or (not email):
                return redirect("/admin?err=Missing data.")
            e = helper.createPteroUser(user, email)
            if e.get("errors"): return redirect(f"/admin?err={e['errors'][0]}")
            if e.get("error"): return redirect(f"/admin?err={e['error']}")
            else: return redirect("/admin?err=none")
        else: abort(403)
