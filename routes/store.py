# type: ignore
from app.runtime import *
import time
import db

@app.route("/store/", methods=["GET"])
def _store():
    if request.method == "GET":
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")

        return render_template(
            "store.html",
            name=helper.get_site_settings().get("site_name", name),
            isAdmin=False,
            user=check[1]["user"],
            mIt=menuItems,
            coin=check[1]["coin"],
            store=store,
            
            
            
            error=request.args.get("err"),
            loadTime=int((time.time()-beginT)*100000)/100000
        )

@app.route("/store/buy/", methods=["POST"])
def _buy():
    if request.method == "POST":
        if not helper.is_same_origin(request):
            abort(403)
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")
        item = request.form.get("item")
        amount = request.form.get("amount", "")
        if item not in ["cpu", "ram", "disk", "slot"]:
            return redirect("/store?err=Invalid item.")
        elif not amount.isdigit():
            return redirect("/store?err=Invalid data type.")
        if int(amount) <= 0 or int(amount) > 1000:
            return redirect("/store?err=Invalid amount.")
        if (store[item][0]*int(amount)) > check[1]["coin"]:
            return redirect("/store?err=Not enough coins.")
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(f"update user set {item}={item}+? where user=?",(store[item][1]*int(amount), check[1]["user"]))
        cursor.execute(f"update user set coin=coin-? where user=?",(store[item][0]*int(amount), check[1]["user"]))
        conn.commit()
        conn.close()
        return redirect("/store?err=none")
