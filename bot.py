import discord, json, asyncio, datetime, logging, sys, time
from discord.ext import commands
from logging.handlers import TimedRotatingFileHandler
from announcements_dit import *

f = open("config.txt", "r")
bot_key = f.read()  # There should be only 1 line in the file, the key.
f.close()

intents = discord.Intents.default()
intents.members = True

prefix = "//"

bot = commands.Bot(command_prefix=prefix, help_command=None, intents=intents)

data = None

# Silence discord's logging messages. (Only critical should appear, but I haven't seen any yet)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)
handler = logging.FileHandler(filename="logs/discord.log", encoding="utf-8", mode='w')
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
discord_logger.addHandler(handler)

logname = "logs/output.log"
handler = TimedRotatingFileHandler(logname, when="midnight", interval=1, backupCount=1)
handler.suffix = "%Y%m%d"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        handler,
        logging.StreamHandler(sys.stdout)
    ]
)

################# BOT EVENTS #################

@bot.event
async def on_ready():
    global data
    data = GuildData()
    ret = await check_guilds()
    if ret:
        logging.info("Guild check successful.")
    else:
        with open("guilds.json", "a+") as f:
            json.dump({}, f, indent=4)

        logging.critical("Recreating guilds.json. If the bot is in any guild, restart the bot.")

    bot.loop.create_task(get_announcements())
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="//help"))
    logging.info("Bot logged in and ready")

@bot.event
async def on_guild_join(guild):
    global data
    channel = await guild.create_text_channel("announcements")
    await channel.send("You can move this channel to any category you want. If you delete it, you will have to"
                       "reconfigure the bot with //config.\n"
                       "By default everyone can config the bot. You should probably change that.\n"
                       "The server owner can always control the bot. Even if he's not in a control role.\n"
                       "If the control list is empty, everyone can control the bot, so you have to keep at least"
                       "one role in it")

    ret = data.add_guild(str(guild.id), str(channel.id))
    if ret:
        logging.info(f"Guild {guild.id}: Added to json file.")
    else:
        logging.warning(f"Guild {guild.id}: Failed to add to json file")

@bot.event
async def on_guild_remove(guild):
    global data
    ret = data.remove_guild(str(guild.id))
    if ret:
        logging.info(f"Guild {guild.id}: Removed from json file.")
    else:
        logging.warning(f"Guild {guild.id}: Failed to remove from json file.")

@bot.event
async def on_message(message):
    await bot.process_commands(message)


################# BOT COMMANDS #################

