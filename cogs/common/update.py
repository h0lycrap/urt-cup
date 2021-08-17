import discord
import cogs.common.embeds as embeds

async def roster(bot):
    # Get channel
    roster_channel = discord.utils.get(bot.guilds[0].channels, id=bot.channel_roster_id) 

    # Delete index message if any
    roster_channel_messages = await roster_channel.history(limit=5).flatten()
    index_message = None
    for message in roster_channel_messages:
        if not message.embeds:
            continue
        if message.embeds[0].title.startswith(":pencil: Clan index"):
            index_message = message

    bot.cursor.execute("SELECT * FROM Teams;")
    for team in bot.cursor.fetchall():  

        # Generate the embed
        embed, insuficient_roster = embeds.team(bot, tag=team['tag'])

        if insuficient_roster:
            # Remove message from roster if there was one
            try:
                roster_message = await roster_channel.fetch_message(team['roster_message_id'])
                await roster_message.delete()
            except:
                pass
            continue

        # Check if there is a message id stored
        try:
            roster_message = await roster_channel.fetch_message(team['roster_message_id'])
            await roster_message.edit(embed=embed)
        except:
            # Delete index message
            if index_message:
                await index_message.delete()
                index_message = None

            # Send new message and store message id
            new_roster_msg = await roster_channel.send(embed=embed)
            bot.cursor.execute("UPDATE Teams SET roster_message_id=%s WHERE tag=%s", (str(new_roster_msg.id), team['tag']))
            bot.conn.commit()

    # Post or edit team index
    index_embed = await embeds.team_index(bot)
    if index_message:
        await index_message.edit(embed=index_embed)
    else:
        await roster_channel.send(embed=index_embed)


async def signups(bot):
    # Get channel (TODO:REFACTOR to account for new channels for different cups)
    signup_channel = discord.utils.get(bot.guilds[0].channels, id=836895695269134386)

    # Get all cups
    bot.cursor.execute("SELECT id, signup_message_id FROM Cups;")
    for cup_info in bot.cursor.fetchall():

        # Generate the embed
        embed = embeds.signup(bot, cup_info['id'])

        # Check if there is a message id stored
        try:
            signup_message = await signup_channel.fetch_message(cup_info['signup_message_id'])
            await signup_message.edit(embed=embed)

        except:
            # Send new message and store message id
            new_signup_msg = await signup_channel.send(embed=embed)
            bot.cursor.execute("UPDATE Cups SET signup_message_id=%s WHERE id=%s", (str(new_signup_msg.id), cup_info['id']))
            bot.conn.commit()