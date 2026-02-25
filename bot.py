import discord
from discord.ext import commands, app_commands
import re
import base64
import json
import random
import logging
import psutil
import time

TOKEN = ""
GUILD_ID = 1475937462726426634
SYSTEM_CHANNEL_ID = 1476001984082346134

BOT_VERSION = "1.0.7"
START_TIME = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

log = logging.getLogger("crumb-bot")

intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="c.", intents=intents)

guild = discord.Object(id=GUILD_ID)

ENCODED_BANNED = (
    "WyJuaWdnZXIiLCAibmlnZ2EiLCAiZmFnIiwgImZhZ2dvdCIsICJjaGluayIsICJ0cmFubnkiLCAi"
    "bmlnYSIsICJpZ2dhIiwgIm5paWciLCAiYmxhY2t5IiwgImJsYWNraWVzIiwgInBvcm5odWIuY29t"
    "IiwgInh2aWRlb3MiLCAiZTYyMS5uZXQiLCAib25seWZhbnMuY29tIiwgImNoaWxkcG9ybiIsICJy"
    "YXBlIiwgInJhcGVkIiwgInJhcGluZyIsICJyYXBlciIsICJyYXBlcyIsICJwYWtpIiwgImt5cyIs"
    "ICJraWxsIHlvdXJzZWxmIiwgImNvbW1pdCBzdWljaWRlIiwgInN1aWNpZGFsIiwgInBlZG9waGls"
    "ZSIsICJ4eHgiLCAiaW5jZXN0IiwgImJlc3RpYWxpdHkiLCAiYmRzbSIsICJjcCIsICJzaG90YSIs"
    "ICJsb2xpIiwgImdvcmUiLCAi4piNIiwgIuKYkiJd"
)

decoded_json = base64.b64decode(ENCODED_BANNED).decode("utf-8")
banned_words = json.loads(decoded_json)

LEET_MAP = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "7": "t",
    "@": "a",
    "$": "s"
}

def normalize(text: str) -> str:
    text = text.lower()

    for k, v in LEET_MAP.items():
        text = text.replace(k, v)

    text = re.sub(r'[^a-z\s]', '', text)
    text = re.sub(r'(.)\1{2,}', r'\1', text)

    return text

NORMALIZED_BANNED = [normalize(word) for word in banned_words]

@bot.event
async def setup_hook():
    await bot.tree.sync(guild=guild)
    log.info("Commands synced.")

@bot.event
async def on_ready():
    log.info(f"Logged in as {bot.user}")

PING_MESSAGES = [
    "clanker mode activated",
    "im a clanker",
    "quite literally chronically online",
    "online and managing this server",
    "how many of these messages do i need bruh",
    "dude stop adding more ping messages",
    "ow that hurts",
    "dont say 'crumb' in chat btw",
]

@bot.tree.command(
    name="ping",
    description="check if crumb is online",
    guild=guild
)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(
        random.choice(PING_MESSAGES),
        ephemeral=True
    )

@bot.tree.command(
    name="info",
    description="see some info about crumb",
    guild=guild
)
async def info(interaction: discord.Interaction):

    uptime_seconds = int(time.time() - START_TIME)

    hours = uptime_seconds // 3600
    minutes = (uptime_seconds % 3600) // 60
    seconds = uptime_seconds % 60

    process = psutil.Process()

    cpu_usage = process.cpu_percent(interval=0.5)
    memory_usage = process.memory_info().rss / 1024 / 1024  # MB

    member_count = interaction.guild.member_count

    await interaction.response.send_message(
        f"""
**crumb info**

crumb is a private bot made for this server, it's use is primarily for automation to make this server even better!

**stats**
**Uptime:** {hours}h {minutes}m {seconds}s  
**Version:** {BOT_VERSION}  
**CPU Usage:** {cpu_usage:.1f}%  
**Memory Usage:** {memory_usage:.1f} MB  
**Members:** {member_count}

**open source?**
yuh you know i got that open sourced flow... [github](https://github.com/PxslGames/crumb)
just follow the license ok?
""",
        ephemeral=True
    )

@bot.tree.command(
    name="status",
    description="change crumb's rpc (admin only lol)",
    guild=guild
)
@app_commands.checks.has_permissions(manage_guild=True)
async def status(interaction: discord.Interaction, text: str):

    await bot.change_presence(
        activity=discord.CustomActivity(name=text)
    )

    await interaction.response.send_message(
        f"Status updated to: {text}",
        ephemeral=True
    )

JOIN_MESSAGES = ["existed here", "has joined the server", "has arrived"]
LEAVE_MESSAGES = ["doesnt exist here anymore", "has left the chat"]
BOOST_MESSAGES = ["is now a booster! thank you so much!"]

@bot.event
async def on_member_join(member: discord.Member):
    log.info(f"Member joined: {member} ({member.id})")

    channel = bot.get_channel(SYSTEM_CHANNEL_ID)
    if channel:
        await channel.send(f"{member.mention} {random.choice(JOIN_MESSAGES)}")

@bot.event
async def on_member_remove(member: discord.Member):
    log.info(f"Member left: {member} ({member.id})")

    channel = bot.get_channel(SYSTEM_CHANNEL_ID)
    if channel:
        await channel.send(f"{member.mention} {random.choice(LEAVE_MESSAGES)}")

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    if not before.premium_since and after.premium_since:
        log.info(f"Server boost: {after} ({after.id})")

        channel = bot.get_channel(SYSTEM_CHANNEL_ID)
        if channel:
            await channel.send(f"{after.mention} {random.choice(BOOST_MESSAGES)}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if message.content.lower() == "crumb":
        await message.reply("what, what do you want?")

    INVITE_REGEX = re.compile(r"(?:discord(?:\.gg|\.com/invite)/[a-zA-Z0-9]+)")

    if not message.author.guild_permissions.manage_guild:
        if INVITE_REGEX.search(message.content):
            log.warning(f"Invite link detected from {message.author}")

            try:
                await message.delete()
                log.info("Message deleted (invite link)")
            except Exception as e:
                log.error(f"Delete failed: {e}")

            try:
                await message.guild.ban(message.author, reason="Posted invite link")
                log.info(f"User banned: {message.author}")
            except Exception as e:
                log.error(f"Ban failed: {e}")

            return

    normalized_message = normalize(message.content)
    words = normalized_message.split()

    for banned_word in NORMALIZED_BANNED:
        if banned_word in words:
            log.warning(f"Banned word detected from {message.author}")

            try:
                await message.delete()
                log.info("Message deleted (banned word)")
            except Exception as e:
                log.error(f"Delete failed: {e}")

            try:
                await message.guild.ban(message.author, reason="Used banned word")
                log.info(f"User banned: {message.author}")
            except Exception as e:
                log.error(f"Ban failed: {e}")

            return

    await bot.process_commands(message)

log.info("Bot starting...")
bot.run(TOKEN)