@bot.command()
async def config(ctx: commands.Context, *, arg="default"):
    global data

    if arg == "default":
        await ctx.send("Missing arguments, type //config help to see available commands.")
        return

    if ctx.author != ctx.guild.owner:
        author_roles = ctx.author.roles
        control_list = data.get_control_list(str(ctx.guild.id))

        if not len(control_list):
            has_permissions = True
        else:
            has_permissions = False
            for i in author_roles:
                cur = str(i.id)
                
                if cur in control_list:
                    has_permissions = True
                    break
            
        if not has_permissions:
            await ctx.send("You don't have permission to configure the bot.")
            return

    arg = arg.split()
    if arg[0].upper() == "HELP":
        embed = discord.Embed(title="Config Help",
                              url="https://github.com/DanielPikilidis/DIT-Announcements",
                              description="All options for //config.",
                              color=discord.Color.red()
                             )
        embed.add_field(name="//config announcements #channel_name.",
                        value="Change to which channel the bot sends the new announcements.", inline=False)
        embed.add_field(name="//config permissions add/remove @role_name.", 
                        value="Add / Remove roles that will be allowed to configure the bot."
                              "You have to tag the role to add it.", inline=False)
        embed.add_field(name="//config control_list.",
                        value="Get a list with all the roles that are allowed to configure the bot.", inline=False)

        await ctx.send(embed=embed)
    elif arg[0].upper() == "ANNOUNCEMENTS":
        if len(arg) < 2:
            await ctx.send("Invalid Arguments.")
            return

        channel = str(arg[1][2:-1])
        guild_channels = ctx.guild.text_channels
        try:
            channel = bot.get_channel(int(channel))
        except:
            await ctx.send("Invalid channel.")
            return

        valid_channel = False
        for i in guild_channels:
            if channel.id == i.id:
                valid_channel = True
                break
        
        if not valid_channel:
            await ctx.send("Invalid channel.")
            return

        ret = data.configure_announcements_channel(str(ctx.guild.id), str(channel.id))
        if ret:
            logging.info(f"Guild {ctx.guild.id}: Changed announcements channel")
            await ctx.send("Channel for announcements changed.")
        else:
            logging.warning(f"Guild {ctx.guild.id}: Failed to change announcements channel.")
    elif arg[0].upper() == "PERMISSIONS":
        if len(arg) < 3:
            await ctx.send("Invalid Arguments.")
            return
        
        if arg[1].upper() != "ADD" and arg[1].upper() != "REMOVE":
            await ctx.send("Unknown argument for //config permissions. See //config help")
            return

        try:
            role = ctx.guild.get_role(int(arg[2][3:-1]))
        except:
            await ctx.send("That role doesn't exist.")
            return
        if arg[1].upper() == "ADD":
            ret = data.add_control(str(ctx.guild.id), role)
            if ret:
                logging.info(f"Guild {ctx.guild.id}: Added Role {role.id} to control list.")
                await ctx.send(f"Successfully added role {role} to the control list.")
            else:
                logging.info(f"Guild {ctx.guild.id}: Role {role.id} already in control list.")
                await ctx.send(f"That role {role} is already in the control list.")
        elif arg[1].upper() == "REMOVE":
            ret = data.remove_control(str(ctx.guild.id), role)
            control_list = data.get_control_list(str(ctx.guild.id))
            if ret:
                logging.info(f"Guild {ctx.guild.id}: Removed Role {role.id} from control list.")
                if len(control_list):
                    await ctx.send(f"Successfully removed role {role} from the control list.")
                else:
                    await ctx.send(f"Successfully removed role {role} from the control list.\n"
                                            "There are no more roles left in the control list. Now everyone "
                                            "can control the bot!")
            else:
                logging.warning(f"Guild {ctx.guild.id}: Failed to remove Role {role.id} from control list.")
                await ctx.send("That role isn't in the control list.")
    elif arg[0].upper() == "CONTROL_LIST":
        control_list = data.get_control_list(str(ctx.guild.id))
        for i in range(len(control_list)):
            control_list[i] = ctx.guild.get_role(int(control_list[i]))
            
        if not len(control_list):
            await ctx.send("Everyone is allowed to control the bot.")
            return
        s = control_list[0].name        
        for i in control_list[1:]:
            s += ", "
            s += i.name
        await ctx.send(s)
    else:
        await ctx.send("Unknown parameter for config. See //config help")

@bot.command()
async def help(ctx: commands.Context):
    embed = discord.Embed(title="Help",
                          url="https://github.com/DanielPikilidis/DIT-Announcements",
                          description="All the commands the bot supports are listed here.",
                          color=discord.Color.blue()
                          )

    embed.add_field(name="//config help",
                    value="Configure the bot.", inline=False)

    await ctx.send(embed=embed)


################# HELPER FUNCTIONS #################

