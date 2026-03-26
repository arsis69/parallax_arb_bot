"""
Final arbitrage finder using CLEAN AI-VALIDATED matches
Post-processed to remove false positives (different dates/FDV/projects)
"""

import json
import requests
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()


def get_opinion_prices(yes_token_id, no_token_id):
    """Quick Opinion price fetch"""
    opinion_key = os.getenv("OPINION_API_KEY")
    if not opinion_key or not yes_token_id:
        return None

    try:
        url = "https://proxy.opinion.trade:8443/openapi/token/orderbook"
        headers = {"apikey": opinion_key}

        result = {}

        # YES
        params = {"token_id": yes_token_id}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        data = resp.json()
        if data.get("errno") == 0:
            asks = data.get("result", {}).get("asks", [])
            if asks:
                sorted_asks = sorted(asks, key=lambda x: float(x['price']))
                result['yes_ask_1'] = float(sorted_asks[0]['price'])
                if len(sorted_asks) > 1:
                    result['yes_ask_2'] = float(sorted_asks[1]['price'])

        # NO
        if no_token_id:
            params = {"token_id": no_token_id}
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            data = resp.json()
            if data.get("errno") == 0:
                asks = data.get("result", {}).get("asks", [])
                if asks:
                    sorted_asks = sorted(asks, key=lambda x: float(x['price']))
                    result['no_ask_1'] = float(sorted_asks[0]['price'])
                    if len(sorted_asks) > 1:
                        result['no_ask_2'] = float(sorted_asks[1]['price'])

        return result if result else None
    except:
        return None


def get_polymarket_prices(slug):
    """Quick Polymarket price fetch"""
    try:
        url = "https://gamma-api.polymarket.com/markets"
        params = {"slug": slug}
        resp = requests.get(url, params=params, timeout=10)
        markets = resp.json()

        if not markets:
            return None

        m = markets[0]
        token_ids = json.loads(m.get('clobTokenIds', '[]'))
        if len(token_ids) < 2:
            return None

        result = {}

        # YES
        yes_url = f"https://clob.polymarket.com/book?token_id={token_ids[0]}"
        yes_ob = requests.get(yes_url, timeout=10).json()
        if yes_ob.get('asks'):
            sorted_asks = sorted(yes_ob['asks'], key=lambda x: float(x['price']))
            result['yes_ask_1'] = float(sorted_asks[0]['price'])
            if len(sorted_asks) > 1:
                result['yes_ask_2'] = float(sorted_asks[1]['price'])

        # NO
        no_url = f"https://clob.polymarket.com/book?token_id={token_ids[1]}"
        no_ob = requests.get(no_url, timeout=10).json()
        if no_ob.get('asks'):
            sorted_asks = sorted(no_ob['asks'], key=lambda x: float(x['price']))
            result['no_ask_1'] = float(sorted_asks[0]['price'])
            if len(sorted_asks) > 1:
                result['no_ask_2'] = float(sorted_asks[1]['price'])

        return result if result else None
    except:
        return None


def get_limitless_prices(slug):
    """Quick Limitless price fetch"""
    try:
        url = f"https://api.limitless.exchange/markets/{slug}/orderbook"
        resp = requests.get(url, timeout=10)
        ob = resp.json()

        result = {}

        asks = ob.get('asks', [])
        bids = ob.get('bids', [])

        # YES
        sorted_asks = sorted(asks, key=lambda x: float(x['price']))
        if sorted_asks:
            result['yes_ask_1'] = float(sorted_asks[0]['price'])
            if len(sorted_asks) > 1:
                result['yes_ask_2'] = float(sorted_asks[1]['price'])

        # NO
        sorted_bids = sorted(bids, key=lambda x: float(x['price']), reverse=True)
        if sorted_bids:
            result['no_ask_1'] = 1.0 - float(sorted_bids[0]['price'])
            if len(sorted_bids) > 1:
                result['no_ask_2'] = 1.0 - float(sorted_bids[1]['price'])

        return result if result else None
    except:
        return None


