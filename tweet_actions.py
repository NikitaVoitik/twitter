import aiohttp
import asyncio
from hashlib import md5
from random import randbytes
from fake_useragent import UserAgent
from logs.logger import Logger

logger = Logger("tweet_actions_py")


class Account():
    def __init__(self, token: str, query_ids: dict, proxy) -> None:
        self.headers = None
        self.name = None
        self.proxy = proxy
        self.ids = query_ids
        self.token = token
        self.user_agent = UserAgent().random

    async def launch_session(self) -> None:
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
            csrf_token = await self._get_ct0()
            self.headers['cookie'] = f"des_opt_in=Y; auth_token={self.token}; ct0={csrf_token};"
            self.headers['x-csrf-token'] = csrf_token
            # await self.like('1732373008176816235')
            # await self.retweet('1732373008176816235')
            # await self.follow('OP_SPOILERS2023')
            # await self.tweet('Hello guys')
            # await self.comment('1732373008176816235', 'Cool')
            await self.get_users()

    async def _get_ct0(self) -> str:
        try:
            username_url = 'https://mobile.twitter.com/i/api/1.1/account/settings.json?include_mention_filter=true&include_nsfw_user_flag=true&include_nsfw_admin_flag=true&include_ranked_timeline=true&include_alt_text_compose=true&ext=ssoConnections&include_country_code=true&include_ext_dm_nsfw_media_filter=true&include_ext_sharing_audiospaces_listening_data_with_followers=true'
            async with self.session.get(username_url, ssl=False) as res:
                js = await res.json()
                self.name = js.get('screen_name')
                csrf = self.session.cookie_jar.filter_cookies(username_url).get("ct0").value
                return str(csrf)
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when getting csrf token")

    async def like(self, tweet_id: str) -> None:
        try:
            url = f'https://twitter.com/i/api/graphql/{self.ids["like"]}/FavoriteTweet'
            data = {
                'variables': {
                    'tweet_id': tweet_id
                },
                'query_id': self.ids['like']
            }
            headers = self.headers
            headers['content-type'] = 'application/json'
            async with self.session.post(url, headers=headers, ssl=False, json=data) as res:
                txt = await res.text()
                if "has already favorited tweet" in txt or '"favorite_tweet":"Done"' in txt:
                    logger.info(f"Account {self.name} liked tweet {tweet_id}")
                else:
                    logger.error(f"Account {self.name} error {txt} when liking {tweet_id}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when liking {tweet_id}")

    async def retweet(self, tweet_id: str) -> None:
        try:
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
            async with self.session.post(url, headers=headers, ssl=False, json=data) as res:
                txt = await res.text()
                if "You have already retweeted this Tweet" in txt or 'create_retweet' in txt:
                    logger.info(f"Account {self.name} retweeted tweet {tweet_id}")
                else:
                    logger.error(f"Account {self.name} error {txt} when retweeting {tweet_id}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when retweeting {tweet_id}")

    async def follow(self, username: str) -> None:
        try:
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
            async with self.session.get(user_url, headers=self.headers, ssl=False, params=data) as res:
                user_id = await res.json()
                user_id = user_id.get('data', {}).get('user', {}).get('result', {}).get('rest_id')
                if user_id is None:
                    logger.error(f"Account {self.name} error {res.text()} when getting id of {username}")

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
            async with self.session.post(url, headers=headers, data=data, ssl=False) as res:
                js = await res.json()
                if js['id'] == int(user_id):
                    logger.info(f"Account {self.name} is now following {username}")
                else:
                    logger.error(f"Account {self.name} error {res.text()} when subbing {username}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} in time of following {username}")

    async def tweet(self, content: str) -> None:
        try:
            url = f'https://twitter.com/i/api/graphql/{self.ids["tweet"]}/CreateTweet'
            data = {
                "variables": "{\"tweet_text\":\"" + content + "\",\"media\":{\"media_entities\":[],\"possibly_sensitive\":false},\"withDownvotePerspective\":false,\"withReactionsMetadata\":false,\"withReactionsPerspective\":false,\"withSuperFollowsTweetFields\":true,\"withSuperFollowsUserFields\":true,\"semantic_annotation_ids\":[],\"dark_request\":false,\"__fs_dont_mention_me_view_api_enabled\":false,\"__fs_interactive_text_enabled\":false,\"__fs_responsive_web_uc_gql_enabled\":false}"
            }
            headers = self.headers
            headers['content-type'] = 'application/json'
            async with self.session.post(url, headers=headers, json=data, ssl=False) as res:
                txt = await res.text()
                if "rest_id" in txt:
                    logger.info(f"Account {self.name} successfully tweeted.")
                else:
                    logger.error(f"Account {self.name} error {txt} when tweeting")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when tweeting")

    async def comment(self, tweet_id: str, content: str) -> None:
        try:
            url = f'https://twitter.com/i/api/graphql/{self.ids["comment"]}/CreateTweet'
            headers = self.headers
            headers['content-type'] = 'application/json'
            data = {
                "variables": "{\"tweet_text\":\"" + content + "\",\"reply\":{\"in_reply_to_tweet_id\":\"" + tweet_id + "\",\"exclude_reply_user_ids\":[]},\"media\":{\"media_entities\":[],\"possibly_sensitive\":false},\"withDownvotePerspective\":false,\"withReactionsMetadata\":false,\"withReactionsPerspective\":false,\"withSuperFollowsTweetFields\":true,\"withSuperFollowsUserFields\":true,\"semantic_annotation_ids\":[],\"dark_request\":false,\"withUserResults\":true,\"withBirdwatchPivots\":false}",
                "queryId": "" + self.ids['comment'] + ""
            }
            async with self.session.post(url, headers=headers, json=data, ssl=False) as res:
                txt = await res.text()
                if "rest_id" in txt:
                    logger.info(f"Account {self.name} successfully commented.")
                else:
                    logger.error(f"Account {self.name} error {txt} when commenting {tweet_id}")
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when commenting {tweet_id}")

    async def get_users(self) -> list:
        try:
            url = "https://api.twitter.com/1.1/account/multi/list.json"
            async with self.session.get(url, headers=self.headers, ssl=False) as res:
                js = await res.json()
                print(js)
        except Exception as er:
            logger.error(f"Account {self.name} error {er} when getting popular users")
