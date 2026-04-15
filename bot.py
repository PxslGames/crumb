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
import os
from collections import defaultdict, deque

BOT_VERSION = "1.1.8"

START_TIME = time.time()

DATA_FILE = "data.json"

OWNER_ID = 994116541559865416

JOIN_EMOJI = "<:join:1493694693840785598>"
LEAVE_EMOJI = "<:leave:1493694784815235153>"
BOOST_EMOJI = "<a:boost:1493695082799304764>"
NEW_EMOJI = "<a:emoji:1493702510928597073>"

data_lock = asyncio.Lock()

class GiveawayView(discord.ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=None)
        self.message_id = str(message_id)

    @discord.ui.button(
        label="Enter Giveaway 🎉",
        style=discord.ButtonStyle.green
    )
    async def enter(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        async with data_lock:
            giveaways = data.setdefault("giveaways", {})
            g = giveaways.get(self.message_id)

            if not g:
                return await interaction.response.send_message(
                    "this giveaway is over or invalid",
                    ephemeral=True
                )

            participants = g.setdefault("participants", [])
            uid = interaction.user.id

            if uid in participants:
                participants.remove(uid)
                await save_data()
                return await interaction.response.send_message(
                    "you left the giveaway",
                    ephemeral=True
                )

            participants.append(uid)
            await save_data()

        await interaction.response.send_message(
            "you entered the giveaway",
            ephemeral=True
        )

async def safe_delete(msg):
    try:
        if msg.channel.permissions_for(msg.guild.me).manage_messages:
            await msg.delete()
    except:
        pass

async def issue_warn(guild, user, reason):
    gid_str = str(guild.id)
    uid_str = str(user.id)

    warns.setdefault(gid_str, {}).setdefault(uid_str, [])

    warn_data = {
        "reason": reason,
        "moderator": "AutoMod",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    warns[gid_str][uid_str].append(warn_data)
    total_warns = len(warns[gid_str][uid_str])

    await save_data()

    # ✅ timeout ALWAYS on warn
    try:
        await user.timeout(datetime.timedelta(minutes=10), reason=reason)
    except:
        pass

    try:
        await user.send(
            f"You were warned in {guild.name}\n"
            f"Reason: {reason}\n"
            f"Total warns: {total_warns}"
        )
    except:
        pass

    if total_warns >= 5:
        try:
            await guild.ban(user, reason="Reached 5 warnings (auto-mod)")
        except:
            pass

        warns[gid_str].pop(uid_str, None)
        await save_data()

    return total_warns

def load_data():
    if not os.path.exists(DATA_FILE):
        data = {
            "token": "",
            "warns": {},
            "giveaways": {},
            "reminders": []
        }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return data

    with open(DATA_FILE, "r") as f:
        return json.load(f)

async def save_data():
    async with data_lock:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)

data = load_data()
TOKEN = data.get("token", "")

if not TOKEN:
    raise RuntimeError("Bot token is missing in data.json")

def parse_time(t: str):
    t = t.lower()
    if t.endswith("m"):
        return int(t[:-1]) * 60
    if t.endswith("h"):
        return int(t[:-1]) * 3600
    if t.endswith("s"):
        return int(t[:-1])
    return int(t)

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

def get_member_count(guild: discord.Guild) -> int:
    return guild.member_count or len(guild.members)

def get_boost_count(guild: discord.Guild) -> int:
    return guild.premium_subscription_count or 0

synced = False

def get_warns():
    return data.setdefault("warns", {})

warns = data["warns"]

data.setdefault("warns", {})

spam_tracker = defaultdict(list)
spam_cooldown = {}
warned_cooldown = set()
SPAM_WINDOW = 3
SPAM_LIMIT = 4
SPAM_PUNISH_COOLDOWN = 30

@bot.event
async def on_ready():
    global synced

    if not synced:
        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                log.info(f"Synced commands to {guild.name}")
            except Exception as e:
                log.error(f"Sync failed for {guild.name}: {e}")

        synced = True
    
    bot.loop.create_task(reminder_loop())
    bot.loop.create_task(giveaway_loop())
    log.info("created loops for reminders and giveaways")

    log.info(f"Logged in as {bot.user}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    log.exception(error)

    if interaction.response.is_done():
        await interaction.followup.send("something broke 💀", ephemeral=True)
    else:
        await interaction.response.send_message("something broke 💀", ephemeral=True)

@bot.event
async def on_guild_join(guild: discord.Guild):
    log.info(f"Joined {guild.name}")

    try:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        log.info(f"Synced commands to {guild.name}")
    except Exception as e:
        log.error(f"Failed to sync commands for {guild.name}: {e}")

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
        "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    }

    warns[gid][uid].append(warn_data)
    total_warns = len(warns[gid][uid])

    await save_data()

    try:
        await member.send(
            f"You have been warned in {interaction.guild.name}\nReason: {reason}\nTotal warns: {total_warns}"
        )
    except:
        pass

    if total_warns >= 5:
        try:
            await member.ban(reason="Reached 5 warnings")
        except:
            pass

        warns[gid].pop(uid, None)
        await save_data()

        await interaction.response.send_message(
            f"{member.mention} reached 5 warns and was banned.",
            ephemeral=True
        )
        return

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
        await save_data()
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
    await interaction.response.send_message("yo updated status cuh", ephemeral=True)

@bot.tree.command(name="announce", description="Send a message to all servers system channels (owner only)")
async def announce(interaction: discord.Interaction, message: str):

    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message(
            "you are not allowed to use this command.",
            ephemeral=True
        )

    await interaction.response.send_message(
        "sending announcement...",
        ephemeral=True
    )

    sent = 0
    failed = 0

    for guild in bot.guilds:
        channel = get_system_channel(guild)

        if not channel:
            failed += 1
            continue

        try:
            await channel.send(message)
            sent += 1
        except:
            failed += 1

    await interaction.followup.send(
        f"done.\nsent: {sent}\nfailed: {failed}",
        ephemeral=True
    )

@bot.tree.command(name="stats", description="view server stats")
async def stats(interaction: discord.Interaction):
    guild = interaction.guild

    total_members = guild.member_count or len(guild.members)
    bots = sum(1 for m in guild.members if m.bot)
    humans = total_members - bots

    online = sum(
        1 for m in guild.members
        if m.status != discord.Status.offline
    )

    boosts = guild.premium_subscription_count or 0
    boost_level = guild.premium_tier

    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)

    roles = len(guild.roles)
    emojis = len(guild.emojis)
    stickers = len(guild.stickers)

    msg = (
        f"**{guild.name} stats**\n\n"

        f"👥 **Members**\n"
        f"Total: {total_members}\n"
        f"Humans: {humans}\n"
        f"Bots: {bots}\n"
        f"Online: {online}\n\n"

        f"🚀 **Boosts**\n"
        f"Boosts: {boosts}\n"
        f"Level: {boost_level}\n\n"

        f"📊 **Server**\n"
        f"Roles: {roles}\n"
        f"Emojis: {emojis}\n"
        f"Stickers: {stickers}\n\n"

        f"📁 **Channels**\n"
        f"Text: {text_channels}\n"
        f"Voice: {voice_channels}\n"
        f"Categories: {categories}\n\n"

        f"ID: {guild.id}"
    )

    await interaction.response.send_message(msg, ephemeral=True)

async def reminder_loop():
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = time.time()
        changed = False

        for r in list(data["reminders"]):
            if now >= r["time"]:
                try:
                    channel = bot.get_channel(r["channel_id"])
                    user = await bot.fetch_user(r["user_id"])
                    await channel.send(f"⏰ {user.mention} reminder: {r['text']}")
                except:
                    pass

                data["reminders"].remove(r)
                changed = True

        if changed:
            await save_data()

        await asyncio.sleep(5)

@bot.tree.command(name="remindme", description="set a reminder")
async def remindme(interaction: discord.Interaction, time_str: str, *, reminder: str):

    seconds = parse_time(time_str)

    data["reminders"].append({
        "user_id": interaction.user.id,
        "channel_id": interaction.channel.id,
        "time": time.time() + seconds,
        "text": reminder
    })

    await save_data()

    await interaction.response.send_message(
        f"⏰ I’ll remind you in {time_str}: {reminder}",
        ephemeral=True
    )

async def giveaway_loop():
    await bot.wait_until_ready()

    while not bot.is_closed():
        now = time.time()
        changed = False

        for msg_id in list(data["giveaways"].keys()):
            g = data["giveaways"][msg_id]

            if now >= g["end_time"]:
                channel = bot.get_channel(g["channel_id"])
                participants = g["participants"]

                if not participants:
                    await channel.send(f"🎉 Giveaway ended: {g['prize']}\nNo entries 😭")
                else:
                    winners = random.sample(
                        participants,
                        k=min(g["winners"], len(participants))
                    )

                    mentions = []
                    for uid in winners:
                        user = await bot.fetch_user(uid)
                        mentions.append(user.mention)

                    await channel.send(
                        f"🎉 **GIVEAWAY ENDED** 🎉\n"
                        f"Prize: {g['prize']}\n"
                        f"Winners: {', '.join(mentions)}"
                    )

                del data["giveaways"][msg_id]
                changed = True

        if changed:
            await save_data()

        await asyncio.sleep(5)

@bot.tree.command(name="giveaway", description="create a giveaway")
@app_commands.checks.has_permissions(administrator=True)
async def giveaway(interaction: discord.Interaction, winners: int, time_str: str, *, prize: str):

    seconds = parse_time(time_str)
    end_time = time.time() + seconds

    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=(
            f"**Prize:** {prize}\n"
            f"**Winners:** {winners}\n"
            f"**Ends in:** {time_str}\n\n"
            "Press the button below to enter!"
        ),
        color=discord.Color.gold()
    )

    msg = await interaction.channel.send(embed=embed)
    view = GiveawayView(msg.id)
    await msg.edit(view=view)

    data["giveaways"][str(msg.id)] = {
        "channel_id": interaction.channel.id,
        "winners": winners,
        "prize": prize,
        "end_time": end_time,
        "participants": []
    }

    await save_data()

    await interaction.response.send_message("giveaway created", ephemeral=True)

