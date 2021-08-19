from discord.ext import commands

def in_dm():
    def predicate(ctx):
        return ctx.guild == None
    return commands.check(predicate)

def is_guild_manager():
    def predicate(ctx):
        return ctx.author.guild_permissions.manage_guild
    return commands.check(predicate)

'''
def not_busy(bot):
    def predicate():
        return ctx.guild == None
    return commands.check(predicate)
'''