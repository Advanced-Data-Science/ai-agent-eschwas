import json
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def get_polygon_tickers(limit=5):
    """
    Minimal test call to Polygon: list reference tickers.
    Docs: GET /v3/reference/tickers
    """
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        api_key = config.get("polygon_api_key")
    except Exception as e:
        logging.error(f"Could not load config.json: {e}")
        return None

    if not api_key:
        logging.error("polygon_api_key not found in config.json")
        return None

    url = "https://api.polygon.io/v3/reference/tickers"
    params = {
        "active": "true",
        "limit": limit,
        "apiKey": api_key
    }

    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Polygon request failed: {e}")
        return None

# Run the test
data = get_polygon_tickers(limit=5)
if data:
    results = data.get("results", [])
    print(f"\nRetrieved {len(results)} tickers:")
    for r in results:
        # Each r has fields like 'ticker', 'name', 'market', etc.
        print(f" - {r.get('ticker')} — {r.get('name')}")
    # Save raw JSON so you can show it works
    with open("api_test.json", "w") as f:
        json.dump(data, f, indent=2)
    print('\nSaved raw API response to "polygon_sample.json"')
else:
    print("No data returned. Check your key, network, or rate limits.")