JOIN_MESSAGES = [
    "existed here",
    "has joined",
    "arrived",
    "just spawned in",
    "loaded into the server",
    "connected to reality",
    "materialised out of nowhere",
    "slid into the server",
    "just pulled up",
    "entered the chat",
    "has appeared!",
    "joined like a legend",
    "joined… suspiciously",
    "has been summoned",
    "phased into existence",
    "teleported in",
    "has logged on",
    "came out of hiding",
    "just vibed in",
    "has entered the arena",
    "spawned without warning",
    "joined the chaos",
    "has been deployed",
    "joined successfully (probably)",
    "is now part of the problem",
    "just walked in like they own the place",
    "joined and immediately got judged",
    "has joined… everyone act normal",
    "just dropped in",
    "connected (wifi permitting)",
    "has entered the void",
    "joined the cult",
    "has arrived fashionably late",
    "just appeared out of thin air",
    "joined the madness",
]

LEAVE_MESSAGES = [
    "left",
    "disappeared",
    "vanished",
    "rage quit",
    "faded away",
    "evaporated",
    "has left the building",
    "disconnected from reality",
    "just dipped",
    "went offline forever (maybe)",
    "escaped",
    "ran away",
    "has logged off",
    "quit while ahead",
    "quit while behind",
    "just vanished into the void",
    "has left us 😔",
    "despawned",
    "went poof",
    "has exited stage left",
    "backspaced themselves",
    "left without saying goodbye",
    "has been yeeted",
    "took the exit",
    "ghosted the server",
    "just disappeared… weird",
    "has left the chaos",
    "rage quit (understandable)",
    "is gone. reduced to atoms.",
    "just dipped out",
    "has departed",
]

