"""
Match markets across multiple platforms using embeddings
Optimized with numpy matrix operations
"""

import json
import numpy as np
from collections import Counter

print("\n" + "="*80)
print("MATCHING PLATFORMS: Predict + Polymarket")
print("="*80)

# Load markets
with open('three_platforms_complete.json', 'r', encoding='utf-8') as f:
    markets = json.load(f)

# Count by platform
platforms = Counter(m['platform'] for m in markets)
print(f"\nTotal markets: {len(markets)}")
for p, count in platforms.items():
    print(f"  {p.capitalize()}: {count}")

# Load embeddings
with open('market_embeddings.json', 'r', encoding='utf-8') as f:
    embeddings_list = json.load(f)

embedding_map = {item['title']: item['embedding'] for item in embeddings_list}

# Filter markets with embeddings
markets_with_emb = [m for m in markets if m['title'] in embedding_map]
print(f"\nMarkets with embeddings: {len(markets_with_emb)} / {len(markets)}")

# Group by platform for cross-platform matching only
by_platform = {}
for m in markets_with_emb:
    p = m['platform']
    if p not in by_platform:
        by_platform[p] = []
    by_platform[p].append(m)

THRESHOLD = 0.97  # Raised from 0.90 to reduce false positives
matches = []

# For each pair of platforms, do efficient matrix comparison
platform_list = list(by_platform.keys())
print(f"\nMatching across platforms: {platform_list}")

for i, p1 in enumerate(platform_list):
    for p2 in platform_list[i+1:]:
        markets_1 = by_platform[p1]
        markets_2 = by_platform[p2]

        print(f"\n  Comparing {p1} ({len(markets_1)}) vs {p2} ({len(markets_2)})...")

        # Build embedding matrices
        emb_1 = np.array([embedding_map[m['title']] for m in markets_1])
        emb_2 = np.array([embedding_map[m['title']] for m in markets_2])

        # Normalize for cosine similarity
        emb_1_norm = emb_1 / np.linalg.norm(emb_1, axis=1, keepdims=True)
        emb_2_norm = emb_2 / np.linalg.norm(emb_2, axis=1, keepdims=True)

        # Matrix multiply for all cosine similarities at once
        sim_matrix = np.dot(emb_1_norm, emb_2_norm.T)

        # Find matches above threshold
        match_indices = np.where(sim_matrix >= THRESHOLD)

        found = 0
        for idx1, idx2 in zip(match_indices[0], match_indices[1]):
            sim = float(sim_matrix[idx1, idx2])
            matches.append({
                'similarity': sim,
                'markets': [markets_1[idx1], markets_2[idx2]]
            })
            found += 1

        print(f"    Found {found} matches")

# Sort by similarity
matches.sort(key=lambda x: x['similarity'], reverse=True)

print(f"\nFound {len(matches)} matches at {THRESHOLD*100:.0f}% threshold")

# Save
with open('similar_options_embeddings.json', 'w', encoding='utf-8') as f:
    json.dump(matches, f, indent=2)

print(f"Saved to: similar_options_embeddings.json")
print("="*80 + "\n")
