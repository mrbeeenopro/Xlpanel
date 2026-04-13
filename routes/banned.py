#type: ignore
from app.runtime import *

@app.route("/banned/")
def _bn():
    return render_template("banned.html")
