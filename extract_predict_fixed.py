"""
Fixed Predict extraction - properly extract parent questions and options
"""

import requests
import os
import json
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

predict_key = os.getenv("PREDICT_API_KEY")
headers = {"x-api-key": predict_key}


def fetch_all_markets():
    """Fetch all ACTIVE markets from Predict API using categories endpoint"""
    all_markets = []
    seen_ids = set()

    # Primary source: Categories endpoint with status=OPEN
    # This is the most reliable way to get all active/tradeable markets
    print("  Fetching from categories (status=OPEN)...")
    cursor = None
    page = 1

    while page <= 20:  # Safety limit
        params = {"first": "100", "status": "OPEN"}
        if cursor:
            params["after"] = cursor

        try:
            response = requests.get(
                "https://api.predict.fun/v1/categories",
                headers=headers,
                params=params,
                timeout=15
            )
            data = response.json()

            if not data.get("success"):
                break

            categories = data.get("data", [])
            if not categories:
                break

            # Extract markets from each category
            for cat in categories:
                cat_slug = cat.get('slug', '')
                cat_title = cat.get('title', '')
                cat_markets = cat.get('markets', [])

                for m in cat_markets:
                    market_id = m.get('id')
                    
                    # Exclude opinion and probable markets
                    title_check = m.get('title', '').lower()
                    question_check = m.get('question', '').lower()
                    if 'opinion' in title_check or 'opinion' in question_check or 'probable' in title_check or 'probable' in question_check:
                        continue
                        
                    if market_id and market_id not in seen_ids:
                        # Add category info to market
                        m['categorySlug'] = cat_slug
                        m['categoryTitle'] = cat_title
                        all_markets.append(m)
                        seen_ids.add(market_id)

            print(f"  Page {page}: {len(categories)} categories, {len(all_markets)} markets so far")

            cursor = data.get("cursor")
            if not cursor:
                break

            page += 1

        except Exception as e:
            print(f"  Error fetching categories page {page}: {e}")
            break

    # Secondary source: Markets endpoint (for any markets not in categories)
    # Note: /v1/markets does NOT support status filter, so we filter client-side
    print("\n  Fetching standalone markets...")
    cursor = None
    page = 1
    added_from_markets = 0

    while page <= 10:  # Fewer pages since most markets are in categories
        params = {"first": "100"}
        if cursor:
            params["after"] = cursor

        try:
            response = requests.get(
                "https://api.predict.fun/v1/markets",
                headers=headers,
                params=params,
                timeout=15
            )
            data = response.json()

            if not data.get("success"):
                break

            markets = data.get("data", [])
            if not markets:
                break

            for m in markets:
                market_id = m.get('id')
                market_status = m.get('status', '')

                # Exclude opinion and probable markets
                title_check = m.get('title', '').lower()
                question_check = m.get('question', '').lower()
                if 'opinion' in title_check or 'opinion' in question_check or 'probable' in title_check or 'probable' in question_check:
                    continue

                # Only add ACTIVE markets (not RESOLVED) that we haven't seen
                # Active statuses: REGISTERED, PRICE_PROPOSED, PRICE_DISPUTED, PAUSED, UNPAUSED
                if market_id and market_id not in seen_ids and market_status != 'RESOLVED':
                    all_markets.append(m)
                    seen_ids.add(market_id)
                    added_from_markets += 1

            cursor = data.get("cursor")
            if not cursor:
                break

            page += 1

        except Exception as e:
            print(f"  Error fetching markets page {page}: {e}")
            break

    print(f"  Added {added_from_markets} additional markets from /v1/markets endpoint")

    return all_markets


