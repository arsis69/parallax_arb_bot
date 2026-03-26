import json
import os
import sys
import re


print("=" * 80)
print("COMBINING FRESH DATA - MULTIPLE PLATFORMS")
print("=" * 80)




KEYWORD_THRESHOLD = 2  # Minimum shared keywords to consider a match for filtering

PLATFORM_FILES = {
    "polymarket": "polymarket_markets.json",
    "predict": "predict_markets_fixed.json",
    "limitless": "limitless_markets_complete.json",
}

def extract_keywords(title):
    """Extract non-trivial keywords from a market title."""
    # Stop words that cause false matches
    STOP_WORDS = {
        'will', 'the', 'a', 'an', 'in', 'at', 'on', 'of', 'to', 'by', 'be',
        'or', 'and', 'vs', 'for', 'is', 'it', 'win', 'game', 'end', 'draw',
        'any', 'other', 'who', 'no', 'first', 'team', 'player', 'listed',
        'none', 'above', 'before', 'after', 'less', 'than', 'between', 'more',
        'equal', 'greater', 'from', 'up', 'down', 'hit', 'close', 'would',
        'have', 'not', 'this', 'that', 'with', 'are', 'was', 'were'
    }
    words = re.findall(r'[a-z]+', title.lower())
    return set(w for w in words if len(w) >= 3 and w not in STOP_WORDS)


def main():
    if len(sys.argv) > 1:
        selected_platforms = sys.argv[1].split(',')
    else:
        print("ERROR: No platforms specified. Usage: python combine_fresh_three_platforms.py platform1,platform2")
        sys.exit(1)

    print(f"Selected platforms for combination: {', '.join(selected_platforms).upper()}")

    combined = []
    loaded_data = {}

    # Load data for selected platforms
    for platform in selected_platforms:
        filename = PLATFORM_FILES.get(platform)
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"{platform.capitalize()}: {len(data)} options")
                loaded_data[platform] = data
            except FileNotFoundError:
                print(f"WARNING: {filename} not found for {platform}. Skipping.")
            except json.JSONDecodeError:
                print(f"ERROR: Could not decode JSON from {filename}. Skipping {platform}.")
        else:
            print(f"WARNING: Unknown platform '{platform}'. Skipping.")

    # Apply keyword filtering if both 'predict' and 'polymarket' are selected
    if "predict" in selected_platforms and "polymarket" in selected_platforms:
        predict_markets = loaded_data.get("predict", [])
        polymarket_markets = loaded_data.get("polymarket", [])

        if predict_markets and polymarket_markets:
            predict_keyword_sets = [extract_keywords(m['title']) for m in predict_markets]

            inverted_index = {}
            poly_keyword_sets = []
            for idx, m in enumerate(polymarket_markets):
                kws = extract_keywords(m['title'])
                poly_keyword_sets.append(kws)
                for kw in kws:
                    if kw not in inverted_index:
                        inverted_index[kw] = set()
                    inverted_index[kw].add(idx)

            matched_poly_indices = set()
            for pred_kws in predict_keyword_sets:
                candidate_counts = {}
                for kw in pred_kws:
                    if kw in inverted_index:
                        for poly_idx in inverted_index[kw]:
                            candidate_counts[poly_idx] = candidate_counts.get(poly_idx, 0) + 1

                for poly_idx, count in candidate_counts.items():
                    if count >= KEYWORD_THRESHOLD:
                        matched_poly_indices.add(poly_idx)

            filtered_polymarket = [polymarket_markets[i] for i in sorted(matched_poly_indices)]
            print(f"Polymarket: {len(filtered_polymarket)} candidates (filtered from {len(polymarket_markets)}) based on Predict keywords.")
            combined.extend(predict_markets)
            combined.extend(filtered_polymarket)
        elif predict_markets:
            print("No Polymarket markets to filter, including all Predict markets.")
            combined.extend(predict_markets)
        elif polymarket_markets:
            print("No Predict markets to filter against, including all Polymarket markets.")
            combined.extend(polymarket_markets)

    else: # No specific keyword filtering needed, just combine all loaded data
        for platform_data in loaded_data.values():
            combined.extend(platform_data)

    print(f"\nTotal combined: {len(combined)} options")

    # Save
    with open('three_platforms_complete.json', 'w', encoding='utf-8') as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)

    print(f"Saved to: three_platforms_complete.json")
    print("=" * 80)

if __name__ == "__main__":
    main()
