from pyrogram import Client, filters
import database as db
import asyncio

app = Client("bot")


# python3 /scripts/sponsorManagerUser/updateUsersEarned.py
async def main():
    async with app:
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
            sponsor_id, invite_url, channel_id = channel
            info = await app.get_chat_invite_link(chat_id=channel_id, invite_link=invite_url)
            db.wquery("UPDATE channels SET earned_users = %s WHERE id = %s", info.member_count, sponsor_id)
            await asyncio.sleep(1)


app.run(main())
