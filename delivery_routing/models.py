"""Shared data models for delivery routing across e-commerce platforms."""

from dataclasses import dataclass


@dataclass
class DeliveryAddress:
    """A delivery address extracted from an e-commerce order."""

    order_id: str
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
