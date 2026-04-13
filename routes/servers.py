# type: ignore
from app.runtime import *
import time

@app.route("/servers/", methods=["GET"])
def servers():
    if request.method == "GET":
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")
        runtime_nodes = helper.get_runtime_nodes()
        runtime_eggs = helper.get_runtime_eggs()
        resolved_nodes = runtime_nodes[1] if runtime_nodes[0] else nodeList
        resolved_eggs = runtime_eggs[1] if runtime_eggs[0] else eggsList

        return render_template(
            "server.html",
            name=helper.get_site_settings().get("site_name", name),
            isAdmin=False,
            user=check[1]["user"],
            sv = [],
            error = request.args.get("err", None),
            eggs=resolved_eggs,
            nodes=resolved_nodes,
            mIt=menuItems,
            
            
            
            coin=check[1]["coin"],
            loadTime=int((time.time()-beginT)*100000)/100000
        )

@app.route("/server/<identity>/", methods=["GET", "DELETE"])
def _sv(identity: str):
    beginT = time.time()
    check = helper.chSID(request.cookies.get("sid"))
    if (not check[0]):
        return redirect("/login")
    if request.method == "GET":
        return render_template(
            "iserver.html",
            name=helper.get_site_settings().get("site_name", name),
            isAdmin=False,
            user=check[1]["user"],
            i={
                "name": "Loading...",
                "identifier": identity,
                "limits": {"cpu": 1, "memory": 1, "disk": 1},
                "status": "loading"
            },
            error=request.args.get("err"),
            mIt=menuItems,
            coin=check[1]["coin"],
            loadTime=int((time.time()-beginT)*100000)/100000
        )
    elif request.method == "DELETE":
        if not helper.is_same_origin(request):
            return jsonify({"status": "error", "message": "Forbidden."}), 403
        uSv = helper.listPteroServer(check[1]["user"])
        if not uSv[0]:
            return jsonify({"status": "error", "message": str(uSv[1]) if len(uSv) > 1 else "Cannot load servers."})
        for i in uSv[1]:
            if i["identifier"] == identity:
                if i["status"] == "suspended":
                    return jsonify({"status": "error", "message": "This server has been suspended."})
                e = helper.delPteroServer(i["id"])
                if (e[0]):
                    return jsonify({"status": "ok"})
                else:
                    return jsonify({"status": "error", "message": str(e[1])})
        return jsonify({"status": "error", "message": "You don't have permission to modify this server."})
