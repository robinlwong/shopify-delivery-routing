"""Lazada Open Platform API client for extracting order and address information."""

import hashlib
import hmac
import os
import time

import requests
from dotenv import load_dotenv

from delivery_routing.base_client import EcommercePlatformClient
from delivery_routing.models import DeliveryAddress

load_dotenv()

# Regional API gateway domains.
_REGION_DOMAINS = {
    "sg": "api.lazada.sg",
    "my": "api.lazada.com.my",
    "th": "api.lazada.co.th",
    "ph": "api.lazada.com.ph",
    "id": "api.lazada.co.id",
    "vn": "api.lazada.vn",
}

# Mapping from generic status names to Lazada order statuses.
_STATUS_MAP = {
    "unfulfilled": "pending",
    "fulfilled": "delivered",
    "partial": "shipped",
    "any": "",
}


def _sign(app_secret: str, api_path: str, params: dict) -> str:
    """Generate HMAC-SHA256 signature for the Lazada Open Platform API.

    Args:
        app_secret: Lazada app secret.
        api_path: API endpoint path (e.g. /orders/get).
        params: All request parameters (excluding sign itself).

    Returns:
        Hex-encoded HMAC-SHA256 signature string (uppercase).
    """
    sorted_params = sorted(params.items())
    base_string = api_path + "".join(f"{k}{v}" for k, v in sorted_params)
    return hmac.new(
        app_secret.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest().upper()


class LazadaClient(EcommercePlatformClient):
    """Client for the Lazada Open Platform API."""

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        access_token: str | None = None,
        region: str | None = None,
    ):
        self.app_key = app_key or os.getenv("LAZADA_APP_KEY", "")
        self.app_secret = app_secret or os.getenv("LAZADA_APP_SECRET", "")
        self.access_token = access_token or os.getenv("LAZADA_ACCESS_TOKEN", "")
        self.region = (region or os.getenv("LAZADA_REGION", "sg")).lower()

        if not self.app_key or not self.app_secret or not self.access_token:
            raise ValueError(
                "LAZADA_APP_KEY, LAZADA_APP_SECRET, and LAZADA_ACCESS_TOKEN "
                "must be set either as arguments or in a .env file."
            )

        domain = _REGION_DOMAINS.get(self.region)
        if not domain:
            raise ValueError(
                f"Unsupported Lazada region '{self.region}'. "
                f"Supported: {', '.join(sorted(_REGION_DOMAINS))}."
            )

        self.base_url = f"https://{domain}/rest"
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get(self, api_path: str, params: dict | None = None) -> dict:
        """Make a signed GET request to the Lazada API.

        Args:
            api_path: API endpoint path (e.g. /orders/get).
            params: Additional request parameters.

        Returns:
            Parsed JSON response dict.
        """
        common_params: dict = {
            "app_key": self.app_key,
            "access_token": self.access_token,
            "timestamp": str(int(time.time() * 1000)),
            "sign_method": "sha256",
        }
        if params:
            common_params.update(params)

        common_params["sign"] = _sign(self.app_secret, api_path, common_params)

        resp = self.session.get(f"{self.base_url}{api_path}", params=common_params)
        resp.raise_for_status()
        return resp.json()

    def get_orders(
        self,
        status: str = "unfulfilled",
        limit: int = 100,
    ) -> list[dict]:
        """Fetch orders from Lazada.

        Args:
            status: Fulfillment status filter. Accepted values:
                    "unfulfilled", "fulfilled", "partial", "any".
            limit: Max orders per request.

        Returns:
            List of order dicts from the Lazada API.
        """
        params: dict = {
            "sort_by": "created_at",
            "sort_direction": "DESC",
            "limit": str(limit),
            "offset": "0",
        }
        lazada_status = _STATUS_MAP.get(status, "")
        if lazada_status:
            params["status"] = lazada_status

        data = self._get("/orders/get", params)
        return data.get("data", {}).get("orders", [])

    def _get_order_items(self, order_id: str) -> list[dict]:
        """Fetch items for a single order (contains shipping details).

        Args:
            order_id: The Lazada order ID.

        Returns:
            List of order item dicts.
        """
        data = self._get("/order/items/get", {"order_id": order_id})
        return data.get("data", [])

    def extract_delivery_addresses(
        self,
        status: str = "unfulfilled",
    ) -> list[DeliveryAddress]:
        """Extract delivery addresses from Lazada orders.

        Args:
            status: Fulfillment status filter passed to get_orders().

        Returns:
            List of DeliveryAddress objects for orders that have an
            address.
        """
        orders = self.get_orders(status=status)
        addresses: list[DeliveryAddress] = []

        for order in orders:
            address_shipping = order.get("address_shipping", {})
            if not address_shipping:
                continue

            first_name = address_shipping.get("first_name", "")
            last_name = address_shipping.get("last_name", "")

            addresses.append(
                DeliveryAddress(
                    order_id=str(order.get("order_id", "")),
                    order_name=str(order.get("order_number", order.get("order_id", ""))),
                    name=f"{first_name} {last_name}".strip(),
                    address1=address_shipping.get("address1", ""),
                    address2=address_shipping.get("address2", ""),
                    city=address_shipping.get("city", ""),
                    province=address_shipping.get("address3", ""),
                    country=address_shipping.get("country", ""),
                    zip_code=address_shipping.get("post_code", ""),
                    phone=address_shipping.get("phone", ""),
                    latitude=None,
                    longitude=None,
                )
            )

        return addresses
