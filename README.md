# Prediction Market Arbitrage Bot

Automated arbitrage finder that detects price discrepancies across multiple prediction market platforms using AI-powered semantic matching.

## How It Works

The bot finds "riskless" arbitrage opportunities by:
1. Extracting markets from multiple platforms
2. Using AI embeddings to match identical markets across platforms (even with different names)
3. Fetching live orderbook prices
4. Finding opportunities where `YES price + NO price < $1.00`

**Example Arbitrage:**
- BUY YES on Predict @ $0.54
- BUY NO on Opinion @ $0.42
- Total: $0.96 → Guaranteed $1.00 payout → **4.2% profit**

## Supported Platforms

- **Opinion Trade** (opinion.trade)
- **Predict.fun** (predict.fun)
- **Probable Markets** (probable.markets)
- **Polymarket** (polymarket.com) - extraction only
- **Limitless Exchange** (limitless.exchange) - disabled

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file:

```env
# Required
OPENROUTER_API_KEY=your_openrouter_key
PREDICT_API_KEY=your_predict_key
OPINION_API_KEY=your_opinion_key

# Optional (for Telegram alerts)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Run the Bot

```bash
python main_bot.py
```

## Pipeline

1. **Extract** - Parallel extraction from all platforms
2. **Combine** - Merge into unified format
3. **Embed** - Generate AI embeddings (text-embedding-3-small)
4. **Match** - Find cross-platform matches (0.90+ similarity)
5. **Validate** - Filter false positives (dates, FDV values, etc.)
6. **Price** - Fetch live orderbook prices (20 concurrent threads)
7. **Arbitrage** - Calculate profitable opportunities

## Project Structure

```
all-round-arb/
├── main_bot.py                    # Main entry - runs full pipeline
├── extract_predict_fixed.py       # Predict.fun extraction
├── extract_all_options.py         # Opinion.trade extraction
├── extract_probable_options.py    # Probable.markets extraction
├── combine_fresh_three_platforms.py
├── add_all_embeddings.py          # AI embedding generation
├── match_three_platforms.py       # Cross-platform matching
├── validate_ai_matches.py         # Match validation
├── final_arb_finder_clean.py      # Arbitrage calculation
├── telegram_bot.py                # Telegram alerts (for VPS)
├── requirements.txt
└── .env                           # API keys (not committed)
```

## VPS Deployment with Telegram Alerts

See `telegram_bot.py` for automated alerts every 30 minutes.

```bash
# Run with cron (every 30 min)
*/30 * * * * cd /path/to/bot && python telegram_bot.py >> bot.log 2>&1
```

## Performance

- **Parallel extraction**: 3 platforms simultaneously
- **Cached embeddings**: Only generates for new markets
- **Concurrent price fetching**: 20 threads
- **Typical runtime**: ~2-3 minutes for full pipeline

## Output

Results saved to `final_arbitrage_clean.json`:

```json
{
  "arbitrage_opportunities": [
    {
      "profit_pct": 4.2,
      "total_cost": 0.96,
      "buy_yes": {"platform": "predict", "price": 0.54, "link": "..."},
      "buy_no": {"platform": "opinion", "price": 0.42, "link": "..."}
    }
  ]
}
```

## License

MIT
