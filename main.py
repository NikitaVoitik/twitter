import aiohttp
import asyncio
from get_query_ids import get_query_ids
from tweet_actions import Account
import config

async def main():
    with open('data/accounts.txt') as file:
        accounts = file.readlines()
    with open('data/proxy.txt') as file:
        proxy = file.readlines()
    config.options()
    print(config.settings['overall_length'])
    async with aiohttp.ClientSession() as session:
        query_ids = await get_query_ids(session, "")

    test = Account(accounts[0], query_ids, "")
    await test.launch_session()


asyncio.run(main())
