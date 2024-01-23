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
from random import randint
from asyncio import StreamReader
import sys
from loguru import logger

twitterDB = None
table_name = 'TasksAndSchedule'
localDB = dict()
accounts = []
last_db_update = Datetime.now()
"""
id
token
tasks (json) [like: 34234, comment: 3242, Hello]
schedule (json) [[time, time], [time, time],...]
ещё нужен 
"""


class DateTimeEncoder(JSONEncoder):
    # Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime)):
            return obj.isoformat()


def DecodeDateTime(empDict):
    if 'joindate' in empDict:
        empDict["joindate"] = dateutil.parser.parse(empDict["joindate"])
        return empDict


def fill_local_db(data):
    for account in data:
        localDB[account[0]] = dict()
        localDB[account[0]]['Tasks'] = json.loads(account[1])
        localDB[account[0]]['Schedule'] = json.loads(account[2], object_hook=DecodeDateTime)
        if type(localDB[account[0]]['Schedule']) == str:
            # print('change')
            localDB[account[0]]['Schedule'] = list()
        # print('........')
        # print(type(localDB[account[0]]['Tasks']))
        for session in range(len(localDB[account[0]]['Schedule'])):
            localDB[account[0]]['Schedule'][session] = Datetime.strptime(
                localDB[account[0]]['Schedule'][session], '%Y-%m-%dT%H:%M:%S.%f'
            )
        for task in range(len(localDB[account[0]]['Tasks'])):
            if localDB[account[0]]['Tasks'][task][0] == 'follow_first_launch':
                continue
            localDB[account[0]]['Tasks'][task][0] = Datetime.strptime(
                localDB[account[0]]['Tasks'][task][0], '%Y-%m-%dT%H:%M:%S.%f'
            )
        # print('........')


async def check_new_accounts(tokens: list):
    for token in tokens:
        if localDB.get(token):
            continue
        else:
            localDB[token] = dict()
            number_of_users = config.settings['users_to_follow_at_start']
            localDB[token]['Tasks'] = [["follow_first_launch", randint(number_of_users[0], number_of_users[1])]]
            localDB[token]['Schedule'] = []
            await twitterDB.insert(table_name, [token, '{}', '[]'], ['Token', 'Tasks', 'Schedule'])


async def renew_db():
    db_data = await twitterDB.select(table_name)
    for account in db_data:
        token = account[0]
        if localDB[token]['Tasks'] != account[1] or localDB[token]['Schedule'] != account[2]:
            data = [json.dumps(localDB[token]['Tasks'], cls=DateTimeEncoder),
                    json.dumps(localDB[token]['Schedule'], cls=DateTimeEncoder)]
            await twitterDB.update(table_name, data, ['Tasks', 'Schedule'], f"Token='{token}'")
    # db_data = await twitterDB.select(table_name)
    # print('5555555')
    # for account in db_data:
    # print(account)
    # print('5555555')


async def main():
    logger.add("logs/main.log", rotation="1 day")
    global accounts
    global twitterDB
    global localDB
    with open('data/accounts.txt') as file:
        accounts_tokens = file.readlines()
    for i in range(len(accounts_tokens)):
        if accounts_tokens[i][len(accounts_tokens[i]) - 1] == '\n':
            accounts_tokens[i] = accounts_tokens[i][:-1]
        print(repr(accounts_tokens[i]))
    with open('data/proxy.txt') as file:
        proxy = file.readlines()
    for i in range(len(proxy)):
        if proxy[i][len(proxy[i]) - 1] == '\n':
            proxy[i] = proxy[i][:-1]
    config.options()
    twitterDB = Database()
    columns = [
        "Token VARCHAR(255) PRIMARY KEY",
        "Tasks VARCHAR(65535)",
        "Schedule VARCHAR(65535)",
    ]
    await twitterDB.connect()
    await twitterDB.create_table(table_name, columns)
    db_data = await twitterDB.select(table_name)
    # print('/////////')
    # print(db_data)
    # print('/////////')
    fill_local_db(db_data)

    await check_new_accounts(accounts_tokens)

    await renew_db()

    # print(Datetime.strptime(localDB['ad17ed4d04f6ccf9974e7086ff8b8f51fd26a439']['Schedule'][0][0],
    # '%Y-%m-%dT%H:%M:%S.%f'))

    # await twitterDB.insert(table_name, ('Hihihihi', 'HeHehehehe', 'Hohohoho'), ['token', 'tasks', 'schedule'])

    for ind, val in enumerate(proxy):
        val = val.split('@')
        proxy[ind] = f'http://{val[1]}@{val[0]}'
    async with aiohttp.ClientSession() as session:
        query_ids = await get_query_ids(session, proxy[0])
    #localDB[accounts_tokens[0]]['Schedule'].append(Datetime.now() + timedelta(seconds=20))
    sessions_queue = asyncio.Queue()
    accounts = list(
        Account(accounts_tokens[ind], query_ids, proxy[ind]) for ind in range(len(accounts_tokens)))
    workers = list(asyncio.create_task(process_session(sessions_queue)) for _ in accounts)
    while True:
        await asyncio.gather(asyncio.create_task(session_producer(sessions_queue, accounts)), *workers)


async def create_stdin_reader() -> StreamReader:
    stream_reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(stream_reader)
    loop = asyncio.get_running_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    return stream_reader


