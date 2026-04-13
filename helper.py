import db
import ende
import dns.resolver
import random
import time
import secrets
import requests
import hashlib
from urllib.parse import urlparse

from app.config_loader import load_config
from app.redis_cache import (
	delete_session as redis_delete_session,
	delete_verify as redis_delete_verify,
	get_session_user as redis_get_session_user,
	get_verify as redis_get_verify,
	set_session as redis_set_session,
	set_verify as redis_set_verify,
)
from sendmail import sendVerify

config = load_config()
panel_cfg = config.get("calagopus", config.get("pterodactyl", {}))
pteroHost = panel_cfg["host"].rstrip("/")
pteroKey = panel_cfg["key"]
api_base = panel_cfg.get("api_base", "/api/admin")
client_api_base = "/api/client"

# pteroHeader
headers = {
  'Authorization': f'Bearer {pteroKey}',
  'Content-Type': 'application/json',
  'Accept': panel_cfg.get("accept", "application/json")
}
# pteroHeader

_chr = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0987654321"
SITE_SETTINGS_DEFAULTS = {
	"site_name": config.get("name", "Xlpanel"),
	"site_logo": "/assets/img/logo.png",
	"discord_link": "",
	"panel_link": panel_cfg.get("host", ""),
	"theme_primary": "#0000aa",
	"theme_accent": "#0000dd",
	"theme_danger": "#aa0000",
	"theme_bg": "#000010",
	"discord_oauth_enable": "0",
	"discord_client_id": "",
	"discord_client_secret": "",
	"discord_redirect_uri": "",
}
SID_TTL_SECONDS = 86400 * 15
API_TIMEOUT_SECONDS = 20

def _normalize_site_logo(value):
	logo = str(value or "").strip()
	if not logo:
		return SITE_SETTINGS_DEFAULTS["site_logo"]
	if logo.startswith(("http://", "https://", "//", "data:", "/")):
		return logo
	return f"/{logo.lstrip('/')}"

def get_site_settings():
	conn = db.connect()
	cursor = conn.cursor()
	settings = dict(SITE_SETTINGS_DEFAULTS)
	cursor.execute("select key, value from site_settings")
	for key, value in cursor.fetchall():
		settings[key] = value if value is not None else settings.get(key, "")
	for key, default_value in SITE_SETTINGS_DEFAULTS.items():
		if key not in settings:
			settings[key] = default_value
		cursor.execute(
			"insert or ignore into site_settings (key, value) values (?, ?)",
			(key, str(settings[key])),
		)
	conn.commit()
	conn.close()
	settings["discord_oauth_enable"] = str(settings.get("discord_oauth_enable", "0")).lower() in ("1", "true", "on", "yes")
	settings["site_logo"] = _normalize_site_logo(settings.get("site_logo"))
	return settings

def update_site_settings(values):
	conn = db.connect()
	cursor = conn.cursor()
	for key in SITE_SETTINGS_DEFAULTS.keys():
		if key not in values:
			continue
		value = values[key]
		if key == "discord_oauth_enable":
			value = "1" if str(value).lower() in ("1", "true", "on", "yes") else "0"
		elif key == "site_logo":
			value = _normalize_site_logo(value)
		cursor.execute(
			"insert into site_settings (key, value) values (?, ?) on conflict(key) do update set value=excluded.value",
			(key, str(value)),
		)
	conn.commit()
	conn.close()

def create_discord_user(email, username_hint, discord_id):
	base = "".join(ch for ch in str(username_hint).lower() if ch.isalnum())[:20] or "discord"
	user = base
	conn = db.connect()
	cursor = conn.cursor()
	attempt = 0
	while True:
		cursor.execute("select 1 from user where user=?", (user,))
		if not cursor.fetchall():
			break
		attempt += 1
		user = f"{base}{attempt}"[:24]
	passwd = ende.encode(secrets.token_urlsafe(24))
	default_cfg = config.get("default", {})
	cursor.execute(
		"insert into user (user, password, email, cpu, ram, disk, slot, coin, verified, discord_id) values (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
		(
			user,
			passwd,
			email,
			int(default_cfg.get("cpu", 0)),
			int(default_cfg.get("ram", 0)),
			int(default_cfg.get("disk", 0)),
			int(default_cfg.get("slot", 0)),
			int(default_cfg.get("coin", 0)),
			str(discord_id),
		),
	)
	conn.commit()
	conn.close()
	return user

def _api(path):
	return f"{pteroHost}{api_base}{path}"


def _api_client(path):
	return f"{pteroHost}{client_api_base}{path}"

def _json_or_error(resp):
	try:
		return (True, resp.json())
	except ValueError:
		return (False, {"error": f"Panel API returned non-JSON response (HTTP {resp.status_code})."})
	except Exception:
		return (False, {"error": "Panel API request failed."})

