from bs4 import BeautifulSoup as bs
from urllib.request import urlopen

def get_an_list():
    url = "https://www.di.uoa.gr/announcements"
    page = urlopen(url)

    html_bytes = page.read()
    html = html_bytes.decode("utf-8")

    soup = bs(html, features="html.parser")
    table = soup.findChildren("tbody")[0]   # Getting the table with the announcements

    announcements_raw = table.findChildren("tr")    # A list with all the announcements (everything from <tr> to </tr>)

    announcements = []

    for i in announcements_raw:
        # There are 4 td fields in each announcements The first 2 are useless (for this bot).
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

        current = {"link": link, "title": title, "categories": categories}
        announcements.append(current)

    return announcements

def check_for_new(old_list):
    new_list = get_an_list()
    ret_list = new_list[:]
    new_link = new_list[0]["link"]
    old_link = old_list[0]["link"]
    new_announcements = []
    while new_link != old_link:
        new_announcements.append(new_list.pop(0))
        new_link = new_list[0]["link"]
        old_link = old_list[0]["link"]

    if len(new_announcements):
        return ret_list, new_announcements
    else:
        return ret_list, None