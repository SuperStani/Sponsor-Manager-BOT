from pyrogram import Client, filters
import database as db
import redis
import re
from pyrogram.types import InlineKeyboardMarkup as Keyboard
from pyrogram.types import InlineKeyboardButton as Button
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

api_id = 707541
api_hash = "8f9f3b9eff7524256a57bdbcc75da866"
# screen -S sponsorbot python3 /scripts/sponsorManagerUser/app.py
App = Client("bot", api_id, api_hash)
scheduler = AsyncIOScheduler()


@App.on_message(filters.command(["start"], [".", "/"]))
async def start(App, message):
    e = message.command
    if len(message.command) > 1:
        await viewSponsor(message, message.command[1].split("_")[1])
    else:
        db.page("start", message.chat.id)
        buttons = []
        bots = db.rquery("SELECT username FROM bots ORDER by id DESC", one=False)
        for bot in bots:
            buttons.append([Button("@" + bot[0], "sponsor:selectBot|" + bot[0])])

        buttons = Keyboard(buttons)
        await message.reply("**Menu principale**", reply_markup=buttons)


@App.on_callback_query(filters.regex("sponsor"))
async def sponsorSection(App, query):
    print("gg")
    data = query.data.split(":")[-1].split("|")[0]
    print(data)
    params = query.data.split("|")[1::-1]
    if data == "home":
        buttons = []
        bots = db.rquery("SELECT username FROM bots", one=False)
        for bot in bots:
            buttons.append([Button("@" + bot[0], "sponsor:selectBot|" + bot[0])])

        buttons = Keyboard(buttons)
        await  query.message.edit("**Menu principale**", reply_markup=buttons)

    elif data == "new":
        bot_username = params[0] if len(params) > 0 else None
        buttons = Keyboard([
            [Button("INDIETRO", f"sponsor:selectBot|{bot_username}")]
        ])
        await query.message.edit("Ok, inoltrami un qualsiasi messaggio dal canale / o inviami direttamente il chat id:", reply_markup=buttons)
        db.page("sendChannel_" + bot_username, query.from_user.id)

    elif data == "selectBot":
        print(params)
        bot_username = params[0] if len(params) > 0 else None
        text = "**LISTA SPONSOR:**\n\n"
        channels = db.rquery(
            "SELECT id, title FROM channels WHERE bot_username = %s ORDER by id DESC", bot_username)
        for channel in channels:
            text += f"» [{channel[1]}](https://t.me/NetfluzManagerBot?start=sponsor_{channel[0]})\n"
        buttons = Keyboard([
            [Button("NUOVO SPONSOR", f"sponsor:new|{bot_username}")],
            [Button("INDIETRO", "sponsor:home")]
        ])
        await query.message.edit(text, reply_markup=buttons)

    elif data == "selectRange":
        sponsor_id = params[0] if len(params) > 0 else None
        await query.message.edit("Ok, invia il limite di utenti:")
        db.page(f"usersRange_{sponsor_id}", query.from_user.id)

    elif data == "selectSchedule":
        sponsor_id = params[0] if len(params) > 0 else None
        await query.message.edit("Ok, invia la data d'inizio:")
        db.page(f"dateStart_{sponsor_id}", query.from_user.id)

    elif data == "delete":
        await query.answer("Eliminato!")
        db.wquery("DELETE FROM channels WHERE id = %s", params[0])
        await query.message.delete()