def _request_json(method, path, **kwargs):
	url = _api(path)
	timeout = kwargs.pop("timeout", API_TIMEOUT_SECONDS)
	try:
		resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
	except requests.RequestException:
		return (False, {"error": "Cannot connect to panel API."})
	ok, data = _json_or_error(resp)
	if not ok:
		return (False, data)
	return (True, data)


def _request_client_json(method, path, **kwargs):
	url = _api_client(path)
	timeout = kwargs.pop("timeout", API_TIMEOUT_SECONDS)
	try:
		resp = requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
	except requests.RequestException:
		return (False, {"error": "Cannot connect to panel API."})
	ok, data = _json_or_error(resp)
	if not ok:
		return (False, data)
	return (True, data)

def _attrs(item):
	if isinstance(item, dict) and "attributes" in item:
		return item["attributes"]
	return item

def _extract_list(resp, primary_key):
	# Pterodactyl: {"data":[{"attributes":{...}}]}
	data = resp.get("data")
	if isinstance(data, list):
		return [_attrs(i) for i in data]
	# Calagopus: {"users":{"data":[...]}} / {"servers":{"data":[...]}}
	container = resp.get(primary_key, {})
	if isinstance(container, dict) and isinstance(container.get("data"), list):
		return container["data"]
	return []

def _extract_error(resp):
	if not isinstance(resp, dict):
		return "Something went wrong."
	if isinstance(resp.get("errors"), list) and resp["errors"]:
		first = resp["errors"][0]
		if isinstance(first, dict):
			return first.get("detail", first.get("message", first))
		return first
	if isinstance(resp.get("error"), str):
		return resp["error"]
	return "Something went wrong."

def _paginated_items(path, primary_key, per_page=100):
	page = 1
	items = []
	while True:
		sep = "&" if "?" in path else "?"
		ok, resp = _request_json("GET", f"{path}{sep}per_page={per_page}&page={page}")
		if not ok:
			return (False, _extract_error(resp))
		if (resp.get("errors")) or (resp.get("error")):
			return (False, _extract_error(resp))
		chunk = _extract_list(resp, primary_key)
		items.extend(chunk)
		if len(chunk) < per_page:
			break
		page += 1
	return (True, items)

def _value_id(value):
	if isinstance(value, dict):
		for key in ("id", "uuid", "user_id", "owner_id", "owner_uuid", "external_id"):
			if key in value and value.get(key) is not None:
				return value.get(key)
		return None
	return value

def _norm_id(value):
	value = _value_id(value)
	if value is None:
		return None
	return str(value)

def _owner_id_from_relationships(server):
	relationships = server.get("relationships")
	if not isinstance(relationships, dict):
		return None
	owner = relationships.get("owner")
	if not isinstance(owner, dict):
		return None
	owner_data = owner.get("data")
	if isinstance(owner_data, dict):
		return owner_data.get("id")
	return None

def _server_owner_candidates(server):
	candidates = []
	for key in ("user", "user_id", "user_uuid", "owner_id", "owner_uuid", "owner", "owner_user_id"):
		if key in server:
			candidates.append(server.get(key))
	rel_owner = _owner_id_from_relationships(server)
	if rel_owner is not None:
		candidates.append(rel_owner)
	# Some panel variants expose owner email instead of ids.
	for key in ("user_email", "owner_email", "email"):
		if key in server and server.get(key):
			candidates.append(str(server.get(key)).strip().lower())
	return {_norm_id(v) for v in candidates if v is not None}

def _user_id_candidates(user):
	candidates = []
	for key in ("id", "uuid", "user_id", "owner_id", "external_id"):
		if key in user:
			candidates.append(user.get(key))
	if user.get("email"):
		candidates.append(str(user.get("email")).strip().lower())
	return {_norm_id(v) for v in candidates if v is not None}

def _is_root_admin(user):
	for key in ("root_admin", "is_root_admin", "is_admin", "admin", "rootAdmin"):
		if key in user:
			return bool(user.get(key))
	return False

def _normalize_user(user):
	if not isinstance(user, dict):
		return user
	user["root_admin"] = _is_root_admin(user)
	return user

def _normalize_server(server):
	if not isinstance(server, dict):
		return server
	if "id" not in server:
		server["id"] = server.get("uuid")
	if "identifier" not in server:
		server["identifier"] = server.get("uuid_short", server.get("uuid", server.get("id")))
	if "status" not in server:
		server["status"] = "active"
		
	# Prevent sensitive admin information from leaking to the frontend
	server.pop("node", None)
	server.pop("backup_configuration", None)
	if "relationships" in server and isinstance(server["relationships"], dict):
		server["relationships"].pop("node", None)

	return server

def _server_owner(server):
	candidates = _server_owner_candidates(server)
	if not candidates:
		return None
	return list(candidates)[0]

