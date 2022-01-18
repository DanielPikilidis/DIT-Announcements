import discord, json, logging, sys, os
from discord.ext import commands
from logging.handlers import TimedRotatingFileHandler
from announcements_dit import DitAnnouncements
from guild_data import GuildData

intents = discord.Intents.default()
intents.members = True

prefix = "//"

bot = commands.Bot(command_prefix=prefix, help_command=None, intents=intents)

if not os.path.exists("logs"):
    os.mkdir("logs")

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

# Sometimes the bot just logs off and then back on causing the on_ready to run again.
class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.started = False
        
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.started:
            bot.data = GuildData(bot, logging)
            result = await bot.data.check_guilds()
            if result:
                logging.info("Guild check completed.")
            else:
                with open("guilds.json", "w") as file:
                    json.dump({}, file, indent=4)
                
                logging.critical("Recreating guilds.json. If the bot is in any guild, restart the bot.")

            bot.add_cog(DitAnnouncements(bot, logging))
            self.started = True
            logging.info("Bot logged in and ready")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="//help"))

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        channel = await guild.create_text_channel("announcements")
        await channel.send("You can move this channel to any category you want. If you delete it, you will have to"
                        "reconfigure the bot with //config.\n"
                        "By default everyone can config the bot. You should probably change that.\n"
                        "The server owner can always control the bot. Even if he's not in a control role.\n"
                        "If the control list is empty, everyone can control the bot, so you have to keep at least"
                        "one role in it")

        ret = bot.data.add_guild(str(guild.id), str(channel.id))
        if ret:
            logging.info(f"Guild {guild.id}: Added to json file.")
        else:
            logging.warning(f"Guild {guild.id}: Failed to add to json file")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        ret = bot.data.remove_guild(str(guild.id))
        if ret:
            logging.info(f"Guild {guild.id}: Removed from json file.")
        else:
            logging.warning(f"Guild {guild.id}: Failed to remove from json file.")
    
    ################# BOT COMMANDS #################

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(title="Help",
                        url="https://github.com/DanielPikilidis/DIT-Announcements",
                        description="All the commands the bot supports are listed here.",
                        color=discord.Color.blue()
                    )

        embed.add_field(name="//config",
                        value="Configure the bot.", inline=False)

        await ctx.send(embed=embed)

    @commands.group(name="config", invoke_without_command=True)
    async def config(self, ctx: commands.Context):
        if not bot.data.has_permission(ctx):
            await ctx.send("You don't have permission to configure the bot.")
            return

        embed = discord.Embed(title="Config Help",
                        url="https://github.com/DanielPikilidis/DIT-Announcements",
                        description="All subcommands for //config.",
                        color=discord.Color.blue()
                    )
        embed.add_field(name="//config announcements <#channel_name>.",
                        value="Change to which channel the bot sends the new announcements.", inline=False)
        embed.add_field(name="//config permissions add/remove <@role_name>.", 
                        value="Add / Remove roles that will be allowed to configure the bot."
                                "You have to tag the role to add it.", inline=False)
        embed.add_field(name="//config permissions list.",
                        value="Get a list with all the roles that are allowed to configure the bot.", inline=False)

        await ctx.send(embed=embed)

    @config.command(name="announcements")
    async def announcements(self, ctx: commands.Context, arg1):
        if not bot.data.has_permission(ctx):
            await ctx.send("You don't have permissions to configure the bot.")
            return 

        try:
            int(arg1[2:-1])
        except:
            await ctx.send("Invalid channel.")
            return

        channel = bot.get_channel(int(arg1[2:-1]))
        if channel is None:
            await ctx.send("Invalid channel.")
            return

        result = bot.data.set_announcements_channel(str(ctx.guild.id), str(channel.id))
        if result:
            logging.info(f"Guild {ctx.guild.id}: Changed announcements channel.")
            await ctx.send("Channel for announcements changed.")
        else:
            logging.warning(f"Guild {ctx.guild.id}: Failed to change announcements channel.")
            await ctx.send("Failed to change announcements channel.")

    @config.group(name="permissions", invoke_without_command=True)
    async def permissions(self, ctx: commands.Context):
        embed = discord.Embed(title="Permissions Help",
                            url="https://github.com/DanielPikilidis/DIT-Announcements",
                            description="All subcommans for //config permissions",
                            color=discord.Color.blue()
                        )

        embed.add_field(name="add <@role>.", 
                        value="Adds the role to the control list.", inline=False)
        embed.add_field(name="remove <@role>.",
                        value="Removes the role from the control list.", inline=False)
        
        await ctx.send(embed=embed)

    @permissions.command(name="add")
    async def add_control(self, ctx: commands.Context, arg1):
        if not bot.data.has_permission(ctx):
            await ctx.send("You don't have permissions to configure the bot.")
            return

        try:
            int(arg1[3:-1])
        except:
            await ctx.send("Invalid role.")
            return

        role = ctx.guild.get_role(int(arg1[3:-1]))
        if role is None:
            await ctx.send("Invalid role.")
            return

        result = bot.data.add_control(str(ctx.guild.id), str(role.id))
        if result:
            logging.info(f"Guild {ctx.guild.id}: Added role {role.id} to control list.")
            await ctx.send(f"Successfully added role {role.id} to the control list.")
        else:
            logging.info(f"Guild {ctx.guild.id}: Role {role.id} already in control list.")
            await ctx.send(f"That role {role} is already in the control list.")

    @permissions.command(name="remove")
    async def remove_control(self, ctx: commands.Context, arg1):
        if not bot.data.has_permission(ctx):
            await ctx.send("You don't have permissions to configure the bot.")
            return

        try:
            int(arg1[3:-1])
        except:
            await ctx.send("Invalid role.")
            return

        role = ctx.guild.get_role(int(arg1[3:-1]))
        if role is None:
            await ctx.send("Invalid role.")
            return

        result = bot.data.remove_control(str(ctx.guild.id), str(role.id))
        if result:
            logging.info(f"Guild {ctx.guild.id}: Removed Role {role.id} from control list.")
            control_list = bot.data.get_control_list(str(ctx.guild.id))
            if len(control_list):
                await ctx.send(f"Successfully removed role {role} from the control list.")
            else:
                await ctx.send(f"Successfully removed role {role} from the control list.\n"
                                "There are no more roles left in the control list. Now everyone "
                                "can control the bot!")
        else:
            logging.warning(f"Guild {ctx.guild.id}: Failed to remove Role {role.id} from control list.")
            await ctx.send("That role isn't in the control list.")

    @permissions.command(name="list")
    async def list_control(self, ctx: commands.Context):
        control_list = bot.data.get_control_list(str(ctx.guild.id))
        if not len(control_list):
            await ctx.send("Everyone is allowed to control the bot.")
            return

        s = ""
        for i in control_list:
            s += ctx.guild.get_role(int(i)).name
            s += ", " 

        s = s[:-2]
        await ctx.send(s)

    ################# ERROR HANDLING #################

    @announcements.error
    async def announcements_error(ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing channel parameter.")

    @add_control.error
    async def add_control_error(ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing role parameter.")

    @remove_control.error
    async def remove_control_error(ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Missing role parameter.")


if __name__ == "__main__":
    bot.add_cog(Main(bot))

    # Checking if the required files are created
    if not os.path.exists("guilds.json"):
        with open("guilds.json", "a+") as f:
            json.dump({}, f, indent=4)

    if os.path.exists("config.txt"):
        with open("config.txt", "r") as f:
            bot_key = f.read()
        bot.run(bot_key)
    else:
        open("config.txt", "w").close()
        print("Paste the api key in the config.txt (nothing else in there) and restart the bot.")
        