"""
Fetch prices from Probable Markets orderbook
Uses public API endpoint (no auth required for orderbook)
"""

import json
import time
import requests

API_BASE = "https://api.probable.markets"
MARKET_API_BASE = "https://market-api.probable.markets"

HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
}


def get_orderbook(token_id):
    """Get orderbook for a specific token ID"""
    url = f"{API_BASE}/public/api/v1/book?token_id={token_id}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        else:
            return None
    except Exception as e:
        return None


def get_market_details(market_id):
    """Get market details including token IDs from public API"""
    url = f"{MARKET_API_BASE}/public/api/v1/markets/{market_id}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def get_best_prices_from_orderbook(orderbook):
    """Extract best bid/ask from orderbook"""
    if not orderbook:
        return None, None

    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])

    # Best bid is highest, best ask is lowest
    # Sort bids descending, asks ascending
    if bids:
        sorted_bids = sorted(bids, key=lambda x: float(x['price']), reverse=True)
        best_bid = float(sorted_bids[0]['price'])
    else:
        best_bid = None

    if asks:
        sorted_asks = sorted(asks, key=lambda x: float(x['price']))
        best_ask = float(sorted_asks[0]['price'])
    else:
        best_ask = None

    return best_bid, best_ask


def get_probable_price(market_id):
    """
    Get Yes/No prices for a Probable market
    Returns (yes_price, no_price) where prices are cost to BUY that outcome
    """
    # Get market details with token IDs
    market = get_market_details(market_id)
    if not market:
        return None, None

    tokens = market.get('tokens', [])
    if len(tokens) < 2:
        return None, None

    # Find Yes and No token IDs
    yes_token_id = None
    no_token_id = None

    for token in tokens:
        outcome = token.get('outcome', '').lower()
        if outcome == 'yes':
            yes_token_id = token.get('token_id')
        elif outcome == 'no':
            no_token_id = token.get('token_id')

    # For non Yes/No markets (like team names), use first as "Yes" and second as "No"
    if not yes_token_id and len(tokens) >= 2:
        yes_token_id = tokens[0].get('token_id')
        no_token_id = tokens[1].get('token_id')

    # Get orderbook for Yes token
    yes_orderbook = get_orderbook(yes_token_id) if yes_token_id else None
    yes_bid, yes_ask = get_best_prices_from_orderbook(yes_orderbook)

    # Yes price = best ask (cost to buy Yes)
    yes_price = yes_ask

    # For No price, we can either:
    # 1. Get No token orderbook and use its best ask
    # 2. Or calculate from Yes: no_price = 1 - yes_bid
    # Let's get the actual No orderbook
    no_orderbook = get_orderbook(no_token_id) if no_token_id else None
    no_bid, no_ask = get_best_prices_from_orderbook(no_orderbook)

    no_price = no_ask

    return yes_price, no_price


def main():
    """Test price fetching"""
    print("\n" + "=" * 60)
    print("PROBABLE MARKETS PRICE FETCHER")
    print("=" * 60)

    # Load Probable markets
    try:
        with open('probable_markets.json', 'r', encoding='utf-8') as f:
            markets = json.load(f)
    except FileNotFoundError:
        print("ERROR: probable_markets.json not found")
        return

    print(f"\nFound {len(markets)} Probable markets")

    # Test with first 10 markets
    test_markets = [m for m in markets if m.get('market_type') == 'binary'][:10]
    print(f"\nTesting with {len(test_markets)} binary markets...")

    prices_found = 0
    for market in test_markets:
        market_id = market.get('market_id', '')
        title = market.get('title', '')[:50]

        print(f"\n  Market {market_id}: {title}...")

        yes_price, no_price = get_probable_price(market_id)

        if yes_price or no_price:
            prices_found += 1
            print(f"    Yes price: ${yes_price:.4f}" if yes_price else "    Yes price: N/A")
            print(f"    No price:  ${no_price:.4f}" if no_price else "    No price: N/A")
            if yes_price and no_price:
                total = yes_price + no_price
                print(f"    Total: ${total:.4f} ({'profit' if total < 1 else 'no arb'} if < $1)")
        else:
            print("    No price data available")

        time.sleep(0.2)

    print(f"\n\nPrices found: {prices_found}/{len(test_markets)} markets")
    print("=" * 60)


if __name__ == "__main__":
    main()