def _server_ref(server):
	return server.get("id", server.get("uuid"))

def is_same_origin(req):
	expected_host = req.host
	for header_name in ("Origin", "Referer"):
		value = req.headers.get(header_name, "").strip()
		if not value:
			continue
		try:
			parsed = urlparse(value)
		except Exception:
			return False
		if not parsed.netloc:
			continue
		return parsed.netloc == expected_host
	return False

def should_use_secure_cookie(req):
	if req.is_secure:
		return True
	return req.headers.get("X-Forwarded-Proto", "").lower() == "https"

def set_auth_cookie(resp, sid, req):
	resp.set_cookie(
		"sid",
		sid,
		max_age=SID_TTL_SECONDS,
		path="/",
		httponly=True,
		secure=should_use_secure_cookie(req),
		samesite="Lax",
	)

def clear_auth_cookie(resp, req):
	resp.set_cookie(
		"sid",
		"",
		max_age=0,
		path="/",
		httponly=True,
		secure=should_use_secure_cookie(req),
		samesite="Lax",
	)

def genSID():
	return "s."+"".join(random.choice(_chr) for i in range(random.randint(60, 90)))

def addSID(sid, user):
	sid_hash = ende.hash(sid)
	redis_set_session(sid_hash, user, SID_TTL_SECONDS)
	conn = db.connect()
	cursor = conn.cursor()
	cursor.execute("insert into session (sid, passport, alive) values (?, ?, ?)", (sid_hash, user, time.time()+SID_TTL_SECONDS))
	conn.commit()
	conn.close()

def countPteroServer(nodeID):
	count = 0
	node_refs = {str(nodeID)}
	if isinstance(nodeID, (list, tuple, set)):
		node_refs = {str(i) for i in nodeID if i is not None}
	if not node_refs:
		return 0
	resp = _paginated_items("/servers", "servers")
	if not resp[0]:
		return 0
	for i in resp[1]:
		s_node = i.get("node", i.get("node_id", i.get("node_uuid")))
		if (str(s_node) in node_refs) and (not i.get("suspended", False)): count+=1
	return count

def createPteroUser(user, email):
	username_seed = "".join(ch for ch in str(user).lower() if ch.isalnum() or ch == "_")
	if not username_seed:
		username_seed = ende.hash(str(user))[:12].lower()
	username = username_seed[:15]
	if len(username) < 3:
		username = (username + "usr")[:3]
	name_first = "".join(ch for ch in str(user) if ch.isalpha())[:12] or "User"
	if len(name_first) < 2:
		name_first = "User"
	name_last = ende.hash(str(email))[:10]
	data = {
	"email": str(email).strip().lower(),
	"username": username,
	"name_first": name_first,
	"name_last": name_last,
	"admin": False,
	"language": "en"
	}
	ok, resp = _request_json("POST", "/users", json=data)
	if not ok:
		return (False, _extract_error(resp))
	if (resp.get("errors")) or (resp.get("error")):
		return (False, _extract_error(resp))
	return (True, resp)

def login(user, passwd):
	user = user.lower()
	conn = db.connect()
	cursor = conn.cursor()

	cursor.execute("select * from user where user=?", (user,))
	result = cursor.fetchall()
	conn.close()
	if len(result) == 0:
		return (False, "Invalid username or password.")
	if not ende.checkpw(result[0][1], passwd):
		return (False, "Invalid username or password.")
	if result[0][8]==0 and config.get("mail", {}).get("verifyUser", False):
		user_name = result[0][0]
		email = result[0][2]
		code = None
		cached_verify = redis_get_verify(user_name)
		if cached_verify:
			code = cached_verify["code"]
		if not code:
			code = "".join(random.choice(_chr) for i in range(6))
			if not redis_set_verify(user_name, email, code):
				conn = db.connect()
				cursor = conn.cursor()
				try:
					cursor.execute("insert into verify (user, email, code) values (?, ?, ?)", (user_name, email, code))
				except Exception:
					cursor.execute("select code from verify where user=?", (user_name,))
					row = cursor.fetchone()
					if row:
						code = row[0]
				conn.commit()
				conn.close()
		e = sendVerify(result[0][2], code)
		if e[0] == False:
			return (False, "Cannot send verify mail.")
		return (False, "verify", result[0][0])
	elif result[0][10]:
		return (False, "banned")
	sid = genSID()
	addSID(sid, user)
	return (True, sid)

def getUser(user):
	conn = db.connect()
	cursor = conn.cursor()
	cursor.execute("select * from user where user=?", (user,))
	result = cursor.fetchall()
	if not len(result): return (False, "User not found.")
	result = {
			"user": result[0][0],
			"email": result[0][2],
			"slot": result[0][3],
			"cpu": result[0][4],
			"disk": result[0][5],
			"ram": result[0][6],
			"coin": result[0][7],
			"banned": result[0][10]
		}
	return (True, result)

