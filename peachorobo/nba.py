from dataclasses import dataclass
from datetime import date
from typing import List

import requests
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


def main():
    team_abbreviation = "DEN"
    player_name = "Nikola Jokic"
    game_data = get_most_recent_game(team_abbreviation, player_name)
    # video_uris = [
    #     get_video_data(game_id, play_data.event_id) for play_data in game_data.plays
    # ]
    play_descriptions = [play.description for play in game_data.plays]
    game_description = (
        f"{game_data.home_team} vs {game_data.away_team} on "
        f"{game_data.game_date.strftime('%A')} {game_data.game_date}"
    )
    return game_data


def get_most_recent_game(team_abbreviation: str, player_name: str) -> GameData:
    team_id = get_team_id(team_abbreviation)
    player_id = get_player_id(player_name)
    video = videodetails.VideoDetails(
        context_measure_detailed=ContextMeasureDetailed.ast,
        last_n_games=1,
        team_id=team_id,
        player_id=player_id,
    )
    data = video.get_normalized_dict()
    first_play = data["playlist"][0]
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


def get_video_data(game_id: str, event_id: int) -> VideoData:
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
    r = requests.get(url, headers=headers)
    json = r.json()
    video_urls = json["resultSets"]["Meta"]["videoUrls"]
    playlist = json["resultSets"]["playlist"]
    video_data = VideoData(uri=video_urls[0]["lurl"], description=playlist[0]["desc"])
    return video_data


if __name__ == "__main__":
    main()
