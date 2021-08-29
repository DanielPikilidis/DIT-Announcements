from urllib.request import urlopen

def get_an_list():
    url = "https://www.di.uoa.gr/announcements"
    page = urlopen(url)

    html_bytes = page.read()
    html = html_bytes.decode("utf-8")

    start = html.find("<tbody>")
    end = html.find("</tbody>") + 8

    table = ""
    for i in range(start,end):
        table += html[i]

    announcements = []
    start = table.find("<tr>")
    end = table.find("</tr>") + 5
    announcements.append(table[start:end])

    while end <= len(table):
        table = table[end:]
        start = table.find("<tr>")
        end = table.find("</tr>") + 5
        announcements.append(table[start:end])

    announcement_titles = []
    announcement_text = []

    for i in announcements:
        title_ind = i.find("href=") + 6
        title = "https://www.di.uoa.gr"
        while title_ind < len(i) and i[title_ind] != "\"":
            title += i[title_ind]
            title_ind += 1

        if title != "":
            announcement_titles.append(title)

        text_ind = title_ind + 16
        text = ""
        while text_ind < len(i) and i[text_ind] != "<":
            text += i[text_ind]
            text_ind += 1

        if text != "":
            announcement_text.append(text)

    announcements = []

    for i in range(len(announcement_text) - 1):
        cur = {"title": announcement_titles[i], "text": announcement_text[i]}
        announcements.append(cur)

    return announcements

def check_for_new(old_list):
    new_list = get_an_list()
    ret_list = new_list[:] # new_list will be modified in the next few lines, so I keep ret_list to return it.
    new_title = new_list[0]["title"]
    old_title = old_list[0]["title"]
    new_announcements = []
    while new_title != old_title:
        new_announcements.append(new_list.pop(0))
        new_title = new_list[0]["title"]
        old_title = old_list[0]["title"]

    if len(new_announcements):
        return ret_list, new_announcements
    else:
        return ret_list, None