BOOST_MESSAGES = [
    "boosted the server!",
    "just boosted the server 🚀",
    "gave the server more power!",
    "boosted like a legend",
    "just dropped a boost 💜",
    "made the server stronger!",
    "boosted the vibes",
    "just powered up the server",
    "gave us extra juice ⚡",
    "boosted like an absolute unit",
    "just upgraded the server",
    "boosted the server (W)",
    "just gave us a level up!",
    "boosted because they’re cool like that",
    "just carried the server",
    "boosted the server into the future",
    "just made everything better",
    "boosted the chaos",
    "just pressed the boost button",
    "boosted. everyone clap.",
    "just flexed with a boost",
    "boosted the server… respect",
    "just dropped a premium boost",
    "boosted and didn’t even hesitate",
]

EMOJI_ADD_MESSAGES = [
    "new emoji just dropped: {emoji}",
    "someone cooked this emoji: {emoji}",
    "fresh emoji alert: {emoji}",
    "we got a new emoji: {emoji}",
    "this just got added → {emoji}",
    "emoji expansion pack unlocked: {emoji}",
]

EMOJI_REMOVE_MESSAGES = [
    "rip emoji: {emoji}",
    "this emoji got deleted: {emoji}",
    "we lost an emoji... {emoji}",
    "gone but not forgotten: {emoji}",
    "emoji got yeeted: {emoji}",
    "this one didn’t make it: {emoji}",
]