class GuildData:
    def __init__(self):
        try:
            with open("guilds.json", "r") as f:
                self.data = json.loads(f.read())
                self.backup = self.data.copy()
        except IOError:
            return None

    def get_announcement_channels(self):
        arr = list(self.data.values())
        for i in range(len(arr)):
            arr[i] = arr[i]["announcements"]

        return arr

    def configure_announcements_channel(self, guild, channel):
        self.data[guild]["announcements"] = channel
        return self.write_to_json()

    def add_control(self, guild, role):
        try:
            self.data[guild]["control"].remove(str(role.id))
            self.data[guild]["control"].append(str(role.id))
            return 0
        except:
            pass

        self.data[guild]["control"].append(str(role.id))
        return self.write_to_json()

    def remove_control(self, guild, role):
        try:
            self.data[guild]["control"].remove(str(role.id))
        except:
            return 0
        return self.write_to_json()

    def get_control_list(self, guild):
        arr = []
        for i in self.data[guild]["control"]:
            arr.append(i)
        return arr

    def add_guild(self, guild, channel):
        self.data[guild] = {"announcements": channel, "control": []}
        return self.write_to_json()

    def remove_guild(self, guild):
        self.data.pop(guild)
        return self.write_to_json()

    def write_to_json(self):
        try:
            with open("guilds.json", "w") as f:     
                json.dump(self.data, f, indent=4)
            self.backup = self.data.copy()
            return 1
        except:
            logging.error("Failed to make changes to json file. Reverting to old.")
            self.data = self.backup.copy()
            with open("guilds.json", "w") as f:     
                json.dump(self.data, f, indent=4)
            return 0


async def check_guilds():
    if not data:
        return 0

    joined = bot.guilds
    try:
        with open("guilds.json", "r") as f:
            cur_data = json.loads(f.read())
    except IOError:
        logging.critical("guilds.json doesn't exist.")
        return 0

    stored = list(cur_data.keys())

    for i in range(len(joined)):
        joined[i] = str(joined[i].id)

    joined.sort()
    stored.sort()

    if joined == stored:
        return 1

    for i in joined:
        if i not in stored:
            guild = bot.get_guild(int(i))
            channel = await guild.create_text_channel("announcements")
            await channel.send("You can move this channel to any category you want. If you delete it, you will have to reconfigure the bot with //config")
            ret = data.add_guild(str(guild.id), str(channel.id))
            if ret:
                logging.info(f"Guild {guild.id}: Added to json file.")
            else:
                logging.warning(f"Guild {guild.id}: Failed to add to json file.")

    with open("guilds.json", "r") as f:
        cur_data = json.loads(f.read())
    
    stored = list(cur_data.keys())

    if joined == stored:
        return 1

    for i in stored:
        if i not in joined:
            ret = data.remove_guild(str(i))
            if ret:
                logging.info(f"Guild {i}: Added to json file.")
            else:
                logging.warning(f"Guild {i}: Failed to add to json file.")


################# ALWAYS RUNNING FUNCTIONS #################

async def get_announcements():
    ann = Announcements()
    cat_colors = {"Γενικά": "⚪ ", "Προπτυχιακά": "🔴 ", "Μεταπτυχιακά": "🔵 ", "Διδακτορικά": "🟣 ",
                  "CIVIS": "⚫ ", "Πρακτική Άσκηση": "🟠 ", "Νέες θέσεις εργασίας": "🟢 "}
    while True:
        announcements = ann.check_for_new()
        # announcements also has tags for every new announcement. I haven't used them anywhere yet.
        if announcements:
            date = datetime.datetime.now().strftime("%A, %d/%m/%Y, %H:%M")
            logging.info("Found new announcements, sending.")
            start = time.time()
            channels = data.get_announcement_channels()
            for i in announcements:
                link = i["link"]
                title = i["title"]
                categories = ""
                length = len(i["tags"]) - 1
                for tag in i["tags"]:                    
                    if i["tags"].index(tag) != length:
                        tag = tag[:-1]

                    try:
                        color = cat_colors[tag]
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
                    current = bot.get_channel(int(ch))
                    await current.send(embed=embed)
            end = time.time()
            total = end - start
            total_formatted = str(datetime.timedelta(seconds=int(total)))
            logging.info(f"Successfully sent new announcements to all servers. Total time: {total_formatted}")
        await asyncio.sleep(15)

if __name__ == "__main__":
    bot.run(bot_key)
