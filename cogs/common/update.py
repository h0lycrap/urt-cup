import discord
import cogs.common.embeds as embeds
from datetime import datetime, timedelta


# Temporary while discord.py 2.0 isnt out
from discord_components import DiscordComponents, Button, ButtonStyle, InteractionType, Select, SelectOption, component, interaction

async def roster(bot):
    await update_roster(bot, 0)
    await update_roster(bot, 1)

async def update_roster(bot, admin_managed):
    # Get channel
    channel_id  = bot.channel_roster_id
    if admin_managed == 1:
        channel_id  = bot.channel_roster_national_teams_id
    roster_channel = discord.utils.get(bot.guilds[0].channels, id=channel_id) 

    # Delete index message if any
    roster_channel_messages = await roster_channel.history(limit=5).flatten()
    index_message = None
    for message in roster_channel_messages:
        if not message.embeds:
            continue
        if message.embeds[0].title.startswith(":pencil: Clan index"):
            index_message = message

    for team in bot.db.get_all_clans(admin_managed): 
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
            bot.db.edit_clan(tag=team['tag'], roster_message_id=str(new_roster_msg.id))

    # Post or edit team index
    index_embed = await embeds.team_index(bot, admin_managed)
    if index_message:
        await index_message.edit(embed=index_embed)
    else:
        await roster_channel.send(embed=index_embed)


async def signups(bot):

    # Get all cups
    for cup_info in bot.db.get_all_cups(1):
        # Get signups channel
        signup_channel = discord.utils.get(bot.guilds[0].channels, id=int(cup_info['chan_signups_id']))
        stage_channel = discord.utils.get(bot.guilds[0].channels, id=int(cup_info['chan_stage_id']))

        # Generate the embed
        embed = await embeds.signup(bot, cup_info['id'])

        signup_start_date = datetime.strptime(cup_info['signup_start_date'], '%Y-%m-%d %H:%M:%S')
        signup_end_date = datetime.strptime(cup_info['signup_end_date'], '%Y-%m-%d %H:%M:%S')

        # Check if the signup are open 
        #bot.cursor.execute("SELECT * FROM Signups WHERE cup_id=%d", (cup_info['id'],))

        if not(signup_start_date <= datetime.now() <= signup_end_date + timedelta(days=1)): # TEMPORARYYYYY
            signup_button = [Button(style=ButtonStyle.grey, disabled=True, label="Signup closed", custom_id=f"button_signup_{cup_info['id']}")]
        else:
            signup_button = [Button(style=ButtonStyle.green, label="Signup", custom_id=f"button_signup_{cup_info['id']}")]

        # Check if there is a message id stored
        try:
            signup_message = await signup_channel.fetch_message(cup_info['signup_message_id'])
            await signup_message.edit(embed=embed, components=signup_button)

        except:
            # Send new message and store message id
            new_signup_msg = await signup_channel.send(embed=embed, components=signup_button)
            bot.db.edit_cup(id=cup_info['id'], signup_message_id=str(new_signup_msg.id))

        # Check if there are divs
        divisions = bot.db.get_all_divisions(cup_info['id'])

        if divisions:
            for division in divisions:
                # Get division embed
                division_embed = await embeds.division(bot, cup_info['id'], division['div_number'])

                # Check if there is a message id stored
                try:
                    division_message = await stage_channel.fetch_message(division['embed_id'])
                    await division_message.edit(embed=division_embed)

                except:
                    # Send new message and store message id
                    new_division_msg = await stage_channel.send(embed=division_embed)
                    bot.db.edit_division(id=division['id'], embed_id=str(new_division_msg.id))


async def fixtures(bot):
    # Get all cups
    for cup_info in bot.db.get_all_cups(1):
        # Update match_index
        match_index_chan = discord.utils.get(bot.guilds[0].channels, id=int(cup_info['chan_match_index_id']))
        await match_index_chan.purge(limit=10000)
        await embeds.match_index(bot, cup_info['id'], match_index_chan)
        # Check if there is a message id stored

        # Get calendar channel
        calendar_chan = discord.utils.get(bot.guilds[0].channels, id=int(cup_info['chan_calendar_id']))

        # Get calendar embed
        calendar_chan_messages = await calendar_chan.history(limit=5).flatten()
        calendar_message = None
        for message in calendar_chan_messages:
            if not message.embeds:
                continue
            if message.embeds[0].title.startswith(":calendar_spiral: Calendar"):
                calendar_message = message
                break

        #Update calendar
        calendar_embed = embeds.calendar(bot, cup_info)
        if calendar_message:
            await calendar_message.edit(embed=calendar_embed)
        else:
            await calendar_chan.send(embed=calendar_embed)

async def fixture_cards(bot):
    # Get all fixtures
    for fixture_info in bot.db.get_all_fixtures():
        # Get channel
        channel = discord.utils.get(bot.guilds[0].channels, id=int(fixture_info['channel_id']))
        # Update embed
        embed_message = await channel.fetch_message(fixture_info['embed_id'])
        if embed_message:
            fixture_embed, components = await embeds.fixture(bot, fixture_id=fixture_info['id'])
            await embed_message.edit(embed=fixture_embed, components=components)

        
