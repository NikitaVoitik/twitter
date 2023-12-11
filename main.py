import aiohttp
import asyncio
from get_query_ids import get_query_ids
from tweet_actions import Account

async def main():
    with open('data/accounts.txt') as file:
        accounts = file.readlines()
    with open('data/proxy.txt') as file:
        proxy = file.readlines()
    async with aiohttp.ClientSession() as session:
        query_ids = await get_query_ids(session)

    test = Account(accounts[0], query_ids, proxy)
    await test.launch_session()


asyncio.run(main())
