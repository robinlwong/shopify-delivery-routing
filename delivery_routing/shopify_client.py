"""Shopify API client for extracting order and address information."""

import os
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

API_VERSION = "2024-01"


@dataclass
class DeliveryAddress:
    """A delivery address extracted from a Shopify order."""

    order_id: int
    order_name: str
    name: str
    address1: str
    address2: str
    city: str
    province: str
    country: str
    zip_code: str
    phone: str
    latitude: float | None = None
    longitude: float | None = None

    @property
    def full_address(self) -> str:
        parts = [self.address1]
        if self.address2:
            parts.append(self.address2)
        parts.extend([self.city, self.province, self.zip_code, self.country])
        return ", ".join(p for p in parts if p)


class ShopifyClient:
    """Client for the Shopify Admin REST API."""

    def __init__(
        self,
        store_url: str | None = None,
        access_token: str | None = None,
    ):
        self.store_url = (store_url or os.getenv("SHOPIFY_STORE_URL", "")).rstrip("/")
        self.access_token = access_token or os.getenv("SHOPIFY_ACCESS_TOKEN", "")
        if not self.store_url or not self.access_token:
            raise ValueError(
                "SHOPIFY_STORE_URL and SHOPIFY_ACCESS_TOKEN must be set "
                "either as arguments or in a .env file."
            )
        self.base_url = f"https://{self.store_url}/admin/api/{API_VERSION}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Shopify-Access-Token": self.access_token,
                "Content-Type": "application/json",
            }
        )

    def _get(self, endpoint: str, params: dict | None = None) -> dict:
        url = f"{self.base_url}/{endpoint}.json"
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    def get_orders(
        self,
        status: str = "unfulfilled",
        limit: int = 250,
    ) -> list[dict]:
        """Fetch orders from Shopify.

        Args:
            status: Fulfillment status filter. Common values:
                    "unfulfilled", "any", "partial", "fulfilled".
            limit: Max orders per page (Shopify max is 250).

        Returns:
            List of order dicts from the Shopify API.
        """
        params: dict = {
            "status": "any",
            "fulfillment_status": status,
            "limit": limit,
        }
        data = self._get("orders", params)
        return data.get("orders", [])

    def extract_delivery_addresses(
        self,
        status: str = "unfulfilled",
    ) -> list[DeliveryAddress]:
        """Extract delivery addresses from orders.

        Args:
            status: Fulfillment status filter passed to get_orders().

        Returns:
            List of DeliveryAddress objects for orders that have a
            shipping address.
        """
        orders = self.get_orders(status=status)
        addresses: list[DeliveryAddress] = []

        for order in orders:
            shipping = order.get("shipping_address")
            if not shipping:
                continue

            addresses.append(
                DeliveryAddress(
                    order_id=order["id"],
                    order_name=order.get("name", ""),
                    name=f'{shipping.get("first_name", "")} {shipping.get("last_name", "")}'.strip(),
                    address1=shipping.get("address1", ""),
                    address2=shipping.get("address2", ""),
                    city=shipping.get("city", ""),
                    province=shipping.get("province", ""),
                    country=shipping.get("country", ""),
                    zip_code=shipping.get("zip", ""),
                    phone=shipping.get("phone", ""),
                    latitude=shipping.get("latitude"),
                    longitude=shipping.get("longitude"),
                )
            )

        return addresses
