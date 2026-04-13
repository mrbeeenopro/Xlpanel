# type: ignore
from app.runtime import *
import time

@app.route("/afk/", methods=["GET"])
def _afk():
    if request.method == "GET":
        beginT = time.time()
        check = helper.chSID(request.cookies.get("sid"))
        if (not check[0]):
            return redirect("/login")

        return render_template(
            "afk.html",
            name=helper.get_site_settings().get("site_name", name),
            isAdmin=False,
            user=check[1]["user"],
            mIt=menuItems,
            coin=check[1]["coin"],
            
            
            
            loadTime=int((time.time()-beginT)*100000)/100000
        )
