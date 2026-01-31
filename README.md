# delivery-routing

Python tool to extract delivery addresses from Shopify orders and plan an
optimised delivery route using the nearest-neighbour heuristic.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and fill in your Shopify credentials:

```bash
cp .env.example .env
```

You need a **Shopify custom app** with the `read_orders` access scope.
Get the Admin API access token from your app settings.

## Usage

```bash
# Plan a route for all unfulfilled orders (default)
python -m delivery_routing.main

# Filter by fulfillment status
python -m delivery_routing.main --status any

# Export route to CSV
python -m delivery_routing.main --csv route.csv

# Pass credentials directly instead of using .env
python -m delivery_routing.main --store-url my-store.myshopify.com --access-token shpat_xxx
```

## How it works

1. Connects to the Shopify Admin REST API and fetches orders matching the
   given fulfillment status.
2. Extracts shipping addresses (including lat/lon coordinates when available).
3. Builds a distance matrix using the haversine formula.
4. Applies a nearest-neighbour heuristic to order the stops into a short route.
5. Prints the route to the terminal and optionally exports it to CSV.

Addresses without coordinates are appended at the end of the route with a
warning so they are not lost.