STICKER_ADD_MESSAGES = [
    "new sticker just dropped: {sticker}",
    "fresh sticker added: {sticker}",
    "we got a new sticker: {sticker}",
    "sticker unlocked: {sticker}",
    "this sticker just appeared → {sticker}",
]

STICKER_REMOVE_MESSAGES = [
    "rip sticker: {sticker}",
    "sticker got deleted: {sticker}",
    "we lost a sticker... {sticker}",
    "gone but not forgotten: {sticker}",
    "sticker got yeeted: {sticker}",
]

@bot.event
async def on_member_join(member: discord.Member):
    channel = get_system_channel(member.guild)
    if channel:
        count = get_member_count(member.guild)
        await channel.send(
            f"{JOIN_EMOJI} {member.mention} {random.choice(JOIN_MESSAGES)}, we now have {count} members!"
        )

@bot.event
async def on_member_remove(member: discord.Member):
    channel = get_system_channel(member.guild)
    if channel:
        count = get_member_count(member.guild)
        await channel.send(
            f"{LEAVE_EMOJI} {member.mention} {random.choice(LEAVE_MESSAGES)}, we now have {count} members!"
        )

@bot.event
async def on_member_update(before, after):
    if not before.premium_since and after.premium_since:
        channel = get_system_channel(after.guild)
        if channel:
            members = get_member_count(after.guild)
            boosts = get_boost_count(after.guild)

            await channel.send(
                f"{BOOST_EMOJI} {after.mention} {random.choice(BOOST_MESSAGES)}, we now have {boosts} boosts!")

INVITE_REGEX = re.compile(r"(discord\.gg|discord\.com/invite|discordapp\.com/invite)/[a-zA-Z0-9]+")

