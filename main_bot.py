"""
MAIN ARBITRAGE BOT
Automatically fetches fresh data and finds arbitrage opportunities
OPTIMIZED: Parallel extraction + quick mode for faster results
"""
import json
import subprocess
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# How old (in minutes) before we re-run full extraction
DATA_FRESHNESS_MINUTES = 30


def is_data_fresh():
    """Check if market data is recent enough to skip extraction"""
    try:
        # Check age of validated matches file
        file_path = 'similar_options_validated_ai.json'
        if not os.path.exists(file_path):
            return False

        age_seconds = time.time() - os.path.getmtime(file_path)
        age_minutes = age_seconds / 60

        return age_minutes < DATA_FRESHNESS_MINUTES
    except:
        return False


def run_command(command, description, quiet=False):
    """Run a command and show progress"""
    if not quiet:
        print(f"\n>> {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=quiet,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=300
        )
        if result.returncode != 0:
            print(f"   WARNING: {description} had issues (exit code: {result.returncode}) but continuing...")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"   WARNING: {description} timed out, continuing...")
        return False
    except Exception as e:
        print(f"   ERROR: {str(e)}")
        return False


def run_extraction(task):
    """Run a single extraction task (for parallel execution)"""
    command, description = task
    start = time.time()
    success = run_command(command, description, quiet=True)
    elapsed = time.time() - start
    return (description, success, elapsed)


def fetch_fresh_data(force_full=False):
    """Run the arbitrage pipeline. Uses quick mode if data is recent."""
    print("\n" + "=" * 100)

    # Check if we can use quick mode (just refresh prices)
    if not force_full and is_data_fresh():
        print(" " * 30 + "QUICK REFRESH (prices only)")
        print("=" * 100)
        print("\n>> Market data is recent, refreshing prices only...")

        # Run price fetching on all matches (no --fast, we need all opportunities)
        run_command("python final_arb_finder_clean.py", "Fetching fresh prices")

        print("\n" + "=" * 100)
        print(" " * 35 + "QUICK REFRESH COMPLETE")
        print("=" * 100)
        return

    # FULL REFRESH
    print(" " * 30 + "FULL DATA REFRESH")
    print("=" * 100)

    # PARALLEL EXTRACTION - Run all 3 extractions simultaneously
    extraction_tasks = [
        ("python extract_predict_fixed.py", "Extracting Predict markets"),
        ("python extract_all_options.py", "Extracting Opinion markets"),
        ("python extract_probable_options.py", "Extracting Probable markets"),
    ]

    print("\n>> Running parallel extraction (3 platforms)...")
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(run_extraction, task): task for task in extraction_tasks}

        for future in as_completed(futures):
            desc, success, elapsed = future.result()
            status = "OK" if success else "WARN"
            print(f"   [{status}] {desc} ({elapsed:.1f}s)")

    parallel_time = time.time() - start_time
    print(f">> Parallel extraction complete in {parallel_time:.1f}s")

    # SEQUENTIAL PIPELINE
    run_command("python combine_fresh_three_platforms.py", "Combining all platforms")
    run_command("python add_all_embeddings.py", "Generating embeddings for new markets")
    run_command("python match_three_platforms.py", "Finding similar markets with AI")
    run_command("python validate_ai_matches.py", "Validating AI matches")
    run_command("python final_arb_finder_clean.py", "Finding arbitrage opportunities")

    print("\n" + "=" * 100)
    print(" " * 30 + "FULL REFRESH COMPLETE")
    print("=" * 100)


def display_opportunities():
    """Display top 20 arbitrage opportunities"""
    print("\n" + "=" * 100)
    print(" " * 35 + "ARBITRAGE BOT")
    print("=" * 100)

    # Load arbitrage opportunities
    try:
        with open('final_arbitrage_clean.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Extract opportunities list from the dict
            if isinstance(data, dict):
                opportunities = data.get('arbitrage_opportunities', [])
            else:
                opportunities = data
    except FileNotFoundError:
        print("\n>> ERROR: No arbitrage data found after refresh.")
        return

    if not opportunities:
        print("\n>> No arbitrage opportunities found at this time.")
        return

    # Show top 20
    top_20 = opportunities[:20]

    print(f"\n>> Found {len(opportunities)} total opportunities")
    print(f">> Showing TOP {len(top_20)} arbitrage opportunities\n")
    print("=" * 100)

    for idx, opp in enumerate(top_20, 1):
        profit_pct = opp['profit_pct']
        total_cost = opp['total_cost']
        profit = opp['profit']
        similarity = opp['similarity']

        buy_yes = opp['buy_yes']
        buy_no = opp['buy_no']

        # Header
        print(f"\n#{idx} - PROFIT: {profit_pct:.2f}% (${profit:.4f}) | Match: {similarity:.1%}")
        print("-" * 100)

        # Market title (extract common part)
        yes_title = buy_yes['title']
        no_title = buy_no['title']

        # Use the shorter or cleaner title and remove emojis
        if len(yes_title) <= len(no_title):
            market_name = yes_title
        else:
            market_name = no_title

        # Remove emojis and non-ASCII characters for console compatibility
        market_name = market_name.encode('ascii', 'ignore').decode('ascii')

        print(f">> Market: {market_name}")
        print()

        # BUY YES side
        yes_platform = buy_yes['platform'].upper()
        yes_price = buy_yes['price']
        yes_link = buy_yes['link']

        print(f"  [YES] BUY on {yes_platform:<10} @ ${yes_price:.4f}")
        print(f"        {yes_link}")
        print()

        # BUY NO side
        no_platform = buy_no['platform'].upper()
        no_price = buy_no['price']
        no_link = buy_no['link']

        print(f"  [NO]  BUY on {no_platform:<10} @ ${no_price:.4f}")
        print(f"        {no_link}")
        print()

        # Summary
        print(f"  >> Total Cost: ${total_cost:.4f} | Guaranteed Return: $1.0000 | Profit: ${profit:.4f} ({profit_pct:.2f}%)")
        print("-" * 100)

    print("\n" + "=" * 100)
    print(f">> Analysis complete! {len(top_20)} opportunities displayed.")
    print("=" * 100 + "\n")


def main():
    # Step 1: Fetch fresh data
    fetch_fresh_data()

    # Step 2: Display opportunities
    display_opportunities()


if __name__ == "__main__":
    main()