def checkVcode(user, code):
	cached_verify = redis_get_verify(user)
	if cached_verify:
		if code != cached_verify["code"]:
			return (False, "Invalid verify code!")
		sid = genSID()
		addSID(sid, user)
		conn = db.connect()
		cursor = conn.cursor()
		cursor.execute("update user set verified=1 where user=?", (user,))
		cursor.execute("delete from verify where user=?", (user,))
		conn.commit()
		conn.close()
		redis_delete_verify(user)
		createPteroUser(user, cached_verify["email"])
		return (True, sid)

	conn = db.connect()
	cursor = conn.cursor()
	cursor.execute("select * from verify where user=?", (user,))
	r = cursor.fetchall()
	
	if len(r) == 0:
		conn.close()
		return (False, "User not found.")
	rcode = r[0][2]
	if code != rcode:
		conn.close()
		return (False, "Invalid verify code!")
	sid = genSID()
	addSID(sid, user)
	cursor.execute("update user set verified=1 where user=?", (user,))
	cursor.execute("delete from verify where user=?", (user,))
	conn.commit()
	conn.close()
	redis_delete_verify(user)
	createPteroUser(r[0][0], r[0][1])
	return (True, sid)

def register(user, passwd, email, cpu, ram, disk, slot, coin):
	if not user.isascii():
		return (False, "Username must contain only latin characters.")
	user = user.lower().replace(" ", "")
	conn = db.connect()
	cursor = conn.cursor()
	passwd = ende.encode(passwd)
	cursor.execute("select * from user where email=?", (email,))
	result = cursor.fetchall()
	e = int(not config["mail"]["verifyUser"])
	if len(result) != 0:
		return (False, "Email has been used.")
	try:
		cursor.execute("insert into user (user, password, email, cpu, ram, disk, slot, coin, verified) values (?, ?, ?, ?, ?, ?, ?, ?, ?)", (user, passwd, email, cpu, ram, disk, slot, coin, e))
	except Exception:
		return (False, "Username has been used.")
	if not config["mail"]["verifyUser"]: createPteroUser(user, email)
	conn.commit()
	conn.close()
	return (True,)

def logout(sid, pre_hashed=False):
	if sid is None:
		return
	sid_hash = sid if pre_hashed else ende.hash(sid)
	redis_delete_session(sid_hash)
	conn = db.connect()
	cursor = conn.cursor()
	cursor.execute("delete from session where sid=?",(sid_hash,))
	conn.commit()
	conn.close()

def chSID(sid):
	if sid is None:
		return (False,)
	sid_hash = ende.hash(sid)
	session_user = redis_get_session_user(sid_hash)
	if session_user:
		conn = db.connect()
		cursor = conn.cursor()
		cursor.execute("select * from user where user=?",(session_user,))
		result = cursor.fetchall()
		if len(result) == 0:
			logout(sid_hash, pre_hashed=True)
			conn.close()
			return (False,)
		if result[0][10]:
			logout(sid_hash, pre_hashed=True)
			conn.close()
			return (False, "banned")
		conn.close()
		result = {
			"user": result[0][0],
			"pwd": result[0][1],
			"email": result[0][2],
			"slot": result[0][3],
			"cpu": result[0][4],
			"disk": result[0][5],
			"ram": result[0][6],
			"coin": result[0][7],
			"banned": result[0][10]
		}
		return (True, result)

	conn = db.connect()
	cursor = conn.cursor()
	cursor.execute("select * from session where sid=?",(sid_hash,))
	result = cursor.fetchall()

	if len(result) == 0:
		conn.close()
		return (False,)
	else:
		if (float(result[0][2]) < time.time()):
			logout(sid_hash, pre_hashed=True)
			conn.close()
			return (False,)
		ttl = int(float(result[0][2]) - time.time())
		if ttl > 0:
			redis_set_session(sid_hash, result[0][1], ttl)
		cursor.execute("select * from user where user=?",(result[0][1],))
		result = cursor.fetchall()
		if result[0][10]:
			logout(sid_hash, pre_hashed=True)
			conn.close()
			return (False, "banned")
		conn.close()
		result = {
			"user": result[0][0],
			"pwd": result[0][1],
			"email": result[0][2],
			"slot": result[0][3],
			"cpu": result[0][4],
			"disk": result[0][5],
			"ram": result[0][6],
			"coin": result[0][7],
			"banned": result[0][10]
		}
		return (True, result)

def checkPteroUser(name):
	e = getUser(name)
	if not e[0]:
		return (False, "nf")
	resp = _paginated_items("/users", "users")
	if not resp[0]:
		return (False, resp[1])
	target_email = str(e[1]["email"]).strip().lower() #pyright: ignore
	for i in resp[1]:
		if str(i.get("email", "")).strip().lower() == target_email:
			return (True, _normalize_user(i))
	return (False, "nf")


