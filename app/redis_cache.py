import json

from app.config_loader import load_config

try:
    import redis
except Exception:  # pragma: no cover - optional dependency at runtime
    redis = None

config = load_config()
redis_cfg = config.get("redis", {})
_client = None
_initialized = False
_prefix = str(redis_cfg.get("prefix", "xlpanel")).strip() or "xlpanel"


def _key(name, identifier):
    return f"{_prefix}:{name}:{identifier}"


def _get_client():
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    if not redis_cfg.get("enable", False):
        return None
    if redis is None:
        return None
    try:
        url = redis_cfg.get("url")
        if url:
            client = redis.Redis.from_url(url, decode_responses=True)
        else:
            client = redis.Redis(
                host=redis_cfg.get("host", "127.0.0.1"),
                port=int(redis_cfg.get("port", 6379)),
                db=int(redis_cfg.get("db", 0)),
                password=redis_cfg.get("password"),
                decode_responses=True,
            )
        client.ping()
        _client = client
    except Exception:
        _client = None
    return _client


def set_session(sid_hash, user, ttl_seconds):
    client = _get_client()
    if not client:
        return False
    try:
        client.setex(_key("session", sid_hash), int(ttl_seconds), user)
        return True
    except Exception:
        return False


def get_session_user(sid_hash):
    client = _get_client()
    if not client:
        return None
    try:
        return client.get(_key("session", sid_hash))
    except Exception:
        return None


def delete_session(sid_hash):
    client = _get_client()
    if not client:
        return False
    try:
        client.delete(_key("session", sid_hash))
        return True
    except Exception:
        return False


def set_verify(user, email, code):
    client = _get_client()
    if not client:
        return False
    try:
        key = _key("verify", user)
        payload = json.dumps({"email": email, "code": code})
        ttl = int(redis_cfg.get("verify_ttl_seconds", 0))
        if ttl > 0:
            client.setex(key, ttl, payload)
        else:
            client.set(key, payload)
        return True
    except Exception:
        return False


def get_verify(user):
    client = _get_client()
    if not client:
        return None
    try:
        payload = client.get(_key("verify", user))
        if not payload:
            return None
        data = json.loads(payload)
        if (not data.get("email")) or (not data.get("code")):
            return None
        return data
    except Exception:
        return None


def delete_verify(user):
    client = _get_client()
    if not client:
        return False
    try:
        client.delete(_key("verify", user))
        return True
    except Exception:
        return False