def get_predict_prices(market_id):
    """Quick Predict price fetch"""
    predict_key = os.getenv("PREDICT_API_KEY")
    if not predict_key:
        return None

    try:
        url = f"https://api.predict.fun/v1/markets/{market_id}/orderbook"
        headers = {"x-api-key": predict_key}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()

        if not data.get('success'):
            return None

        ob = data.get('data', {})
        result = {}

        asks = ob.get('asks', [])
        bids = ob.get('bids', [])

        # YES
        sorted_asks = sorted(asks, key=lambda x: float(x[0]))
        if sorted_asks:
            result['yes_ask_1'] = float(sorted_asks[0][0])
            if len(sorted_asks) > 1:
                result['yes_ask_2'] = float(sorted_asks[1][0])

        # NO
        sorted_bids = sorted(bids, key=lambda x: float(x[0]), reverse=True)
        if sorted_bids:
            result['no_ask_1'] = 1.0 - float(sorted_bids[0][0])
            if len(sorted_bids) > 1:
                result['no_ask_2'] = 1.0 - float(sorted_bids[1][0])

        return result if result else None
    except:
        return None


def get_probable_prices(market_id):
    """Quick Probable price fetch using public orderbook API"""
    MARKET_API = "https://market-api.probable.markets"
    ORDERBOOK_API = "https://api.probable.markets"

    try:
        # Step 1: Get market details to find token IDs
        market_url = f"{MARKET_API}/public/api/v1/markets/{market_id}"
        resp = requests.get(market_url, timeout=10)
        if resp.status_code != 200:
            return None

        market = resp.json()
        tokens = market.get('tokens', [])

        if len(tokens) < 2:
            return None

        # Find Yes and No token IDs
        yes_token_id = None
        no_token_id = None

        for token in tokens:
            outcome = token.get('outcome', '').lower()
            if outcome == 'yes':
                yes_token_id = token.get('token_id')
            elif outcome == 'no':
                no_token_id = token.get('token_id')

        # For team markets (not Yes/No), use first as "Yes", second as "No"
        if not yes_token_id and len(tokens) >= 2:
            yes_token_id = tokens[0].get('token_id')
            no_token_id = tokens[1].get('token_id')

        result = {}

        # Step 2: Get Yes orderbook
        if yes_token_id:
            yes_url = f"{ORDERBOOK_API}/public/api/v1/book?token_id={yes_token_id}"
            yes_resp = requests.get(yes_url, timeout=10)
            if yes_resp.status_code == 200:
                yes_ob = yes_resp.json()
                asks = yes_ob.get('asks', [])
                if asks:
                    sorted_asks = sorted(asks, key=lambda x: float(x['price']))
                    result['yes_ask_1'] = float(sorted_asks[0]['price'])
                    if len(sorted_asks) > 1:
                        result['yes_ask_2'] = float(sorted_asks[1]['price'])

        # Step 3: Get No orderbook
        if no_token_id:
            no_url = f"{ORDERBOOK_API}/public/api/v1/book?token_id={no_token_id}"
            no_resp = requests.get(no_url, timeout=10)
            if no_resp.status_code == 200:
                no_ob = no_resp.json()
                asks = no_ob.get('asks', [])
                if asks:
                    sorted_asks = sorted(asks, key=lambda x: float(x['price']))
                    result['no_ask_1'] = float(sorted_asks[0]['price'])
                    if len(sorted_asks) > 1:
                        result['no_ask_2'] = float(sorted_asks[1]['price'])

        return result if result else None
    except:
        return None


def get_market_link(market):
    """Generate proper link for each platform"""
    platform = market['platform']

    if platform == 'opinion':
        topic_id = market.get('market_id')
        return f"https://app.opinion.trade/detail?topicId={topic_id}"

    elif platform == 'polymarket':
        # Use pre-built url if available, otherwise build from event_slug
        url = market.get('url', '')
        if url:
            return url
        event_slug = market.get('event_slug', market.get('slug', ''))
        event_slug = event_slug.split('?')[0]
        return f"https://polymarket.com/event/{event_slug}"

    elif platform == 'limitless':
        slug = market.get('slug', '')
        return f"https://limitless.exchange/pro/markets/{slug}"

    elif platform == 'predict':
        # Use category_slug if available, fallback to market_id
        category_slug = market.get('category_slug', '')
        if category_slug:
            return f"https://predict.fun/market/{category_slug}"
        else:
            market_id = market.get('market_id')
            return f"https://predict.fun/markets/{market_id}"

    elif platform == 'probable':
        url = market.get('url', '')
        if url:
            # Convert /markets/ to /event/
            return url.replace('/markets/', '/event/')
        slug = market.get('market_slug', market.get('market_id', ''))
        return f"https://probable.markets/event/{slug}"

    return ""