@App.on_message()
async def on_message(App, message):
    page = db.getPage(message.chat.id)
    print(page)
    if page.find("sendChannel") >= 0:
        if message.forward_from_chat.id is not None:
            channel_id = message.forward_from_chat.id
            title = message.forward_from_chat.title
        else:
            if message.text.isnumeric():
                channel_id = message.text
            else:
                channel_id = None
        if channel_id is not None:
            try:
                info = await App.get_chat(channel_id)
                title = info.title
            except ValueError as e:
                title = None
            if title is not None:
                bot_username = page.split("_")[-1]
                sponsor_id = db.wquery("INSERT INTO channels SET channel_id = %s,title = %s,  bot_username = %s",
                                       channel_id, title, bot_username)
                buttons = Keyboard([
                    [Button("RANGE UTENTI", f"sponsor:selectRange|{sponsor_id}")],
                    [Button("PROGRAMMAZIONE", f"sponsor:selectSchedule|{sponsor_id}")]
                ])
                await message.reply("Seleziona la modalita di sponsor:", reply_markup=buttons)
                db.page("", message.chat.id)
            else:
                await message.reply("Il bot non è admin nel canale!")

    elif page.find("usersRange") >= 0:
        sponsor_id = page.split("_")[-1]
        channel_id, bot_username = db.rquery("SELECT channel_id, bot_username FROM channels WHERE id = %s", sponsor_id,
                                             one=True)
        link = await createInviteUrl(App, channel_id, message.text)
        db.wquery("UPDATE channels SET users_range = %s, invite_url = %s WHERE id = %s", message.text, link.invite_link,
                  sponsor_id)
        buttons = Keyboard([
            [Button("INDIETRO", f"sponsor:selectBot|{bot_username}")]
        ])
        await message.reply("Sponsor creato con successo!", reply_markup=buttons)
        db.page("", message.chat.id)

    elif page.find("dateStart") >= 0:
        sponsor_id = page.split("_")[-1]
        db.wquery("UPDATE channels SET datetime_start = %s WHERE id = %s", message.text, sponsor_id)
        await message.reply("Ok invia la data di fine:")
        db.page(f"dateStop_{sponsor_id}", message.chat.id)

    elif page.find("dateStop") >= 0:
        sponsor_id = page.split("_")[-1]
        channel_id, bot_username = db.rquery("SELECT channel_id, bot_username FROM channels WHERE id = %s", sponsor_id,
                                             one=True)
        link = await createInviteUrl(App, channel_id)
        db.wquery("UPDATE channels SET datetime_stop = %s, invite_url = %s WHERE id = %s", message.text,
                  link.invite_link, sponsor_id)
        buttons = Keyboard([
            [Button("INDIETRO", f"sponsor:selectBot|{bot_username}")]
        ])
        await message.reply("Sponsor creato con successo!", reply_markup=buttons)
        db.page("", message.chat.id)


async def viewSponsor(message, sponsor_id):
    info = db.rquery(
        "SELECT title, channel_id, invite_url, users_range, earned_users, datetime_start, datetime_stop FROM channels WHERE id = %s",
        sponsor_id, one=True)
    title, channel_id, invite_url, users_range, earned_users, datetime_start, datetime_stop = info
    users_range = users_range if users_range is not None else '__Non impostato__'
    datetime_start = datetime_start if datetime_start is not None else '__Non impostato__'
    datetime_stop = datetime_stop if datetime_stop is not None else '__Non impostato__'
    text = f"**Titolo:** {title}\n**Link d'invito:** {invite_url}\n**Utenti entrati:** {earned_users}\n**Limite utenti:** {users_range}\n**Data inizio:** __{datetime_start}__\n**Data fine:** __{datetime_stop}__"
    buttons = Keyboard([
        [Button("ELIMINA", f"sponsor:delete|{sponsor_id}")],
        [Button("HOME", f"sponsor:home")]
    ])
    await message.reply(text, reply_markup=buttons)


async def createInviteUrl(App, channel_id, limit_users=None):
    return await App.create_chat_invite_link(chat_id=channel_id, name="NetfluzManager", member_limit=int(limit_users))


async def updateEarnedUser():
    sql = """
        SELECT channels.channel_id,
            channels.invite_url,
            channels.id
        FROM (
                SELECT c.channel_id, c.invite_url, c.datetime, c.id
                FROM channels c
                WHERE c.users_range IS NOT NULL
                AND c.users_range > c.earned_users
                UNION
                SELECT c1.channel_id, c1.invite_url, c1.datetime, c1.id
                FROM channels c1
                WHERE c1.datetime_start <= NOW()
                AND c1.datetime_stop > NOW()
                ORDER BY datetime -- Add an ORDER BY clause to specify the desired order
                LIMIT 5 -- Limit the results in the subquery
            ) channels
        ORDER by channels.datetime
    """
    channels = db.rquery(sql, one=False)
    for channel in channels:
        channel_id, invite_url, sponsor_id = channel
        info = await App.get_chat_invite_link(chat_id=channel_id, invite_link=invite_url)
        print(info)
        db.wquery("UPDATE channels SET earned_users = %s WHERE id = %s", info.member_count, sponsor_id)
        await asyncio.sleep(1)


#scheduler.add_job(updateEarnedUser, 'interval', minutes=1)

#scheduler.start()

print("App avviata..")

App.run()
