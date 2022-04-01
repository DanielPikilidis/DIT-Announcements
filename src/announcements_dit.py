import discord, logging
from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup as bs
from feedparser import parse
from time import time as current_time
from calendar import timegm
from json import dump, loads
from requests import get, ReadTimeout
from dataclasses import dataclass

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
        self.rss_feed = "http://www.di.uoa.gr/rss.xml"
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
            get(self.rss_feed, timeout=4.0)
        except ReadTimeout:
            self.logger.warn(f"{self.rss_feed} is not working, Is it up?")
            return (1, [])

        feed = parse(self.rss_feed)

        new_announcements = []
        previous_urls = [] # Sometimes this rss feed has duplicate items, this filters them out
        for entry in feed.entries:
            entry_time = timegm(entry.published_parsed)     # mktime converts to wrong timezone for some reason
            if entry_time <= self.timestamp:
                break

            title = entry.title
            url = entry.link
            if url in previous_urls:
                continue
            else:
                previous_urls.append(url)

            utc_time = datetime.fromtimestamp(entry_time).replace(tzinfo=ZoneInfo('UTC'))
            local_time = utc_time.astimezone(ZoneInfo('Europe/Athens')).strftime("%A, %d/%m/%Y, %H:%M")

            new_announcements.append(
                Announcement(title, url, local_time, self.get_tags(url))
            )
        
        if len(new_announcements):
            self.data["last_update"] = self.timestamp = timegm(feed.entries[0].published_parsed)
            with open("data/data.json", "w") as file:
                dump(self.data, file, indent=4)
            return (0, new_announcements[::-1])
        else:
            return (1, [])

    def get_tags(self, link) -> list:
        """ 
        The rss feed doesn't have the announcement tags, so when a there's a new announcement this 
        function is called with the link and gathers the tags from that announcement's page.
        """
        response = get(link)
        soup = bs(response.text, features="html.parser")
        tags_table = soup.find("div", {"class": "field__items"})
        
        tags = [i.text for i in tags_table.children if i != "\n"]
        return tags

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
            