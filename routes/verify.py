# type: ignore
from app.runtime import *

from flask import jsonify, make_response, redirect, request

@app.route("/verify/", methods=["GET","POST"])
def verify():
    if request.method == "GET":
        if not request.args.get("user"): abort(403)
        return render_template("verify.html", name=helper.get_site_settings().get("site_name", name))
    else:
        if not helper.is_same_origin(request):
            abort(403)
        code = request.form.get("code")
        user = request.form.get("user")
        if (not code) or (not user): abort(403)
        check = helper.checkVcode(user, code)
        if not check[0]:
            return jsonify({"status": False, "message": check[1]})
        resp = jsonify({"status": True, "redirect": "/dashboard/"})
        helper.set_auth_cookie(resp, check[1], request)
        return resp
