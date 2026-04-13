# type: ignore
from app.runtime import *

@app.route("/panel/")
@app.route("/panel/<a>")
def gtpn(a:str=None):
    panel_host = helper.get_site_settings().get("panel_link", "").strip() or config.get("calagopus", config.get("pterodactyl", {})).get("host", "")
    if a: return redirect(panel_host+f"/server/{a}")
    return redirect(panel_host)
