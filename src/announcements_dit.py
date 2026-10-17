import discord, logging
from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo
from feedparser import parse
from calendar import timegm
from requests import get, RequestException
from dataclasses import dataclass
from os import environ
import data_store
from categories import CATEGORY_COLOURS, CATEGORY_NAMES, EMOJI_PREFIX, emoji_name
from pathlib import Path

EMOJI_DIR = Path(__file__).resolve().parent.parent / "assets" / "category_emojis"

@dataclass
class Announcement:
    title: str
    url: str
    date: str
    tags: list


class DitAnnouncements(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger: logging = bot.logger
        self.rss_feed = environ.get("DIT_RSS_FEED", "http://www.di.uoa.gr/rss.xml")
        # Keyed by taxonomy term ID, so renamed terms keep their colour.
        # Fallback when the site colour emojis aren't available.
        self.tag_colours = {
            "171": "⚪ ",   # Γενικά
            "56": "🔴 ",    # Προπτυχιακά
            "57": "🔵 ",    # Μεταπτυχιακά
            "60": "🟣 ",    # Διδακτορικά
            "215": "⚫ ",   # CIVIS
            "59": "🟠 ",    # Πρακτική Άσκηση
            "131": "🟢 "    # Νέες θέσεις εργασίας
        }
        # Only this cog's keys, "guilds" belongs to GuildData
        data = data_store.read()
        self.data = {key: data[key] for key in ("last_update", "seen") if key in data}

        self.timestamp = self.data["last_update"]

        # term ID -> "<:dit_cat_xxxxxx:id> ", filled in by load_emojis()
        self.tag_emojis = {}

        self.send_new_annoucements.start()

    async def load_emojis(self):
        """
        Makes sure the bot has an application emoji for every site colour (uploading missing ones
        from assets/category_emojis), caches them per term ID and deletes its old dit_cat_ emojis.
        On any failure the tags just keep using the plain circle emojis, it never stops the announcements.
        """
        try:
            existing = {emoji.name: emoji for emoji in await self.bot.fetch_application_emojis()}
        except Exception:
            self.logger.warning("Couldn't list the application emojis, using the default circles.", exc_info=True)
            return

        for colour in sorted(set(CATEGORY_COLOURS.values())):
            name = emoji_name(colour)
            emoji = existing.get(name)
            if emoji is None:
                try:
                    emoji = await self.bot.create_application_emoji(name=name, image=(EMOJI_DIR / f"{name}.png").read_bytes())
                    self.logger.info(f"Uploaded application emoji {name}.")
                except Exception:
                    self.logger.warning(f"Couldn't upload application emoji {name}, using the default circle.", exc_info=True)
                    continue

            for term_id, term_colour in CATEGORY_COLOURS.items():
                if term_colour == colour:
                    self.tag_emojis[term_id] = f"{emoji} "

        # Remove emojis of older styles or colours, only the ones this bot manages
        current = {emoji_name(colour) for colour in CATEGORY_COLOURS.values()}
        for name, emoji in existing.items():
            if name.startswith(EMOJI_PREFIX) and name not in current:
                try:
                    await emoji.delete()
                    self.logger.info(f"Deleted old application emoji {name}.")
                except Exception:
                    self.logger.warning(f"Couldn't delete old application emoji {name}.", exc_info=True)

    async def get_new_announcements(self) -> tuple:
        try:
            response = get(self.rss_feed, timeout=4.0)
            response.raise_for_status()
        except RequestException:
            self.logger.warning(f"{self.rss_feed} is not working, Is it up?")
            return (1, [])

        feed = parse(response.content)

        # The feed also contains events and highlights, only announcements have categories
        entries = [entry for entry in feed.entries if entry.get("tags")]
        if not entries:
            return (1, [])

        # Many announcements share the same timestamp (date only, midnight), so a timestamp
        # alone can't tell which ones were already sent. Remember the guids instead.
        if "seen" not in self.data:
            self.data["seen"] = [
                entry.id for entry in entries if timegm(entry.published_parsed) <= self.timestamp
            ]
        seen = set(self.data["seen"])

        if self.timestamp == 0:  # First time running the bot
            self.data["last_update"] = self.timestamp = timegm(entries[0].published_parsed)
            seen.update(entry.id for entry in entries)

        new_announcements = []
        for entry in entries:
            if entry.id in seen:
                continue
            seen.add(entry.id)

            # published_parsed is in UTC. Convert explicitly, so the host's timezone doesn't matter
            utc_time = datetime.fromtimestamp(timegm(entry.published_parsed), tz=ZoneInfo('UTC'))
            local_time = utc_time.astimezone(ZoneInfo('Europe/Athens')).strftime("%A, %d/%m/%Y, %H:%M")

            tags = [(self.term_id(tag), tag.term) for tag in entry.tags]
            new_announcements.append(Announcement(entry.title, entry.link, local_time, tags))

        # Newest first, capped so the list doesn't grow forever (the feed has 30 items)
        current = [entry.id for entry in entries if entry.id in seen]
        current += [guid for guid in self.data["seen"] if guid not in current]
        current = current[:200]
        changed = current != self.data["seen"]
        self.data["seen"] = current

        if len(new_announcements):
            self.data["last_update"] = self.timestamp = max(self.timestamp, timegm(entries[0].published_parsed))

        if changed:
            state = {"last_update": self.data["last_update"], "seen": self.data["seen"]}
            try:
                data_store.update(lambda data: data.update(state))
            except Exception:
                self.logger.error("Failed to save the sent announcements to data.json.", exc_info=True)

        if len(new_announcements):
            return (0, new_announcements[::-1])
        else:
            return (1, [])

    def term_id(self, tag) -> str:
        """ The term ID is the last path segment of the <category domain=".../taxonomy/term/ID"> """
        if tag.get("scheme"):
            return tag.scheme.rstrip("/").rsplit("/", 1)[-1]
        return CATEGORY_NAMES.get(tag.term)

    def format_tags(self, tags) -> str:
        """ Returns a string with the tags and their colour """
        ptags = ""
        for (term_id, name) in tags:
            colour = self.tag_emojis.get(term_id) or self.tag_colours.get(term_id, "🟡 ")
            ptags += f"\n{colour} {name}"
        return ptags

    def embed_colour(self, tags) -> int:
        """ The site's colour of the first category, the same one it shows first """
        return CATEGORY_COLOURS.get(tags[0][0], 0x36ABCC)

    @tasks.loop(seconds=15.0)
    async def send_new_annoucements(self):
        (result, new_announcements) = await self.get_new_announcements()
        if result == 1:
            return

        self.logger.info("Found new announcements, sending.")
        channels = self.bot.data.get_announcement_channels()
        for announcement in new_announcements:
            title = announcement.title
            url = announcement.url
            tags = self.format_tags(announcement.tags)
            colour = self.embed_colour(announcement.tags)

            embed = discord.Embed(
                title = "New Announcement!",
                url = url,
                description = f"{title}\n\n{tags}",
                color = colour
            )
            embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1255901921896009729/xKsBUtgN.jpg")
            embed.set_footer(text=announcement.date)
            for ch in channels:
                # One deleted channel or missing permission must not stop the other guilds
                current = self.bot.get_channel(int(ch))
                if current is None:
                    self.logger.warning(f"Channel {ch}: Not found, skipping. Was it deleted?")
                    continue
                try:
                    await current.send(embed=embed)
                except discord.HTTPException:
                    self.logger.warning(f"Channel {ch}: Couldn't send the announcement.", exc_info=True)
            
    @send_new_annoucements.before_loop
    async def before_send_new_announcements(self):
        await self.bot.wait_until_ready()
        await self.load_emojis()
