# Quick Start Guide

## Installation & Running

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Add Your OpenRouter API Key
Edit `.env` file and add your OpenRouter API key:
```
OPENROUTER_API_KEY=your_key_here
```

Get your key at: https://openrouter.ai/keys

### Step 3: Run the Scraper
```bash
python main.py
```

That's it! The scraper will now:
1. Fetch markets from Opinion, Predict.fun, Limitless, and Polymarket
2. Use AI to find similar markets across platforms
3. Show you NEW matches in the terminal
4. Save results to `output/` folder
5. Wait 60 seconds and repeat

## What You'll See

```
🔍 Scraping Iteration #1 - 2026-01-01 12:00:00
================================================================================
📡 Fetching markets from opinion...
   ✓ Found 150 active markets
📡 Fetching markets from predict...
   ✓ Found 200 active markets
📡 Fetching markets from limitless...
   ✓ Found 100 active markets
📡 Fetching markets from polymarket...
   ✓ Found 300 active markets

🤖 Using AI to find similar markets across platforms...

🆕 Found 5 NEW cross-platform matches!

1. Fed decision in January?
   Platforms: limitless, opinion, polymarket, predict
   └─ [limitless] Fed decision in January?
   └─ [opinion] US Fed Rate Decision in January?
   ...
```

## Stop the Scraper

Press `Ctrl+C` to stop.

## View Saved Results

Check the `output/` folder for JSON files with detailed results.

## Need Help?

See [README.md](README.md) for full documentation.
