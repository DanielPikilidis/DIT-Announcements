# DIT-Announcements
Sends new announcements from https://www.di.uoa.gr/announcements to discord
<br>
<br>
You can invite the bot or install it to host it yourself. (instructions below)
<br>
Invite link: https://discord.com/api/oauth2/authorize?client_id=881568952378073149&permissions=27664&scope=bot
<br>
The base of the bot can be used for sending other announcements / notifications as well by adding more cogs.


## Installation
For any method you will need a bot token from the [Discord Developer Portal](https://discord.com/developers/applications).

Configuration is read from environment variables, see `.env.example`:

| Variable | Description |
| --- | --- |
| `DISCORD_TOKEN` | Your Discord bot token |
| `DIT_RSS_FEED` | The announcements feed (default: `http://www.di.uoa.gr/rss.xml`) |

**Upgrading an existing deployment:** the bot no longer reads `data/config.json`. Before upgrading, move the
`"discord-key"` value from `data/config.json` into `.env` as `DISCORD_TOKEN`.

### Local:

1. Clone the repository

```
git clone https://github.com/DanielPikilidis/DIT-Announcements.git DitAnnouncements
cd DitAnnouncements
```

2. Install required dependencies: 

`pip3 install -r requirements.txt`

3. Create your `.env` and paste your bot token in `DISCORD_TOKEN`:

`cp .env.example .env`

4. Start the bot:

`python3 src/bot.py`

### Docker:

1. Clone the repository:

```
git clone https://github.com/DanielPikilidis/DIT-Announcements.git DitAnnouncements
cd DitAnnouncements
```

2. Create your `.env` and paste your bot token in `DISCORD_TOKEN`:

`cp .env.example .env`

3. Build the Docker image:

`docker build -t dit_announcements .`

4. Create and start the container:

`docker run -d --env-file .env -v $(pwd)/data:/data -v $(pwd)/logs:/logs --restart unless-stopped --name dit_announcements dit_announcements`
