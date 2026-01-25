"""
TELEGRAM ARBITRAGE BOT
Simple bot: /start runs once, shows top 10, then waits
"""

import json
import os
import subprocess
import asyncio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def send_message(chat_id, text):
    """Send a message via Telegram API"""
    import aiohttp

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return resp.status == 200


def run_pipeline():
    """Run the main arbitrage pipeline"""
    print(f"[{datetime.now()}] Running pipeline...")
    try:
        result = subprocess.run(
            "python main_bot.py",
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=600
        )
        return result.returncode == 0
    except Exception as e:
        print(f"Pipeline error: {e}")
        return False


def format_opportunities():
    """Load and format top 10 arbitrage opportunities"""
    try:
        with open('final_arbitrage_clean.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        opportunities = data.get('arbitrage_opportunities', [])

        if not opportunities:
            return None, "No arbitrage opportunities found."

        messages = []

        # Header
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        header = f"""<b>ARBITRAGE OPPORTUNITIES</b>
{now}
{"─" * 30}"""
        messages.append(header)

        # Format top 10 only
        for idx, opp in enumerate(opportunities[:10], 1):
            profit_pct = opp['profit_pct']
            profit = opp['profit']

            buy_yes = opp['buy_yes']
            buy_no = opp['buy_no']

            # Clean title (remove non-ASCII)
            title = buy_yes['title'][:50]
            title = ''.join(c for c in title if ord(c) < 128)

            # Calculate YES + NO sum
            arb_sum = buy_yes['price'] + buy_no['price']

            msg = f"""
<b>#{idx}</b>  <b>{profit_pct:.2f}%</b> profit

<i>{title}</i>

YES + NO = <b>${arb_sum:.4f}</b>
Profit: <b>${profit:.4f}</b>

<b>BUY YES</b> @ {buy_yes['platform'].upper()}
${buy_yes['price']:.4f}
<a href="{buy_yes['link']}">Open Market</a>

<b>BUY NO</b> @ {buy_no['platform'].upper()}
${buy_no['price']:.4f}
<a href="{buy_no['link']}">Open Market</a>
{"─" * 30}"""
            messages.append(msg)

        return messages, None

    except FileNotFoundError:
        return None, "No data found. Running pipeline first..."
    except Exception as e:
        return None, f"Error: {str(e)}"


async def send_opportunities(chat_id):
    """Send formatted opportunities to chat"""
    messages, error = format_opportunities()

    if error:
        await send_message(chat_id, f"Error: {error}")
        return False

    for msg in messages:
        await send_message(chat_id, msg)
        await asyncio.sleep(0.5)  # Avoid rate limiting

    return True


async def handle_updates():
    """Long polling for Telegram updates"""
    import aiohttp

    offset = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    print(f"Bot started! Waiting for /start command...")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                params = {"offset": offset, "timeout": 30}
                async with session.get(url, params=params) as resp:
                    data = await resp.json()

                if not data.get("ok"):
                    await asyncio.sleep(1)
                    continue

                for update in data.get("result", []):
                    offset = update["update_id"] + 1

                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "")

                    if not chat_id or not text:
                        continue

                    if text == "/start":
                        print(f"[{datetime.now()}] /start from {chat_id}")

                        await send_message(chat_id, "Running arbitrage scan...")

                        # Run pipeline
                        loop = asyncio.get_event_loop()
                        success = await loop.run_in_executor(None, run_pipeline)

                        if success:
                            await send_opportunities(chat_id)
                            await send_message(chat_id, "Done. Send /start to scan again.")
                        else:
                            await send_message(chat_id, "Pipeline had issues. Try /start again.")

            except Exception as e:
                print(f"Update error: {e}")
                await asyncio.sleep(5)


async def main():
    """Main entry point"""
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
        print("\nTo set up:")
        print("1. Message @BotFather on Telegram")
        print("2. Send /newbot and follow instructions")
        print("3. Copy the token to your .env file:")
        print("   TELEGRAM_BOT_TOKEN=your_token_here")
        return

    print("\n" + "=" * 50)
    print("TELEGRAM ARBITRAGE BOT")
    print("=" * 50)
    print(f"Token: {TELEGRAM_BOT_TOKEN[:10]}...")
    print("\nSend /start to scan for opportunities")
    print("=" * 50 + "\n")

    await handle_updates()


if __name__ == "__main__":
    asyncio.run(main())
