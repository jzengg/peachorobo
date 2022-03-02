import asyncio
import time

import aiohttp
from bs4 import BeautifulSoup

from config import peachorobo_config

URL = "https://www.etsy.com/shop/WicksByWerby"
SOLD_HREF = "https://www.etsy.com/shop/WicksByWerby/sold"


def wack_has_been_run() -> bool:
    last_success_timestamp_seconds = _get_last_wack_timestamp()
    # 5 minutes = 60 seconds * 5 = 300 seconds
    did_run = time.time() - last_success_timestamp_seconds < 300
    return did_run


def _get_last_wack_timestamp() -> float:
    with open(peachorobo_config.wack_last_success_ts_path) as f:
        last_success_timestamp_seconds = float(f.read())
        return last_success_timestamp_seconds


def get_internal_num_sales() -> int:
    with open(peachorobo_config.wack_num_sales_path) as f:
        num = f.read()
        return int(num)


async def get_live_num_sales() -> int:
    async with aiohttp.ClientSession() as session:
        async with session.get(URL) as response:
            if response.status != 200:
                raise ValueError(
                    f"Scraping etsy.com failed, status_code: {response.status}"
                )
            page = await response.text()
            soup = BeautifulSoup(page, "html.parser")
            num_sales_tags = soup.find_all(href=SOLD_HREF)
            num_sales_text = num_sales_tags[0].text.replace(",", "")
            num_sales = int(num_sales_text.split(" ")[0])
            return num_sales


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_live_num_sales())
    loop.close()
