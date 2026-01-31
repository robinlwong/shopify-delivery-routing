#!/usr/bin/env python3
"""CLI entry point for the Shopify delivery route planner."""

import argparse
import csv
import sys

from delivery_routing.shopify_client import ShopifyClient
from delivery_routing.route_planner import nearest_neighbour_route, total_route_distance


def _print_route(addresses, total_km):
    """Print the planned route to stdout."""
    print(f"\n{'=' * 70}")
    print("  DELIVERY ROUTE PLAN")
    print(f"  {len(addresses)} stops | {total_km:.2f} km estimated total distance")
    print(f"{'=' * 70}\n")

    for i, addr in enumerate(addresses, 1):
        print(f"  Stop {i}: {addr.order_name}")
        print(f"    Name:    {addr.name}")
        print(f"    Address: {addr.full_address}")
        if addr.phone:
            print(f"    Phone:   {addr.phone}")
        if addr.latitude and addr.longitude:
            print(f"    Coords:  {addr.latitude}, {addr.longitude}")
        print()


def _export_csv(addresses, path):
    """Export the route to a CSV file."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "stop", "order_name", "name", "address",
            "city", "province", "zip", "country",
            "phone", "latitude", "longitude",
        ])
        for i, addr in enumerate(addresses, 1):
            writer.writerow([
                i, addr.order_name, addr.name, addr.full_address,
                addr.city, addr.province, addr.zip_code, addr.country,
                addr.phone, addr.latitude or "", addr.longitude or "",
            ])
    print(f"Route exported to {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract Shopify delivery addresses and plan a route.",
    )
    parser.add_argument(
        "--status",
        default="unfulfilled",
        help='Fulfillment status filter (default: "unfulfilled").',
    )
    parser.add_argument(
        "--csv",
        metavar="FILE",
        help="Export the planned route to a CSV file.",
    )
    parser.add_argument(
        "--store-url",
        help="Shopify store URL (overrides SHOPIFY_STORE_URL env var).",
    )
    parser.add_argument(
        "--access-token",
        help="Shopify access token (overrides SHOPIFY_ACCESS_TOKEN env var).",
    )
    args = parser.parse_args()

    try:
        client = ShopifyClient(
            store_url=args.store_url,
            access_token=args.access_token,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Fetching orders from Shopify...")
    addresses = client.extract_delivery_addresses(status=args.status)

    if not addresses:
        print("No orders with shipping addresses found.")
        sys.exit(0)

    print(f"Found {len(addresses)} delivery address(es).")

    # Filter to addresses with coordinates for routing.
    routable = [a for a in addresses if a.latitude and a.longitude]
    unroutable = [a for a in addresses if not (a.latitude and a.longitude)]

    if unroutable:
        print(
            f"\nWarning: {len(unroutable)} address(es) have no coordinates "
            "and will be appended at the end of the route:"
        )
        for addr in unroutable:
            print(f"  - {addr.order_name}: {addr.full_address}")

    if routable:
        planned = nearest_neighbour_route(routable)
        total_km = total_route_distance(planned)
    else:
        planned = []
        total_km = 0.0

    # Append unroutable addresses at the end so they aren't lost.
    full_route = planned + unroutable
    _print_route(full_route, total_km)

    if args.csv:
        _export_csv(full_route, args.csv)


if __name__ == "__main__":
    main()
