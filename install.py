import os

os.system("pip3 install bs4")
os.system("pip3 install asyncio")
os.system("pip3 install discord")
os.system("pip3 install json")
os.system("pip3 install datetime")
os.system("pip3 install sys")
os.system("pip3 install logging")
os.system("pip3 install time")

os.system("touch config.txt")
os.system("mkdir logs")

import json

with open("guilds.json", "a+") as f:
    json.dump({}, f, indent=4)
