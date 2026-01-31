"""Abstract base class for e-commerce platform clients."""

from abc import ABC, abstractmethod

from delivery_routing.models import DeliveryAddress


class EcommercePlatformClient(ABC):
    """Base class that all e-commerce platform clients must implement."""

    @abstractmethod
    def get_orders(self, status: str = "unfulfilled", limit: int = 250) -> list[dict]:
        """Fetch orders from the platform.

        Args:
            status: Fulfillment status filter.
            limit: Maximum number of orders to fetch.

        Returns:
            List of order dicts from the platform API.
        """

    @abstractmethod
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