def ensurePteroUser(name):
	user_data = getUser(name)
	if not user_data[0]:
		return (False, "User not found.")
	panel_user = checkPteroUser(name)
	if panel_user[0]:
		return (True, panel_user[1])
	created = createPteroUser(name, user_data[1].get("email", ""))
	if not created[0]:
		return (False, str(created[1]))
	panel_user = checkPteroUser(name)
	if not panel_user[0]:
		return (False, "Cannot create panel user.")
	return (True, panel_user[1])

def getPteroAllocation(node_id, _random=False):
	def _is_free(allocation):
		if not isinstance(allocation, dict):
			return False
		if isinstance(allocation.get("server"), dict):
			return False
		if allocation.get("server") not in (None, ""):
			return False
		if allocation.get("assigned", False):
			return False
		if allocation.get("is_assigned", False):
			return False
		return True

	resp = _paginated_items(f"/nodes/{node_id}/allocations", "allocations")
	if not resp[0]:
		return (False, resp[1])
	r = [i for i in resp[1] if _is_free(i)]
	if len(r) == 0:
		return (False,)
	i = 0
	if _random:
		i = random.randint(0, len(r)-1)
	return (True, r[i])


def getPteroAllocations(node_id):
	def _is_free(allocation):
		if not isinstance(allocation, dict):
			return False
		if isinstance(allocation.get("server"), dict):
			return False
		if allocation.get("server") not in (None, ""):
			return False
		if allocation.get("assigned", False):
			return False
		if allocation.get("is_assigned", False):
			return False
		return True

	resp = _paginated_items(f"/nodes/{node_id}/allocations", "allocations")
	if not resp[0]:
		return (False, resp[1])
	return (True, [i for i in resp[1] if _is_free(i)])

def listPteroNode(name):
	resp = _paginated_items("/nodes", "nodes")
	if not resp[0]:
		return (False, resp[1])
	for i in resp[1]:
		if i.get("name") == name:
			return (True, i)
	return (False, "nf")


def get_runtime_nodes():
	raw_locations = config.get("locations", {})
	locations = raw_locations if isinstance(raw_locations, dict) else {}
	nodes = {}

	for cfg_key, cfg in locations.items():
		if not isinstance(cfg, dict):
			continue
		node_id_s = str(cfg.get("node_id", "")).strip()
		node_uuid_s = str(cfg.get("node_uuid", "")).strip()
		node_name = str(cfg.get("name") or cfg_key).strip()
		key = str(cfg_key).strip()
		if not key:
			continue
		nodes[key] = {
			"name": node_name or f"Node {key}",
			"node_id": node_id_s,
			"node_uuid": node_uuid_s,
			"limit": int(cfg.get("limit", -1)),
		}

	if nodes:
		return (True, nodes)
	return (False, "No locations configured in config.json. Please configure them manually.")


def get_runtime_eggs():
	config_eggs = config.get("eggs", {})
	eggs = config_eggs if isinstance(config_eggs, dict) else {}
	if eggs:
		return (True, eggs)
	return (False, "No eggs configured in config.json. Please configure them manually.")


def listPteroServer(name):
	userData = checkPteroUser(name)
	if not userData[0]:
		ensured = ensurePteroUser(name)
		if ensured[0]:
			userData = (True, ensured[1])
	resp = _paginated_items("/servers", "servers")
	if not resp[0]:
		return (False, resp[1])
	if (userData[0] == False): return (False, "usernf")
	
	uid_candidates = _user_id_candidates(userData[1])
	uDt = []
	tCPU = 0
	tDisk = 0
	tRam = 0

	for i in resp[1]:
		server_owner_candidates = _server_owner_candidates(i)
		if uid_candidates.intersection(server_owner_candidates):
			i = _normalize_server(i)
			uDt.append(i)
			limits = i.get("limits", {})
			tCPU += limits.get("cpu", 0)
			tRam += limits.get("memory", 0)
			tDisk+= limits.get("disk", 0)
	return (True, uDt, tCPU, tDisk, tRam)

