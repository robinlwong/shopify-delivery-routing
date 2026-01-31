# CLAUDE.md

This file provides guidance for AI assistants working with the **shopify-delivery-routing** codebase.

## Project Overview

A Python CLI tool that fetches delivery addresses from Shopify orders and plans optimized delivery routes using the nearest-neighbour heuristic algorithm. It connects to the Shopify Admin REST API, extracts shipping addresses with geographic coordinates, computes distances via the haversine formula, and outputs an ordered route to stdout or CSV.

## Repository Structure

```
shopify-delivery-routing/
├── CLAUDE.md                 # This file
├── README.md                 # User-facing documentation
├── .env.example              # Template for required environment variables
├── .gitignore                # Python-standard ignore patterns
├── requirements.txt          # Python dependencies (requests, python-dotenv)
└── delivery_routing/         # Main Python package
    ├── __init__.py           # Package marker (empty)
    ├── README.md             # PR summary / implementation notes
    ├── main.py               # CLI entry point (argparse, output formatting, CSV export)
    ├── shopify_client.py     # Shopify Admin REST API client + DeliveryAddress dataclass
    └── route_planner.py      # Haversine distance + nearest-neighbour route optimizer
```

## Architecture

The codebase follows a three-layer architecture:

```
CLI Layer (main.py)            -- argument parsing, display, CSV export
    |
Business Logic (route_planner.py)  -- distance matrix, nearest-neighbour routing
    |
Integration Layer (shopify_client.py) -- Shopify API communication
    |
External (Shopify Admin REST API v2024-01)
```

### Key modules

- **`main.py`** -- Entry point. Orchestrates the full pipeline: parse args, init client, fetch orders, plan route, output results. Run via `python -m delivery_routing.main`.
- **`shopify_client.py`** -- `ShopifyClient` class wraps the Shopify Admin REST API. `DeliveryAddress` dataclass holds per-order address data (including optional lat/lon). Credentials come from `.env` or CLI args.
- **`route_planner.py`** -- Pure-logic module with no external dependencies. `haversine()` computes great-circle distance. `nearest_neighbour_route()` implements the greedy routing heuristic. `total_route_distance()` sums the planned route length.

### Data flow

1. Fetch orders from Shopify API filtered by fulfillment status
2. Extract `DeliveryAddress` objects from order shipping data
3. Separate addresses into routable (have lat/lon) and unroutable (missing coords)
4. Build symmetric distance matrix using haversine formula
5. Apply nearest-neighbour heuristic starting from index 0
6. Append unroutable addresses to end of route
7. Print formatted route and/or export to CSV

## Language and Runtime

- **Python 3.10+** required (uses `float | None` union syntax in type hints)
- Detected runtime: Python 3.11
- No `pyproject.toml`, `setup.py`, or `setup.cfg` -- run as a module directly

## Dependencies

Listed in `requirements.txt`:

| Package | Min Version | Purpose |
|---|---|---|
| `requests` | >=2.31.0 | HTTP client for Shopify API |
| `python-dotenv` | >=1.0.0 | Load `.env` file into environment |

Install with:
```bash
pip install -r requirements.txt
```

## Configuration

### Environment variables (required)

| Variable | Description | Example |
|---|---|---|
| `SHOPIFY_STORE_URL` | Store's `.myshopify.com` domain | `my-store.myshopify.com` |
| `SHOPIFY_ACCESS_TOKEN` | Admin API access token from a custom app | `shpat_xxxx...` |

Copy `.env.example` to `.env` and fill in values. CLI args `--store-url` and `--access-token` override the `.env` values.

### Shopify app requirements

The connected Shopify custom app needs the `read_orders` access scope.

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default settings (unfulfilled orders)
python -m delivery_routing.main

# Filter by fulfillment status
python -m delivery_routing.main --status any

# Export route to CSV
python -m delivery_routing.main --csv route.csv

# Override credentials via CLI
python -m delivery_routing.main --store-url my-store.myshopify.com --access-token shpat_xxx
```

There are no test, lint, or build commands configured for this project.

## Code Conventions

- **Type hints**: Modern Python 3.10+ union syntax (`float | None`, `str | None`, `dict | None`). Use these in all new code.
- **Dataclasses**: Used for data containers (`DeliveryAddress`). Prefer `@dataclass` over plain dicts for structured data.
- **Docstrings**: Google-style with `Args:` and `Returns:` sections.
- **Private functions**: Prefixed with underscore (`_print_route`, `_export_csv`, `_build_distance_matrix`).
- **Imports**: Standard library first, then third-party, then local -- one import per line.
- **String formatting**: f-strings throughout.
- **No formatter/linter configured**: Code follows PEP 8 implicitly. Maintain consistent 4-space indentation.
- **Module execution**: Entry point is `python -m delivery_routing.main` (uses `if __name__ == "__main__"` guard).

## API and Constants

- **Shopify API version**: `2024-01` (defined as `API_VERSION` in `shopify_client.py:11`)
- **Earth radius**: `6371.0 km` (defined as `_EARTH_RADIUS_KM` in `route_planner.py:8`)
- **Max orders per page**: 250 (Shopify API limit, used in `get_orders()`)

## Known Limitations

- No pagination beyond Shopify's 250-order-per-request limit
- Nearest-neighbour is a greedy heuristic -- produces good but not globally optimal routes
- No retry/backoff logic for Shopify API calls
- No unit tests, CI/CD, or linting configuration
- Addresses without coordinates are appended to the route unsorted
- Purely synchronous execution (no async)
