import asyncio
from dataclasses import dataclass
from datetime import date
from time import sleep
from typing import List, Optional

import aiohttp
from nba_api.stats.endpoints import videodetails
from nba_api.stats.library.parameters import ContextMeasureDetailed
from nba_api.stats.static import players
from nba_api.stats.static import teams


@dataclass
class PlayData:
    event_id: int
    description: str


@dataclass
class GameData:
    game_id: str
    game_date: date
    home_team: str
    away_team: str
    plays: List[PlayData]


@dataclass
class VideoData:
    uri: str
    description: str


class NoHighlightsFoundError(Exception):
    pass


async def main():
    team_abbreviation = "DEN"
    player_name = "Nikola Jokic"
    team_id = get_team_id(team_abbreviation.upper())
    player_id = get_player_id(player_name.title())
    game_data = get_most_recent_game_with_retry(team_id, player_id)
    highlights = await get_assist_highlights(game_data)
    return highlights


def get_most_recent_game_with_retry(team_id: str, player_id: str) -> Optional[GameData]:
    retries = 0
    game_data = None
    while retries < 5 and game_data is None:
        try:
            game_data = get_most_recent_game(team_id, player_id)
        except NoHighlightsFoundError as e:
            return None
        except Exception as e:
            print(
                f"Error getting most recent game: {type(e)} {e}, sleeping 60, retries: {retries}"
            )
            sleep(60)
            retries += 1
    return game_data


async def get_assist_highlights(game_data: GameData) -> List[VideoData]:
    video_datas = []
    for play_data in game_data.plays[:1]:
        retries = 0
        video_data = None
        while retries < 5 and video_data is None:
            try:
                video_data = await get_video_data(game_data.game_id, play_data.event_id)
                if video_data is not None:
                    video_datas.append(video_data)
                sleep(5)
            except Exception as e:
                print(
                    f"Error getting video data: {type(e)} {e}, sleeping 60, retries: {retries}"
                )
                sleep(60)
                retries += 1
    return video_datas


def get_most_recent_game(team_id: str, player_id: str) -> GameData:
    print("Getting most recent game")
    video = videodetails.VideoDetails(
        context_measure_detailed=ContextMeasureDetailed.ast,
        last_n_games=1,
        team_id=team_id,
        player_id=player_id,
    )
    data = video.get_normalized_dict()
    try:
        first_play = data["playlist"][0]
    except IndexError:
        raise NoHighlightsFoundError()
    game_id = first_play["gi"]
    month = int(first_play["m"])
    day = int(first_play["d"])
    year = int(first_play["y"])
    home_team = first_play["ha"]
    away_team = first_play["va"]
    game_date = date(year, month, day)
    plays = [
        PlayData(event_id=play["ei"], description=play["dsc"])
        for play in data["playlist"]
    ]
    print("Got most recent game")
    return GameData(
        game_id=game_id,
        game_date=game_date,
        home_team=home_team,
        away_team=away_team,
        plays=plays,
    )


def get_team_id(team_abbreviation: str) -> str:
    nba_teams = teams.get_teams()
    team = [team for team in nba_teams if team["abbreviation"] == team_abbreviation][0]
    return team["id"]


def get_player_id(player_name: str) -> str:
    nba_players = players.get_players()
    player = [player for player in nba_players if player["full_name"] == player_name][0]
    return player["id"]


async def get_video_data(game_id: str, event_id: int) -> Optional[VideoData]:
    print(f"Getting video data for event_id: {event_id}, game_id: {game_id}")
    headers = {
        "Host": "stats.nba.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "x-nba-stats-origin": "stats",
        "x-nba-stats-token": "true",
        "Connection": "keep-alive",
        "Referer": "https://stats.nba.com/",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
    }
    url = f"https://stats.nba.com/stats/videoeventsasset?GameEventID={event_id}&GameID={game_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as r:
            if r.status == 200:
                json = await r.json()
                video_urls = json["resultSets"]["Meta"]["videoUrls"]
                playlist = json["resultSets"]["playlist"]
                video_data = VideoData(
                    uri=video_urls[0]["lurl"], description=playlist[0]["dsc"]
                )
                print(
                    f"Success got video data for event_id: {event_id}, game_id: {game_id}"
                )
                return video_data
            else:
                print(
                    f"Error getting video data for event_id: {event_id}, game_id: {game_id}, error: {r}"
                )
                raise ValueError("Request status not 200")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