def createPteroServer(name, user, node, egg, cpu, ram, disk, **kwargs):
	try:
		cpu = int(cpu)
		ram = int(ram)
		disk = int(disk)
	except (TypeError, ValueError):
		return (False, "Invalid limits.")

	uDt = getUser(user)
	uPdt = checkPteroUser(user)
	uSv = listPteroServer(user)
	if not uPdt[0] and uDt[0]:
		created_panel_user = createPteroUser(user, uDt[1].get("email", ""))
		if not created_panel_user[0]:
			return (False, f"Cannot create panel user: {created_panel_user[1]}")
		uPdt = checkPteroUser(user)
		uSv = listPteroServer(user)

	if (uDt[0] == False) or (uPdt[0] == False):
		return (False, "User not found.", {
			"uDt": uDt,
			"uPdt": uPdt
		})
	r_eggs = get_runtime_eggs()
	eggs = r_eggs[1] if r_eggs[0] else {}
	if not eggs:
		return (False, "Egg not found.")
	egg_selected = None
	egg_value = str(egg).strip()
	if egg_value and (egg_value in eggs):
		egg_selected = eggs[egg_value]
	elif egg_value:
		for _, egg_item in eggs.items():
			if str(egg_item.get("name", "")).strip().lower() == egg_value.lower():
				egg_selected = egg_item
				break
	if not egg_selected:
		egg_selected = next(iter(eggs.values()))
	egg = egg_selected

	ucpu = uDt[1]["cpu"]-uSv[2] #pyright: ignore
	udisk = uDt[1]["disk"]-uSv[3] #pyright: ignore
	uram = uDt[1]["ram"]-uSv[4] #pyright: ignore

	if (ucpu < cpu):
		return (False, "Not enough cpu.")
	elif (udisk < disk):
		return (False, "Not enough disk.")
	elif (uram < ram):
		return (False, "Not enough ram.")
	elif len(uSv[1]) >= uDt[1]["slot"]:
		return (False, "Not enough slot.")
	
	data = egg["info"]
	r_nodes = get_runtime_nodes()
	if not r_nodes[0]:
		return (False, "Cannot load nodes from panel API.")

	node_map = r_nodes[1]
	selected_node = None
	node_value = str(node).strip()
	if node_value and node_value in node_map:
		selected_node = node_map[node_value]
	elif node_value:
		for _, n in node_map.items():
			if str(n.get("node_id", "")) == node_value or str(n.get("node_uuid", "")) == node_value:
				selected_node = n
				break

	node_hint = str(data.get("node_uuid") or data.get("node_id") or data.get("node") or "").strip()
	candidates = []
	if selected_node:
		candidates.append(selected_node)
	else:
		if node_hint:
			for _, n in node_map.items():
				if str(n.get("node_uuid", "")) == node_hint or str(n.get("node_id", "")) == node_hint:
					candidates.append(n)
					break
		for _, n in node_map.items():
			if n not in candidates:
				candidates.append(n)

	candidate_nodes = []
	for candidate in candidates:
		node_id = str(candidate.get("node_id", "")).strip()
		node_uuid = str(candidate.get("node_uuid", "")).strip()
		node_api_ref = node_id or node_uuid
		if not node_api_ref:
			continue
		node_limit = int(candidate.get("limit", -1))
		if node_limit != -1:
			serverCount = countPteroServer([node_id, node_uuid])
			if (serverCount >= node_limit):
				continue
		candidate_nodes.append((candidate, node_api_ref))

	if not candidate_nodes:
		return (False, "No allocation available.")

	def _build_create_payload(egg_info, chosen_node, allocation):
		node_uuid_value = str(chosen_node.get("node_uuid") or chosen_node.get("node_id") or "")
		if "egg_uuid" in egg_info:
			feature_limits = egg_info.get("feature_limits", {})
			if not isinstance(feature_limits, dict):
				feature_limits = {}
			normalized_feature_limits = {
				"allocations": int(feature_limits.get("allocations", 0) or 0),
				"databases": int(feature_limits.get("databases", 0) or 0),
				"backups": int(feature_limits.get("backups", 0) or 0),
				"schedules": int(feature_limits.get("schedules", 0) or 0),
			}
			
			env_final = dict(egg_info.get("environment", {}))
			for kw_key, kw_val in kwargs.items():
				if kw_key.startswith("env_"):
					env_final[kw_key[4:]] = str(kw_val)

			return {
				"name": name,
				"node_uuid": egg_info.get("node_uuid", node_uuid_value),
				"owner_uuid": uPdt[1].get("uuid", uPdt[1].get("id")),
				"egg_uuid": egg_info["egg_uuid"],
				"allocation_uuid": allocation.get("uuid", allocation.get("id")),
				"allocation_uuids": [],
				"start_on_completion": egg_info.get("start_on_completion", True),
				"skip_installer": egg_info.get("skip_installer", False),
				"description": egg_info.get("description"),
				"limits": {
					"memory": ram,
					"memory_overhead": int(egg_info.get("memory_overhead", 0) or 0),
					"swap": 0,
					"disk": disk,
					"io_weight": int(egg_info.get("io_weight", egg_info.get("io", 500)) or 500),
					"cpu": cpu
				},
				"pinned_cpus": egg_info.get("pinned_cpus", []),
				"startup": egg_info.get("startup", ""),
				"image": egg_info.get("image", egg_info.get("docker_image", "")),
				"timezone": egg_info.get("timezone"),
				"hugepages_passthrough_enabled": egg_info.get("hugepages_passthrough_enabled", False),
				"kvm_passthrough_enabled": egg_info.get("kvm_passthrough_enabled", False),
				"feature_limits": normalized_feature_limits,
				"variables": [{"env_variable": k, "value": str(v)} for k, v in env_final.items()],
			}
		legacy_data = dict(egg_info)
		legacy_data["name"] = name
		legacy_data["user"] = uPdt[1].get("id", uPdt[1].get("uuid"))
		legacy_data["allocation"] = {
			"default": allocation.get("id", allocation.get("uuid"))
		}
		legacy_data["limits"] = {
			"memory": ram,
			"swap": 0,
			"disk": disk,
			"io": 500,
			"cpu": cpu
		}
		return legacy_data

	last_error = "No allocation available."
	for candidate, node_api_ref in candidate_nodes:
		allocs = getPteroAllocations(node_api_ref)
		if not allocs[0]:
			last_error = str(allocs[1])
			continue
		if not allocs[1]:
			continue
		for allocation in allocs[1]:
			payload = _build_create_payload(data, candidate, allocation)
			ok, resp = _request_json("POST", "/servers", json=payload)
			if ok and (not resp.get("errors")) and (not resp.get("error")):
				# Strip sensitive data before returning the new server to the client
				if isinstance(resp, dict) and "server" in resp:
					_normalize_server(resp["server"])
				elif isinstance(resp, dict):
					_normalize_server(resp)
				return (True, resp)
			err_msg = _extract_error(resp if ok else {"error": "Panel API request failed."})
			last_error = str(err_msg)
			lower_err = str(err_msg).lower()
			if ("allocation" in lower_err and "already exists" in lower_err) or ("external id already exists" in lower_err):
				# Retry another free allocation.
				continue
			return (False, err_msg)

	return (False, last_error)

