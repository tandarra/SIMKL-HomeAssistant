"""Constants for SIMKL Hub."""
from __future__ import annotations

DOMAIN = "simkl_hub"
VERSION = "0.1.0"

APP_NAME = "ha-simkl-hub"
USER_AGENT = f"{APP_NAME}/{VERSION}"

API_BASE = "https://api.simkl.com"
CDN_BASE = "https://data.simkl.in/calendar/v2"
POSTER_BASE = "https://simkl.in/posters"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"

CONF_CLIENT_ID = "client_id"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_EXPIRES_AT = "expires_at"

CONF_POPULAR_TV = "popular_tv"
CONF_POPULAR_MOVIES = "popular_movies"
CONF_SCAN_MINUTES = "scan_minutes"
DEFAULT_POPULAR_TV = 40
DEFAULT_POPULAR_MOVIES = 60
DEFAULT_SCAN_MINUTES = 20

CALENDAR_TTL = 5 * 3600
DETAIL_TTL = 12 * 3600

PANEL_URL = "simkl"
CARD_URL = f"/{DOMAIN}/simkl-hub-card.js"
