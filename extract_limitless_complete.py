"""
Extract ALL Limitless markets including categorical/group markets
"""
import requests
import json
import time


def extract_limitless_markets():
    """Extract all active Limitless markets with categorical options"""
    print("=" * 80)
    print("EXTRACTING LIMITLESS MARKETS (INCLUDING CATEGORICAL)")
    print("=" * 80)

    all_options = []
    page = 1
    limit = 25

    while True:
        print(f"\n  Fetching page {page}...")
        url = f"https://api.limitless.exchange/markets/active?page={page}&limit={limit}"

        try:
            resp = requests.get(url, timeout=30)
            data = resp.json()

            # Handle both list and dict responses
            if isinstance(data, dict):
                markets = data.get('data', [])
            else:
                markets = data

            if not markets or len(markets) == 0:
                break

            print(f"  Found {len(markets)} markets on page {page}")

            for market in markets:
                if not isinstance(market, dict):
                    continue
                market_type = market.get('marketType', 'binary')
                slug = market.get('slug', '')
                market_id = market.get('id')
                title = market.get('title', '')

                # Skip if no slug
                if not slug:
                    continue

                if market_type == 'group':
                    # This is a categorical market - fetch details to get sub-markets
                    title_clean = title.encode('ascii', 'ignore').decode('ascii')
                    print(f"    Fetching categorical market: {title_clean}")

                    try:
                        detail_resp = requests.get(f"https://api.limitless.exchange/markets/{slug}", timeout=10)
                        detail = detail_resp.json()

                        sub_markets = detail.get('markets', [])
                        parent_title = detail.get('title', title)

                        print(f"      Found {len(sub_markets)} options")

                        for sub_market in sub_markets:
                            option_title = sub_market.get('title', '')
                            sub_slug = sub_market.get('slug', '')
                            sub_id = sub_market.get('id')
                            tokens = sub_market.get('tokens', {})

                            if option_title and sub_slug:
                                all_options.append({
                                    'platform': 'limitless',
                                    'market_type': 'categorical_option',
                                    'parent_market_id': market_id,
                                    'parent_title': parent_title,
                                    'market_id': sub_id,
                                    'title': f"{parent_title} - {option_title}",
                                    'option_title': option_title,
                                    'slug': sub_slug,
                                    'yes_token_id': tokens.get('yes'),
                                    'no_token_id': tokens.get('no'),
                                    'url': f"https://limitless.exchange/pro/markets/{sub_slug}"
                                })

                        time.sleep(0.1)  # Rate limit

                    except Exception as e:
                        print(f"      Error fetching details: {e}")

                else:
                    # Binary market
                    tokens = market.get('tokens', {})

                    all_options.append({
                        'platform': 'limitless',
                        'market_type': 'binary',
                        'market_id': market_id,
                        'title': title,
                        'option_title': title,
                        'slug': slug,
                        'yes_token_id': tokens.get('yes'),
                        'no_token_id': tokens.get('no'),
                        'url': f"https://limitless.exchange/pro/markets/{slug}"
                    })

            page += 1
            time.sleep(0.2)  # Rate limit between pages

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    print(f"\n" + "=" * 80)
    print(f"EXTRACTION COMPLETE")
    print(f"=" * 80)
    print(f"Total Limitless options: {len(all_options)}")
    print(f"  Binary markets: {len([o for o in all_options if o['market_type'] == 'binary'])}")
    print(f"  Categorical options: {len([o for o in all_options if o['market_type'] == 'categorical_option'])}")

    # Save
    with open('limitless_markets_complete.json', 'w', encoding='utf-8') as f:
        json.dump(all_options, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to: limitless_markets_complete.json")
    print("=" * 80)

    return all_options


if __name__ == "__main__":
    extract_limitless_markets()