def delPteroServer(id):
	try:
		resp = requests.delete(
			_api(f"/servers/{id}"),
			headers=headers,
			json={
				"force": True,
				"delete_backups": False,
			},
			timeout=API_TIMEOUT_SECONDS,
		)
	except requests.RequestException:
		return (False, "Cannot connect to panel API.")
	if resp.status_code not in (200, 204):
		ok, payload = _json_or_error(resp)
		return (False, _extract_error(payload if ok else {"error": "Panel API request failed."}))
	return (True,)


def powerPteroServer(server_id, action):
	action_value = str(action or "").strip().lower()
	if action_value not in ("start", "stop", "restart", "kill"):
		return (False, "Invalid power action.")

	def _matches_server_ref(server_item, ref):
		ref_s = str(ref or "").strip()
		if not ref_s:
			return False
		candidates = {
			str(server_item.get("id", "")).strip(),
			str(server_item.get("uuid", "")).strip(),
			str(server_item.get("uuid_short", "")).strip(),
			str(server_item.get("identifier", "")).strip(),
		}
		return ref_s in candidates

	def _resolve_server_ref(ref):
		ref_s = str(ref or "").strip()
		if not ref_s:
			return ""
		resp = _paginated_items("/servers", "servers")
		if not resp[0]:
			return ref_s
		for item in resp[1]:
			if _matches_server_ref(item, ref_s):
				return str(item.get("uuid") or item.get("id") or ref_s)
		return ref_s

	resolved_ref = _resolve_server_ref(server_id)
	ok, resp = _request_client_json("POST", f"/servers/{resolved_ref}/power", json={"action": action_value})
	if not ok:
		return (False, _extract_error(resp))
	if (resp.get("errors")) or (resp.get("error")):
		return (False, _extract_error(resp))
	return (True, resp)


def getPteroServerStatus(server_id):
	def _matches_server_ref(server_item, ref):
		ref_s = str(ref or "").strip()
		if not ref_s:
			return False
		candidates = {
			str(server_item.get("id", "")).strip(),
			str(server_item.get("uuid", "")).strip(),
			str(server_item.get("uuid_short", "")).strip(),
			str(server_item.get("identifier", "")).strip(),
		}
		return ref_s in candidates

	def _resolve_server_ref(ref):
		ref_s = str(ref or "").strip()
		if not ref_s:
			return ""
		resp = _paginated_items("/servers", "servers")
		if not resp[0]:
			return ref_s
		for item in resp[1]:
			if _matches_server_ref(item, ref_s):
				return str(item.get("uuid") or item.get("id") or ref_s)
		return ref_s

	resolved_ref = _resolve_server_ref(server_id)
	ok, resp = _request_client_json("GET", f"/servers/{resolved_ref}")
	if ok and isinstance(resp, dict):
		server = resp.get("server", {})
		if isinstance(server, dict):
			status = server.get("status")
			if status is not None:
				return (True, str(status))
	# Fallback to admin endpoint status when client endpoint is unavailable.
	ok, resp = _request_json("GET", f"/servers/{resolved_ref}")
	if not ok:
		# Last fallback: inspect list endpoint and extract current status by matching id/uuid/short id.
		all_servers = _paginated_items("/servers", "servers")
		if all_servers[0]:
			for item in all_servers[1]:
				if _matches_server_ref(item, server_id):
					return (True, str(item.get("status", "active")))
		return (False, _extract_error(resp))
	if (resp.get("errors")) or (resp.get("error")):
		all_servers = _paginated_items("/servers", "servers")
		if all_servers[0]:
			for item in all_servers[1]:
				if _matches_server_ref(item, server_id):
					return (True, str(item.get("status", "active")))
		return (False, _extract_error(resp))
	server = resp.get("server", {})
	if isinstance(server, dict) and (server.get("status") is not None):
		return (True, str(server.get("status")))
	return (False, "Cannot get server status.")

