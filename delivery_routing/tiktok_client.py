"""TikTok Shop API client for extracting order and address information."""

import hashlib
import hmac
import os
import time

import requests
from dotenv import load_dotenv

from delivery_routing.base_client import EcommercePlatformClient
from delivery_routing.models import DeliveryAddress

load_dotenv()

BASE_URL = "https://open-api.tiktokglobalshop.com"

# Mapping from generic status names to TikTok Shop order statuses.
_STATUS_MAP = {
    "unfulfilled": "AWAITING_SHIPMENT",
    "fulfilled": "DELIVERED",
    "partial": "IN_TRANSIT",
    "any": "",
}


def _sign(app_secret: str, path: str, params: dict) -> str:
    """Generate HMAC-SHA256 signature for the TikTok Shop API.

    Args:
        app_secret: TikTok Shop app secret.
        path: API endpoint path (e.g. /api/orders/search).
        params: All request parameters (excluding sign and access_token).

    Returns:
        Hex-encoded HMAC-SHA256 signature string.
    """
    sorted_params = sorted(params.items())
    base_string = app_secret + path + "".join(
        f"{k}{v}" for k, v in sorted_params
    ) + app_secret
    return hmac.new(
        app_secret.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class TikTokClient(EcommercePlatformClient):
    """Client for the TikTok Shop Open API."""

    def __init__(
        self,
        app_key: str | None = None,
        app_secret: str | None = None,
        access_token: str | None = None,
        shop_id: str | None = None,
    ):
        self.app_key = app_key or os.getenv("TIKTOK_APP_KEY", "")
        self.app_secret = app_secret or os.getenv("TIKTOK_APP_SECRET", "")
        self.access_token = access_token or os.getenv("TIKTOK_ACCESS_TOKEN", "")
        self.shop_id = shop_id or os.getenv("TIKTOK_SHOP_ID", "")

        if not self.app_key or not self.app_secret or not self.access_token or not self.shop_id:
            raise ValueError(
                "TIKTOK_APP_KEY, TIKTOK_APP_SECRET, TIKTOK_ACCESS_TOKEN, "
                "and TIKTOK_SHOP_ID must be set either as arguments or in a "
                ".env file."
            )

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Make a signed GET request to the TikTok Shop API.

        Args:
            path: API endpoint path (e.g. /api/orders/search).
            params: Additional query parameters (used for signing).

        Returns:
            Parsed JSON response dict.
        """
        timestamp = int(time.time())
        sign_params: dict = {
            "app_key": self.app_key,
            "timestamp": str(timestamp),
            "shop_id": self.shop_id,
        }
        if params:
            sign_params.update(params)

        sign = _sign(self.app_secret, path, sign_params)

        query: dict = {
            **sign_params,
            "sign": sign,
            "access_token": self.access_token,
        }

        resp = self.session.get(f"{BASE_URL}{path}", params=query)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict | None = None) -> dict:
        """Make a signed POST request to the TikTok Shop API.

        Args:
            path: API endpoint path.
            body: JSON body payload.

        Returns:
            Parsed JSON response dict.
        """
        timestamp = int(time.time())
        sign_params: dict = {
            "app_key": self.app_key,
            "timestamp": str(timestamp),
            "shop_id": self.shop_id,
        }
        sign = _sign(self.app_secret, path, sign_params)

        query: dict = {
            **sign_params,
            "sign": sign,
            "access_token": self.access_token,
        }

        resp = self.session.post(
            f"{BASE_URL}{path}",
            params=query,
            json=body or {},
        )
        resp.raise_for_status()
        return resp.json()

    def get_orders(
        self,
        status: str = "unfulfilled",
        limit: int = 100,
    ) -> list[dict]:
        """Fetch orders from TikTok Shop.

        Args:
            status: Fulfillment status filter. Accepted values:
                    "unfulfilled", "fulfilled", "partial", "any".
            limit: Max orders per request (TikTok Shop max is 100).

        Returns:
            List of order dicts with full detail from TikTok Shop.
        """
        create_time_from = int(time.time()) - 15 * 24 * 3600  # last 15 days
        create_time_to = int(time.time())

        tiktok_status = _STATUS_MAP.get(status, "")

        body: dict = {
            "page_size": min(limit, 100),
            "sort_by": "CREATE_TIME",
            "sort_type": 2,  # descending
            "create_time_from": create_time_from,
            "create_time_to": create_time_to,
        }
        if tiktok_status:
            body["order_status"] = tiktok_status

        data = self._post("/api/orders/search", body)
        order_list = data.get("data", {}).get("order_list", [])

        if not order_list:
            return []

        # Fetch full order details in a batch.
        order_ids = [o["order_id"] for o in order_list]
        detail_data = self._post(
            "/api/orders/detail/query",
            {"order_id_list": order_ids},
        )
        return detail_data.get("data", {}).get("order_list", [])

    def extract_delivery_addresses(
        self,
        status: str = "unfulfilled",
    ) -> list[DeliveryAddress]:
        """Extract delivery addresses from TikTok Shop orders.

        Args:
            status: Fulfillment status filter passed to get_orders().

        Returns:
            List of DeliveryAddress objects for orders that have a
            recipient address.
        """
        orders = self.get_orders(status=status)
        addresses: list[DeliveryAddress] = []

        for order in orders:
            recipient = order.get("recipient_address")
            if not recipient:
                continue

            addresses.append(
                DeliveryAddress(
                    order_id=order.get("order_id", ""),
                    order_name=order.get("order_id", ""),
                    name=recipient.get("name", ""),
                    address1=recipient.get("address_detail", ""),
                    address2=recipient.get("address_line2", ""),
                    city=recipient.get("city", ""),
                    province=recipient.get("state", ""),
                    country=recipient.get("region_code", ""),
                    zip_code=recipient.get("zipcode", ""),
                    phone=recipient.get("phone", ""),
                    latitude=None,
                    longitude=None,
                )
            )

        return addresses
