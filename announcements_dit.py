from bs4 import BeautifulSoup as bs
import requests, json, discord, logging, os, datetime, time
from discord.ext import commands, tasks

class DitAnnouncements(commands.Cog):
    def __init__(self, bot: commands.Bot, logger: logging):
        self.bot = bot
        self.logger = logger
        self.send_new_annoucements.start()
        self.remove_deleted_announcements.start()
        self.old_list = []
        self.already_sent = []

        self.category_colors = {"Γενικά": "⚪ ", "Προπτυχιακά": "🔴 ", "Μεταπτυχιακά": "🔵 ", "Διδακτορικά": "🟣 ",
                  "CIVIS": "⚫ ", "Πρακτική Άσκηση": "🟠 ", "Νέες θέσεις εργασίας": "🟢 "}

        if os.path.exists("old_list.json"):
            with open("old_list.json", "r") as file:
                self.old_list = json.loads(file.read())
        else:
            self.old_list = self.get_an_list()
            with open("old_list.json", "w") as file:
                json.dump(self.old_list, file, indent=4)

        if os.path.exists("already_sent.json"):
            with open("already_sent.json", "r") as file:
                self.already_sent = json.loads(file.read())
        else:
            self.already_sent = []
            with open("already_sent.json", "w") as file:
                json.dump(self.already_sent.json, file, indent=4)

    def get_an_list(self):
        # Not using the rss feed because it doesn't return the categories for each announcement.
        response = requests.get("https://www.di.uoa.gr/announcements")

        if response.status_code == 400:
            return None

        announcements = {"sticky": [], "normal": []}
        
        html = response.text
        soup = bs(html, features="html.parser")
        announcement_table = soup.find("tbody").find_all("tr")
        for announcement in announcement_table:    
            a = announcement.find("a")
            link = f"https://www.di.uoa.gr{a['href']}"
            title = a.contents[0]


            categories = announcement.find_all("i")
            categories = [' '.join(str(n.next).split()) for n in categories]

            current = {"link": link, "title": title, "tags": categories}
            
            if announcement.find("i", {"class": "fa fa-thumbtack"}):
                announcements["sticky"].append(current)
            else:
                announcements["normal"].append(current)

        return announcements

    def check_for_new(self):
        new_list = self.get_an_list()
        if new_list == None:
            return None
        temp = {"sticky": new_list["sticky"].copy(), "normal": new_list["normal"].copy()}

        new_announcements = []
        if len(new_list["sticky"]):
            # Checking for new sticky announcements
            new_link = new_list["sticky"][0]["link"]
            old_link = self.old_list["sticky"][0]["link"]
            while new_link != old_link:
                new = new_list["sticky"].pop(0)
                if new["link"] in self.already_sent:
                    break
                new_announcements.append(new)
                self.already_sent.append(new["link"])

                if not len(new_list["sticky"]):
                    break
                new_link = new_list["sticky"][0]["link"]

        # Continuing with the non-sticky announcements
        new_link = new_list["normal"][0]["link"]
        old_link = self.old_list["normal"][0]["link"]
        new_announcements = []
        while new_link != old_link:
            new = new_list["normal"].pop(0)
            if new["link"] in self.already_sent:
                break
            new_announcements.append(new)
            self.already_sent.append(new["link"])

            if not len(new_list["normal"]):
                break
            new_link = new_list["normal"][0]["link"]

        self.old_list = temp
        with open("old_list.json", "w") as f:
            json.dump(self.old_list, f, indent=4)

        if len(new_announcements):
            with open("already_sent.json", "w") as f:
                json.dump(self.already_sent, f, indent=4)
            return new_announcements[::-1]  # Reversing the list so the announcements are in the correct order
        else:
            return None

    def get_all_announcements(self):
        sticky_links = []
        normal_links = []
        for i in self.old_list["sticky"]:
            sticky_links.append(i["link"])

        for i in self.old_list["normal"]:
            normal_links.append(i["link"])

        old = {"sticky": sticky_links, "normal": normal_links}
        return old

    @tasks.loop(seconds=15.0)
    async def send_new_annoucements(self):
        announcements = self.check_for_new()
        if announcements:
            date = datetime.datetime.now().strftime("%A, %d/%m/%Y, %H:%M")
            logging.info("Found new announcements, sending.")
            start = time.time()
            channels = self.bot.data.get_announcement_channels()
            for i in announcements:
                link = i["link"]
                title = i["title"]
                categories = ""
                length = len(i["tags"]) - 1
                for tag in i["tags"]:                    
                    if i["tags"].index(tag) != length:
                        tag = tag[:-1]

                    try:
                        color = self.category_colors[tag]
                    except:
                        color = "🟡 "
                    categories += f"\n{color} {tag}"
                
                embed = discord.Embed(
                    title="New Announcement!", 
                    url=link,
                    description=f"{title}\n\n{categories}",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1255901921896009729/xKsBUtgN.jpg")
                embed.set_footer(text=date)
                for ch in channels:
                    current = self.bot.get_channel(int(ch))
                    await current.send(embed=embed)
            end = time.time()
            total = end - start
            total_formatted = str(datetime.timedelta(seconds=int(total)))
            logging.info(f"Successfully sent new announcements to {len(channels)} servers. Total time: {total_formatted}")
        
    @tasks.loop(minutes=30.0)
    async def remove_deleted_announcements(self):
        ids = self.get_all_announcements()
        channels = self.bot.data.get_announcement_channels()
        for ch in channels:
            current = self.bot.get_channel(int(ch))
            messages = await current.history(limit=15).flatten()
            for message in messages:
                try:
                    cur_embed = message.embeds[0]
                    if cur_embed.url not in ids["sticky"]:
                        # If the url is in the sticky, there's no reason to check if it's in the normal. 
                        if cur_embed.url not in ids["normal"]:
                            # If the url is neither in the sticky nor the normal, then it's removed.
                            logging.info(f"Found deleted announcement, removing from channel {ch}.")
                            await message.delete()
                except:
                    continue