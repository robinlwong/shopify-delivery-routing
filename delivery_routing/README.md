Summary
This PR introduces a complete delivery route planning tool that integrates with Shopify's Admin API to extract order addresses and optimize delivery routes using a nearest-neighbour heuristic algorithm.

Key Changes
Shopify API Integration (shopify_client.py): New client for fetching orders and extracting delivery addresses from Shopify, with support for environment-based or CLI-provided credentials
Route Planning Engine (route_planner.py): Implements nearest-neighbour heuristic with haversine distance calculations for geographic routing optimization
CLI Interface (main.py): User-friendly command-line tool with options to filter by fulfillment status, export routes to CSV, and override credentials
Project Setup: Added .env.example, .gitignore, requirements.txt, and comprehensive README.md with setup and usage instructions
Implementation Details
Distance Calculation: Uses the haversine formula to compute great-circle distances between lat/lon coordinates
Graceful Degradation: Addresses without coordinates are appended at the end of the route with warnings, ensuring no orders are lost
Flexible Configuration: Supports both environment variables (.env) and command-line arguments for Shopify credentials
CSV Export: Routes can be exported to CSV for use in external tools or mapping applications
Shopify API Version: Uses the 2024-01 Admin API version with read_orders scope requirement
The nearest-neighbour algorithm provides a fast, practical solution for small to medium-sized delivery routes while remaining simple to understand and maintain.

https://claude.ai/code/session_017UNsyrZdkUjJxzePrA19wJ