def fetch_prices_for_match(match_tuple):
    """Fetch prices for a single match"""
    idx, match = match_tuple

    similarity = match['similarity']
    markets = match['markets']
    validation = match.get('validation', {})

    if len(markets) < 2:
        return None

    # Fetch prices for all markets
    market_prices = []

    for market in markets:
        platform = market['platform']
        prices = None

        if platform == 'opinion':
            prices = get_opinion_prices(market.get('yes_token_id'), market.get('no_token_id'))
        elif platform == 'polymarket':
            prices = get_polymarket_prices(market.get('slug'))
        elif platform == 'limitless':
            prices = get_limitless_prices(market.get('slug'))
        elif platform == 'predict':
            prices = get_predict_prices(market.get('market_id'))
        elif platform == 'probable':
            prices = get_probable_prices(market.get('market_id'))

        if prices:
            market_prices.append({
                'platform': platform,
                'title': market['title'],
                'link': get_market_link(market),
                'prices': prices
            })

        # Removed delay for speed - APIs can handle it

    # Check for cross-platform arbitrage
    arbitrage_opportunities = []

    if len(market_prices) >= 2:
        for i in range(len(market_prices)):
            for j in range(i+1, len(market_prices)):
                m_a = market_prices[i]
                m_b = market_prices[j]

                # Skip if same platform
                if m_a['platform'] == m_b['platform']:
                    continue

                # Check YES(A) + NO(B)
                if 'yes_ask_1' in m_a['prices'] and 'no_ask_1' in m_b['prices']:
                    total = m_a['prices']['yes_ask_1'] + m_b['prices']['no_ask_1']

                    if total < 1.0:  # Changed from 0.99 to catch ALL opportunities
                        profit_pct = ((1.0 - total) / total) * 100

                        arbitrage_opportunities.append({
                            'similarity': similarity,
                            'profit_pct': profit_pct,
                            'total_cost': total,
                            'profit': 1.0 - total,
                            'buy_yes': {
                                'platform': m_a['platform'],
                                'title': m_a['title'],
                                'price': m_a['prices']['yes_ask_1'],
                                'price_2': m_a['prices'].get('yes_ask_2'),
                                'link': m_a['link']
                            },
                            'buy_no': {
                                'platform': m_b['platform'],
                                'title': m_b['title'],
                                'price': m_b['prices']['no_ask_1'],
                                'price_2': m_b['prices'].get('no_ask_2'),
                                'link': m_b['link']
                            },
                            'validation': validation
                        })

                # Check YES(B) + NO(A)
                if 'yes_ask_1' in m_b['prices'] and 'no_ask_1' in m_a['prices']:
                    total = m_b['prices']['yes_ask_1'] + m_a['prices']['no_ask_1']

                    if total < 1.0:  # Changed from 0.99 to catch ALL opportunities
                        profit_pct = ((1.0 - total) / total) * 100

                        arbitrage_opportunities.append({
                            'similarity': similarity,
                            'profit_pct': profit_pct,
                            'total_cost': total,
                            'profit': 1.0 - total,
                            'buy_yes': {
                                'platform': m_b['platform'],
                                'title': m_b['title'],
                                'price': m_b['prices']['yes_ask_1'],
                                'price_2': m_b['prices'].get('yes_ask_2'),
                                'link': m_b['link']
                            },
                            'buy_no': {
                                'platform': m_a['platform'],
                                'title': m_a['title'],
                                'price': m_a['prices']['no_ask_1'],
                                'price_2': m_a['prices'].get('no_ask_2'),
                                'link': m_a['link']
                            },
                            'validation': validation
                        })

    return {
        'idx': idx,
        'arbitrage_opportunities': arbitrage_opportunities,
        'had_prices': len(market_prices) >= 2
    }


