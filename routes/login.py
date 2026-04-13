# type: ignore
from app.runtime import *

from flask import make_response, redirect, request

@app.route("/login/", methods=["GET","POST"])
def login():
	cf_site_key = config["cf_turnstile"]["site_key"]
	cf_enable = config["cf_turnstile"]["enable"]
	discord_oauth_enable = helper.get_site_settings().get("discord_oauth_enable", False)
	if request.method == "GET":
		check = helper.chSID(request.cookies.get("sid"))
		if (check[0]):
			return redirect("/dashboard")
		return render_template("login.html", cf_site_key=cf_site_key, cf_enable=cf_enable, name=helper.get_site_settings().get("site_name", name), discord_oauth_enable=discord_oauth_enable, error=request.args.get("err"))
	else:
		user = request.form.get("user")
		passwd = request.form.get("passwd")
		cf_token = request.form.get("cf-turnstile-response")
		cf_ip = request.form.get("CF-Connecting-IP")
		if (
			(not user)
			or
			(not passwd)): abort(403)
		e = helper.cf_check(cf_token, cf_ip)
		if not e[0]:
			return render_template("login.html",  name=helper.get_site_settings().get("site_name", name),  cf_site_key=cf_site_key, cf_enable=cf_enable, discord_oauth_enable=discord_oauth_enable, error="Invalid captcha.")
		check = helper.login(user, passwd)
		if check[0]:
			resp = make_response(redirect("/dashboard/"))
			helper.set_auth_cookie(resp, check[1], request)
			return resp
		else:
			if check[1] == "verify":
				return redirect(f"/verify?user={check[2]}")
			elif check[1] == "banned":
				return redirect("/banned")
			return render_template("login.html",  name=helper.get_site_settings().get("site_name", name),  cf_site_key=cf_site_key, cf_enable=cf_enable, discord_oauth_enable=discord_oauth_enable, error=check[1])
