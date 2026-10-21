import asyncio
import re

import discord

import api.apiwarpper as api
import config
import db.database as db
from bot.agent import ask

intents = discord.Intents.default()
intents.message_content = True  # also enable "Message Content Intent" in the Developer Portal
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    db.init()
    print(f"Logged in as {client.user}")

# Extract the question from a message addressed to Manhattan
def _question(message: discord.Message):
    """Return the question if the message is addressed to Manhattan, else None."""
    text = message.content
    if client.user in message.mentions:
        text = re.sub(rf"<@!?{client.user.id}>", "", text)
    elif not text.lower().lstrip().startswith("manhattan"):
        return None
    text = re.sub(r"^\s*manhattan[\s,:!-]*", "", text, flags=re.I).strip()
    return text or None

# staff role check: manage_guild OR has a role in MOD_ROLE_NAMES
def _is_staff(member: discord.Member) -> bool:
    """True if the member has manage_guild OR holds a role listed in MOD_ROLE_NAMES."""
    perms = getattr(member, "guild_permissions", None)
    if perms and perms.manage_guild:
        return True
    roles = getattr(member, "roles", [])
    return any(r.name.lower() in config.MOD_ROLE_NAMES for r in roles)


async def _handle_command(message: discord.Message) -> bool:
    parts = message.content.split()
    cmd = parts[0].lower() if parts else ""

    if cmd == "!link":
        # --- permission check: must be mod/staff ---
        if not _is_staff(message.author):
            await message.reply("❌ Only Mods or Staff can link accounts.")
            return True

        # --- usage: !link @mention|discord_user_id viewer_id ---
        if len(parts) != 3 or not parts[2].isdigit():
            await message.reply("Usage: `!link @user|<discord_user_id> <viewer_id>`")
            return True

        if message.mentions:
            target = message.mentions[0]
        elif parts[1].isdigit():
            if message.guild is None:
                await message.reply("Linking by user ID must be done in a server.")
                return True
            target = message.guild.get_member(int(parts[1]))
            if target is None:
                try:
                    target = await message.guild.fetch_member(int(parts[1]))
                except discord.NotFound:
                    await message.reply("I couldn't find that user in this server.")
                    return True
                except discord.HTTPException:
                    await message.reply("I couldn't look up that user right now. Please try again.")
                    return True
        else:
            await message.reply("Usage: `!link @user|<discord_user_id> <viewer_id>`")
            return True

        viewer_id = parts[2]

        name = None
        try:
            name = api.get_user(viewer_id)["trainer"]["name"]
        except Exception:
            pass

        db.link_user(target.id, viewer_id, name)
        await message.reply(
            f"✅ Linked {target.mention} to **{name or viewer_id}** (viewer_id: `{viewer_id}`)."
        )
        return True

    if cmd == "!setcircle":
        perms = getattr(message.author, "guild_permissions", None)
        if message.guild is None or not (perms and perms.manage_guild):
            await message.reply("You need the Manage Server permission, in a server, to do that.")
        elif len(parts) != 2 or not parts[1].isdigit():
            await message.reply("Usage: `!setcircle <circle_id>`")
        else:
            db.set_guild_circle(message.guild.id, parts[1])
            await message.reply(f"Default circle set to {parts[1]}.")
        return True
    return False


@client.event
async def on_message(message: discord.Message):
    # Ignore messages from bots
    if message.author.bot:
        return
    # Handle commands separately from questions for Manhattan.
    if await _handle_command(message):
        return

    # Continue only if the message is addressed to Manhattan.
    question = _question(message)
    if not question:
        return

    # Pass the asker and server/channel IDs to the AI tools.
    ctx = {
        "discord_id": message.author.id,
        "author_name": message.author.display_name,
        "guild_id": message.guild.id if message.guild else None,
        "channel_id": message.channel.id,
    }
    async with message.channel.typing():
        try:
            # ask() is synchronous, so run it in a thread to keep the bot responsive.
            answer = await asyncio.to_thread(ask, question, ctx)
        except Exception as e:
            answer = f"Sorry, something went wrong talking to the model ({type(e).__name__})."
    # Keep the reply within Discord's message length limit.
    await message.reply(answer[:1900])
