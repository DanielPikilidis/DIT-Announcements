import os

os.system("pip3 install bs4")
os.system("pip3 install asyncio")
os.system("pip3 install discord")
os.system("pip3 install json")
os.system("pip3 install datetime")

os.system("touch config.txt")

import json

with open("guilds.json", "a+") as f:
    a = {"announcements": {}}
    json.dump(a, f, indent=4)
