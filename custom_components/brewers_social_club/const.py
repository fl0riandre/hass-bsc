"""Constants for the Brewers Social Club integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "brewers_social_club"
PLATFORMS = ["binary_sensor", "sensor"]
SERVICE_GET_API_DATA = "get_api_data"

CONF_API_KEY = "api_key"
CONF_MODULES = "modules"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_URL = "https://bsc.kloud.best"
DEFAULT_SCAN_INTERVAL = 300
MIN_SCAN_INTERVAL = 60
MAX_SCAN_INTERVAL = 3600

MODULE_OVERVIEW = "overview"
MODULE_MEMBERS = "members"
MODULE_PARTNERS = "partners"
MODULE_BENEFITS = "benefits"
MODULE_GROUP_ORDERS = "group_orders"
MODULE_BREWFATHER = "brewfather"
MODULE_RAPT = "rapt"
MODULE_PAYMENTS = "payments"
MODULE_STORAGE = "storage"

MODULES = (
    MODULE_OVERVIEW,
    MODULE_MEMBERS,
    MODULE_PARTNERS,
    MODULE_BENEFITS,
    MODULE_GROUP_ORDERS,
    MODULE_BREWFATHER,
    MODULE_RAPT,
    MODULE_PAYMENTS,
    MODULE_STORAGE,
)

DEFAULT_MODULES = list(MODULES)

MODULE_ENDPOINTS = {
    MODULE_OVERVIEW: "/api/admin/overview",
    MODULE_MEMBERS: "/api/admin/members",
    MODULE_PARTNERS: "/api/admin/partners",
    MODULE_BENEFITS: "/api/admin/benefits",
    MODULE_GROUP_ORDERS: "/api/admin/group-orders",
    MODULE_BREWFATHER: "/api/admin/brewfather/batches?scope=all",
    MODULE_RAPT: "/api/admin/rapt/controllers",
    MODULE_PAYMENTS: "/api/admin/bsc-payments",
    MODULE_STORAGE: "/api/admin/storage",
}

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
