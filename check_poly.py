import json
d = json.load(open('final_arbitrage_clean.json', 'r', encoding='utf-8'))
opps = d['arbitrage_opportunities']

links = set()
for o in opps:
    if o['buy_yes']['platform'] == 'polymarket':
        links.add(o['buy_yes']['link'])
    if o['buy_no']['platform'] == 'polymarket':
        links.add(o['buy_no']['link'])

print(f"Total unique Polymarket links: {len(links)}")
print("\nAll Polymarket links:")
for l in sorted(links):
    print(f"  {l}")
