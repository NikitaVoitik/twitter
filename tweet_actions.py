import aiohttp
import asyncio
from random import randint
from hashlib import md5
from random import randbytes
from fake_useragent import UserAgent
import time
import dateutil.parser
import json
from json import JSONEncoder
import config
import datetime
from datetime import datetime as Datetime, timedelta
from logs.logger import Logger
from solve_captcha import SolveCaptcha

logger = Logger("tweet_actions_py")
add_to_database = []


class DateTimeEncoder(JSONEncoder):
    # Override the default method
    def default(self, obj):
        if isinstance(obj, (datetime.date, datetime)):
            return obj.isoformat()


def DecodeDateTime(empDict):
    if 'joindate' in empDict:
        empDict["joindate"] = dateutil.parser.parse(empDict["joindate"])
        return empDict


class Account:
    def __init__(self, token: str, query_ids: dict, proxy: str, twitterDB) -> None:
        self.session_length = None
        self.session = None
        self.headers = None
        self.name = None
        self.session_all = None
        self.schedule = list([] for _ in range(0, 7))
        self.proxy = proxy
        self.sessions_in_week = randint(config.settings['sessions_in_week'][0], config.settings['sessions_in_week'][1])
        self.ids = query_ids
        self.token = token
        self.twitterDB = twitterDB
        self.user_agent = UserAgent().random
        self.table_name = 'TasksAndSchedule'

    def update_schedule(self):
        cur_time = Datetime.now()
        for day in self.schedule:
            for ind in range(0, len(day)):
                if day[ind] < cur_time:
                    day.pop(ind)
        overall_length = randint(config.settings['overall_length'][0], config.settings['overall_length'][1])
        self.session_length = overall_length // self.sessions_in_week
        if overall_length % self.sessions_in_week != 0:
            self.session_length += 1
        cur = 0
        for i in self.schedule:
            cur += len(i)
        left_sessions = self.sessions_in_week - cur
        sessions_each_day = list(0 for _ in range(0, 7))
        while left_sessions:
            ind = randint(0, 6)
            sessions_each_day[ind] += 1
            left_sessions -= 1
        for ind in range(0, 7):
            number = sessions_each_day[ind]
            hours = []
            simple_hours = []
            while number:
                hour = randint(2, 23)
                delta = timedelta(days=ind, hours=hour - cur_time.hour)
                if not hour in simple_hours and not hour - 1 in simple_hours and cur_time + delta > cur_time:
                    simple_hours.append(hour)
                    hours.append(cur_time + delta - timedelta(minutes=cur_time.minute))
                number -= 1
            self.schedule[ind] += hours
            self.schedule[ind].sort()

    async def manage(self):
        while True:
            cur_time = Datetime.now()
            self.update_schedule()
            # await self.twitterDB.delete_all(self.table_name)
            # await self.twitterDB.insert(self.table_name, [self.token, ' ', json.dumps(self.schedule, cls=DateTimeEncoder)])
            # local_schedule = await self.twitterDB.select(self.table_name, ['schedule'])
            # local_schedule = json.loads(local_schedule[0][0], object_hook=DecodeDateTime)
            # print(local_schedule)
            # print(Datetime.strptime(local_schedule[0][0], '%Y-%m-%dT%H:%M:%S.%f'))
            next_session = 0
            for day in self.schedule:
                for ind in range(0, len(day)):
                    if day[ind] >= cur_time:
                        next_session = day[ind]
                        break
                if next_session:
                    break
            wait_time = next_session - cur_time
            wait_time = wait_time.total_seconds() + randint(0, 3600)
            await asyncio.sleep(wait_time)
            await self.launch_session(self.session_length, None)

    async def first_launch(self):
        if self.twitterDB.local.get(self.token):
            if self.twitterDB.local.get(self.token).get('schedule'):
                self.schedule = self.twitterDB.local[self.token]['schedule']
        await self.manage()

    async def launch_session(self, session_length: int, tasks: dict | None = None) -> None:
        csrf_token = md5(randbytes(32)).hexdigest()
        cookie = f"des_opt_in=Y; auth_token={self.token}; ct0={csrf_token}; x-csrf-token={csrf_token};"
        self.headers = {
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'User-Agent': self.user_agent,
            'Origin': 'https://mobile.twitter.com',
            'Referer': 'https://mobile.twitter.com/',
            'x-twitter-active-user': 'yes',
            'x-twitter-auth-type': 'OAuth2Session',
            'x-twitter-client-language': 'en',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': cookie,
            'authorization': self.ids['bearer_token'],
            'x-csrf-token': csrf_token
        }

        async with aiohttp.ClientSession(headers=self.headers) as session:
            self.session = session
            lock, csrf_token = await self._get_ct0()
            if lock:
                await SolveCaptcha(self.token, csrf_token).solve_captcha("")
            self.headers['cookie'] = f"des_opt_in=Y; auth_token={self.token}; ct0={csrf_token};"
            self.headers['x-csrf-token'] = csrf_token
            await self.account_life(session_length, tasks)

            # await self.like('1735742272946442398')
            # await self.retweet('1735742272946442398')
            # await self.follow('LondonBreed')
            # await self.tweet(f'Hello guys, {randint(1, 1000000)}')
            # await self.comment('1735742272946442398', f'Cool, {randint(1, 1000000)}')
            # print(await self.get_tweets())

            # users = await self.get_popular_users()
            # await self.follow_users(users, 10)
            # await self.account_life(20, {'follow_popular_users': 10})

    async def account_life(self, session_length: int, tasks: dict | None = None) -> None:
        end_time = time.time() + session_length * 60
        tweets = await self.get_tweets()
        chance_like = randint(config.settings['chance_of_like'][0], config.settings['chance_of_like'][1])
        chance_retweet = randint(config.settings['chance_of_retweet'][0], config.settings['chance_of_retweet'][1])
        cur_tweet = 0
        chance_tasks = randint(1, 100)
        if chance_tasks <= 50:
            await self.complete_tasks(tasks, [2, 3])
        while time.time() < end_time + randint(-60, 60):
            if not tweets[cur_tweet].isdigit():
                await asyncio.sleep(randint(4, 8))
                cur_tweet += 1
                continue
            await asyncio.sleep(randint(7, 12))
            chance = randint(1, 100)
            if chance < chance_like:
                await self.like(tweets[cur_tweet])
            await asyncio.sleep(randint(0, 1))
            if chance < chance_retweet:
                await self.retweet(tweets[cur_tweet])
            await asyncio.sleep(1, 2)
            cur_tweet += 1
        if chance_tasks > 50:
            await self.complete_tasks(tasks, [2, 3])

    async def complete_tasks(self, tasks: dict | None, delay: list) -> None:
        if tasks is None:
            return
        for task in tasks:
            content = tasks[task]
            if task == "follow_popular_users":
                popular_users = await self.get_popular_users()
                await self.follow_users(popular_users, content)
            elif task == "follow_users":
                await self.follow_users(content, len(tasks))
            elif task == "like_tweet":
                await self.like(content)
            elif task == "retweet":
                await self.retweet(content)
            elif task == "comment":
                await self.comment(content['tweet_id'], content['content'])
            await asyncio.sleep(randint(delay[0], delay[1]))

    async def _get_ct0(self) -> tuple[bool, str]:
        try:
            url = 'https://mobile.twitter.com/i/api/1.1/account/settings.json?include_mention_filter=true&include_nsfw_user_flag=true&include_nsfw_admin_flag=true&include_ranked_timeline=true&include_alt_text_compose=true&ext=ssoConnections&include_country_code=true&include_ext_dm_nsfw_media_filter=true&include_ext_sharing_audiospaces_listening_data_with_followers=true'
            async with self.session.get(url, ssl=False, proxy=self.proxy) as res:
                cookie_data = await res.json()
                self.name = cookie_data.get('screen_name')
                csrf = self.session.cookie_jar.filter_cookies(url).get("ct0").value
                if "account is temporarily locked" in await res.text():
                    return True, csrf
                return False, str(csrf)
        except Exception as er:
            logger.error(f"Account {self.token} error {er} when getting csrf token")

    async def like(self, tweet_id: str) -> None:
        url = f'https://twitter.com/i/api/graphql/{self.ids["like"]}/FavoriteTweet'
        data = {
            'variables': {
                'tweet_id': tweet_id
            },
            'query_id': self.ids['like']
        }
        headers = self.headers
        headers['content-type'] = 'application/json'

        try:
            async with self.session.post(url, headers=headers, ssl=False, json=data, proxy=self.proxy) as res:
                txt = await res.text()
                if "already favorited tweet" in txt or '"favorite_tweet":"Done"' in txt:
                    logger.info(f"Account {self.name} liked tweet {tweet_id}")
                else:
                    logger.error(f"Account {self.name} error {txt} when liking {tweet_id}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when liking {tweet_id}")

    async def retweet(self, tweet_id: str) -> None:
        url = f'https://twitter.com/i/api/graphql/{self.ids["retweet"]}/CreateRetweet'
        data = {
            'variables': {
                'tweet_id': tweet_id,
                'dark_request': False
            },
            'query_id': self.ids['retweet']
        }
        headers = self.headers
        headers['content-type'] = 'application/json'

        try:
            async with self.session.post(url, headers=headers, ssl=False, json=data, proxy=self.proxy) as res:
                txt = await res.text()
                if "already retweeted this Tweet" in txt or 'create_retweet' in txt:
                    logger.info(f"Account {self.name} retweeted tweet {tweet_id}")
                else:
                    logger.error(f"Account {self.name} error {txt} when retweeting {tweet_id}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when retweeting {tweet_id}")

    async def follow(self, username: str) -> None:
        user_url = "https://twitter.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName"
        data = {
            'variables': '{"screen_name":"' + username + '","withSafetyModeUserFields":true}',
            'features': '{"hidden_profile_likes_enabled":true,"hidden_profile_subscriptions_enabled":true,'
                        '"responsive_web_graphql_exclude_directive_enabled":true,'
                        '"verified_phone_label_enabled":false,'
                        '"subscriptions_verification_info_is_identity_verified_enabled":true,'
                        '"subscriptions_verification_info_verified_since_enabled":true,'
                        '"highlights_tweets_tab_ui_enabled":true,'
                        '"creator_subscriptions_tweet_preview_api_enabled":true,'
                        '"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,'
                        '"responsive_web_graphql_timeline_navigation_enabled":true}',
            'fieldToggles': '{"withAuxiliaryUserLabels":false}',
        }
        user_id = ""
        try:
            async with self.session.get(user_url, headers=self.headers, ssl=False, params=data,
                                        proxy=self.proxy) as res:
                user_id = await res.json()
                user_id = user_id.get('data', {}).get('user', {}).get('result', {}).get('rest_id')
                if user_id is None:
                    logger.error(f"Account {self.name} error {res.text()} when getting id of {username}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when getting id of {username}")

        data = {
            'include_profile_interstitial_type': '1',
            'include_blocking': '1',
            'include_blocked_by': '1',
            'include_followed_by': '1',
            'include_want_retweets': '1',
            'include_mute_edge': '1',
            'include_can_dm': '1',
            'include_can_media_tag': '1',
            'include_ext_has_nft_avatar': '1',
            'include_ext_is_blue_verified': '1',
            'include_ext_verified_type': '1',
            'include_ext_profile_image_shape': '1',
            'skip_status': '1',
            'user_id': user_id,
        }
        url = "https://twitter.com/i/api/1.1/friendships/create.json"
        headers = self.headers
        headers['content-type'] = 'application/x-www-form-urlencoded'

        try:
            async with self.session.post(url, headers=headers, data=data, ssl=False, proxy=self.proxy) as res:
                follow_data = await res.json()
                if follow_data['id'] == int(user_id):
                    logger.info(f"Account {self.name} is now following {username}")
                else:
                    logger.error(f"Account {self.name} error {res.text()} when subbing {username}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} in time of following {username}")

    async def follow_by_id(self, user_id: str) -> None:
        data = {
            'include_profile_interstitial_type': '1',
            'include_blocking': '1',
            'include_blocked_by': '1',
            'include_followed_by': '1',
            'include_want_retweets': '1',
            'include_mute_edge': '1',
            'include_can_dm': '1',
            'include_can_media_tag': '1',
            'include_ext_has_nft_avatar': '1',
            'include_ext_is_blue_verified': '1',
            'include_ext_verified_type': '1',
            'include_ext_profile_image_shape': '1',
            'skip_status': '1',
            'user_id': user_id,
        }
        url = "https://twitter.com/i/api/1.1/friendships/create.json"
        headers = self.headers
        headers['content-type'] = 'application/x-www-form-urlencoded'

        try:
            async with self.session.post(url, headers=headers, data=data, ssl=False, proxy=self.proxy) as res:
                follow_data = await res.json()
                if follow_data['id'] == int(user_id):
                    logger.info(f"Account {self.name} is now following {user_id}")
                else:
                    logger.error(f"Account {self.name} error {res.text()} when subbing {user_id}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} in time of following {user_id}")

    async def tweet(self, content: str) -> None:
        url = f'https://twitter.com/i/api/graphql/{self.ids["tweet"]}/CreateTweet'
        data = {
            "variables": "{\"tweet_text\":\"" + content + "\",\"media\":{\"media_entities\":[],\"possibly_sensitive\":false},\"withDownvotePerspective\":false,\"withReactionsMetadata\":false,\"withReactionsPerspective\":false,\"withSuperFollowsTweetFields\":true,\"withSuperFollowsUserFields\":true,\"semantic_annotation_ids\":[],\"dark_request\":false,\"__fs_dont_mention_me_view_api_enabled\":false,\"__fs_interactive_text_enabled\":false,\"__fs_responsive_web_uc_gql_enabled\":false}"
        }
        headers = self.headers
        headers['content-type'] = 'application/json'

        try:
            async with self.session.post(url, headers=headers, json=data, ssl=False, proxy=self.proxy) as res:
                txt = await res.text()
                if "rest_id" in txt:
                    logger.info(f"Account {self.name} successfully tweeted.")
                else:
                    logger.error(f"Account {self.name} error {txt} when tweeting")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when tweeting")

    async def comment(self, tweet_id: str, content: str) -> None:
        url = f'https://twitter.com/i/api/graphql/{self.ids["comment"]}/CreateTweet'
        headers = self.headers
        headers['content-type'] = 'application/json'
        data = {
            "variables": "{\"tweet_text\":\"" + content + "\",\"reply\":{\"in_reply_to_tweet_id\":\"" + tweet_id + "\",\"exclude_reply_user_ids\":[]},\"media\":{\"media_entities\":[],\"possibly_sensitive\":false},\"withDownvotePerspective\":false,\"withReactionsMetadata\":false,\"withReactionsPerspective\":false,\"withSuperFollowsTweetFields\":true,\"withSuperFollowsUserFields\":true,\"semantic_annotation_ids\":[],\"dark_request\":false,\"withUserResults\":true,\"withBirdwatchPivots\":false}",
            "queryId": "" + self.ids['comment'] + ""
        }

        try:
            async with self.session.post(url, headers=headers, json=data, ssl=False, proxy=self.proxy) as res:
                txt = await res.text()
                if "rest_id" in txt:
                    logger.info(f"Account {self.name} successfully commented.")
                else:
                    logger.error(f"Account {self.name} error {txt} when commenting {tweet_id}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when commenting {tweet_id}")

    async def get_tweets(self) -> list:
        url = "https://twitter.com/i/api/graphql/4lamDJErKVeOVyGh-y2UXQ/HomeLatestTimeline?variables=%7B%22count%22%3A20%2C%22includePromotedContent%22%3Atrue%2C%22latestControlAvailable%22%3Atrue%2C%22requestContext%22%3A%22launch%22%7D&features=%7B%22responsive_web_graphql_exclude_directive_enabled%22%3Atrue%2C%22verified_phone_label_enabled%22%3Afalse%2C%22responsive_web_home_pinned_timelines_enabled%22%3Atrue%2C%22creator_subscriptions_tweet_preview_api_enabled%22%3Atrue%2C%22responsive_web_graphql_timeline_navigation_enabled%22%3Atrue%2C%22responsive_web_graphql_skip_user_profile_image_extensions_enabled%22%3Afalse%2C%22c9s_tweet_anatomy_moderator_badge_enabled%22%3Atrue%2C%22tweetypie_unmention_optimization_enabled%22%3Atrue%2C%22responsive_web_edit_tweet_api_enabled%22%3Atrue%2C%22graphql_is_translatable_rweb_tweet_is_translatable_enabled%22%3Atrue%2C%22view_counts_everywhere_api_enabled%22%3Atrue%2C%22longform_notetweets_consumption_enabled%22%3Atrue%2C%22responsive_web_twitter_article_tweet_consumption_enabled%22%3Afalse%2C%22tweet_awards_web_tipping_enabled%22%3Afalse%2C%22freedom_of_speech_not_reach_fetch_enabled%22%3Atrue%2C%22standardized_nudges_misinfo%22%3Atrue%2C%22tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled%22%3Atrue%2C%22longform_notetweets_rich_text_read_enabled%22%3Atrue%2C%22longform_notetweets_inline_media_enabled%22%3Atrue%2C%22responsive_web_media_download_video_enabled%22%3Afalse%2C%22responsive_web_enhance_cards_enabled%22%3Afalse%7D"

        try:
            async with self.session.get(url, headers=self.headers, ssl=False, proxy=self.proxy) as res:
                tweets_json = await res.json()
                tweets = tweets_json['data']['home']['home_timeline_urt']['instructions'][0]['entries']
                result = []
                for i in tweets:
                    cur = i['entryId']
                    result.append(cur[6:])
                logger.info(f"Account {self.name} successfully got tweets from followed users")
                return result
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when getting tweets")

    async def get_popular_users(self) -> list:
        url = "https://twitter.com/i/api/graphql/CYSD3D16ZF2JCxd9OR51Yg/ConnectTabTimeline?variables=%7B%22count%22%3A20%2C%22context%22%3A%22%7B%7D%22%7D&features=%7B%22responsive_web_graphql_exclude_directive_enabled%22%3Atrue%2C%22verified_phone_label_enabled%22%3Afalse%2C%22responsive_web_home_pinned_timelines_enabled%22%3Atrue%2C%22creator_subscriptions_tweet_preview_api_enabled%22%3Atrue%2C%22responsive_web_graphql_timeline_navigation_enabled%22%3Atrue%2C%22responsive_web_graphql_skip_user_profile_image_extensions_enabled%22%3Afalse%2C%22c9s_tweet_anatomy_moderator_badge_enabled%22%3Atrue%2C%22tweetypie_unmention_optimization_enabled%22%3Atrue%2C%22responsive_web_edit_tweet_api_enabled%22%3Atrue%2C%22graphql_is_translatable_rweb_tweet_is_translatable_enabled%22%3Atrue%2C%22view_counts_everywhere_api_enabled%22%3Atrue%2C%22longform_notetweets_consumption_enabled%22%3Atrue%2C%22responsive_web_twitter_article_tweet_consumption_enabled%22%3Afalse%2C%22tweet_awards_web_tipping_enabled%22%3Afalse%2C%22freedom_of_speech_not_reach_fetch_enabled%22%3Atrue%2C%22standardized_nudges_misinfo%22%3Atrue%2C%22tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled%22%3Atrue%2C%22longform_notetweets_rich_text_read_enabled%22%3Atrue%2C%22longform_notetweets_inline_media_enabled%22%3Atrue%2C%22responsive_web_media_download_video_enabled%22%3Afalse%2C%22responsive_web_enhance_cards_enabled%22%3Afalse%7D"

        try:
            async with self.session.get(url, headers=self.headers, ssl=False, proxy=self.proxy) as res:
                js = await res.json()
                users = js['data']['connect_tab_timeline']['timeline']['instructions'][2]['entries'][0]['content'][
                    'items']
                results = []
                for i in users:
                    cur = i['item']['itemContent']['user_results']
                    if cur == {}:
                        continue
                    cur = cur['result']['legacy']['screen_name']
                    results.append(cur)
                logger.info(f"Account {self.name} successfully got recommended users")
                return results
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when getting popular users")

    async def follow_users(self, users: list, number: int) -> None:
        generated = set()
        while len(generated) < number:
            generated.add(users[randint(0, len(users) - 1)])
        try:
            for user in generated:
                await self.follow(user)
                await asyncio.sleep(randint(2, 5))
            logger.info(f"Account {self.name} successfully followed users")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when trying to follow users")
