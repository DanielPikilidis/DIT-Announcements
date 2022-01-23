from discord.ext import commands
from json import loads, dump

class GuildData:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        try:
            with open("data/guilds.json", "r") as file:
                self.data = loads(file.read())
                self.backup = self.data.copy()
        except IOError:
            return None

    def get_announcement_channels(self):
        arr = list(self.data.values())
        for i in range(len(arr)):
            arr[i] = arr[i]["announcements"]

        return arr

    def set_announcements_channel(self, guild, channel):
        self.data[guild]["announcements"] = channel
        return self.write_to_json()

    def add_control(self, guild, role):
        try:
            self.data[guild]["control"].remove(role)
            self.data[guild]["control"].append(role)
            return 0
        except:
            pass

        self.data[guild]["control"].append(role)
        return self.write_to_json()

    def remove_control(self, guild, role):
        try:
            self.data[guild]["control"].remove(role)
        except:
            return 0
        return self.write_to_json()

    def get_control_list(self, guild):
        return self.data[guild]["control"]

    def has_permission(self, ctx: commands.Context):
        if ctx.author == ctx.guild.owner:
            return True
        else:
            author_roles = ctx.author.roles
            control_list = self.get_control_list(str(ctx.guild.id))
            if not len(control_list):
                return True
            else:
                for i in author_roles:
                    role_id = str(i.id)
                    if role_id in control_list:
                        return True

    def add_guild(self, guild, channel):
        self.data[guild] = {"announcements": channel, "control": []}
        return self.write_to_json()

    def remove_guild(self, guild):
        self.data.pop(guild)
        return self.write_to_json()

    def write_to_json(self):
        try:
            with open("data/guilds.json", "w") as f:     
                dump(self.data, f, indent=4)
            self.backup = self.data.copy()
            return 1
        except:
            self.bot.logger.error("Failed to make changes to json file. Reverting to old.")
            self.data = self.backup.copy()
            with open("data/guilds.json", "w") as f:     
                dump(self.data, f, indent=4)
            return 0

    async def check_guilds(self):
        if not self.bot.data:
            return 0

        joined = self.bot.guilds
        try:
            with open("data/guilds.json", "r") as f:
                cur_data = loads(f.read())
        except IOError:
            self.bot.logger.critical("data/guilds.json doesn't exist.")
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
                guild = self.bot.get_guild(int(i))
                channel = await guild.create_text_channel("announcements")
                await channel.send("You can move this channel to any category you want. If you delete it, you will have to reconfigure the bot with //config")
                ret = self.bot.data.add_guild(str(guild.id), str(channel.id))
                if ret:
                    self.bot.logger.info(f"Guild {guild.id}: Added to json file.")
                else:
                    self.bot.logger.warning(f"Guild {guild.id}: Failed to add to json file.")

        with open("data/guilds.json", "r") as f:
            cur_data = loads(f.read())
        
        stored = list(cur_data.keys())

        if joined == stored:
            return 1

        for i in stored:
            if i not in joined:
                ret = self.bot.data.remove_guild(str(i))
                if ret:
                    self.bot.logger.info(f"Guild {i}: Added to json file.")
                else:
                    self.bot.logger.warning(f"Guild {i}: Failed to add to json file.")
