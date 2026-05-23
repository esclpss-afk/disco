# Discord Bot Railway Deploy (Plug and Play)

This setup deploys `discord_hide_bot.py` on Railway without touching your existing `requirements.txt`.

## Files included

- `discord_hide_bot.py`
- `requirements-bot.txt`
- `Procfile`
- `railway.toml`
- `nixpacks.toml`
- `.env.example` (create from step below if needed)

## 1) Discord bot setup

1. Go to the Discord Developer Portal and create an app.
2. Add a Bot user.
3. In **Bot** settings, enable **Server Members Intent**.
4. Copy your bot token.
5. Invite bot with permissions:
   - Manage Roles
   - Manage Channels
   - View Channels

## 2) Prepare repo

1. Put the bot files in a GitHub repo.
2. Commit and push to GitHub.

## 3) Deploy on Railway

1. Open Railway and create a **New Project**.
2. Choose **Deploy from GitHub repo** and select your repo.
3. Railway will detect config files and deploy.

## 4) Set environment variable

In Railway service -> **Variables**, add:

- `DISCORD_BOT_TOKEN=your_real_token_here`

After adding/updating variables, trigger a redeploy if Railway does not auto-redeploy.

## 5) Verify startup

Open Railway logs and confirm you see:

- `Logged in as ...`
- `Configured hidden role in guild: ...`

## 6) Discord role order check

In your server:

1. Go to **Server Settings -> Roles**.
2. Move the bot's role above `HiddenUser`.

If bot role is below `HiddenUser`, Discord blocks role assignment/permission changes.

## 7) What the bot does

- Targets user ID: `332714060707528718`
- Creates role: `HiddenUser` if missing
- Denies `View Channel` on all categories/channels for `HiddenUser`
- Assigns `HiddenUser` to that target user on startup and when they join

## Troubleshooting

- If deployment fails at install:
  - Confirm `nixpacks.toml` and `requirements-bot.txt` are in repo root.
- If bot is online but no role assigned:
  - Check bot role position and permissions.
  - Confirm user ID matches exactly.
- If bot doesn't see members:
  - Re-check **Server Members Intent** in Developer Portal.
