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
    """Run a single extraction task (for parallel execution)
    task is a tuple: (command_string, description)
    """
    command, description = task
    start = time.time()
    success = run_command(command, description, quiet=True)
    elapsed = time.time() - start
    return (description, success, elapsed)


import sys

def fetch_fresh_data(force_full=False):
    """Run the arbitrage pipeline based on user's platform selection."""
    print("\n" + "=" * 100)

    # Get platforms from command line or use default
    if len(sys.argv) > 1:
        selected_platforms = sys.argv[1].split(',')
    else:
        # Default fallback
        selected_platforms = ["limitless", "predict"] 

    print(f"Selected platforms: {', '.join(selected_platforms).upper()}")
    print("=" * 100)

    # FULL REFRESH (quick mode disabled)
    print(" " * 30 + "FULL DATA REFRESH")
    print("=" * 100)

    # PARALLEL EXTRACTION - Build tasks based on selection
    extraction_tasks = []

    # Define mapping of platform names to their extraction scripts
    platform_configs = {
        "polymarket": {"script": "python extract_polymarket.py", "description": "Extracting Polymarket markets"},
        "predict": {"script": "python extract_predict_fixed.py", "description": "Extracting Predict markets"},
        "limitless": {"script": "python extract_limitless_complete.py", "description": "Extracting Limitless markets"}
    }

    for platform in selected_platforms:
        if platform in platform_configs:
            config = platform_configs[platform]
            
            # Caching logic to avoid re-extracting if data is fresh
            try:
                if platform == "polymarket":
                    file_path = 'polymarket_markets.json'
                    if os.path.exists(file_path):
                        age_minutes = (time.time() - os.path.getmtime(file_path)) / 60
                        if age_minutes < DATA_FRESHNESS_MINUTES:
                            print(f"   [SKIP] Polymarket data is fresh ({age_minutes:.1f} mins old). Skipping extraction.")
                            continue
            except Exception as e:
                pass
                
            extraction_tasks.append((config["script"], config["description"]))
        else:
            print(f"WARNING: Unknown platform '{platform}' selected. Skipping.")

    # --- Execute Extraction Tasks ---
    print(f"\n>> Running extraction for {len(selected_platforms)} selected platform(s) in parallel...")
    start_time = time.time()

    # Execute script-based extractions in parallel
    if extraction_tasks:
        with ThreadPoolExecutor(max_workers=len(extraction_tasks)) as executor:
            futures = {executor.submit(run_extraction, task): task for task in extraction_tasks}
            for future in as_completed(futures):
                desc, success, elapsed = future.result()
                status = "OK" if success else "WARN"
                print(f"   [{status}] {desc} ({elapsed:.1f}s)")

    parallel_time = time.time() - start_time
    print(f">> Extraction tasks finished in {parallel_time:.1f}s")

    # --- Combination Step ---
    platforms_arg = ','.join(selected_platforms)
    run_command(f"python combine_fresh_three_platforms.py {platforms_arg}", "Combining selected platforms data")

    # --- Sequential Pipeline ---
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

    top_20 = opportunities[:20]

    print(f"\n>> Found {len(opportunities)} total opportunities")
    print(f">> Showing TOP {len(top_20)} arbitrage opportunities\n")
    print("=" * 100)

    for idx, opp in enumerate(top_20, 1):
        profit_pct = opp.get('profit_pct', 0)
        total_cost = opp.get('total_cost', 0)
        profit = opp.get('profit', 0)
        similarity = opp.get('similarity', 0)

        buy_yes = opp.get('buy_yes', {})
        buy_no = opp.get('buy_no', {})

        print(f"\n#{idx} - PROFIT: {profit_pct:.2f}% (${profit:.4f}) | Match: {similarity:.1%}")
        print("-" * 100)

        yes_title = buy_yes.get('title', 'N/A')
        no_title = buy_no.get('title', 'N/A')

        if len(yes_title) <= len(no_title):
            market_name = yes_title
        else:
            market_name = no_title

        market_name = market_name.encode('ascii', 'ignore').decode('ascii')

        print(f">> Market: {market_name}")
        print()

        yes_platform = buy_yes.get('platform', 'Unknown').upper()
        yes_price = buy_yes.get('price', 0)
        yes_link = buy_yes.get('link', '#')

        print(f"  [YES] BUY on {yes_platform:<10} @ ${yes_price:.4f}")
        print(f"        {yes_link}")
        print()

        no_platform = buy_no.get('platform', 'Unknown').upper()
        no_price = buy_no.get('price', 0)
        no_link = buy_no.get('link', '#')

        print(f"  [NO]  BUY on {no_platform:<10} @ ${no_price:.4f}")
        print(f"        {no_link}")
        print()

        print(f"  >> Total Cost: ${total_cost:.4f} | Guaranteed Return: $1.0000 | Profit: ${profit:.4f} ({profit_pct:.2f}%)")
        print("-" * 100)

    print("\n" + "=" * 100)
    print(f">> Analysis complete! {len(top_20)} opportunities displayed.")
    print("=" * 100 + "\n")


def main():
    # Step 1: Fetch fresh data based on user selection
    fetch_fresh_data()

    # Step 2: Display opportunities
    display_opportunities()


if __name__ == "__main__":
    main()
