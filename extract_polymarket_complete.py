"""
Complete Polymarket extraction - fetch ALL active markets and ALL options
Fixes the root cause: previous extraction skipped multi-option markets
"""

import json
import requests
import time


def fetch_all_polymarket_options():
    """
    Fetch ALL Polymarket options (binary + categorical)
    Uses Gamma API /events endpoint with pagination
    """
    base_url = "https://gamma-api.polymarket.com"
    all_options = []

    # Step 1: Fetch all events
    print("\n" + "="*80)
    print("FETCHING ALL POLYMARKET EVENTS")
    print("="*80)

    events = []
    offset = 0
    limit = 100
    max_offset = 10000

    while offset < max_offset:
        params = {
            "limit": limit,
            "offset": offset,
            "closed": "false",  # Only active markets
            "order": "id",
            "ascending": "false"
        }

        try:
            response = requests.get(
                f"{base_url}/events",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            batch = response.json()

            if not batch or len(batch) == 0:
                break

            events.extend(batch)
            print(f"  Offset {offset}: Fetched {len(batch)} events (Total: {len(events)})")

            if len(batch) < limit:
                break

            offset += limit
            time.sleep(0.3)  # Rate limiting

        except Exception as e:
            print(f"  Error at offset {offset}: {e}")
            break

    print(f"\nTotal events fetched: {len(events)}")

    # Step 2: Extract options from each event
    print("\n" + "="*80)
    print("EXTRACTING OPTIONS FROM EVENTS")
    print("="*80)

    for idx, event in enumerate(events, 1):
        event_id = event.get("id")
        event_title = event.get("title", "")
        event_slug = event.get("slug", "")
        markets = event.get("markets", [])
        num_markets = len(markets)

        # Skip "updown" / "up or down" markets
        if "updown" in event_slug.lower() or "up or down" in event_title.lower():
            continue

        # Determine if categorical or binary
        if num_markets > 2:
            # CATEGORICAL MARKET: Create one option per market
            try:
                print(f"\n  [{idx}] CATEGORICAL: {event_title} ({num_markets} options)")
            except:
                print(f"\n  [{idx}] CATEGORICAL: [Special chars] ({num_markets} options)")

            for market in markets:
                market_id = market.get("conditionId")
                question = market.get("question", event_title)

                all_options.append({
                    "platform": "polymarket",
                    "market_type": "categorical_option",
                    "event_id": event_id,
                    "market_id": market_id,
                    "parent_title": event_title,
                    "title": question,
                    "option_title": question.replace(event_title, "").strip(" -:"),
                    "slug": event_slug,
                    "url": f"https://polymarket.com/event/{event_slug}",
                })

        elif num_markets == 2:
            # BINARY MARKET: Usually YES/NO, but check if it's actually categorical
            # If both markets have the same question, it's binary YES/NO
            # If they have different questions, treat as 2-option categorical

            questions = [m.get("question", "") for m in markets]

            if len(set(questions)) == 1:
                # TRUE BINARY: Both markets are YES/NO for same question
                question = questions[0] or event_title

                all_options.append({
                    "platform": "polymarket",
                    "market_type": "binary",
                    "event_id": event_id,
                    "market_id": markets[0].get("conditionId"),  # Use first market's ID
                    "title": question,
                    "option_title": question,
                    "slug": event_slug,
                    "url": f"https://polymarket.com/event/{event_slug}",
                })
            else:
                # 2-OPTION CATEGORICAL: Two different outcomes
                try:
                    print(f"\n  [{idx}] 2-OPTION CATEGORICAL: {event_title}")
                except:
                    print(f"\n  [{idx}] 2-OPTION CATEGORICAL: [Special chars]")

                for market in markets:
                    market_id = market.get("conditionId")
                    question = market.get("question", event_title)

                    all_options.append({
                        "platform": "polymarket",
                        "market_type": "categorical_option",
                        "event_id": event_id,
                        "market_id": market_id,
                        "parent_title": event_title,
                        "title": question,
                        "option_title": question.replace(event_title, "").strip(" -:"),
                        "slug": event_slug,
                        "url": f"https://polymarket.com/event/{event_slug}",
                    })

        elif num_markets == 1:
            # SINGLE MARKET: Rare, but exists
            market = markets[0]
            market_id = market.get("conditionId")
            question = market.get("question", event_title)

            all_options.append({
                "platform": "polymarket",
                "market_type": "binary",
                "event_id": event_id,
                "market_id": market_id,
                "title": question,
                "option_title": question,
                "slug": event_slug,
                "url": f"https://polymarket.com/event/{event_slug}",
            })

    return all_options


def main():
    print("\n" + "="*80)
    print("COMPLETE POLYMARKET EXTRACTION")
    print("Extracting ALL active markets (binary + categorical)")
    print("="*80)

    options = fetch_all_polymarket_options()

    # Save to file
    output_file = "polymarket_options_complete.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(options, f, indent=2)

    # Statistics
    binary = [o for o in options if o['market_type'] == 'binary']
    categorical = [o for o in options if o['market_type'] == 'categorical_option']

    print("\n" + "="*80)
    print("EXTRACTION COMPLETE")
    print("="*80)
    print(f"Total options extracted: {len(options)}")
    print(f"  Binary markets: {len(binary)}")
    print(f"  Categorical options: {len(categorical)}")
    print(f"\nSaved to: {output_file}")
    print("="*80 + "\n")

    # Check for Abstract specifically
    abstract_options = [o for o in options if 'abstract' in o['title'].lower() and 'token' in o['title'].lower()]

    if abstract_options:
        print("\n" + "="*80)
        print("ABSTRACT TOKEN MARKETS FOUND")
        print("="*80)
        for opt in abstract_options:
            print(f"\n  Title: {opt['title']}")
            print(f"  Slug: {opt['slug']}")
            print(f"  Type: {opt['market_type']}")
            print(f"  URL: {opt['url']}")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()
