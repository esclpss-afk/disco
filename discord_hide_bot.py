import os
import asyncio
import discord
from discord import app_commands
from discord.ext import tasks


TARGET_USER_IDS = {
    332714060707528718,
    1318272541160247486,
}
HIDDEN_ROLE_NAME = "16+"
HIDE_REASON = "sus account"
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


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
    await interaction.response.send_message("Bot is online and responsive.", ephemeral=True)


@tree.command(name="ping", description="Check if the bot is responsive.")
async def ping_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("Pong.", ephemeral=True)


@tree.command(name="serverinfo", description="Show basic server info.")
async def serverinfo_command(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this in a server.", ephemeral=True)
        return
    await interaction.response.send_message(
        f"Server: {guild.name}\nMembers: {guild.member_count}\nChannels: {len(guild.channels)}",
        ephemeral=True,
    )


@tree.command(name="coinflip", description="Flip a coin.")
async def coinflip_command(interaction: discord.Interaction) -> None:
    import random
    await interaction.response.send_message(
        f"Result: {'Heads' if random.choice([True, False]) else 'Tails'}",
        ephemeral=True,
    )


@tree.command(name="roll", description="Roll a dice.")
@app_commands.describe(sides="Number of sides (default 6)")
async def roll_command(interaction: discord.Interaction, sides: app_commands.Range[int, 2, 100] = 6) -> None:
    import random
    value = random.randint(1, sides)
    await interaction.response.send_message(f"You rolled: {value} (1-{sides})", ephemeral=True)


@tree.command(name="choose", description="Choose one option from a comma-separated list.")
@app_commands.describe(options="Example: pizza, burgers, tacos")
async def choose_command(interaction: discord.Interaction, options: str) -> None:
    import random
    picks = [o.strip() for o in options.split(",") if o.strip()]
    if len(picks) < 2:
        await interaction.response.send_message("Give at least 2 comma-separated options.", ephemeral=True)
        return
    await interaction.response.send_message(f"I choose: {random.choice(picks)}", ephemeral=True)


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
        ephemeral=True,
    )


@tree.command(name="uptime", description="Show bot uptime.")
async def uptime_command(interaction: discord.Interaction) -> None:
    if not hasattr(bot, "started_at") or bot.started_at is None:
        await interaction.response.send_message("Uptime unavailable.", ephemeral=True)
        return
    delta = discord.utils.utcnow() - bot.started_at
    seconds = int(delta.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    await interaction.response.send_message(
        f"Uptime: {hours}h {minutes}m {secs}s",
        ephemeral=True,
    )


@tree.command(name="helpme", description="Show available commands.")
async def helpme_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(
        (
            "Commands:\n"
            "/status, /ping, /serverinfo, /userinfo, /avatar, /say, /purge, /botperms,\n"
            "/coinflip, /roll, /choose, /8ball, /uptime, /helpme"
        ),
        ephemeral=True,
    )


@tree.command(name="userinfo", description="Show basic info about a member.")
@app_commands.describe(member="The member to inspect")
async def userinfo_command(interaction: discord.Interaction, member: discord.Member) -> None:
    joined = member.joined_at.isoformat() if member.joined_at else "unknown"
    created = member.created_at.isoformat() if member.created_at else "unknown"
    await interaction.response.send_message(
        f"User: {member} ({member.id})\nCreated: {created}\nJoined: {joined}",
        ephemeral=True,
    )


@tree.command(name="avatar", description="Show avatar URL for a member.")
@app_commands.describe(member="The member (defaults to you)")
async def avatar_command(interaction: discord.Interaction, member: discord.Member | None = None) -> None:
    target = member or interaction.user
    if isinstance(target, discord.Member):
        avatar_url = target.display_avatar.url
        await interaction.response.send_message(f"Avatar: {avatar_url}", ephemeral=True)
        return
    await interaction.response.send_message("Could not resolve member.", ephemeral=True)


@tree.command(name="say", description="Make the bot repeat a message.")
@app_commands.describe(message="Message to send")
async def say_command(interaction: discord.Interaction, message: str) -> None:
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You need Manage Messages for this.", ephemeral=True)
        return
    await interaction.response.send_message("Sent.", ephemeral=True)
    await interaction.channel.send(message)


@tree.command(name="purge", description="Delete recent messages in this channel.")
@app_commands.describe(amount="How many messages to delete (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def purge_command(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
    guild = interaction.guild
    channel = interaction.channel
    if guild is None or not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message("Use this in a server.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True, thinking=True)
    deleted = await channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)


@tree.command(name="botperms", description="Show bot permissions in this server.")
async def botperms_command(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message("Use this in a server.", ephemeral=True)
        return
    ok, reason = has_required_permissions(guild)
    me = guild.me
    top_role = me.top_role.name if me else "unknown"
    await interaction.response.send_message(
        f"Permissions OK: {'yes' if ok else 'no'}\nDetails: {reason}\nBot top role: {top_role}",
        ephemeral=True,
    )


@purge_command.error
async def permissions_error_handler(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "You do not have permission to use this command.",
            ephemeral=True,
        )
        return
    raise error


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} ({bot.user.id})")
    bot.started_at = discord.utils.utcnow()
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="Hiding channels"),
    )
    print("Presence set to ONLINE.")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as error:
        print(f"Failed to sync slash commands: {error}")

    await reconcile_all_guilds()


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if member.id not in TARGET_USER_IDS:
        return

    try:
        await hide_target_users_in_guild(member.guild)
        print(f"Applied hidden role to target user in {member.guild.name}")
    except Exception as error:
        print(f"Failed applying role on join: {error}")


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    try:
        await hide_target_users_in_guild(guild)
        print(f"Configured hidden role after joining guild: {guild.name}")
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


@tasks.loop(minutes=2)
async def periodic_reconcile() -> None:
    await reconcile_all_guilds()


@periodic_reconcile.before_loop
async def before_periodic_reconcile() -> None:
    await bot.wait_until_ready()


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN environment variable.")
    async with bot:
        periodic_reconcile.start()
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
