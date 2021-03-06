import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv


@dataclass
class PeachoroboConfig:
    channel_id: int = 0
    debug_channel_id: int = 0
    discord_bot_token: str = ""
    calendar_emails: List[str] = field(default_factory=list)
    db_json_path: str = ""
    is_prod: bool = False
    bot_command_prefix = ""
    wack_last_success_ts_path: str = ""
    wack_num_sales_path: str = ""

    def load(self, is_prod: bool) -> None:
        load_dotenv()
        self.is_prod = is_prod
        self.channel_id = int(os.environ["DISCORD_MYSTERY_DINNER_CHANNEL_ID"])
        self.debug_channel_id = int(os.environ["DEBUG_CHANNEL_ID"])
        self.discord_bot_token = os.environ["DISCORD_TOKEN"]
        self.calendar_emails = os.environ["CALENDAR_EMAILS"].split(",")
        self.db_json_path = os.environ["DB_JSON_PATH"]
        self.bot_command_prefix = "!" if is_prod else "?"
        self.wack_last_success_ts_path = os.environ["WACK_LAST_SUCCESS_TS_PATH"]
        self.wack_num_sales_path = os.environ["WACK_NUM_SALES_PATH"]


peachorobo_config = PeachoroboConfig()
