import discord
from discord.ext import commands
from discord import app_commands
import re
import base64
import json
import random
import logging
import psutil
import time
import datetime
import asyncio

TOKEN = ""

BOT_VERSION = "1.1.2"
START_TIME = time.time()

WARNS_FILE = "warns.json"

def load_warns():
    try:
        with open(WARNS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_warns(data):
    with open(WARNS_FILE, "w") as f:
        json.dump(data, f, indent=4)

warns = load_warns()

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

def get_system_channel(guild: discord.Guild):
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).send_messages:
        return guild.system_channel

    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            return channel
    return None

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
    "0": "o","1": "i","3": "e","4": "a",
    "5": "s","7": "t","@": "a","$": "s"
}

CRUMB_RESPONSES = ["what, what do you want?", "yeah?", "huh?", "you called?", "ai mode activated", "im here, whats up?", "you rang?", "crumb at your service", "yessir?"]

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
    for guild in bot.guilds:
        try:
            await bot.tree.sync(guild=guild)
            log.info(f"Synced commands to {guild.name}")
        except Exception as e:
            log.error(f"Sync failed for {guild.name}: {e}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    log.info(f"Joined {guild.name}")
    try:
        await bot.tree.sync(guild=guild)
    except Exception as e:
        log.error(e)

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

@bot.tree.command(name="ping", description="check if crumb is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(PING_MESSAGES), ephemeral=True)

@bot.tree.command(name="warn", description="Warn a member")
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):

    if member.bot:
        return await interaction.response.send_message("you cant warn bots.", ephemeral=True)

    gid = str(interaction.guild.id)
    uid = str(member.id)

    warns.setdefault(gid, {}).setdefault(uid, [])

    warn_data = {
        "reason": reason,
        "moderator": str(interaction.user),
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    warns[gid][uid].append(warn_data)
    save_warns(warns)

    try:
        await member.send(f"You have been warned in {interaction.guild.name}\nReason: {reason}")
    except:
        pass

    total_warns = len(warns[gid][uid])

    await interaction.response.send_message(
        f"{member.mention} warned.\nTotal warns: {total_warns}",
        ephemeral=True
    )

    if total_warns == 3:
        try:
            await member.timeout(datetime.timedelta(minutes=10))
        except:
            pass

@bot.tree.command(name="warns", description="View warnings")
@app_commands.checks.has_permissions(moderate_members=True)
async def view_warns(interaction: discord.Interaction, member: discord.Member):

    gid = str(interaction.guild.id)
    uid = str(member.id)

    if gid not in warns or uid not in warns[gid]:
        return await interaction.response.send_message("no warnings", ephemeral=True)

    msg = ""
    for i, w in enumerate(warns[gid][uid], 1):
        msg += f"{i}. {w['reason']} ({w['timestamp']})\n"

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="clearwarns", description="Clear warnings")
@app_commands.checks.has_permissions(moderate_members=True)
async def clear_warns(interaction: discord.Interaction, member: discord.Member):

    gid = str(interaction.guild.id)
    uid = str(member.id)

    if gid in warns and uid in warns[gid]:
        warns[gid][uid] = []
        save_warns(warns)
        await interaction.response.send_message("cleared", ephemeral=True)
    else:
        await interaction.response.send_message("no warns", ephemeral=True)

@bot.tree.command(name="ban", description="Ban member")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):

    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("role too high", ephemeral=True)

    try:
        await member.send(f"Banned from {interaction.guild.name}\nReason: {reason}")
    except:
        pass

    await member.ban(reason=reason)
    await interaction.response.send_message("banned", ephemeral=True)

@bot.tree.command(name="kick", description="Kick member")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):

    if member.top_role >= interaction.user.top_role:
        return await interaction.response.send_message("role too high", ephemeral=True)

    await member.kick(reason=reason)
    await interaction.response.send_message("kicked", ephemeral=True)

@bot.tree.command(name="mute", description="Timeout member")
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int):

    await member.timeout(datetime.timedelta(minutes=minutes))
    await interaction.response.send_message("muted", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmute member")
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):

    await member.timeout(None)
    await interaction.response.send_message("unmuted", ephemeral=True)

@bot.tree.command(name="unban", description="Unban user")
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):

    user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message("unbanned", ephemeral=True)

@bot.tree.command(name="slowmode", description="Set slowmode")
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int):
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message("done", ephemeral=True)

@bot.tree.command(name="purge", description="Delete messages")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"deleted {len(deleted)}", ephemeral=True)

@bot.tree.command(name="info", description="bot info")
async def info(interaction: discord.Interaction):

    uptime = int(time.time() - START_TIME)
    process = psutil.Process()

    await interaction.response.send_message(
        f"uptime: {uptime}s\nram: {process.memory_info().rss / 1024 / 1024:.1f}MB\nservers: {len(bot.guilds)}",
        ephemeral=True
    )

@bot.tree.command(name="status", description="set status")
@app_commands.checks.has_permissions(manage_guild=True)
async def status(interaction: discord.Interaction, text: str):

    await bot.change_presence(activity=discord.CustomActivity(name=text))
    await interaction.response.send_message("updated", ephemeral=True)

JOIN_MESSAGES = ["existed here", "has joined", "arrived"]
LEAVE_MESSAGES = ["left", "disappeared"]
BOOST_MESSAGES = ["boosted the server!"]

@bot.event
async def on_member_join(member: discord.Member):
    channel = get_system_channel(member.guild)
    if channel:
        await channel.send(f"{member.mention} {random.choice(JOIN_MESSAGES)}")

@bot.event
async def on_member_remove(member: discord.Member):
    channel = get_system_channel(member.guild)
    if channel:
        await channel.send(f"{member.mention} {random.choice(LEAVE_MESSAGES)}")

@bot.event
async def on_member_update(before, after):
    if not before.premium_since and after.premium_since:
        channel = get_system_channel(after.guild)
        if channel:
            await channel.send(f"{after.mention} {random.choice(BOOST_MESSAGES)}")

INVITE_REGEX = re.compile(r"(discord(?:\.gg|\.com/invite)/[a-zA-Z0-9]+)")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    if "crumb" in message.content.lower() or bot.user.mentioned_in(message):
        await message.reply(random.choice(CRUMB_RESPONSES))

    if not message.author.guild_permissions.manage_guild:
        if INVITE_REGEX.search(message.content):
            await message.delete()
            await message.guild.ban(message.author, reason="invite link")
            return

    norm = normalize(message.content).split()

    for bad in NORMALIZED_BANNED:
        if bad in norm:
            await message.delete()
            await message.guild.ban(message.author, reason="banned word")
            return

    await bot.process_commands(message)

log.info("Bot starting...")
bot.run(TOKEN)