#!/usr/bin/env python3
"""CLI entry point for the e-commerce delivery route planner."""

import argparse
import csv
import sys

from delivery_routing.base_client import EcommercePlatformClient
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


def _build_client(args) -> EcommercePlatformClient:
    """Instantiate the correct platform client based on CLI arguments.

    Args:
        args: Parsed argparse namespace.

    Returns:
        An EcommercePlatformClient instance for the chosen platform.
    """
    platform = args.platform.lower()

    if platform == "shopify":
        from delivery_routing.shopify_client import ShopifyClient
        return ShopifyClient(
            store_url=args.store_url,
            access_token=args.access_token,
        )

    if platform == "shopee":
        from delivery_routing.shopee_client import ShopeeClient
        return ShopeeClient(
            partner_id=args.partner_id,
            partner_key=args.partner_key,
            shop_id=args.shop_id,
            access_token=args.access_token,
        )

    if platform == "lazada":
        from delivery_routing.lazada_client import LazadaClient
        return LazadaClient(
            app_key=args.app_key,
            app_secret=args.app_secret,
            access_token=args.access_token,
            region=args.region,
        )

    if platform == "tiktok":
        from delivery_routing.tiktok_client import TikTokClient
        return TikTokClient(
            app_key=args.app_key,
            app_secret=args.app_secret,
            access_token=args.access_token,
            shop_id=args.shop_id,
        )

    raise ValueError(f"Unsupported platform: {platform}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract delivery addresses from e-commerce orders and plan a route.",
    )
    parser.add_argument(
        "--platform",
        default="shopify",
        choices=["shopify", "shopee", "lazada", "tiktok"],
        help='E-commerce platform to fetch orders from (default: "shopify").',
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

    # Shared credential argument.
    parser.add_argument(
        "--access-token",
        help="API access token (overrides platform-specific env var).",
    )

    # Shopify-specific arguments.
    shopify_group = parser.add_argument_group("Shopify options")
    shopify_group.add_argument(
        "--store-url",
        help="Shopify store URL (overrides SHOPIFY_STORE_URL env var).",
    )

    # Shopee-specific arguments.
    shopee_group = parser.add_argument_group("Shopee options")
    shopee_group.add_argument(
        "--partner-id",
        help="Shopee partner ID (overrides SHOPEE_PARTNER_ID env var).",
    )
    shopee_group.add_argument(
        "--partner-key",
        help="Shopee partner key (overrides SHOPEE_PARTNER_KEY env var).",
    )

    # Lazada-specific arguments.
    lazada_group = parser.add_argument_group("Lazada options")
    lazada_group.add_argument(
        "--region",
        help="Lazada region code: sg, my, th, ph, id, vn (overrides LAZADA_REGION env var).",
    )

    # Shared arguments used by multiple platforms.
    shared_group = parser.add_argument_group("Shopee / Lazada / TikTok options")
    shared_group.add_argument(
        "--app-key",
        help="App key for Lazada or TikTok (overrides platform-specific env var).",
    )
    shared_group.add_argument(
        "--app-secret",
        help="App secret for Lazada or TikTok (overrides platform-specific env var).",
    )
    shared_group.add_argument(
        "--shop-id",
        help="Shop ID for Shopee or TikTok (overrides platform-specific env var).",
    )

    args = parser.parse_args()

    try:
        client = _build_client(args)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    platform_name = args.platform.capitalize()
    if args.platform == "tiktok":
        platform_name = "TikTok Shop"

    print(f"Fetching orders from {platform_name}...")
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
