# type: ignore
from app.runtime import *

@app.route("/")
def hp():
    return render_template("index.html")
