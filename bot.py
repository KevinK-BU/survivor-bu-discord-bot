from dotenv import load_dotenv
import os
import re
import asyncio
import discord
from discord.ext import commands

#
# Config
# 

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Setup intents
intents = discord.Intents.default()
intents.members = True         # needed to access guild.members / role.members
intents.guilds = True          # needed to access guild info
intents.messages = True        # needed to receive/send messages
intents.message_content = True # needed if reading message content

# Create the bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Helper function to check for moderator/executive permissions
def is_mod():
    async def predicate(ctx):
        mod_roles = ["Moderator", "Executive Board"]  # adjust names
        return (
            ctx.author == ctx.guild.owner or
            any(role.name in mod_roles for role in ctx.author.roles)
        )
    return commands.check(predicate)

#
# 
# Pair-tag helpers
#
#

PAIR_RE = re.compile(r"pair:(\d+)-(\d+)")

def pair_key(a: discord.Member, b: discord.Member) -> tuple[int, int]:
    """Stable identity for a 1-on-1 pair using member IDs (order-insensitive)."""
    x, y = sorted([a.id, b.id])
    return (x, y)

def parse_pair_from_topic(topic: str | None):
    """Extract (id1, id2) from a topic containing 'pair:<id1>-<id2>'. Returns None if absent."""
    if not topic:
        return None
    m = PAIR_RE.search(topic)
    if not m:
        return None
    x, y = sorted([int(m.group(1)), int(m.group(2))])
    return (x, y)

# 
#
# Commands
#
#

@is_mod()
@bot.command(name="makeOneonOnes")
async def make_one_on_ones(ctx, tribe_role: discord.Role):
    """Create 1-on-1 channels for all human members of the given role, deduped by ID pair tag."""
    guild = ctx.guild
    if not guild:
        return await ctx.reply("This command can only be used in a server.", mention_author=False)

    # Optional: gather a staff role that should see all channels
    prod_role = discord.utils.get(guild.roles, name="Prod")  # adjust name if needed

    
    players = [m for m in tribe_role.members if not m.bot]


    existing_pairs: set[tuple[int, int]] = set()
    for ch in guild.text_channels:
        key = parse_pair_from_topic(ch.topic)
        if key:
            existing_pairs.add(key)

    created = 0
    for i, p1 in enumerate(players):
        for j, p2 in enumerate(players):
            if i >= j:
                continue  # skip self-pairs and mirrored duplicates

            key = pair_key(p1, p2)
            if key in existing_pairs:
                continue  # already exists from a previous run

            n1, n2 = sorted([p1.name.lower(), p2.name.lower()])
            channel_name = f"{n1}-{n2}"[:100] 

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                p1: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                p2: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
            if prod_role:
                overwrites[prod_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

            topic = f"pair:{key[0]}-{key[1]} | 1-on-1 for {p1.name} & {p2.name} ({tribe_role.name})"
            new_channel = await guild.create_text_channel(
                name=channel_name,
                overwrites=overwrites,
                topic=topic
            )
            existing_pairs.add(key)
            created += 1

            await asyncio.sleep(0.2)

    await ctx.send(f"Done. Created {created} new 1-on-1 channel(s)." if created else "No new channels needed.")

# 
#
# Events
#
#

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}! ✅")

# Run the bot
bot.run(TOKEN)
