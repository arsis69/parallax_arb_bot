# Main Arbitrage Bot - Quick Start Guide

## Usage

Simply run:
```bash
python main_bot.py
```

## What It Does

Shows the **TOP 20 arbitrage opportunities** with:
- ✅ Market name
- ✅ Which platform to BUY YES on (with price)
- ✅ Which platform to BUY NO on (with price)
- ✅ Direct clickable links to both platforms
- ✅ Arbitrage profit % and dollar amount
- ✅ AI match confidence %

## Output Format

```
#1 - PROFIT: 4.06% ($0.0390) | Match: 91.8%
--------------------------------------------------
>> Market: Metamask FDV above $1B one day after launch?

  [YES] BUY on LIMITLESS  @ $0.5390
        https://limitless.exchange/...

  [NO]  BUY on OPINION    @ $0.4220
        https://app.opinion.trade/...

  >> Total Cost: $0.9610 | Guaranteed Return: $1.0000 | Profit: $0.0390 (4.06%)
```

## How to Execute an Arbitrage

1. Find an opportunity from the bot output
2. Click the [YES] link → Buy YES shares at that price
3. Click the [NO] link → Buy NO shares at that price
4. **Total cost will be less than $1.00**
5. **Guaranteed payout is $1.00 when market resolves**
6. **Profit = $1.00 - Total Cost**

## Fresh Data

To get fresh arbitrage opportunities, run the full pipeline:

```bash
# 1. Extract fresh markets
python extract_predict_fixed.py
python extract_all_options.py
python combine_fresh_three_platforms.py

# 2. Generate embeddings for new markets
python add_predict_embeddings.py

# 3. Run matching pipeline
python match_three_platforms.py
python validate_ai_matches.py
python final_arb_finder_clean.py

# 4. View results
python main_bot.py
```

Or use the automated script (if available):
```bash
python run_full_pipeline.py  # Coming soon
```

## Files

- `main_bot.py` - Main arbitrage bot (this file)
- `final_arbitrage_clean.json` - Contains all arbitrage data
- `COMPLETE_ARBITRAGE_LIST.md` - Full detailed report

## Platform Links

- Opinion: https://app.opinion.trade
- Predict: https://predict.fun
- Limitless: https://limitless.exchange

---

**Last Updated**: January 4, 2026
**Platforms**: Opinion, Predict, Limitless
**Current Opportunities**: 20
