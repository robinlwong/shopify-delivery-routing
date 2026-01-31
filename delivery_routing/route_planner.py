"""Delivery route planner using nearest-neighbour heuristic."""

from math import atan2, cos, radians, sin, sqrt

from delivery_routing.shopify_client import DeliveryAddress

# Approximate radius of Earth in kilometres.
_EARTH_RADIUS_KM = 6371.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in km between two lat/lon points."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return _EARTH_RADIUS_KM * 2 * atan2(sqrt(a), sqrt(1 - a))


def _build_distance_matrix(
    addresses: list[DeliveryAddress],
) -> list[list[float]]:
    """Build a symmetric distance matrix between all addresses."""
    n = len(addresses)
    matrix: list[list[float]] = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine(
                addresses[i].latitude or 0.0,
                addresses[i].longitude or 0.0,
                addresses[j].latitude or 0.0,
                addresses[j].longitude or 0.0,
            )
            matrix[i][j] = d
            matrix[j][i] = d
    return matrix


def nearest_neighbour_route(
    addresses: list[DeliveryAddress],
    start_index: int = 0,
) -> list[DeliveryAddress]:
    """Plan a delivery route using the nearest-neighbour heuristic.

    Starting from ``start_index``, the algorithm repeatedly visits the
    closest unvisited address until all addresses have been included.

    Args:
        addresses: List of delivery addresses with lat/lon coordinates.
        start_index: Index into *addresses* to start the route from.

    Returns:
        The addresses reordered as a delivery route.
    """
    if not addresses:
        return []

    n = len(addresses)
    if start_index < 0 or start_index >= n:
        raise ValueError(f"start_index {start_index} out of range [0, {n})")

    matrix = _build_distance_matrix(addresses)
    visited = [False] * n
    route_indices: list[int] = [start_index]
    visited[start_index] = True

    for _ in range(n - 1):
        current = route_indices[-1]
        best_dist = float("inf")
        best_idx = -1
        for j in range(n):
            if not visited[j] and matrix[current][j] < best_dist:
                best_dist = matrix[current][j]
                best_idx = j
        visited[best_idx] = True
        route_indices.append(best_idx)

    return [addresses[i] for i in route_indices]


def total_route_distance(addresses: list[DeliveryAddress]) -> float:
    """Return the total distance in km for an ordered list of addresses."""
    total = 0.0
    for i in range(len(addresses) - 1):
        total += haversine(
            addresses[i].latitude or 0.0,
            addresses[i].longitude or 0.0,
            addresses[i + 1].latitude or 0.0,
            addresses[i + 1].longitude or 0.0,
        )
    return total
