import os
import asyncio
import discord
from discord import app_commands


TARGET_USER_ID = 332714060707528718
HIDDEN_ROLE_NAME = "HiddenUser"
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")


intents = discord.Intents.default()
intents.guilds = True
intents.members = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


async def ensure_hidden_role(guild: discord.Guild) -> discord.Role:
    role = discord.utils.get(guild.roles, name=HIDDEN_ROLE_NAME)
    if role:
        return role

    role = await guild.create_role(
        name=HIDDEN_ROLE_NAME,
        reason="Auto-created for hiding target user from channels.",
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
            reason="Hide channels from hidden role.",
        )

    for channel in guild.channels:
        overwrite = channel.overwrites_for(role)
        overwrite.view_channel = False
        await channel.set_permissions(
            role,
            overwrite=overwrite,
            reason="Hide channels from hidden role.",
        )


async def hide_target_user_in_guild(guild: discord.Guild) -> None:
    role = await ensure_hidden_role(guild)
    await apply_hidden_overwrites(guild, role)

    member = guild.get_member(TARGET_USER_ID)
    if member is None:
        try:
            member = await guild.fetch_member(TARGET_USER_ID)
        except discord.NotFound:
            member = None
        except discord.Forbidden:
            member = None

    if member and role not in member.roles:
        await member.add_roles(role, reason="Target user auto-hidden.")


@tree.command(name="status", description="Check hidden-role bot status in this server.")
async def status_command(interaction: discord.Interaction) -> None:
    guild = interaction.guild
    if guild is None:
        await interaction.response.send_message(
            "This command must be used in a server.",
            ephemeral=True,
        )
        return

    role = discord.utils.get(guild.roles, name=HIDDEN_ROLE_NAME)
    member = guild.get_member(TARGET_USER_ID)
    if member is None:
        try:
            member = await guild.fetch_member(TARGET_USER_ID)
        except (discord.NotFound, discord.Forbidden):
            member = None

    has_role = bool(role and member and role in member.roles)
    channels_total = len(guild.channels)
    channels_locked = 0
    if role:
        for channel in guild.channels:
            overwrite = channel.overwrites_for(role)
            if overwrite.view_channel is False:
                channels_locked += 1

    await interaction.response.send_message(
        (
            f"Role exists: {'yes' if role else 'no'}\n"
            f"Target member in server: {'yes' if member else 'no'}\n"
            f"Target has hidden role: {'yes' if has_role else 'no'}\n"
            f"Channels locked for hidden role: {channels_locked}/{channels_total}"
        ),
        ephemeral=True,
    )


@bot.event
async def on_ready() -> None:
    print(f"Logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as error:
        print(f"Failed to sync slash commands: {error}")

    for guild in bot.guilds:
        try:
            await hide_target_user_in_guild(guild)
            print(f"Configured hidden role in guild: {guild.name}")
        except Exception as error:
            print(f"Failed in guild {guild.name}: {error}")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    if member.id != TARGET_USER_ID:
        return

    try:
        await hide_target_user_in_guild(member.guild)
        print(f"Applied hidden role to target user in {member.guild.name}")
    except Exception as error:
        print(f"Failed applying role on join: {error}")


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    try:
        await hide_target_user_in_guild(guild)
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
            reason="Auto-hide new channel from hidden role.",
        )
        print(f"Applied hidden overwrite to new channel: {channel.name} in {guild.name}")
    except Exception as error:
        print(f"Failed applying overwrite to new channel in {guild.name}: {error}")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Missing DISCORD_BOT_TOKEN environment variable.")
    async with bot:
        await bot.start(BOT_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
