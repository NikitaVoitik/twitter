import aiohttp
import asyncio
from logs.logger import Logger

logger = Logger("get_query_ids_py")

timeout = aiohttp.ClientTimeout(total=60)


async def main_response(session: aiohttp.ClientSession, proxy: str):
    url = 'https://abs.twimg.com/responsive-web/client-web/main.f3ada2b5.js'
    async with session.get(url, ssl=False, timeout=timeout, proxy=proxy) as result:
        return await result.text()


async def tweet_response(session, proxy: str):
    url = 'https://abs.twimg.com/responsive-web/client-web/main.70ac9f25.js'
    async with session.get(url, ssl=False, timeout=timeout, proxy=proxy) as result:
        return await result.text()


async def get_query_ids(session: aiohttp.ClientSession, proxy: str) -> dict:
    try:
        main, tweet = await asyncio.gather(main_response(session, proxy), tweet_response(session, proxy))
    except Exception as er:
        logger.error(f"Error when getting ids: {er}")

    result = {
        'subscribe': main.split('fDBV:function(e,t){e.exports={queryId:"')[-1].split('"')[0],
        'retweet':
            main.split('user_spam_reports"]}')[1].split('operationName:"CreateRetweet')[0].split('queryId:"')[1].split(
                '"')[0],
        'like': main.split('"x/WR":function(e,t){e.exports={queryId:"')[-1].split('"')[0],
        'comment': main.split('operationName:"ListProductSubscriptions",operationType:"query"')[-1].split(
            'operationName:"CreateTweet')[0].split('queryId:"')[-1].split('"')[0],
        'tweet': tweet.split('qpTX:function(e,t){e.exports={queryId:"')[-1].split('"')[0],
        'bearer_token': 'Bearer ' +
                        main.split('const r="ACTION_FLUSH",i="ACTION_REFRESH')[-1].split(',l="d_prefs"')[0].split(
                            ',s="')[-1].split('"')[0]
    }
    return result
