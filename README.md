# DIT-Announcements

A Discord bot that posts new announcements from the RSS feed of the Department of Informatics and Telecommunications (DIT) website, [di.uoa.gr](https://www.di.uoa.gr/announcements), to Discord. Each announcement is sent as an embed with its categories, coloured like the categories on the website.

Invite the hosted bot: [invite link](https://discord.com/api/oauth2/authorize?client_id=881568952378073149&permissions=27664&scope=bot). You can also host it yourself, as described below.

## Features

- Checks the RSS feed every 15 seconds and posts each new announcement once.
- Shows the announcement's categories, taken from the feed. Each category gets an emoji in its website colour, and the embed is coloured by the first category.
- Works in many servers at once. Each server has its own announcements channel and its own list of roles that may configure the bot.
- Creates an `#announcements` channel when it joins a server.

## Requirements

- Python 3 (tested with Python 3.12) and the packages in `requirements.txt` (discord.py, feedparser, requests, python-dotenv).
- A Discord application with a bot user, created in the [Discord Developer Portal](https://discord.com/developers/applications). Under **Bot > Privileged Gateway Intents**, enable:
  - **Message Content Intent**, needed for the `//` commands.
  - **Server Members Intent**.
- These bot permissions in each server (`permissions=27664` in the invite link):
  - Manage Channels, to create the announcements channel on join.
  - View Channels.
  - Send Messages.
  - Manage Messages.
  - Embed Links.

## Configuration

The bot is configured with environment variables. For a local setup, it also reads them from a `.env` file in the repository root. Create one from the example:

```
cp .env.example .env
```

| Variable | Required | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | Yes | The bot token from the Discord Developer Portal. The bot exits with an error if it is not set. |
| `DIT_RSS_FEED` | No | The announcements feed. Default: `http://www.di.uoa.gr/rss.xml`. |

## Installation and running

### Local

```
git clone https://github.com/DanielPikilidis/DIT-Announcements.git
cd DIT-Announcements
python3 -m venv env
env/bin/pip install -r requirements.txt
cp .env.example .env    # then set DISCORD_TOKEN in .env
env/bin/python src/bot.py
```

Run the bot from the repository root. It creates `data/` and `logs/` there on first start.

### Docker

```
git clone https://github.com/DanielPikilidis/DIT-Announcements.git
cd DIT-Announcements
cp .env.example .env    # then set DISCORD_TOKEN in .env
docker build -t dit_announcements .
docker run -d --env-file .env \
    -v $(pwd)/data:/data -v $(pwd)/logs:/logs \
    --restart unless-stopped --name dit_announcements dit_announcements
```

## Commands

The command prefix is `//`. The server owner can always configure the bot. Other members can if they have a role in the server's control list. While that list is empty, everyone can configure the bot, so add at least one role after inviting it. `//help`, `//config permissions` and `//config permissions list` are available to everyone.

| Command | Description |
| --- | --- |
| `//help` | Shows the help message, which points to `//config`. |
| `//config` | Shows the configuration commands. |
| `//config announcements <#channel>` | Sets the channel that new announcements are posted to. |
| `//config permissions` | Shows the permission commands. |
| `//config permissions add <@role>` | Adds a role to the control list. |
| `//config permissions remove <@role>` | Removes a role from the control list. |
| `//config permissions list` | Lists the roles in the control list. |

## Data and logs

- `data/data.json` stores the bot's state:
  - `guilds`: the announcements channel and control roles of each server.
  - `seen`: the IDs of the announcements already posted.
  - `last_update`: the time of the newest announcement.

  The file is written atomically, so it is never left half written.
- `logs/output.log` is the bot's own log. It is rotated at midnight, and the previous day's log is kept.
- `logs/discord.log` is the log of the discord.py library. It is overwritten on every start.

With Docker, both directories are mounted from the host, so they survive container restarts.

## Category emojis

Each category is shown with a round emoji in its website colour:

- **Where the colours come from:** they are defined in `src/categories.py`, which mirrors the website's `categories.css`. Categories are matched by their taxonomy term ID from the feed, so renaming a category on the website does not change its colour.
- **How the images are made:** `scripts/make_category_emojis.py` generates one PNG per colour into `assets/category_emojis/`. The circle's size is set by `CIRCLE_RATIO` in `src/categories.py`. The script needs Pillow, which is only required for this script, not to run the bot:

  ```
  pip install pillow
  python3 scripts/make_category_emojis.py
  ```

- **How they reach Discord:** at startup, the bot uploads any of these images that are missing as application emojis of its Discord application. No manual setup is needed, and the same code works for any bot token.
- **Old emojis are removed:** the emoji names include the circle size and the colour (for example `dit_cat_s60_3a0ca3`). At startup, the bot deletes its own application emojis that start with `dit_cat_` but are no longer in the current set, for example after a size or colour change.
- **When something is missing:** if the emojis cannot be listed or uploaded, the bot falls back to standard circle emojis. Categories without a website colour keep a standard emoji too.

After changing a colour or `CIRCLE_RATIO` in `src/categories.py`, run the script again and commit the new images. On the next start, the bot uploads them and deletes the old ones.

## Upgrading from older versions

- **Token:** the bot no longer reads `data/config.json`. Before upgrading, move the `"discord-key"` value from `data/config.json` into `.env` as `DISCORD_TOKEN`. With Docker, start the container with `--env-file .env`.
- **Library:** the bot now uses discord.py instead of py-cord. Both packages provide the `discord` module, so remove both and then reinstall:

  ```
  env/bin/pip uninstall -y py-cord discord.py
  env/bin/pip install -r requirements.txt
  ```

- **Intents:** enable the Message Content Intent in the Developer Portal, as described under Requirements.
