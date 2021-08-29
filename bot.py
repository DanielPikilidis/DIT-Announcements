import discord, json, asyncio, datetime
from discord.ext import commands
from announcements import *

f = open("config.txt", "r")
bot_key = f.read()  # There should be only 1 line in the file, the key.
f.close()

prefix = "./"

bot = commands.Bot(command_prefix=prefix, help_command=None)

data = None

################# BOT EVENTS #################

@bot.event
async def on_ready():
    global data
    print("Bot Ready")
    data = GuildData()
    bot.loop.create_task(get_announcements())

@bot.event
async def on_guild_join(guild):
    global data
    channel = await guild.create_text_channel("announcements")
    await channel.send("You can move this channel to any category you want. If you delete it, you will have to reconfigure the bot with ./configure")

    ret = data.add_guild(str(guild.id), str(channel.id))
    if ret:
        print(f"Guild ({guild.id}) added to json file.")
    else:
        print(f"Guild ({guild.id}) addition to json file failed.")

@bot.event
async def on_guild_remove(guild):
    global data
    ret = data.remove_guild(str(guild.id))
    if ret:
        print(f"Guild ({guild.id}) removed from json file.")
    else:
        print(f"Guild ({guild.id}) removal from json file failed.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)


################# BOT COMMANDS #################

@bot.command(pass_context=True)
async def configure(ctx, *, arg):
    global data
    arg = arg.split()
    ret = data.configure_announcements_channel(str(ctx.guild.id), str(arg[0][2:-1]))
    if ret:
        print(f"Changed announcements channel for guild ({ctx.guild.id})")
    else:
        print(f"Failed to configure announcements channel for guild ({ctx.guild.id})")

@bot.command(pass_contect=True)
async def help(ctx):
    embed = discord.Embed(title="Help",
                          url="https://github.com/DanielPikilidis",
                          description="All the commands the bot supports are listed here.",
                          color=discord.Color.blue()
                          )

    embed.add_field(name="./configure \{#channel_name\}",
                    value="Change announcements channel.", inline=False)

    await ctx.channel.send(embed=embed)


################# HELPER FUNCTIONS #################

class GuildData:
    def __init__(self):
        with open("guilds.json", "r+") as f:
            self.data = json.loads(f.read())

    def get_announcement_channels(self):
        arr = []
        for guild in self.data["announcements"]:
            arr.append(self.data["announcements"][guild])
        return arr

    def configure_announcements_channel(self, guild, channel):
        self.data["announcements"][guild] = channel

        with open("guilds.json", "w") as f:     
            json.dump(self.data, f, indent=4)
        return 1

    def add_guild(self, guild, channel):
        self.data["announcements"][guild] = channel
        
        with open("guilds.json", "w") as f:     
            json.dump(self.data, f, indent=4)
        return 1

    def remove_guild(self, guild):
        self.data["announcements"].pop(guild)

        with open("guilds.json", "w") as f:     
            json.dump(self.data, f, indent=4)
        return 1


################# ALWAYS RUNNING FUNCTIONS #################

async def get_announcements():
    old = get_an_list()
    while True:
        new, announcements = check_for_new(old)
        if announcements:
            print("Found new announcements, sending.")
            for i in announcements:
                link = i["link"]
                title = i["title"]
                date = datetime.datetime.now().strftime("%A, %d/%m/%Y, %H:%M")
                embed = discord.Embed(
                                      title="New Announcement!", 
                                      url=link,
                                      description=title,
                                      color=discord.Color.blue())
                embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/1255901921896009729/xKsBUtgN.jpg")
                embed.set_footer(text=date)
                channels = data.get_announcement_channels()
                for ch in channels:
                    current = bot.get_channel(ch)
                    await current.send(embed=embed)
            old = new
        await asyncio.sleep(30)

if __name__ == "__main__":
    bot.run(bot_key)