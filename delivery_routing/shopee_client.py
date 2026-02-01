"""Shopee Open Platform API client for extracting order and address information."""

import hashlib
import hmac
import os
import time

import requests
from dotenv import load_dotenv

from delivery_routing.base_client import EcommercePlatformClient
from delivery_routing.models import DeliveryAddress

load_dotenv()

BASE_URL = "https://partner.shopeemobile.com/api/v2"

# Mapping from generic status names to Shopee order statuses.
_STATUS_MAP = {
    "unfulfilled": "READY_TO_SHIP",
    "fulfilled": "SHIPPED",
    "partial": "RETRY_SHIP",
    "any": "",
}


def _sign(partner_id: int, partner_key: str, path: str,
          timestamp: int, access_token: str, shop_id: int) -> str:
    """Generate HMAC-SHA256 signature for Shopee API v2.

    Args:
        partner_id: Shopee partner ID.
        partner_key: Shopee partner key (secret).
        path: API endpoint path (e.g. /api/v2/order/get_order_list).
        timestamp: Unix timestamp in seconds.
        access_token: OAuth access token.
        shop_id: Shopee shop ID.

    Returns:
        Hex-encoded HMAC-SHA256 signature string.
    """
    base_string = f"{partner_id}{path}{timestamp}{access_token}{shop_id}"
    return hmac.new(
        partner_key.encode("utf-8"),
        base_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class ShopeeClient(EcommercePlatformClient):
    """Client for the Shopee Open Platform API v2."""

    def __init__(
        self,
        partner_id: str | None = None,
        partner_key: str | None = None,
        shop_id: str | None = None,
        access_token: str | None = None,
    ):
        self.partner_id = int(partner_id or os.getenv("SHOPEE_PARTNER_ID", "0"))
        self.partner_key = partner_key or os.getenv("SHOPEE_PARTNER_KEY", "")
        self.shop_id = int(shop_id or os.getenv("SHOPEE_SHOP_ID", "0"))
        self.access_token = access_token or os.getenv("SHOPEE_ACCESS_TOKEN", "")

        if not self.partner_id or not self.partner_key or not self.shop_id or not self.access_token:
            raise ValueError(
                "SHOPEE_PARTNER_ID, SHOPEE_PARTNER_KEY, SHOPEE_SHOP_ID, and "
                "SHOPEE_ACCESS_TOKEN must be set either as arguments or in a .env file."
            )

        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Make a signed GET request to the Shopee API.

        Args:
            path: API endpoint path (e.g. /api/v2/order/get_order_list).
            params: Additional query parameters.

        Returns:
            Parsed JSON response dict.
        """
        timestamp = int(time.time())
        sign = _sign(
            self.partner_id, self.partner_key, path,
            timestamp, self.access_token, self.shop_id,
        )

        query: dict = {
            "partner_id": self.partner_id,
            "timestamp": timestamp,
            "access_token": self.access_token,
            "shop_id": self.shop_id,
            "sign": sign,
        }
        if params:
            query.update(params)

        resp = self.session.get(f"{BASE_URL}{path}", params=query)
        resp.raise_for_status()
        return resp.json()

    def get_orders(
        self,
        status: str = "unfulfilled",
        limit: int = 100,
    ) -> list[dict]:
        """Fetch orders from Shopee.

        Args:
            status: Fulfillment status filter. Accepted values:
                    "unfulfilled", "fulfilled", "partial", "any".
            limit: Max orders per request (Shopee max is 100).

        Returns:
            List of order dicts with full detail from the Shopee API.
        """
        time_from = int(time.time()) - 15 * 24 * 3600  # last 15 days
        time_to = int(time.time())

        params: dict = {
            "time_range_field": "create_time",
            "time_from": time_from,
            "time_to": time_to,
            "page_size": min(limit, 100),
            "cursor": "",
        }
        shopee_status = _STATUS_MAP.get(status, "")
        if shopee_status:
            params["order_status"] = shopee_status

        data = self._get("/api/v2/order/get_order_list", params)
        response = data.get("response", {})
        order_list = response.get("order_list", [])

        if not order_list:
            return []

        # Fetch full order details (including addresses) in a single batch.
        order_sn_list = ",".join(o["order_sn"] for o in order_list)
        detail_params: dict = {
            "order_sn_list": order_sn_list,
            "response_optional_fields": (
                "buyer_username,recipient_address,note"
            ),
        }
        detail_data = self._get("/api/v2/order/get_order_detail", detail_params)
        return detail_data.get("response", {}).get("order_list", [])

    def extract_delivery_addresses(
        self,
        status: str = "unfulfilled",
    ) -> list[DeliveryAddress]:
        """Extract delivery addresses from Shopee orders.

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
                    order_id=order.get("order_sn", ""),
                    order_name=order.get("order_sn", ""),
                    name=recipient.get("name", ""),
                    address1=recipient.get("full_address", ""),
                    address2=recipient.get("district", ""),
                    city=recipient.get("city", ""),
                    province=recipient.get("state", ""),
                    country=recipient.get("region", ""),
                    zip_code=recipient.get("zipcode", ""),
                    phone=recipient.get("phone", ""),
                    latitude=None,
                    longitude=None,
                )
            )

        return addresses
