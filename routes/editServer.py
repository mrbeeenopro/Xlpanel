# type: ignore
from app.runtime import *
import time
import random

@app.route("/server/<_id>/edit/", methods=["POST"])
def editSv(_id):
    if request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")

        cpu = request.form.get("cpu","")
        ram = request.form.get("ram","")
        disk = request.form.get("disk","")

        if (
            (not cpu.isdigit())
            or
            (not ram.isdigit())
            or
            (not disk.isdigit())
        ): return redirect(f"/server/{_id}?err=invalid data type.")
        elif (
            (int(cpu) == 0)
            or
            (int(ram) == 0)
            or
            (int(disk) == 0)
        ): return redirect(f"/server/{_id}?err=Hi lil exploiter.")

        r = helper.editPteroServer(check[1]["user"], _id, int(cpu), int(ram), int(disk))
        if not r[0]: return redirect(f"/server/{_id}?err={r[1]}")
        else: return redirect(f"/server/{_id}?err=none")
