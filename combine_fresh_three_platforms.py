"""
Combine fresh extractions from multiple platforms
Currently: Predict + Probable
(Opinion + Limitless can be re-enabled when needed)
"""
import json
import os

print("=" * 80)
print("COMBINING FRESH DATA - MULTIPLE PLATFORMS")
print("=" * 80)

combined = []

# Load Predict
try:
    with open('predict_markets_fixed.json', 'r', encoding='utf-8') as f:
        predict = json.load(f)
    print(f"Predict: {len(predict)} options")
    combined.extend(predict)
except FileNotFoundError:
    print("WARNING: predict_markets_fixed.json not found")

# Load Probable
try:
    with open('probable_markets.json', 'r', encoding='utf-8') as f:
        probable = json.load(f)
    print(f"Probable: {len(probable)} options")
    combined.extend(probable)
except FileNotFoundError:
    print("WARNING: probable_markets.json not found")

# Load Opinion
try:
    with open('all_tradeable_options.json', 'r', encoding='utf-8') as f:
        all_options = json.load(f)
    opinion = [opt for opt in all_options if opt['platform'] == 'opinion']
    print(f"Opinion: {len(opinion)} options")
    combined.extend(opinion)
except FileNotFoundError:
    print("WARNING: all_tradeable_options.json not found")

# --- TEMPORARILY DISABLED PLATFORMS (kept for future use) ---
# Load Limitless
# if os.path.exists('limitless_markets_complete.json'):
#     with open('limitless_markets_complete.json', 'r', encoding='utf-8') as f:
#         limitless = json.load(f)
#     print(f"Limitless: {len(limitless)} options")
#     combined.extend(limitless)
# -----------------------------------------------------------

print(f"\nTotal combined: {len(combined)} options")

# Save
with open('three_platforms_complete.json', 'w', encoding='utf-8') as f:
    json.dump(combined, f, indent=2, ensure_ascii=False)

print(f"Saved to: three_platforms_complete.json")
print("=" * 80)
