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
        # Keyed by taxonomy term ID, so renamed terms keep their colour
        self.tag_colours = {
            "171": "⚪ ",   # Γενικά
            "56": "🔴 ",    # Προπτυχιακά
            "57": "🔵 ",    # Μεταπτυχιακά
            "60": "🟣 ",    # Διδακτορικά
            "215": "⚫ ",   # CIVIS
            "59": "🟠 ",    # Πρακτική Άσκηση
            "131": "🟢 "    # Νέες θέσεις εργασίας
        }
        # Same colours as the website (dit_theme/css/components/categories.css)
        self.category_colours = {
            "56": 0x730071,     # Προπτυχιακά
            "57": 0xB7AAFF,     # Μεταπτυχιακά
            "58": 0x98CE00,     # Υποτροφίες Προπτυχιακών
            "59": 0xF5B700,     # Πρακτική Άσκηση
            "60": 0xF0A6CA,     # Διδακτορικά
            "61": 0xF71735,     # Προκηρύξεις Μεταπτυχιακών
            "62": 0xDC0073,     # Προκηρύξεις Διδακτορικών
            "131": 0x01FFFF,    # Νέες θέσεις εργασίας
            "132": 0x98CE00,    # Υποτροφίες Μεταπτυχιακών
            "133": 0x98CE00,    # Υποτροφίες Διδακτορικών
            "171": 0x0190D6,    # Γενικά
            "182": 0xEE7727,    # Προκηρύξεις Μελών ΔΕΠ
            "193": 0x6B9080,    # Erasmus+
            "210": 0x3A0CA3,    # ΠΜΣ Πληροφορική
            "211": 0x4361EE,    # ΠΜΣ Μηχανική Υπολογιστών, Τηλεπικοινωνιών και Δικτύων
            "212": 0xFF97B7,    # ΠΜΣ Τεχνολογίες Πληροφορικής και Επικοινωνιών
            "213": 0xA6808C     # ΔΠΜΣ Γλωσσική Τεχνολογία
        }
        # Fallback for categories without a term ID in the feed
        self.category_names = {
            "Γενικά": "171", "Προπτυχιακά": "56", "Μεταπτυχιακά": "57", "Υποτροφίες Προπτυχιακών": "58",
            "Πρακτική Άσκηση": "59", "Διδακτορικά": "60", "Προκηρύξεις Μεταπτυχιακών": "61",
            "Προκηρύξεις Διδακτορικών": "62", "Νέες θέσεις εργασίας": "131",
            "Υποτροφίες Μεταπτυχιακών": "132", "Υποτροφίες Διδακτορικών": "133",
            "Προκηρύξεις Μελών ΔΕΠ": "182", "Erasmus+": "193", "ΠΜΣ Πληροφορική": "210",
            "ΠΜΣ Μηχανική Υπολογιστών, Τηλεπικοινωνιών και Δικτύων": "211",
            "ΠΜΣ Τεχνολογίες Πληροφορικής και Επικοινωνιών": "212",
            "ΔΠΜΣ Γλωσσική Τεχνολογία": "213", "CIVIS": "215"
        }

        # Only this cog's keys, "guilds" belongs to GuildData
        data = data_store.read()
        self.data = {key: data[key] for key in ("last_update", "seen") if key in data}

        self.timestamp = self.data["last_update"]

        self.send_new_annoucements.start()

    async def get_new_announcements(self) -> tuple:
        try:
            response = get(self.rss_feed, timeout=4.0)
            response.raise_for_status()
        except RequestException:
            self.logger.warn(f"{self.rss_feed} is not working, Is it up?")
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

            entry_time = timegm(entry.published_parsed)     # mktime converts to wrong timezone for some reason
            utc_time = datetime.fromtimestamp(entry_time).replace(tzinfo=ZoneInfo('UTC'))
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
        return self.category_names.get(tag.term)

    def format_tags(self, tags) -> str:
        """ Returns a string with the tags and their colour """
        ptags = ""
        for (term_id, name) in tags:
            colour = self.tag_colours.get(term_id, "🟡 ")
            ptags += f"\n{colour} {name}"
        return ptags

    def embed_colour(self, tags) -> int:
        """ The site's colour of the first category, the same one it shows first """
        return self.category_colours.get(tags[0][0], 0x36ABCC)

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
                current = self.bot.get_channel(int(ch))
                await current.send(embed=embed)
            