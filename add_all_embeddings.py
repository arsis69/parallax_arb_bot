"""
Generate embeddings for ALL new markets (Opinion, Predict, Limitless)
"""
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def batch_get_embeddings(texts, batch_size=100):
    """Get embeddings from OpenRouter API"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment")

    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]

        response = requests.post(
            "https://openrouter.ai/api/v1/embeddings",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "text-embedding-3-small",
                "input": batch
            },
            timeout=60
        )

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        all_embeddings.extend(embeddings)

        print(f"  Generated embeddings {i+1}-{min(i+batch_size, len(texts))}/{len(texts)}")

    return all_embeddings


def main():
    print("=" * 80)
    print("GENERATE EMBEDDINGS FOR ALL NEW MARKETS")
    print("=" * 80)

    # Load all markets
    with open('three_platforms_complete.json', 'r', encoding='utf-8') as f:
        all_markets = json.load(f)

    print(f"\nTotal markets: {len(all_markets)}")

    # Load existing embeddings
    try:
        with open('market_embeddings.json', 'r', encoding='utf-8') as f:
            existing_embeddings = json.load(f)
        print(f"Existing embeddings: {len(existing_embeddings)}")
    except FileNotFoundError:
        existing_embeddings = []
        print("No existing embeddings found")

    # Find markets without embeddings
    existing_titles = {e['title'] for e in existing_embeddings}

    markets_without_emb = []
    for market in all_markets:
        title = market['title']
        if title not in existing_titles:
            markets_without_emb.append(market)

    print(f"Markets without embeddings: {len(markets_without_emb)}")

    if len(markets_without_emb) == 0:
        print("\nAll markets already have embeddings!")
        return

    # Show breakdown
    by_platform = {}
    for m in markets_without_emb:
        platform = m['platform']
        if platform not in by_platform:
            by_platform[platform] = 0
        by_platform[platform] += 1

    print("\nBreakdown by platform:")
    for platform, count in by_platform.items():
        print(f"  {platform}: {count} new markets")

    # Calculate cost
    total_chars = sum(len(m['title']) for m in markets_without_emb)
    estimated_cost = (total_chars / 1000000) * 0.015
    print(f"\nEstimated cost: ${estimated_cost:.4f}")

    # Generate embeddings
    print(f"\nGenerating embeddings for {len(markets_without_emb)} new markets...")

    new_titles = [m['title'] for m in markets_without_emb]
    new_embeddings_vectors = batch_get_embeddings(new_titles)

    # Create embedding objects
    new_embeddings = []
    for i, market in enumerate(markets_without_emb):
        new_embeddings.append({
            'title': market['title'],
            'platform': market['platform'],
            'embedding': new_embeddings_vectors[i]
        })

    # Combine with existing
    all_embeddings = existing_embeddings + new_embeddings

    # Save
    with open('market_embeddings.json', 'w', encoding='utf-8') as f:
        json.dump(all_embeddings, f, ensure_ascii=False)

    print(f"\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"Total embeddings now: {len(all_embeddings)}")
    print(f"  Added {len(new_embeddings)} new embeddings")
    print(f"Saved to: market_embeddings.json")
    print("=" * 80)


if __name__ == "__main__":
    main()
