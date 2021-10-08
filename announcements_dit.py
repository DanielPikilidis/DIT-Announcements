from bs4 import BeautifulSoup as bs
import requests
import json

class Announcements:
    def __init__(self):
        self.url = "https://www.di.uoa.gr/announcements"
        try:
            with open("old_list.json", "r") as f:
                self.old_list = json.loads(f.read())
        except:
            self.old_list = self.get_an_list()

        """
        old_list format: 
        {
            "sticky": [
                
            ],
            "normal": [

            ]
        }
        """

        try:
            with open("already_sent.json", "r") as f:
                self.already_sent = json.loads(f.read())
        except:
            self.already_sent = []

    def get_an_list(self):
        # Not using the rss feed because it doesn't return the categories for each announcement.
        page = requests.get("https://www.di.uoa.gr/announcements")
        html = page.text

        soup = bs(html, features="html.parser")
        table = soup.findChildren("tbody")[0]   # Getting the table with the announcements

        announcements_raw = table.findChildren("tr")    # A list with all the announcements (everything from <tr> to </tr>)
        
        announcements = {"sticky": [], "normal": []}
        for i in announcements_raw:
            # There are 4 td fields in each announcements. The first is useless (for this bot).
            fields = i.findChildren("td")
            link_raw = fields[2]   # Has the link to the announcement page and title
            categories_raw = fields[3]    # Has the announcement categories.
            a = link_raw.findChildren('a')[0]
            link = "https://www.di.uoa.gr" + a["href"]
            title = a.contents[0]

            categories = []
            for i_tag in categories_raw.find_all('i'):
                temp = str(i_tag.next_sibling)
                temp = ' '.join(temp.split())   # Removing spaces and tabs
                categories.append(temp)

            current = {"link": link, "title": title, "tags": categories}

            # If there's an i tag in this field, then it's a sticky announcement.
            sticky = fields[1].find("i")
            if sticky != None:
                announcements["sticky"].append(current)
            else:
                announcements["normal"].append(current)

        return announcements

    def check_for_new(self):
        new_list = self.get_an_list()
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

            if not len(new_list):
                break
            new_link = new_list["normal"][0]["link"]

        self.old_list = temp
        with open("old_list.json", "w") as f:
            json.dump(self.old_list, f, indent=4)

        if len(new_announcements):
            with open("already_sent.json", "w") as f:
                json.dump(self.already_sent, f, indent=4)
            return new_announcements
        else:
            return None

    def get_all_announcements(self):
        old = []
        for i in self.old_list.values():
            for n in i:
                old.append(n["link"])
        return old
        