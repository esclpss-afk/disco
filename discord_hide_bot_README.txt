Discord Hidden Role Bot

1) Install dependency:
   pip install -U discord.py

2) Set your bot token:
   PowerShell:
   $env:DISCORD_BOT_TOKEN="YOUR_BOT_TOKEN_HERE"

3) Run:
   python discord_hide_bot.py

What it does:
- Targets user ID: 332714060707528718
- Creates role: HiddenUser (if missing)
- Sets deny "View Channel" on all categories/channels for that role
- Assigns that role to the target user if they are in the server
- Reapplies on startup and when that user joins

Important:
- Bot needs permissions: Manage Roles, Manage Channels, View Channels
- In Server Settings > Roles, move the bot role above HiddenUser
- Enable Privileged Gateway Intent "Server Members Intent" in the Discord Developer Portal
