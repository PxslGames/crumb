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
GUILD_ID = 1475937462726426634
SYSTEM_CHANNEL_ID = 1476001984082346134

BOT_VERSION = "1.0.9"
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

@bot.tree.command(name="warn", description="Warn a member", guild=guild)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):

    if member.bot:
        await interaction.response.send_message("you cant warn bots.", ephemeral=True)
        return

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    if guild_id not in warns:
        warns[guild_id] = {}

    if user_id not in warns[guild_id]:
        warns[guild_id][user_id] = []

    warn_data = {
        "reason": reason,
        "moderator": str(interaction.user),
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    warns[guild_id][user_id].append(warn_data)
    save_warns(warns)

    try:
        await member.send(
            f"You have been **warned** in {interaction.guild.name}.\nReason: {reason}"
        )
    except:
        pass

    total_warns = len(warns[guild_id][user_id])

    await interaction.response.send_message(
        f"{member.mention} has been warned.\nReason: {reason}\nTotal warns: {total_warns}",
        ephemeral=True
    )

    if total_warns == 3:
        try:
            await member.timeout(datetime.timedelta(minutes=10), reason="3 warnings reached")
        except:
            pass
    
@bot.tree.command(name="warns", description="View a member's warnings", guild=guild)
@app_commands.checks.has_permissions(moderate_members=True)
async def view_warns(interaction: discord.Interaction, member: discord.Member):

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    if guild_id not in warns or user_id not in warns[guild_id]:
        await interaction.response.send_message(
            f"{member.mention} has no warnings.",
            ephemeral=True
        )
        return

    user_warns = warns[guild_id][user_id]

    msg = f"**Warnings for {member}:**\n\n"
    for i, w in enumerate(user_warns, 1):
        msg += f"**{i}.** {w['reason']}\nMod: {w['moderator']}\nTime: {w['timestamp']}\n\n"

    await interaction.response.send_message(msg, ephemeral=True)

@bot.tree.command(name="clearwarns", description="Clear all warnings for a member", guild=guild)
@app_commands.checks.has_permissions(moderate_members=True)
async def clear_warns(interaction: discord.Interaction, member: discord.Member):

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    if guild_id in warns and user_id in warns[guild_id]:
        warns[guild_id][user_id] = []
        save_warns(warns)

        await interaction.response.send_message(
            f"All warnings cleared for {member.mention}.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"{member.mention} has no warnings.",
            ephemeral=True
        )

@bot.tree.command(name="ban", description="Ban a member", guild=guild)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):

    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("you cant ban someone with equal or higher role.", ephemeral=True)
        return

    try:
        await member.send(f"You have been **banned** from {interaction.guild.name}.\nReason: {reason}")
    except:
        pass

    await member.ban(reason=reason)
    await interaction.response.send_message(
        f"{member.mention} has been banned.\nReason: {reason}",
        ephemeral=True
    )

@bot.tree.command(name="kick", description="Kick a member", guild=guild)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):

    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("you cant kick someone with equal or higher role.", ephemeral=True)
        return

    try:
        await member.send(f"You have been **kicked** from {interaction.guild.name}.\nReason: {reason}")
    except:
        pass

    await member.kick(reason=reason)
    await interaction.response.send_message(
        f"{member.mention} has been kicked.\nReason: {reason}",
        ephemeral=True
    )

@bot.tree.command(name="mute", description="Timeout a member", guild=guild)
@app_commands.checks.has_permissions(moderate_members=True)
async def mute(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):

    if minutes < 1 or minutes > 10080:
        await interaction.response.send_message("minutes must be between 1 and 10080 (7 days).", ephemeral=True)
        return

    duration = datetime.timedelta(minutes=minutes)

    try:
        await member.send(f"You have been **muted** in {interaction.guild.name} for {minutes} minutes.\nReason: {reason}")
    except:
        pass

    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(
        f"{member.mention} has been muted for {minutes} minutes.\nReason: {reason}",
        ephemeral=True
    )

    async def notify_unmute():
        await asyncio.sleep(minutes * 60)
        try:
            await member.send(f"Your mute in {interaction.guild.name} has **expired**. You can speak again!")
        except:
            pass

    bot.loop.create_task(notify_unmute())

@bot.tree.command(name="unmute", description="Remove timeout from a member", guild=guild)
@app_commands.checks.has_permissions(moderate_members=True)
async def unmute(interaction: discord.Interaction, member: discord.Member):

    await member.timeout(None)

    try:
        await member.send(f"You have been **unmuted** in {interaction.guild.name}. You can speak now!")
    except:
        pass

    await interaction.response.send_message(
        f"{member.mention} has been unmuted.",
        ephemeral=True
    )

@bot.tree.command(name="unban", description="Unban a user by ID", guild=guild)
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str):

    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user)

        await interaction.response.send_message(
            f"{user} has been unbanned.",
            ephemeral=True
        )

    except:
        await interaction.response.send_message(
            "invalid user id or user not banned.",
            ephemeral=True
        )
    
@bot.tree.command(name="slowmode", description="Set slowmode for this channel", guild=guild)
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int):

    if seconds < 0 or seconds > 21600:
        await interaction.response.send_message("slowmode must be between 0 and 21600 seconds (6 hours).", ephemeral=True)
        return

    await interaction.channel.edit(slowmode_delay=seconds)

    await interaction.response.send_message(
        f"slowmode set to {seconds} seconds.",
        ephemeral=True
    )

@bot.tree.command(name="nickname", description="Change a member's nickname", guild=guild)
@app_commands.checks.has_permissions(manage_nicknames=True)
async def nickname(interaction: discord.Interaction, member: discord.Member, new_name: str):

    if member.top_role >= interaction.user.top_role:
        await interaction.response.send_message("you cant change nickname of equal or higher role.", ephemeral=True)
        return

    await member.edit(nick=new_name)

    await interaction.response.send_message(
        f"{member.mention}'s nickname changed to **{new_name}**.",
        ephemeral=True
    )

@bot.tree.command(
    name="purge",
    description="Delete a number of messages from this channel",
    guild=guild
)
@app_commands.describe(amount="Number of messages to delete")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge(interaction: discord.Interaction, amount: int):

    if amount < 1:
        await interaction.response.send_message(
            "you need to delete at least 1 message.",
            ephemeral=True
        )
        return

    if amount > 100:
        await interaction.response.send_message(
            "you can only delete up to 100 messages at once.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    deleted = await interaction.channel.purge(limit=amount)

    await interaction.followup.send(
        f"deleted {len(deleted)} messages.",
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