def smart_group_markets(markets):
    """
    Intelligently group markets by detecting shared parent questions
    Uses both categorySlug AND title similarity
    """
    # All markets are already filtered to REGISTERED status
    active = markets

    # Group by category first
    by_category = defaultdict(list)
    for m in active:
        cat = m.get('categorySlug', 'unknown')
        by_category[cat].append(m)

    # Now intelligently merge categories that are clearly related
    groups = {}

    for cat, cat_markets in by_category.items():
        if len(cat_markets) == 1:
            # Standalone binary market
            groups[cat] = {
                'type': 'binary',
                'markets': cat_markets,
                'parent_question': None
            }
        else:
            # Potential multi-option - extract common question
            # Use 'question' field which has full context
            questions = [m.get('question', '') for m in cat_markets]

            # Find common prefix (parent question)
            if questions:
                # Method 1: Find longest common prefix
                common = questions[0]
                for q in questions[1:]:
                    # Find common prefix
                    common_len = 0
                    for i in range(min(len(common), len(q))):
                        if common[i] == q[i]:
                            common_len += 1
                        else:
                            break
                    common = common[:common_len]

                common = common.strip().rstrip('-').rstrip(':').rstrip('?').strip()

                if len(common) > 10:  # At least 10 chars in common
                    groups[cat] = {
                        'type': 'categorical',
                        'markets': cat_markets,
                        'parent_question': common
                    }
                else:
                    # Fallback: treat as separate binaries
                    for m in cat_markets:
                        unique_cat = f"{cat}_{m.get('id')}"
                        groups[unique_cat] = {
                            'type': 'binary',
                            'markets': [m],
                            'parent_question': None
                        }

    return groups


def extract_options(groups):
    """Extract all tradeable options from grouped markets"""
    options = []

    for group_id, group_data in groups.items():
        group_type = group_data['type']
        markets = group_data['markets']
        parent_q = group_data['parent_question']

        if group_type == 'binary':
            # Binary market
            m = markets[0]
            market_id = m.get('id')
            # Prefer 'question' over 'title' as it has full context
            title = m.get('question', m.get('title', 'Unknown'))

            # Get category slug for URL
            category_slug = m.get('categorySlug', '')

            options.append({
                'platform': 'predict',
                'market_id': market_id,
                'title': title,
                'option_title': title,
                'market_type': 'binary',
                'category_slug': category_slug,
                'url': f"https://predict.fun/market/{category_slug}" if category_slug else f"https://predict.fun/markets/{market_id}"
            })

        else:
            # Categorical market - multiple options
            print(f"\n  Categorical: {parent_q} ({len(markets)} options)")

            for m in markets:
                market_id = m.get('id')
                question = m.get('question', '')
                title_short = m.get('title', '')
                category_slug = m.get('categorySlug', '')

                # For categorical: question has full context, title is just option name
                option_name = title_short if title_short else question

                # If we have a parent question, remove it from the full question
                if parent_q and question.startswith(parent_q):
                    option_name = question[len(parent_q):].strip()
                    option_name = option_name.lstrip('-').lstrip(':').strip()
                elif ' - ' in question:
                    option_name = question.split(' - ')[-1]
                elif ': ' in question:
                    option_name = question.split(': ')[-1]

                # Clean unicode
                option_name_clean = option_name.encode('ascii', 'ignore').decode('ascii')
                print(f"    - {option_name_clean}")

                # Full title includes parent
                if parent_q:
                    full_title = f"{parent_q} - {option_name}"
                else:
                    full_title = question  # Use full question as title

                options.append({
                    'platform': 'predict',
                    'market_id': market_id,
                    'title': full_title,
                    'option_title': option_name,
                    'parent_question': parent_q,
                    'market_type': 'categorical',
                    'category_slug': category_slug,
                    'url': f"https://predict.fun/market/{category_slug}" if category_slug else f"https://predict.fun/markets/{market_id}"
                })

    return options


def main():
    print("\n" + "="*80)
    print("FIXED PREDICT EXTRACTION")
    print("="*80)

    # Fetch all markets
    print("\nFetching markets...")
    markets = fetch_all_markets()
    print(f"\nTotal markets fetched: {len(markets)}")

    # Group intelligently
    print("\nGrouping markets...")
    groups = smart_group_markets(markets)

    binary_groups = [g for g in groups.values() if g['type'] == 'binary']
    categorical_groups = [g for g in groups.values() if g['type'] == 'categorical']

    print(f"Binary markets: {len(binary_groups)}")
    print(f"Categorical markets: {len(categorical_groups)}")

    # Extract options
    print("\nExtracting tradeable options...")
    options = extract_options(groups)

    # Save
    output_file = 'predict_markets_fixed.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(options, f, indent=2)

    print("\n" + "="*80)
    print("EXTRACTION COMPLETE")
    print("="*80)
    print(f"Total tradeable options: {len(options)}")
    print(f"  Binary: {len([o for o in options if o['market_type'] == 'binary'])}")
    print(f"  Categorical: {len([o for o in options if o['market_type'] == 'categorical'])}")
    print(f"\nSaved to: {output_file}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
