import discord
from discord.ext import commands, tasks
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup as bs
from feedparser import parse
from time import mktime, time
from requests import get
from json import dump, loads
from os.path import exists


class DitAnnouncements(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.old_list = []
        self.already_sent = []
        self.tag_colours = {
            "Γενικά": "⚪ ", 
            "Προπτυχιακά": "🔴 ", 
            "Μεταπτυχιακά": "🔵 ", 
            "Διδακτορικά": "🟣 ",
            "CIVIS": "⚫ ", 
            "Πρακτική Άσκηση": "🟠 ", 
            "Νέες θέσεις εργασίας": "🟢 "
        }

        if exists("data/old_list.json"):
            with open("data/old_list.json", "r") as file:
                self.old_list = loads(file.read())
        else:
            (result, self.old_list) = self.get_an_list()
            with open("data/old_list.json", "w") as file:
                dump(self.old_list, file, indent=4)

        if exists("data/already_sent.json"):
            with open("data/already_sent.json", "r") as file:
                self.already_sent = loads(file.read())
        else:
            self.already_sent = []
            with open("data/already_sent.json", "w") as file:
                dump(self.already_sent, file, indent=4)
        
        self.send_new_annoucements.start()

    def get_an_list(self) -> tuple:
        """ Returns the items in the rss feed """
        response = get("https://www.di.uoa.gr/announcements")
        if response.status_code == 400:
            return (1, [])

        announcements_feed = parse("http://www.di.uoa.gr/rss.xml")
        
        announcements = []
        previous_links = []
        for i in announcements_feed["entries"]:
            title = i["title"]
            link = i["link"]
            if link in previous_links:
                continue
            else:
                previous_links.append(link)
            utc_unaware = datetime.fromtimestamp(mktime(i["published_parsed"]))
            utc_aware = utc_unaware.replace(tzinfo=ZoneInfo('UTC'))
            local_aware = utc_aware.astimezone(ZoneInfo('Europe/Athens')).strftime("%A, %d/%m/%Y, %H:%M")

            cur = {"link": link, "title": title, "dt": local_aware, "tags": []}
            announcements.append(cur)

        return (0, announcements)

    def check_for_new(self) -> tuple:
        """ Checks for any differences in the beginning of new list and the old list. """
        (result, announcements_list) = self.get_an_list()

        if result == 1:
            return (1, [])

        new_announcements = []
        for announcement in announcements_list:
            if announcement["link"] == self.old_list[0]:
                break
            else:
                announcement["tags"] = self.get_tags(announcement["link"])
                if announcement["link"] not in self.already_sent:
                    new_announcements.append(announcement)
                    self.already_sent.append(announcement["link"])

        if len(new_announcements):
            self.old_list = announcements_list
            with open("data/old_list.json", "w") as file:
                dump(self.old_list, file, indent=4)

            with open("data/already_sent.json", "w") as file:
                dump(self.already_sent, file, indent=4)
            return (0, new_announcements)
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
        (result, new_announcements) = self.check_for_new()
        if result == 0:
            channels = self.bot.data.get_announcement_channels()
            for announcement in new_announcements:
                link = announcement["link"]
                title = announcement["title"]
                tags = self.format_tags(announcement["tags"])
                
                embed = discord.Embed(
                    title="New Announcement!", 
                    url=link,
                    description=f"{title}\n\n{tags}",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1255901921896009729/xKsBUtgN.jpg")
                embed.set_footer(text=announcement["dt"])
                for ch in channels:
                    current = self.bot.get_channel(int(ch))
                    await current.send(embed=embed)
            self.bot.logger.info(f"Successfully sent new announcements to {len(channels)} servers.")