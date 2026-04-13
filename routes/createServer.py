# type: ignore
from app.runtime import *
import time
import random

@app.route("/servers/create/", methods=["POST"])
def crsv():
    if request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")

        name = request.form.get("name", "").strip()
        cpu = request.form.get("cpu", "")
        ram = request.form.get("ram", "")
        disk = request.form.get("disk", "")
        node = request.form.get("node", "")
        egg = request.form.get("egg", "")

        if not name:
            return redirect("/servers?err=Missing name.")

        if (
            (not cpu.isdigit())
            or
            (not ram.isdigit())
            or
            (not disk.isdigit())
        ): return redirect(f"/servers?err=invalid data type.")
        elif (
            (int(cpu) == 0)
            or
            (int(ram) == 0)
            or
            (int(disk) == 0)
        ): return redirect(f"/servers?err=Hi lil exploiter.")

        r = helper.createPteroServer(name, check[1]["user"], node, egg, int(cpu), int(ram), int(disk))
        if not r[0]: return redirect(f"/servers?err={r[1]}")
        else: return redirect(f"/servers?err=none")