def main():
    import sys

    # Check for fast mode (only check top N matches)
    fast_mode = '--fast' in sys.argv
    limit = 50 if fast_mode else None

    # Load CLEAN AI-validated matches (post-processed)
    print("Loading clean AI-validated matches...")
    with open('similar_options_validated_ai.json', 'r', encoding='utf-8') as f:
        matches = json.load(f)

    # In fast mode, only process top matches by similarity
    if limit and len(matches) > limit:
        matches = sorted(matches, key=lambda x: x.get('similarity', 0), reverse=True)[:limit]
        print(f"FAST MODE: Processing top {limit} matches only")

    print(f"\n{'='*100}")
    print(f"CLEAN AI-VALIDATED CROSS-PLATFORM ARBITRAGE FINDER")
    print(f"Total validated matches: {len(matches)}")
    print(f"Post-processing: Removed different dates/FDV/projects")
    print(f"Matching: text-embedding-3-small (OpenAI) + validation rules")
    print(f"{'='*100}\n")

    arbitrage_opportunities = []
    matches_with_prices = 0

    # Use concurrent fetching with more workers for speed
    print("Fetching prices concurrently...")
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {
            executor.submit(fetch_prices_for_match, (idx, match)): idx
            for idx, match in enumerate(matches)
        }

        completed = 0
        for future in as_completed(futures):
            result = future.result()
            completed += 1

            if completed % 20 == 0 or completed == len(matches):
                print(f"Progress: {completed}/{len(matches)} matches processed...")

            if result:
                if result['had_prices']:
                    matches_with_prices += 1

                if result['arbitrage_opportunities']:
                    arbitrage_opportunities.extend(result['arbitrage_opportunities'])

    # Sort by total cost (lowest first - best opportunities)
    arbitrage_opportunities.sort(key=lambda x: x['total_cost'])

    print(f"\n{'='*100}")
    print(f"RESULTS")
    print(f"{'='*100}")
    print(f"Validated matches analyzed: {len(matches)}")
    print(f"Matches with prices: {matches_with_prices}")
    print(f"Arbitrage opportunities found: {len(arbitrage_opportunities)}")
    print(f"{'='*100}\n")

    # Display results
    if arbitrage_opportunities:
        print(f"{'='*100}")
        print(f"VALIDATED ARBITRAGE OPPORTUNITIES (sorted by total cost)")
        print(f"{'='*100}\n")

        for i, opp in enumerate(arbitrage_opportunities, 1):
            print(f"\n{'='*100}")
            print(f"#{i} - ARBITRAGE OPPORTUNITY")
            print(f"Total Cost: ${opp['total_cost']:.4f} | Profit: ${opp['profit']:.4f} ({opp['profit_pct']:.2f}%)")
            print(f"Similarity: {opp['similarity']:.3f}")
            print(f"{'='*100}\n")

            yes_title = opp['buy_yes']['title'][:70].encode('ascii', 'ignore').decode('ascii')
            no_title = opp['buy_no']['title'][:70].encode('ascii', 'ignore').decode('ascii')

            print(f"BUY YES on {opp['buy_yes']['platform'].upper()}:")
            print(f"  {yes_title}")
            print(f"  Price: ${opp['buy_yes']['price']:.4f}", end="")
            if opp['buy_yes'].get('price_2'):
                print(f" | Ask 2: ${opp['buy_yes']['price_2']:.4f}")
            else:
                print()
            print(f"  Link: {opp['buy_yes']['link']}")

            print(f"\nBUY NO on {opp['buy_no']['platform'].upper()}:")
            print(f"  {no_title}")
            print(f"  Price: ${opp['buy_no']['price']:.4f}", end="")
            if opp['buy_no'].get('price_2'):
                print(f" | Ask 2: ${opp['buy_no']['price_2']:.4f}")
            else:
                print()
            print(f"  Link: {opp['buy_no']['link']}")

            print(f"\nGUARANTEED PAYOUT: $1.00")
            print(f"TOTAL COST: ${opp['total_cost']:.4f}")
            print(f"PROFIT: ${opp['profit']:.4f} ({opp['profit_pct']:.2f}%)")

            # Show validation context
            validation = opp.get('validation', {})
            if validation:
                ctx_a = validation.get('context_a', {})
                ctx_b = validation.get('context_b', {})
                all_dates = set(ctx_a.get('dates', [])).union(set(ctx_b.get('dates', [])))
                all_nums = set(ctx_a.get('numbers', [])).union(set(ctx_b.get('numbers', [])))

                if all_dates or all_nums:
                    print(f"\nValidation context:", end="")
                    if all_dates:
                        print(f" dates={all_dates}", end="")
                    if all_nums:
                        print(f" numbers={all_nums}", end="")
                    print()

    # Save to file
    output = {
        'total_clean_matches': len(matches),
        'matches_with_prices': matches_with_prices,
        'arbitrage_count': len(arbitrage_opportunities),
        'matching_model': 'text-embedding-3-small (OpenAI) + post-processing validation',
        'arbitrage_opportunities': arbitrage_opportunities
    }

    with open('final_arbitrage_clean.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*100}")
    print(f"Analyzed {len(matches)} clean AI-validated market matches")
    print(f"Found {len(arbitrage_opportunities)} arbitrage opportunities")
    print(f"Results saved to: final_arbitrage_clean.json")
    print(f"{'='*100}\n")


if __name__ == "__main__":
    main()
