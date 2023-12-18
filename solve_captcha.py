import asyncio
import aiohttp
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import time
from logs.logger import Logger

logger = Logger("solve_captcha_py")


async def create_task() -> tuple[int | bool, str]:
    async with aiohttp.ClientSession() as session:
        async with session.get(url='https://api.capmonster.cloud/createTask',
                               ssl=False,
                               json={
                                   'clientKey': '75f7d1557090aa6bf4c27b2a94951efc',
                                   'task': {
                                       'type': 'FunCaptchaTaskProxyless',
                                       'websiteURL': 'https://twitter.com/account/access',
                                       'websitePublicKey': '0152B4EB-D2DC-460A-89A1-629838B529C9'
                                   }
                               }) as r:
            #print(await r.json(content_type=None))
            return (await r.json(content_type=None))['taskId'] if (await r.json(content_type=None))['errorId'] == 0 else False, await r.text()


async def get_task_result(task_id: int | str) -> tuple[bool, str]:
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(url='https://api.capmonster.cloud/getTaskResult',
                                    ssl=False,
                                    json={
                                        'clientKey': '75f7d1557090aa6bf4c27b2a94951efc',
                                        'taskId': task_id
                                    }) as r:
                #print(await r.json(content_type=None))
                if (await r.json(content_type=None))['status'] in ['processing']:
                    await asyncio.sleep(5)
                    continue
                elif (await r.json(content_type=None))['status'] == 'ready':
                    return True, (await r.json(content_type=None))['solution']['token']

                else:
                    return False, await r.text()


class SolveCaptcha:
    def __init__(self, auth_token: str, ct0: str):
        self.auth_token = auth_token
        self.ct0 = ct0

    @staticmethod
    async def wait_for_url(page, url, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            #print(page.url, '////')
            if url in page.url:
                return True
            await asyncio.sleep(1)
        # noinspection PyProtectedMember
        raise Exception('Timeout error url')

    async def wait_for_multiple_conditions(self, page, selector, url, timeout=180000) -> tuple[any, any]:
        # noinspection PyProtectedMember
        try:
            element_task = asyncio.create_task(page.wait_for_selector(selector, timeout=timeout))
            url_task = asyncio.create_task(self.wait_for_url(page=page, url=url))

            done, pending = await asyncio.wait(fs=[element_task, url_task], return_when=asyncio.ALL_COMPLETED)
            for task in pending:
                task.cancel()
            if element_task.done() and element_task.result():
                return None, element_task.result()
            if url_task.done() and url_task.result():
                return True, None
            return None, None

        except Exception as er:
            #print(er)
            return None, None

    async def solve_captcha(self, proxy: str | None) -> bool:
        for _ in range(5):
            try:
                async with async_playwright() as p:
                    context_options = {
                        'user_data_dir': '',
                        'viewport': None,
                    }

                    """if proxy:
                        context_options['proxy'] = {
                            "server": f"http://{Proxy.from_str(proxy=proxy).host}:{Proxy.from_str(proxy=proxy).port}",
                            "username": Proxy.from_str(proxy=proxy).login,
                            "password": Proxy.from_str(proxy=proxy).password,
                        }"""

                    context = await p.firefox.launch_persistent_context(**context_options)

                    await context.add_cookies(
                        [
                            {
                                "name": "auth_token",
                                "value": self.auth_token,
                                "domain": "twitter.com",
                                "path": "/",
                            },
                            {
                                "name": "ct0",
                                "value": self.ct0,
                                "domain": "twitter.com",
                                "path": "/",
                            },
                        ]
                    )

                    page = await context.new_page()
                    await stealth_async(page)
                    await page.goto('https://twitter.com/account/access')
                    await page.wait_for_load_state(state='networkidle',
                                                   timeout=180000)

                    #print(await page.content())
                    #print('ne ok')

                    #print('ok')
                    try:
                        await page.click('input[type="submit"]')
                        if 'twitter.com/home' in page.url:
                            logger.info(f'{self.auth_token} | Аккаунт успешно разморожен')
                        await asyncio.sleep(10)
                        await context.close()
                    except:
                        pass

                    home_page, element = await self.wait_for_multiple_conditions(page=page,
                                                                                 selector="#arkose_iframe, input["
                                                                                          "type='submit'].Button.EdgeButton.EdgeButton--primary",
                                                                                 url="https://twitter.com/home")
                    if not home_page and not element:
                        logger.error(f'{self.auth_token} | Не удалось обнаружить элемент с капчей на странице')
                        continue

                    if home_page:
                        logger.info(f'{self.auth_token} | Аккаунт успешно разморожен')
                        return True

                    if element and await element.get_attribute('value') == 'Continue to Twitter':
                        await element.click()
                        logger.info(f'{self.auth_token} | Аккаунт успешно разморожен')
                        return True

                    elif element and await element.get_attribute('value') == 'Delete':
                        await element.click()
                        continue

                    elif element and await element.get_attribute('value') == 'Start':
                        await element.click()

                        await page.goto('https://twitter.com/account/access')
                        await page.wait_for_selector('#arkose_iframe')

                    while True:
                        task_id, response_text = await create_task()

                        if not task_id:
                            logger.error(
                                f'{self.auth_token} | Ошибка при создании Task на решение капчи, ответ: {response_text}')
                            continue

                        task_result, response_text = await get_task_result(task_id=task_id)

                        if not task_result:
                            logger.error(f'{self.auth_token} | Ошибка при решении капчи, ответ: {response_text}')
                            continue

                        captcha_result = response_text
                        logger.info(f'{self.auth_token} | Решение капчи получено, пробую отправить')
                        break

                    iframe_element = await page.query_selector('#arkose_iframe')
                    #print(await page.content())
                    #print(page.url)
                    #print(iframe_element, '//////////////////')

                    if not iframe_element:
                        try:
                            if 'twitter.com/home' in page.url:
                                logger.info(f'{self.auth_token} | Аккаунт успешно разморожен')
                                return True
                            await page.click('input[type="submit"]')
                            if 'twitter.com/home' in page.url:
                                logger.info(f'{self.auth_token} | Аккаунт успешно разморожен')
                                return True
                        except Exception as er:
                            logger.error(f'{self.auth_token} | Не удалось обнаружить элемент с капчей на странице')
                            continue

                    iframe = await iframe_element.content_frame()

                    await iframe.evaluate(
                        f'parent.postMessage(JSON.stringify({{eventId:"challenge-complete",payload:{{sessionToken:"{captcha_result}"}}}}),"*")')

                    await page.wait_for_load_state(state='networkidle',
                                                   timeout=180000)
                    await page.reload()
                    await asyncio.sleep(10)
                    try:
                        await page.click('input[type="submit"]')
                        if 'twitter.com/home' in page.url:
                            logger.info(f'{self.auth_token} | Аккаунт успешно разморожен')
                    except:
                        pass

                    await self.wait_for_url(page=page,
                                            url='twitter.com/home',
                                            timeout=15)

                    logger.info(f'{self.auth_token} | Аккаунт успешно разморожен')
                    await asyncio.sleep(15)
                    await context.close()

            except Exception as error:
                logger.error(f'{self.auth_token} | Неизвестная ошибка при попытке разморозить аккаунт: {error}')
                continue
            else:
                return True

        else:
            logger.error(f'{self.auth_token} | Empty Attempts')
