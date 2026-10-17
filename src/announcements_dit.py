import discord, logging
from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo
from feedparser import parse
from calendar import timegm
from json import dump, loads
from requests import get, RequestException
from dataclasses import dataclass
from os import environ

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
        self.tag_colours = {
            "Γενικά": "⚪ ", 
            "Προπτυχιακά": "🔴 ", 
            "Μεταπτυχιακά": "🔵 ", 
            "Διδακτορικά": "🟣 ",
            "CIVIS": "⚫ ", 
            "Πρακτική Άσκηση": "🟠 ", 
            "Νέες θέσεις εργασίας": "🟢 "
        }

        with open("data/data.json", "r") as file:
            self.data = loads(file.read())

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

            tags = [tag.term for tag in entry.tags]
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
            with open("data/data.json", "w") as file:
                dump(self.data, file, indent=4)

        if len(new_announcements):
            return (0, new_announcements[::-1])
        else:
            return (1, [])

    def format_tags(self, tags) -> str:
        """ Returns a string with the tags and their colour """
        ptags = ""
        for tag in tags:
            if tag in self.tag_colours.keys():
                colour = self.tag_colours[tag]
            else:
                colour = "🟡 "
            
            ptags += f"\n{colour} {tag}"
        return ptags

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

            embed = discord.Embed(
                title = "New Announcement!",
                url = url,
                description = f"{title}\n\n{tags}",
                color = 0x36ABCC
            )
            embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1255901921896009729/xKsBUtgN.jpg")
            embed.set_footer(text=announcement.date)
            for ch in channels:
                current = self.bot.get_channel(int(ch))
                await current.send(embed=embed)
            