@bot.event
async def on_message(message: discord.Message):
    try:
        if message.author.bot or not message.guild:
            return

        now = time.time()
        uid = message.author.id
        gid = message.guild.id
        key = (gid, uid)

        cooldown_end = spam_cooldown.get(key)
        if cooldown_end and now < cooldown_end:
            try:
                await message.delete()
            except:
                pass

            if key not in warned_cooldown:
                warned_cooldown.add(key)
                await message.channel.send(
                    f"⏳ {message.author.mention} you're on cooldown, slow down."
                )

            return
        else:
            warned_cooldown.discard(key)

        timestamps = spam_tracker.setdefault(key, [])

        while timestamps and now - timestamps[0] > SPAM_WINDOW:
            timestamps.pop(0)

        mention_count = (
            len(message.mentions)
            + len(message.role_mentions)
            + (1 if message.mention_everyone else 0)
        )

        if mention_count > 3 and not message.author.guild_permissions.manage_messages:
            await safe_delete(message)

            await issue_warn(
                message.guild,
                message.author,
                f"Mass mentioning ({mention_count} mentions)"
            )

            await message.channel.send(
                f"🚨 {message.author.mention} stop mass mentioning."
            )
            return

        timestamps.append(now)

        if len(timestamps) >= SPAM_LIMIT:
            spam_tracker[key] = []
            spam_cooldown[key] = now + SPAM_PUNISH_COOLDOWN

            await issue_warn(message.guild, message.author, "Spamming (rapid messages)")
            await message.channel.send(f"🚨 {message.author.mention} stop spamming.")

            try:
                async for msg in message.channel.history(limit=20):
                    if msg.author.id == uid and (now - msg.created_at.timestamp()) <= SPAM_WINDOW:
                        try:
                            await msg.delete()
                        except:
                            pass
            except:
                pass

            return

        if "crumb" in message.content.lower():
            await message.reply(random.choice(CRUMB_RESPONSES))

        if not message.author.guild_permissions.manage_messages:
            if INVITE_REGEX.search(message.content):
                await safe_delete(message)

                await message.channel.send(
                    f"{message.author.mention} no invite links allowed."
                )

                try:
                    await message.author.timeout(datetime.timedelta(minutes=10))
                except:
                    pass

                return

        norm = normalize(message.content)
        words = set(norm.split())
        matched = words.intersection(NORMALIZED_BANNED)

        if matched:
            await safe_delete(message)

            bad = next(iter(matched))

            await issue_warn(
                message.guild,
                message.author,
                f"Used banned word: {bad}"
            )

            await message.channel.send(
                f"🚨 {message.author.mention} watch your language."
            )
            return

        await bot.process_commands(message)

    except Exception:
        log.exception("on_message crashed")

@bot.event
async def on_guild_emojis_update(guild, before, after):
    channel = get_system_channel(guild)
    if not channel:
        return

    before_set = {e.id: e for e in before}
    after_set = {e.id: e for e in after}

    added = [e for eid, e in after_set.items() if eid not in before_set]
    removed = [e for eid, e in before_set.items() if eid not in after_set]

    for emoji in added:
        msg = random.choice(EMOJI_ADD_MESSAGES).format(emoji=str(emoji))
        await channel.send(f"{NEW_EMOJI} {msg}")

    for emoji in removed:
        msg = random.choice(EMOJI_REMOVE_MESSAGES).format(emoji=str(emoji))
        await channel.send(f"{NEW_EMOJI} {msg}")

@bot.event
async def on_guild_stickers_update(guild, before, after):
    channel = get_system_channel(guild)
    if not channel:
        return

    before_set = {s.id: s for s in before}
    after_set = {s.id: s for s in after}

    added = [s for sid, s in after_set.items() if sid not in before_set]
    removed = [s for sid, s in before_set.items() if sid not in after_set]

    for sticker in added:
        msg = random.choice(STICKER_ADD_MESSAGES).format(sticker=sticker.name)
        try:
            await channel.send(
                f"{NEW_EMOJI} {msg}",
                stickers=[sticker]
            )
        except:
            await channel.send(f"{NEW_EMOJI} {msg}")

    for sticker in removed:
        msg = random.choice(STICKER_REMOVE_MESSAGES).format(sticker=sticker.name)

        if sticker.format == discord.StickerFormatType.lottie:
            await channel.send(f"{NEW_EMOJI} {msg} (animated sticker)")
        else:
            await channel.send(f"{NEW_EMOJI} {msg}\n{sticker.url}")

log.info("Bot starting...")
bot.run(TOKEN)