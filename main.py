import sys

import config
from bot.discord_client import client

if not config.DISCORD_TOKEN:
    sys.exit("Set DISCORD_TOKEN in .env first (see .env.example).")

client.run(config.DISCORD_TOKEN)
