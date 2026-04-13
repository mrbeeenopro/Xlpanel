# type: ignore
from app.runtime import *

@app.route("/logout/", methods=["GET"])
def lout():
    if request.method == "GET":
        helper.logout(request.cookies.get("sid"))
        resp = make_response(redirect("/login"))
        helper.clear_auth_cookie(resp, request)
        return resp
