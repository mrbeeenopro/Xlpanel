# type: ignore
from app.runtime import *

import os
from flask import send_from_directory, abort


DIST_DIR = os.path.join(os.getcwd(), "frontend", "dist")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")


@app.route('/assets/<path:filename>')
def spa_assets(filename):
    if not os.path.isdir(ASSETS_DIR):
        abort(404)
    return send_from_directory(ASSETS_DIR, filename)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def spa_index(path):
    if path.startswith('api/') or path.startswith('afk/ws'):
        abort(404)

    index_path = os.path.join(DIST_DIR, 'index.html')
    if not os.path.isfile(index_path):
        return {
            "ok": False,
            "error": "Frontend build not found. Run: npm run build"
        }, 503

    if path and os.path.isfile(os.path.join(DIST_DIR, path)):
        return send_from_directory(DIST_DIR, path)

    return send_from_directory(DIST_DIR, 'index.html')
