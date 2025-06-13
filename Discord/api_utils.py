import requests
from datetime import datetime

from utils import time_to_EST

NHL_API = "https://api-web.nhle.com/v1"


class Game:
    def __init__(self, away_team, home_team, start_time, game_id, home_score=0, away_score=0, period=0, inIntermission=False, secondsRemaining=0, game_state="FUT"):
        self.away_team = away_team
        self.home_team = home_team
        self.start_time = start_time
        self.id = game_id
        self.home_score = home_score
        self.away_score = away_score
        self.period = period
        self.inIntermission = inIntermission
        self.secondsRemaining = secondsRemaining
        self.game_state = game_state

    def __str__(self):
        start = time_to_EST(self.start_time)
        return f"{self.away_team} @ {self.home_team} at {start}"

    def period_starting(self):
        if self.period == 1:
            return f"{self.away_team} @ {self.home_team} starting soon"
        return f"{self.away_team} @ {self.home_team} period {self.period} starting soon ({self.away_team} {self.away_score}-{self.home_score} {self.home_team})"


def get_todays_games():
    """
    Fetches today's NHL games and their start times in EST.
    Returns a list of strings with game information, as well as a dictionary of games and their id.
    """
    YYYY_MM_DD = datetime.now().strftime(
        '%Y-%m-%d')  # Get today's date in YYYY-MM-DD format

    # NHL API endpoint for today's games
    todays_games = requests.get(
        f'{NHL_API}/score/{YYYY_MM_DD}')

    todays_games = todays_games.json()

    # Extract the 'games' key from the JSON response
    todays_games = todays_games['games']

    # Loop through the games and list them with their start times in EST
    games = []
    for game in todays_games:
        start_time = game['startTimeUTC']

        games.append(Game(game['awayTeam']['abbrev'],
                          game['homeTeam']['abbrev'], start_time, game['id']))
    return games


def get_games_by_date(date):
    """
    Fetches NHL games for a specific date and returns a list of Game objects.
    Args:
        date (str): The date in 'YYYY-MM-DD' format.
    """
    # NHL API endpoint for games on a specific date
    games_by_date = requests.get(
        f'{NHL_API}/score/{date}')

    games_by_date = games_by_date.json()

    # Extract the 'games' key from the JSON response
    games_by_date = games_by_date['games']

    # Loop through the games and create Game objects
    games = []
    for game in games_by_date:
        start_time = game['startTimeUTC']
        games.append(Game(game['awayTeam']['abbrev'],
                          game['homeTeam']['abbrev'], start_time, game['id']))
    return games


def get_game(game_id):
    """
    Fetches the current game information from the NHL API.
    Returns a list of strings with game information.
    """
    # NHL API endpoint for current game info
    game_data = requests.get(
        f'{NHL_API}/gamecenter/{game_id}/landing')

    game_data = game_data.json()

    if game_data['gameState'] == "PRE" or game_data['gameState'] == "FUT":
        return Game(game_id=game_id,
                    away_team=game_data['awayTeam']['abbrev'],
                    away_score=0,
                    home_team=game_data['homeTeam']['abbrev'],
                    home_score=0,
                    period=0,
                    secondsRemaining=0,
                    inIntermission=False,
                    game_state=game_data['gameState'],
                    start_time=game_data['startTimeUTC'])

    return Game(game_id=game_id,
                away_team=game_data['awayTeam']['abbrev'],
                away_score=game_data['awayTeam']['score'],
                home_team=game_data['homeTeam']['abbrev'],
                home_score=game_data['homeTeam']['score'],
                period=game_data['periodDescriptor']['number'],
                secondsRemaining=game_data['clock']['secondsRemaining'],
                inIntermission=game_data['clock']['inIntermission'],
                game_state=game_data['gameState'],
                start_time=game_data['startTimeUTC'])
