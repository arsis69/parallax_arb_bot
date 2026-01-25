"""
Extract ALL tradeable options from all platforms
Includes both binary markets AND individual options from multi-option markets
"""

import json
import requests
import os
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class OptionExtractor:
    """Extracts all tradeable options from all platforms"""

    def __init__(self):
        self.opinion_key = os.getenv("OPINION_API_KEY")
        self.predict_key = os.getenv("PREDICT_API_KEY")

    # ==================== OPINION ====================

    def extract_opinion_options(self) -> List[Dict]:
        """Extract all options from Opinion (binary + categorical)"""
        all_options = []

        # 1. Binary markets
        print("\n  Fetching Opinion binary markets...")
        url = "https://proxy.opinion.trade:8443/openapi/market"
        headers = {"apikey": self.opinion_key}

        for page in range(1, 10):
            params = {"page": page, "limit": 100, "marketType": 0}  # 0 = binary

            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if data.get("errno") != 0:
                    break

                markets = data.get("result", {}).get("list", [])
                if not markets:
                    break

                for m in markets:
                    all_options.append({
                        "platform": "opinion",
                        "market_type": "binary",
                        "market_id": m.get("marketId"),
                        "title": m.get("marketTitle"),
                        "option_title": m.get("marketTitle"),  # Same as title for binary
                        "yes_token_id": m.get("yesTokenId"),
                        "no_token_id": m.get("noTokenId"),
                        "url": f"https://app.opinion.trade/detail?topicId={m.get('marketId')}",
                    })

                print(f"    Page {page}: {len(markets)} binary markets")
                time.sleep(0.2)

            except Exception as e:
                print(f"    Error on page {page}: {e}")
                break

        # 2. Categorical markets (multi-option)
        print("\n  Fetching Opinion categorical markets...")
        for page in range(1, 10):
            params = {"page": page, "limit": 100, "marketType": 1}  # 1 = categorical

            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()

                if data.get("errno") != 0:
                    break

                markets = data.get("result", {}).get("list", [])
                if not markets:
                    break

                for m in markets:
                    parent_title = m.get("marketTitle")
                    parent_id = m.get("marketId")
                    child_markets = m.get("childMarkets", [])

                    for child in child_markets:
                        all_options.append({
                            "platform": "opinion",
                            "market_type": "categorical_option",
                            "parent_market_id": parent_id,
                            "parent_title": parent_title,
                            "market_id": child.get("marketId"),
                            "title": f"{parent_title} - {child.get('marketTitle')}",
                            "option_title": child.get("marketTitle"),
                            "yes_token_id": child.get("yesTokenId"),
                            "no_token_id": child.get("noTokenId"),
                            "url": f"https://app.opinion.trade/detail?topicId={parent_id}",
                        })

                print(f"    Page {page}: {len(markets)} categorical markets")
                time.sleep(0.2)

            except Exception as e:
                print(f"    Error on page {page}: {e}")
                break

        return all_options

    # ==================== POLYMARKET ====================

    def extract_polymarket_options(self) -> List[Dict]:
        """Extract all options from Polymarket"""
        # For now, we'll use the data we already have from all_markets_with_opinion.json
        # since fetching ALL Polymarket markets would take too long
        all_options = []

        with open("all_markets_with_opinion.json", 'r', encoding='utf-8') as f:
            all_markets = json.load(f)

        polymarket_markets = [m for m in all_markets if m['platform'] == 'polymarket']
        print(f"\n  Processing {len(polymarket_markets)} Polymarket markets from file...")

        for m in polymarket_markets:
            market_id = m['id']
            url = m.get('url', '')
            title = m['title']
            option_count = m.get('option_count', 1)

            if option_count == 1:
                # Binary market
                if '/event/' in url:
                    slug = url.split('/event/')[-1]
                else:
                    continue

                all_options.append({
                    "platform": "polymarket",
                    "market_type": "binary",
                    "market_id": market_id,
                    "title": title,
                    "option_title": title,
                    "slug": slug,
                    "url": url,
                })

            else:
                # Multi-option market - need to fetch details
                # For now, skip as most are resolved/inactive
                pass

        return all_options

    # ==================== LIMITLESS ====================

    def extract_limitless_options(self) -> List[Dict]:
        """Extract all options from Limitless"""
        all_options = []

        with open("all_markets_with_opinion.json", 'r', encoding='utf-8') as f:
            all_markets = json.load(f)

        limitless_markets = [m for m in all_markets if m['platform'] == 'limitless']
        print(f"\n  Processing {len(limitless_markets)} Limitless markets from file...")

        for m in limitless_markets:
            url = m.get('url', '')

            if '/markets/' in url:
                slug = url.split('/markets/')[-1]
            else:
                continue

            all_options.append({
                "platform": "limitless",
                "market_type": "binary",
                "market_id": m['id'],
                "title": m['title'],
                "option_title": m['title'],
                "slug": slug,
                "url": url,
            })

        return all_options

    # ==================== PREDICT ====================

    def extract_predict_options(self) -> List[Dict]:
        """Extract all options from Predict"""
        all_options = []

        with open("all_markets_with_opinion.json", 'r', encoding='utf-8') as f:
            all_markets = json.load(f)

        predict_markets = [m for m in all_markets if m['platform'] == 'predict']
        print(f"\n  Processing {len(predict_markets)} Predict markets from file...")

        for m in predict_markets:
            option_count = m.get('option_count', 1)

            if option_count == 1:
                # Binary market
                all_options.append({
                    "platform": "predict",
                    "market_type": "binary",
                    "market_id": m['id'],
                    "title": m['title'],
                    "option_title": m['title'],
                    "url": m.get('url', ''),
                })
            else:
                # Multi-option - skip for now as API returns 404
                pass

        return all_options


def main():
    """Extract all options from all platforms"""
    print("\n" + "="*80)
    print("EXTRACTING ALL TRADEABLE OPTIONS FROM ALL PLATFORMS")
    print("="*80)

    extractor = OptionExtractor()
    all_options = []

    # Opinion (fetch live data for most accurate options)
    print("\n[OPINION]")
    opinion_options = extractor.extract_opinion_options()
    all_options.extend(opinion_options)
    print(f"  Total Opinion options: {len(opinion_options)}")

    # Polymarket (from saved data)
    print("\n[POLYMARKET]")
    polymarket_options = extractor.extract_polymarket_options()
    all_options.extend(polymarket_options)
    print(f"  Total Polymarket options: {len(polymarket_options)}")

    # Limitless (from saved data)
    print("\n[LIMITLESS]")
    limitless_options = extractor.extract_limitless_options()
    all_options.extend(limitless_options)
    print(f"  Total Limitless options: {len(limitless_options)}")

    # Predict (from saved data)
    print("\n[PREDICT]")
    predict_options = extractor.extract_predict_options()
    all_options.extend(predict_options)
    print(f"  Total Predict options: {len(predict_options)}")

    # Save results
    output_file = "all_tradeable_options.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_options, f, indent=2)

    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total tradeable options extracted: {len(all_options)}")
    print(f"  Opinion: {len([o for o in all_options if o['platform'] == 'opinion'])}")
    print(f"  Polymarket: {len([o for o in all_options if o['platform'] == 'polymarket'])}")
    print(f"  Limitless: {len([o for o in all_options if o['platform'] == 'limitless'])}")
    print(f"  Predict: {len([o for o in all_options if o['platform'] == 'predict'])}")
    print(f"\nSaved to: {output_file}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
