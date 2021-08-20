import requests
import flag
import datetime
import re
import emoji
import mariadb

# Check if the auth exists on urt.info
def check_auth(auth):
    login_search = requests.get(f"https://www.urbanterror.info/members/profile/{auth}/")
    if "No member with the login or id" in  login_search.text:
        return False
    else:
        return True

# Check if the text is a valid flag emoji
def check_flag_emoji(cursor, flag_to_check):
    country = flag.dflagize(flag_to_check)
    cursor.execute("SELECT id FROM Countries WHERE id = %s;", (country,))
    return country, cursor.fetchone()

# Returns true if the input is a date DD/MM/YYYY and also returns the date object
def check_date_format(date_input): 
    date_elems = [e for e in date_input.split('/') if e.isnumeric()]
    if len(date_elems) != 3:
        return False, None

    day = int(date_elems[0])
    month = int(date_elems[1])
    year = int(date_elems[2])

    # Datetime checks the date validity (example: cant use 30/02)
    try:
        date = datetime.datetime(year, month, day)
        return True, date

    except ValueError:
        return False, None

def check_time_format(time_input):
    time_elems = time_input.split(':')

    if len(time_elems) == 2 and time_elems[0].isnumeric() and 0 <= int(time_elems[0]) <= 23 and  time_elems[1].isnumeric() and 0 <= int(time_elems[1]) <= 59:

        return True, datetime.time(int(time_elems[0]), int(time_elems[1]))
    else:
        return False, None

def prevent_discord_formating(input_text):
    return input_text.replace('`', '\\`').replace('*', '\\*').replace('_', '\\_')

# Check if there are any emojis in the message (custom or not)
def emojis_in(text):
    return len(re.findall(r'<:\w*:\d*>', text)) + emoji.emoji_count(text) > 0

def ping_db(bot):
    try:
        bot.conn.ping()
    except mariadb.DatabaseError:
        print("The database has gone away -- reconnecting.")
        bot.conn.reconnect()