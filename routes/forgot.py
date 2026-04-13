# type: ignore
from app.runtime import *
import time
import ende
import db
import random

_chr = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0987654321"

@app.route("/forgot/", methods=["GET", "POST"])
def fg():
    if request.method == "GET":
        return render_template(
            "forgot.html",
            name=helper.get_site_settings().get("site_name", name),
            
            
            
        )
    elif request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        email = request.form.get("email","")
        if not email or "@" not in email:
            return jsonify({"status":"ok"})
        conn = db.connect()
        cursor = conn.cursor()
        
        cursor.execute("select lastSend from user where email=?", (email,))
        e = cursor.fetchall()
        if len(e)==0:
            conn.close()
            return jsonify({"status":"ok"})
        ls = e[0][0]
        if (ls > time.time()-3600):
            conn.close()
            return jsonify({"status":"ok"})
        nw = "".join(random.choice(_chr) for i in range(random.randint(10, 15)))
        e = sendmail.sendrspwd(email, nw)
        if (e[0]):
            cursor.execute("update user set password=?, lastSend=? where email=?", (ende.encode(nw), int(time.time()),email))
            conn.commit()
            conn.close()
            return jsonify({"status": "ok"})
        else:
            conn.close()
            return jsonify({"status": "ok"})
