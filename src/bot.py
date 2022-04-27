import discord, json, logging
from discord.ext import commands
from logging.handlers import TimedRotatingFileHandler
from os import mkdir
from os.path import exists
from sys import stdout
from announcements_dit import DitAnnouncements
from guild_data import GuildData

intents = discord.Intents.default()
intents.members = True

class Main(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.started = False
        
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.started:
            bot.data = GuildData(bot)
            result = await bot.data.check_guilds()
            if result:
                bot.logger.info("Guild check completed.")
            else:
                with open("data/guilds.json", "w") as file:
                    json.dump({}, file, indent=4)
                
                bot.logger.critical("Recreating guilds.json. If the bot is in any guild, restart the bot.")

            bot.add_cog(DitAnnouncements(bot))
            self.started = True
            bot.logger.info("Bot logged in and ready")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="//help"))

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        channel = await guild.create_text_channel("announcements")
        await channel.send("You can move this channel to any category you want. If you delete it, you will have to"
                        "reconfigure the bot with //config.\n"
                        "By default everyone can config the bot. You should probably change that.\n"
                        "The server owner can always control the bot. Even if he's not in a control role.\n"
                        "If the control list is empty, everyone can control the bot, so you have to keep at least"
                        "one role in it")

        ret = bot.data.add_guild(str(guild.id), str(channel.id))
        if ret:
            bot.logger.info(f"Guild {guild.id}: Added to json file.")
        else:
            bot.logger.warning(f"Guild {guild.id}: Failed to add to json file")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        ret = bot.data.remove_guild(str(guild.id))
        if ret:
            bot.logger.info(f"Guild {guild.id}: Removed from json file.")
        else:
            bot.logger.warning(f"Guild {guild.id}: Failed to remove from json file.")
    
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
        embed.add_field(name="//config permissions/", 
                        value="View permissions settings for the bot."
                                "You have to tag the role to add it.", inline=False)

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
            bot.logger.info(f"Guild {ctx.guild.id}: Changed announcements channel.")
            await ctx.send("Channel for announcements changed.")
        else:
            bot.logger.warning(f"Guild {ctx.guild.id}: Failed to change announcements channel.")
            await ctx.send("Failed to change announcements channel.")

    @config.group(name="permissions", invoke_without_command=True)
    async def permissions(self, ctx: commands.Context):
        embed = discord.Embed(title="Permissions Help",
                            url="https://github.com/DanielPikilidis/DIT-Announcements",
                            description="All subcommans for //config permissions",
                            color=discord.Color.blue()
                        )

        embed.add_field(name="//config permissions add <@role>.", 
                        value="Adds the role to the control list.", inline=False)
        embed.add_field(name="//config permissions remove <@role>.",
                        value="Removes the role from the control list.", inline=False)
        embed.add_field(name="//config permissions list.",
                        value="Lists roles that are allowd to change bot settings.", inline=False)
        
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
            bot.logger.info(f"Guild {ctx.guild.id}: Added role {role.id} to control list.")
            await ctx.send(f"Successfully added role {role.id} to the control list.")
        else:
            bot.logger.info(f"Guild {ctx.guild.id}: Role {role.id} already in control list.")
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
            bot.logger.info(f"Guild {ctx.guild.id}: Removed Role {role.id} from control list.")
            control_list = bot.data.get_control_list(str(ctx.guild.id))
            if len(control_list):
                await ctx.send(f"Successfully removed role {role} from the control list.")
            else:
                await ctx.send(f"Successfully removed role {role} from the control list.\n"
                                "There are no more roles left in the control list. Now everyone "
                                "can control the bot!")
        else:
            bot.logger.warning(f"Guild {ctx.guild.id}: Failed to remove Role {role.id} from control list.")
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


def setup_logger() -> logging.Logger:
    discord_logger = logging.getLogger('discord')
    handler = logging.FileHandler(filename="logs/discord.log", encoding="utf-8", mode='w')
    handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
    discord_logger.addHandler(handler)

    logger = logging.getLogger("output")
    logname = "logs/output.log"
    logger.level = logging.INFO
    handler = TimedRotatingFileHandler(logname, when="midnight", interval=1, backupCount=1)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    handler.suffix = "%Y%m%d"

    logger.addHandler(handler)
    logger.addHandler(logging.StreamHandler(stdout))
    
    return logger

if __name__ == "__main__":
    prefix = "//"
    bot = commands.Bot(command_prefix=prefix, help_command=None, intents=intents)

    bot.logger = setup_logger()

    bot.add_cog(Main(bot))

    if not exists("logs"):
        mkdir("logs")

    if not exists("data"):
        mkdir("data")

    if not exists("data/data.json"):
        with open("data/data.json", "a+") as file:
            json.dump({"last_update": 0, "guilds": {}}, file, indent=4)

    if exists("data/config.json"):
        with open("data/config.json", "r") as file:
            bot_key = json.loads(file.read())['discord-key']
        bot.run(bot_key)
    else:
        with open("data/config.json", "a+") as file:
            json.dump({"discord-key": ""}, file, indent=4)
        print("Paste your key in config.json file in data/")
        