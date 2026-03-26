import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open('final_arbitrage_clean.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

opps = data.get('arbitrage_opportunities', data) if isinstance(data, dict) else data
opps.sort(key=lambda x: x['profit_pct'], reverse=True)

print(f"Found {len(opps)} arbitrage opportunities\n")

for i, o in enumerate(opps, 1):
    pct = o['profit_pct']
    profit = o['profit']
    cost = o['total_cost']
    sim = o.get('similarity', 0)
    y = o['buy_yes']
    n = o['buy_no']

    # Use whichever title is cleaner (prefer the one without " - ")
    title = y['title'] if ' - ' not in y['title'] else n['title']

    print(f"#{i}  {title}")
    print(f"    Profit: {pct:.2f}% (${profit:.4f})  |  Similarity: {sim:.1%}  |  Cost: ${cost:.4f}")
    print(f"    Buy YES ${y['price']:.4f} on {y['platform'].upper()}: {y['link']}")
    print(f"    Buy NO  ${n['price']:.4f} on {n['platform'].upper()}: {n['link']}")
    print()
