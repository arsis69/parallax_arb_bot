
import json
import requests
import os
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()


class OptionExtractor:
    """
    Extracts market data. Note: Methods for Polymarket, Limitless, and Predict
    read from 'all_markets_with_opinion.json' and may be outdated.
    Dedicated scripts like extract_polymarket.py and extract_predict_fixed.py
    are preferred for live data.
    """

    def __init__(self):
        # Removed: self.opinion_key = os.getenv("OPINION_API_KEY")
        self.predict_key = os.getenv("PREDICT_API_KEY") # This might not be used here, but kept for now.

    # ==================== POLYMARKET ====================

    def extract_polymarket_options(self) -> List[Dict]:
        """Extract all options from Polymarket (reads from JSON file)."""
        all_options = []
        try:
            with open("all_markets_with_opinion.json", 'r', encoding='utf-8') as f:
                all_markets = json.load(f)
        except FileNotFoundError:
            print("  WARNING: 'all_markets_with_opinion.json' not found. Skipping Polymarket extraction.")
            return []

        polymarket_markets = [m for m in all_markets if m.get('platform') == 'polymarket']
        print(f"
  Processing {len(polymarket_markets)} Polymarket markets from file...")

        for m in polymarket_markets:
            market_id = m.get('id')
            url = m.get('url', '')
            title = m.get('title')
            option_count = m.get('option_count', 1)

            if not market_id or not title:
                continue

            if option_count == 1: # Binary market
                if '/event/' in url:
                    slug = url.split('/event/')[-1]
                else:
                    slug = market_id # Fallback slug
                all_options.append({
                    "platform": "polymarket",
                    "market_type": "binary",
                    "market_id": market_id,
                    "title": title,
                    "option_title": title,
                    "slug": slug,
                    "url": url,
                })
            # else: Multi-option markets are skipped for now.

        return all_options

    # ==================== LIMITLESS ====================

    def extract_limitless_options(self) -> List[Dict]:
        """Extract all options from Limitless (reads from JSON file)."""
        all_options = []
        try:
            with open("all_markets_with_opinion.json", 'r', encoding='utf-8') as f:
                all_markets = json.load(f)
        except FileNotFoundError:
            print("  WARNING: 'all_markets_with_opinion.json' not found. Skipping Limitless extraction.")
            return []

        limitless_markets = [m for m in all_markets if m.get('platform') == 'limitless']
        print(f"
  Processing {len(limitless_markets)} Limitless markets from file...")

        for m in limitless_markets:
            url = m.get('url', '')
            title = m.get('title')
            market_id = m.get('id')

            if not market_id or not title:
                continue

            if '/markets/' in url:
                slug = url.split('/markets/')[-1]
            else:
                slug = market_id # Fallback slug

            all_options.append({
                "platform": "limitless",
                "market_type": "binary",
                "market_id": market_id,
                "title": title,
                "option_title": title,
                "slug": slug,
                "url": url,
            })

        return all_options

    # ==================== PREDICT ====================

    def extract_predict_options(self) -> List[Dict]:
        """
        Extract all options from Predict (reads from JSON file).
        Note: This method reads from a static JSON. For live data,
        'extract_predict_fixed.py' should be used.
        """
        all_options = []
        try:
            with open("all_markets_with_opinion.json", 'r', encoding='utf-8') as f:
                all_markets = json.load(f)
        except FileNotFoundError:
            print("  WARNING: 'all_markets_with_opinion.json' not found. Skipping Predict extraction.")
            return []

        predict_markets = [m for m in all_markets if m.get('platform') == 'predict']
        print(f"
  Processing {len(predict_markets)} Predict markets from file...")

        for m in predict_markets:
            option_count = m.get('option_count', 1)
            title = m.get('title')
            market_id = m.get('id')

            if not market_id or not title:
                continue

            if option_count == 1: # Binary market
                all_options.append({
                    "platform": "predict",
                    "market_type": "binary",
                    "market_id": market_id,
                    "title": title,
                    "option_title": title,
                    "url": m.get('url', ''),
                })
            # else: Multi-option markets are skipped.

        return all_options

# The main() function is removed from this file.
# This file now serves as a utility module providing the OptionExtractor class.
# It will be imported and used by main_bot.py.
