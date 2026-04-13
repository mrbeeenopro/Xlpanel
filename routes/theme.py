# type: ignore
from app.runtime import *

from flask import Response


@app.route("/theme.css", methods=["GET"])
def theme_css():
    st = helper.get_site_settings()
    css = f"""
:root {{
  --xl-primary: {st.get("theme_primary", "#0000aa")};
  --xl-accent: {st.get("theme_accent", "#0000dd")};
  --xl-danger: {st.get("theme_danger", "#aa0000")};
  --xl-bg: {st.get("theme_bg", "#000010")};
}}
body {{
  background: radial-gradient(circle at top right, color-mix(in srgb, var(--xl-accent) 40%, transparent), var(--xl-bg));
}}
.nav, .main main .title, .main main .info, .main main .form, .main main .userManager, .main main .welcome, .main main .helper {{
  border-color: color-mix(in srgb, var(--xl-primary) 45%, transparent) !important;
}}
button, input[type=submit], .btn button {{
  border-color: color-mix(in srgb, var(--xl-primary) 55%, transparent) !important;
}}
button:hover, input[type=submit]:hover, .btn button:hover {{
  border-color: var(--xl-primary) !important;
}}
.del {{
  border-color: color-mix(in srgb, var(--xl-danger) 55%, transparent) !important;
}}
.del:hover {{
  border-color: var(--xl-danger) !important;
}}
"""
    return Response(css, mimetype="text/css")

