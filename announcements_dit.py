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

    def get_an_list(self):
        # Not using the rss feed because it doesn't return the categories for each announcement.
        page = requests.get(self.url)
        html = page.text

        soup = bs(html, features="html.parser")
        table = soup.findChildren("tbody")[0]   # Getting the table with the announcements

        announcements_raw = table.findChildren("tr")    # A list with all the announcements (everything from <tr> to </tr>)
        
        announcements = []
        for i in announcements_raw:
            # There are 4 td fields in each announcements. The first 2 are useless (for this bot).
            # We only need the 3rd and 4th.
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
            announcements.append(current)

        return announcements

    def check_for_new(self):
        new_list = self.get_an_list()
        temp = new_list[:]
        new_link = new_list[0]["link"]
        old_link = self.old_list[0]["link"]
        new_announcements = []
        while new_link != old_link:
            new_announcements.append(new_list.pop(0))
            if not len(new_list):
                break
            new_link = new_list[0]["link"]

        self.old_list = temp
        with open("old_list.json", "w") as f:
            json.dump(self.old_list, f, indent=4)

        if len(new_announcements):
            return new_announcements
        else:
            return None

    def get_old_ids(self):
        return [i["link"] for i in self.old_list]
        