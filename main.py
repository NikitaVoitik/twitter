import aiohttp
import asyncio
from get_query_ids import get_query_ids
from tweet_actions import Account
import config
import json
import datetime
from datetime import datetime as Datetime, timedelta
from json import JSONEncoder
import dateutil.parser
from database import Database

twitterDB = None
localDB = dict()
"""
id
token
tasks (json) [like: 34234, comment: 3242, Hello]
schedule (json) [[time, time], [time, time],...]
ещё нужен 
"""

def DecodeDateTime(empDict):
    if 'joindate' in empDict:
        empDict["joindate"] = dateutil.parser.parse(empDict["joindate"])
        return empDict


def fill_local_db(data):
    global localDB
    for account in data:
        localDB[account[0]] = dict()
        localDB[account[0]]['Tasks'] = account[1]
        localDB[account[0]]['Schedule'] = json.loads(account[2], object_hook=DecodeDateTime)

async def main():
    global twitterDB
    global localDB
    with open('data/accounts.txt') as file:
        accounts_tokens = file.readlines()
    with open('data/proxy.txt') as file:
        proxy = file.readlines()
    config.options()
    twitterDB = Database()
    columns = [
        "Token VARCHAR(255) PRIMARY KEY",
        "Tasks VARCHAR(65535)",
        "Schedule VARCHAR(65535)",
    ]
    table_name = 'TasksAndSchedule'
    await twitterDB.connect()
    await twitterDB.create_table(table_name, columns)
    db_data = await twitterDB.select(table_name)
    fill_local_db(db_data)
    print(Datetime.strptime(localDB['ad17ed4d04f6ccf9974e7086ff8b8f51fd26a439']['Schedule'][0][0], '%Y-%m-%dT%H:%M:%S.%f'))
    # await twitterDB.insert(table_name, ('Hihihihi', 'HeHehehehe', 'Hohohoho'), ['token', 'tasks', 'schedule'])
    async with aiohttp.ClientSession() as session:
        query_ids = await get_query_ids(session, "")

    accounts = list(Account(account, query_ids, "", twitterDB) for account in accounts_tokens)
    courutine = list(asyncio.create_task(account.first_launch()) for account in accounts)
    await asyncio.gather(*courutine)


asyncio.run(main())
