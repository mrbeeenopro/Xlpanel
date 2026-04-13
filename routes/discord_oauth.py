# type: ignore
from app.runtime import *

import secrets
import requests

from urllib.parse import urlencode
from flask import make_response

import db


DISCORD_AUTH_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"
DISCORD_USER_URL = "https://discord.com/api/users/@me"


def _discord_settings():
    st = helper.get_site_settings()
    return {
        "enabled": bool(st.get("discord_oauth_enable", False)),
        "client_id": st.get("discord_client_id", ""),
        "client_secret": st.get("discord_client_secret", ""),
        "redirect_uri": st.get("discord_redirect_uri", ""),
    }


@app.route("/auth/discord/login", methods=["GET"])
def discord_login():
    ds = _discord_settings()
    if (not ds["enabled"]) or (not ds["client_id"]) or (not ds["client_secret"]) or (not ds["redirect_uri"]):
        abort(404)
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": ds["client_id"],
        "response_type": "code",
        "redirect_uri": ds["redirect_uri"],
        "scope": "identify email",
        "state": state,
        "prompt": "consent",
    }
    url = f"{DISCORD_AUTH_URL}?{urlencode(params)}"
    resp = make_response(redirect(url))
    resp.set_cookie("discord_oauth_state", state, max_age=300, httponly=True, samesite="Lax", secure=helper.should_use_secure_cookie(request))
    return resp


@app.route("/auth/discord/callback", methods=["GET"])
def discord_callback():
    ds = _discord_settings()
    if not ds["enabled"]:
        abort(404)
    code = request.args.get("code", "")
    state = request.args.get("state", "")
    expected = request.cookies.get("discord_oauth_state", "")
    if (not code) or (not state) or (state != expected):
        return redirect("/login?err=Discord OAuth failed.")

    token_payload = {
        "client_id": ds["client_id"],
        "client_secret": ds["client_secret"],
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ds["redirect_uri"],
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        token_resp = requests.post(DISCORD_TOKEN_URL, data=token_payload, headers=headers, timeout=20)
        token_data = token_resp.json()
    except Exception:
        return redirect("/login?err=Discord OAuth token error.")
    access_token = token_data.get("access_token")
    if not access_token:
        return redirect("/login?err=Discord OAuth token missing.")

    try:
        user_resp = requests.get(DISCORD_USER_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=20)
        user_data = user_resp.json()
    except Exception:
        return redirect("/login?err=Discord OAuth user error.")

    discord_id = str(user_data.get("id", "")).strip()
    email = str(user_data.get("email", "")).strip().lower()
    username = str(user_data.get("username", "")).strip() or "discord"
    if (not discord_id) or (not email):
        return redirect("/login?err=Discord account has no email.")

    conn = db.connect()
    cursor = conn.cursor()
    cursor.execute("select user, banned, discord_id from user where discord_id=? or email=? limit 1", (discord_id, email))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        local_user = helper.create_discord_user(email, username, discord_id)
    else:
        local_user = row[0]
        if int(row[1]) == 1:
            conn.close()
            return redirect("/banned")
        if not row[2]:
            cursor.execute("update user set discord_id=? where user=?", (discord_id, local_user))
            conn.commit()
        conn.close()

    sid = helper.genSID()
    helper.addSID(sid, local_user)
    resp = make_response(redirect("/dashboard/"))
    helper.set_auth_cookie(resp, sid, request)
    resp.set_cookie("discord_oauth_state", "", max_age=0, httponly=True, samesite="Lax", secure=helper.should_use_secure_cookie(request))
    return resp

