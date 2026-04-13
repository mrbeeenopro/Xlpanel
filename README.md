<div align="center">
<h2>Xlpanel - A client for Calagopus.</h2>
<img src="https://img.shields.io/badge/version-1.2.1-blue"></img>
<img src="https://img.shields.io/badge/codename-hydra_meee-0000aa"></img>
</div>

# Major Update: v1.2.1 (hydra meee)
> Just renew everything!
> design for calagopus


# Key features
* Manage your Calagopus server
* Afk for coins
* Admin page
* Easy to use
* Customize your client with your favourite color

# Require
- Python 3.10 or higher.
- Libraries in `requirements.txt` file.
- Node.js 20+ (for frontend build with Vite).

# Installation
<details>

<summary>Nginx Configuration</summary>

## If you are using nginx for webserver, you need to do this step before the main installation:

- Create a nginx's conf file:
``` bash
sudo touch /etc/nginx/sites-available/<name_you_want>.conf
```

- Paste this code into that file:
```conf
server {
    listen 80;
    listen [::]:80;
    listen 443 ssl;
    listen [::]:443 ssl;

    server_name <server_name>;

    ssl_certificate <path_to_ssl_file>;
    ssl_certificate_key <path_to_cert_file>;

    location / {
        proxy_pass http://localhost:<port>;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header    X-Real-IP $remote_addr;
    }
}
```

- Link that file to `sites-enabled` folder:
```bash
sudo ln -s /etc/nginx/sites-available/<name_you_want>.conf /etc/nginx/sites-enabled/<name_you_want>.conf
```

- Restart the nginx:
    + ubuntu: `sudo systemctl restart nginx`
    + alpine: `sudo service restart nginx`

> Done. Now you can go to the main installation!

</details>

- Download the latest version
- Extract the .zip file
- Go to the project folder
```bash
cd xlpanel
```
- Install the requirement libraries:
```bash
pip install -r requirements.txt
```
- Install frontend dependencies:
```bash
npm install
```
- Copy `config.example.json` to `config.json`:
```bash
cp config.example.json config.json
```
- Config the `config.json` file.
- Build frontend assets with Vite:
```bash
npm run build
```
- Build frontend:
```bash
npm run build
```
- Run the server:
```bash
python main.py
```
> Done. Now your server is online!

- To change the icon, please upload your icon into `assets/img` folder and replace the `logo.png` with your new icon.

<details>

<summary>How to change the theme?</summary>

- Edit the `sass/_data.scss` file
- You can change:
    + primary color: `$pcolor`
    + background color: `$bgcolor`
    + text color: `$text-color`
- After that, run `npm run build` to compile assets.

</details>

# Manual Node and Egg Configuration

By default, Xlpanel automatically detects your nodes and eggs from the panel API. However, if you want to set specific server limits for a node or override Docker images, startup commands, and variables for an egg, you can define them manually in your `config.json`.

### Adding a Node (Location) Manually
To add a node manually to set a maximum server limit, edit the `locations` object in your `config.json`:

```json
"locations": {
    "sg-main": {
        "name": "singapore-1",
        "node_uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        "limit": 50
    }
}
```
* `name`: The display name for the node on the frontend.
* `node_uuid`: The UUID of the node from your panel.
* `limit`: The maximum number of servers allowed on this node before it's hidden from the creation list.

### Adding an Egg Manually
To add a custom egg or override an existing egg's configuration, edit the `eggs` object in your `config.json`:

```json
"eggs": {
    "my_custom_egg": {
        "name": "My Custom Java Egg",
        "info": {
            "egg_uuid": "11111111-2222-3333-4444-555555555555",
            "image": "ghcr.io/pterodactyl/yolks:java_21",
            "startup": "java -Xms128M -Xmx{{SERVER_MEMORY}}M -jar {{SERVER_JARFILE}}",
            "memory_overhead": 0,
            "io_weight": 500,
            "environment": { "SERVER_JARFILE": "server.jar", "MINECRAFT_VERSION": "latest" },
            "feature_limits": { "allocations": 0, "databases": 2, "backups": 2, "schedules": 0 }
        }
    }
}
```

# Architecture

The backend now uses an app-factory structure:

- `main.py`: thin launcher.
- `app/factory.py`: creates Flask app, wires runtime, and registers routes.
- `app/features.py`: feature toggle registry to enable/disable route modules.
- `app/runtime.py`: shared runtime context imported by route modules.
- `routes/api.py`: JSON API endpoints used by frontend.
- `routes/spa.py`: serves built Vite SPA (`frontend/dist`).
- `routes/afk_ws.py`: websocket endpoint for AFK feature.

Frontend build is powered by Vite:

- `frontend/src/*`: SPA source code.
- `frontend/dist/*`: production bundle served by Flask.
- `vite.config.mjs`: Vite config with API/WebSocket proxy for dev.

Note: legacy Jinja page templates are no longer used for web pages. The backend is API-only for UI flows.


### **Enjoy your new client!**