def chMX(domain):
	try:
		r = dns.resolver.resolve(domain, "MX")
	except Exception:
		return 0
	else: return len(r)


def getPteroPasswd(e):
	passwd = "".join(random.choice(_chr) for i in range(20))
	data = {
			"email": e[1]["email"],
			"username": e[1]["username"],
			"name_first": e[1].get("name_first", e[1].get("first_name", ".")),
			"name_last": e[1].get("name_last", e[1].get("last_name", "user")),
			"password": passwd
		}
	user_ref = e[1].get("uuid", e[1].get("id"))
	try: resp = requests.patch(_api(f"/users/{user_ref}"),json=data, headers=headers, timeout=API_TIMEOUT_SECONDS)
	except Exception:
		return (False, "Something went wrong!")
	else:
		if resp.status_code >= 400:
			return (False, _extract_error(resp.json()))
		return (True, passwd)

def editPteroServer(user, identifier, cpu, ram, disk):
	uDt = getUser(user)
	uSv = listPteroServer(user)
	for i in uSv[1]:
		if i["identifier"] == identifier: #pyright:ignore
			if i["status"] == "suspended": #pyright:ignore
				return (False,"This server has been suspended.")
			
			ucpu = uDt[1]["cpu"]-uSv[2] #pyright: ignore
			udisk = uDt[1]["disk"]-uSv[3] #pyright: ignore
			uram = uDt[1]["ram"]-uSv[4] #pyright: ignore
			ccpu = i["limits"]["cpu"] #pyright: ignore
			cdisk = i["limits"]["disk"] #pyright: ignore
			cram = i["limits"]["memory"] #pyright: ignore

			if (ucpu < (cpu - ccpu)):
				return (False, "Not enough cpu.")
			elif (udisk < (disk - cdisk)):
				return (False, "Not enough disk.")
			elif (uram < (ram - cram)):
				return (False, "Not enough ram.")

			if "uuid" in i and "allocation_uuid" in i:
				data = {
					"name": i.get("name", identifier),
					"limits": {
						"memory": ram,
						"swap": i["limits"].get("swap", 0), #pyright: ignore
						"disk": disk,
						"io": i["limits"].get("io", 500), #pyright: ignore
						"cpu": cpu
					},
					"feature_limits": i.get("feature_limits", {"databases": 0, "backups": 0}), #pyright: ignore
					"allocation_uuid": i.get("allocation_uuid"),
				}
				ok, resp = _request_json("PATCH", f"/servers/{_server_ref(i)}", json=data) #pyright: ignore
				if not ok: return (False, _extract_error(resp))
			else:
				data = {
					"allocation": i["allocation"], #pyright: ignore
					"memory": ram,
					"swap": i["limits"]["swap"], #pyright: ignore
					"disk": disk,
					"io": i["limits"]["io"], #pyright: ignore
					"cpu": cpu,
					"feature_limits": i["feature_limits"] #pyright: ignore
				}
				ok, resp = _request_json("PATCH", f"/servers/{_server_ref(i)}/build", json=data) #pyright: ignore
				if not ok: return (False, _extract_error(resp))
			if (resp.get("errors")) or (resp.get("error")): return (False, _extract_error(resp))
		if isinstance(resp, dict) and "server" in resp:
			_normalize_server(resp["server"])
		elif isinstance(resp, dict):
			_normalize_server(resp)
			return (True, resp)
	return (False,"You don't have permission to modify this server.")

cf_secret_token = config["cf_turnstile"]["secret_key"]

def cf_check(token, ip):
	data = {
		"secret": cf_secret_token,
		"response": token,
		"remote_ip": ip
	}
	if not config["cf_turnstile"]["enable"]: return (True,)
	try:
		e = requests.post("https://challenges.cloudflare.com/turnstile/v0/siteverify", json=data, timeout=API_TIMEOUT_SECONDS)
		return (e.json().get("success"), ) #pyright: ignore
	except Exception:
		return (False,)