async def read():
    global localDB
    reader = await create_stdin_reader()
    while True:
        data = await reader.readline()
        try:
            data = json.loads(data)
        except:
            logger.error("Wrong format of tasks")
            continue
        task = list(data.keys())[0]
        accounts_needed = data[task][0] if task in ['follow_user', 'like_tweet', 'retweet'] else len(data[task])
        if accounts_needed > len(localDB):
            logger.error("You dont have enough accounts for this task")
            continue
        task_content = data[task][1] if task in ['follow_user', 'like_tweet', 'retweet'] else "undefined"
        accounts = []
        while len(accounts) < accounts_needed:
            for token in localDB.keys():
                chance = randint(1, 100)
                if chance <= 10 and token not in accounts:
                    accounts.append(token)
        ind = 0
        for token in accounts:
            schedule = localDB[token]['Schedule']
            date = schedule[randint(0, len(schedule) - 1)]

            date = schedule[0]

            if task_content == "undefined":
                localDB[token]['Tasks'].append([date, {task: data[task][ind]}])
                ind += 1
            else:
                localDB[token]['Tasks'].append([date, {task: task_content}])
        for token in localDB.keys():
            print(localDB[token])
        logger.info("Your tasks were distributed between accounts and sessions")


async def process_session(queue) -> None:
    while True:
        try:
            account = queue.get_nowait()
            print(1231231, account)
            if account == 'renew':
                await renew_db()
            elif account == "read":
                await read()
            else:
                await account.launch_session()
        except asyncio.QueueEmpty:
            pass
        await asyncio.sleep(1)


async def session_producer(queue, accounts: list) -> None:
    global localDB
    global last_db_update
    queue.put_nowait("read")
    while True:
        cur_time = Datetime.now()

        for token in localDB.keys():
            session_length = update_schedule(token, 120)
            schedule = localDB[token]['Schedule']
            next_session = cur_time
            for session in schedule:
                if session < cur_time:
                    next_session = session
                    break
            #next_session = cur_time - timedelta(seconds=10)
            #print(cur_time, next_session, next_session - timedelta(hours=2))
            #print(cur_time > next_session - timedelta(hours=2))
            # print(type(cur_time), type(next_session))
            if cur_time > next_session:
                for ind in range(len(accounts)):
                    accounts[ind].localDB = localDB[token]
                    if accounts[ind].token == token:
                        try:
                            accounts[ind].session_length = session_length
                            session_length = update_schedule(token)
                            index = 0
                            while index < len(localDB[token]['Tasks']):
                                task = localDB[token]['Tasks'][index]
                                if task[0] == "follow_first_launch":
                                    accounts[index].tasks['follow_first_launch'] = task[1]
                                    localDB[token]['Tasks'].pop(index)
                                elif task[0] <= next_session:
                                    key = list(task[1].keys())[0]
                                    accounts[index].tasks[key] = task[1][key]
                                    localDB[token]['Tasks'].pop(index)
                                else:
                                    index += 1

                            if not accounts[ind].tasks.get('follow_first_launch'):
                                number = config.settings['users_to_follow_every_time']
                                accounts[ind].tasks['follow_popular_users'] = randint(number[0], number[1])
                            #print(33333)
                            #await accounts[ind].launch_session()
                            queue.put_nowait(accounts[ind])
                            #print(33333)
                        except asyncio.QueueFull:
                            pass
                        break
            if cur_time - last_db_update > timedelta(seconds=30):
                last_db_update = Datetime.now()
                queue.put_nowait('renew')
        print('/////////')
        for account in localDB:
            print(account, " : ", localDB[account])
        print('/////////')
        await asyncio.sleep(10)


def check_hours(schedule: list, hour: datetime):
    if hour < Datetime.now():
        return False
    date_top = hour + timedelta(hours=1)
    date_bottom = hour - timedelta(hours=1)
    for date in schedule:
        if date_bottom < date < date_top:
            return False
    return True


def update_schedule(token: str, delay: int = 0) -> int:
    schedule = localDB[token]['Schedule']
    sessions_in_week = 0
    if len(schedule):
        sessions_in_week = len(schedule)
    else:
        schedule = []
    if sessions_in_week < config.settings['sessions_in_week'][0] or sessions_in_week > \
            config.settings['sessions_in_week'][1]:
        sessions_in_week = randint(config.settings['sessions_in_week'][0], config.settings['sessions_in_week'][1])
        if sessions_in_week > config.settings['sessions_in_week'][1]:
            schedule = []
    cur_time = Datetime.now()
    ind = 0
    while ind < len(schedule):
        if schedule[ind] < cur_time - timedelta(seconds=delay):
            schedule.pop(ind)
        else:
            ind += 1
    overall_length = randint(config.settings['overall_length'][0], config.settings['overall_length'][1])
    session_length = overall_length // sessions_in_week
    if overall_length % sessions_in_week != 0:
        session_length += 1
    left_sessions = sessions_in_week - len(schedule)
    while left_sessions > 0:
        cur_time_round = cur_time - timedelta(minutes=cur_time.minute, seconds=cur_time.second)
        day = randint(0, 6)
        hour = randint(0, 24)
        minute = randint(0, 60)
        second = randint(0, 60)
        delta = timedelta(days=day, hours=hour, minutes=minute, seconds=second)
        date = cur_time_round + delta
        if check_hours(schedule, date):
            schedule.append(date)
            left_sessions -= 1
    schedule.sort()
    localDB[token]['Schedule'] = schedule
    return session_length


asyncio.run(main())
