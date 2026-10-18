import discord
from discord.ext import commands
import data_store

class GuildData:
    """ Owns the "guilds" key of data.json. Every read goes to the file, so it never works on a stale copy. """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @property
    def data(self) -> dict:
        return data_store.read()

    def get_announcement_channels(self):
        arr = list(self.data["guilds"].values())
        for i in range(len(arr)):
            arr[i] = arr[i]["announcements"]

        return arr

    def set_announcements_channel(self, guild, channel):
        def change(data):
            # A guild where the bot couldn't create its channel isn't stored yet
            data["guilds"].setdefault(guild, {"announcements": channel, "control": []})
            data["guilds"][guild]["announcements"] = channel
        return self.write_to_json(change)

    def add_control(self, guild, role):
        if role in self.get_control_list(guild):
            return 0

        def change(data):
            if role not in data["guilds"][guild]["control"]:
                data["guilds"][guild]["control"].append(role)
        return self.write_to_json(change)

    def remove_control(self, guild, role):
        if role not in self.get_control_list(guild):
            return 0

        def change(data):
            if role in data["guilds"][guild]["control"]:
                data["guilds"][guild]["control"].remove(role)
        return self.write_to_json(change)

    def get_control_list(self, guild):
        return self.data["guilds"].get(guild, {}).get("control", [])

    def has_permission(self, ctx: commands.Context):
        if ctx.author.id == ctx.guild.owner_id:     # ctx.guild.owner is None when the owner isn't cached
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
        def change(data):
            data["guilds"][guild] = {"announcements": channel, "control": []}
        return self.write_to_json(change)

    def remove_guild(self, guild):
        def change(data):
            data["guilds"].pop(guild, None)
        return self.write_to_json(change)

    def write_to_json(self, change):
        """ Applies change to the current data.json. The write is atomic, so on failure the file is unchanged. """
        try:
            data_store.update(change)
            return 1
        except:
            self.bot.logger.error("Failed to make changes to json file. Kept the old one.", exc_info=True)
            return 0

    async def check_guilds(self):
        if not self.bot.data:
            return 0

        # bot.guilds is a read-only view in discord.py, so build a new list
        joined = sorted(str(guild.id) for guild in self.bot.guilds)
        try:
            cur_data = data_store.read()
        except IOError:
            self.bot.logger.critical("data/data.json doesn't exist.")
            return 0

        stored = sorted(cur_data["guilds"].keys())

        if joined == stored:
            return 1

        for i in joined:
            if i not in stored:
                guild = self.bot.get_guild(int(i))
                try:
                    channel = await guild.create_text_channel("announcements")
                except discord.Forbidden:
                    self.bot.logger.warning(f"Guild {guild.id}: Missing the Manage Channels permission, couldn't create "
                                            "the announcements channel. Set one with //config announcements <#channel>.")
                    continue
                await channel.send("You can move this channel to any category you want. If you delete it, you will have to reconfigure the bot with //config")
                ret = self.bot.data.add_guild(str(guild.id), str(channel.id))
                if ret:
                    self.bot.logger.info(f"Guild {guild.id}: Added to json file.")
                else:
                    self.bot.logger.warning(f"Guild {guild.id}: Failed to add to json file.")

        cur_data = data_store.read()

        stored = sorted(cur_data["guilds"].keys())

        if joined == stored:
            return 1

        for i in stored:
            if i not in joined:
                ret = self.bot.data.remove_guild(str(i))
                if ret:
                    self.bot.logger.info(f"Guild {i}: Removed from json file.")
                else:
                    self.bot.logger.warning(f"Guild {i}: Failed to remove from json file.")

        return 1
