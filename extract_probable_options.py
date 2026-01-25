"""
Extract ALL tradeable options from Probable Markets
Uses the /events API to get correct URLs (not regex guessing)
"""

import requests
import json
import time


API_BASE = "https://market-api.probable.markets/public/api/v1"
OUTPUT_FILE = "probable_markets.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}


def fetch_event_url_map():
    """
    Fetch all events and build a mapping of market_id -> event_slug
    The event_slug is the CORRECT URL path that works on the website
    """
    print("  Building event URL map from /events API...")
    market_to_event = {}

    page = 1
    total_events = 0

    while True:
        try:
            resp = requests.get(
                f"{API_BASE}/events",
                headers=HEADERS,
                params={"page": page, "limit": 50},
                timeout=30
            )
            resp.raise_for_status()
            events = resp.json()

            if not events:
                break

            for event in events:
                event_slug = event.get("slug", "")
                markets = event.get("markets", [])

                for market in markets:
                    market_id = str(market.get("id", ""))
                    if market_id and event_slug:
                        market_to_event[market_id] = event_slug

            total_events += len(events)
            page += 1

            # Check if we got fewer than limit (last page)
            if len(events) < 50:
                break

            time.sleep(0.2)

        except Exception as e:
            print(f"    Error fetching events page {page}: {e}")
            break

    print(f"    Mapped {len(market_to_event)} markets to {total_events} events")
    return market_to_event


def fetch_all_markets():
    """Fetch all active Probable markets with pagination"""
    all_markets = []
    page = 1

    while True:
        print(f"  Fetching markets page {page}...")
        try:
            resp = requests.get(
                f"{API_BASE}/markets",
                headers=HEADERS,
                params={"page": page, "limit": 50},
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            markets = data.get("markets", [])
            pagination = data.get("pagination", {})

            if not markets:
                break

            # Filter for active, non-closed markets
            active_markets = [m for m in markets if m.get("active") and not m.get("closed")]
            all_markets.extend(active_markets)

            print(f"    Found {len(markets)} markets ({len(active_markets)} active)")

            # Check if more pages
            if not pagination.get("hasMore", False):
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            print(f"    Error fetching page {page}: {e}")
            break

    return all_markets


def extract_probable_options(markets, event_url_map):
    """Flatten Probable markets into tradeable options"""
    all_options = []
    urls_from_api = 0
    urls_fallback = 0

    for m in markets:
        market_id = str(m.get("id", ""))
        title = m.get("question", "").strip()
        slug = m.get("market_slug", market_id)

        # Parse outcomes (it's a JSON string)
        try:
            outcomes = json.loads(m.get("outcomes", "[]"))
        except:
            outcomes = []

        # Get URL from event API mapping (authoritative source)
        if market_id in event_url_map:
            event_slug = event_url_map[market_id]
            url = f"https://probable.markets/event/{event_slug}"
            urls_from_api += 1
        else:
            # Fallback: use market slug directly (for markets not in events)
            url = f"https://probable.markets/event/{slug}"
            urls_fallback += 1

        if not title or not outcomes:
            continue

        # Binary market (2 outcomes like Yes/No or Team1/Team2)
        if len(outcomes) == 2:
            all_options.append({
                "platform": "probable",
                "market_type": "binary",
                "market_id": market_id,
                "title": title,
                "option_title": title,
                "outcomes": outcomes,
                "url": url
            })

        # Categorical / multi-option (more than 2 outcomes)
        else:
            title_clean = title.encode("ascii", "ignore").decode("ascii")
            print(f"\n  Categorical: {title_clean} ({len(outcomes)} options)")

            for outcome in outcomes:
                option_clean = str(outcome).encode("ascii", "ignore").decode("ascii")
                print(f"    - {option_clean}")

                all_options.append({
                    "platform": "probable",
                    "market_type": "categorical_option",
                    "parent_market_id": market_id,
                    "parent_title": title,
                    "market_id": f"{market_id}:{outcome}",
                    "title": f"{title} - {outcome}",
                    "option_title": outcome,
                    "url": url
                })

    print(f"\n  URL sources: {urls_from_api} from API, {urls_fallback} fallback")
    return all_options


def main():
    print("\n" + "=" * 80)
    print("EXTRACTING PROBABLE MARKETS")
    print("=" * 80)

    # Step 1: Build event URL mapping from /events API
    event_url_map = fetch_event_url_map()

    # Step 2: Fetch all active markets
    markets = fetch_all_markets()
    print(f"\nTotal active markets fetched: {len(markets)}")

    # Step 3: Extract options with correct URLs
    options = extract_probable_options(markets, event_url_map)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(options, f, indent=2)

    print("\n" + "=" * 80)
    print("EXTRACTION COMPLETE")
    print("=" * 80)
    print(f"Total tradeable options: {len(options)}")
    print(f"  Binary: {len([o for o in options if o['market_type'] == 'binary'])}")
    print(f"  Categorical: {len([o for o in options if o['market_type'] == 'categorical_option'])}")
    print(f"\nSaved to: {OUTPUT_FILE}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
