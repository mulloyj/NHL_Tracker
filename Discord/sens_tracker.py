import asyncio
import os
from datetime import datetime, timedelta
import pytz

from nhl_discord import MyClient
from api_utils import Game, get_game, get_todays_games

TOKEN = os.getenv('DISCORD_TOKEN')
TODAY_CHANNEL_ID = int(os.getenv('TODAYS_GAMES_CHANNEL_ID'))
SENS_CHANNEL_ID = int(os.getenv('SENS_GAMES_CHANNEL_ID'))

test_id = 2024021230


async def wait_until(target_time):
    """
    Waits until the specified target time.
    :param target_time: A datetime object representing the target time.
    """
    now = datetime.now(pytz.timezone("US/Eastern"))
    wait_seconds = (target_time - now).total_seconds()
    if wait_seconds > 0:
        await asyncio.sleep(wait_seconds)


async def get_today():
    games: list[Game] = get_todays_games()
    async with MyClient("today", int(TODAY_CHANNEL_ID), games=games) as client:
        await client.start(TOKEN)

    for game in games:
        if game.away_team == "OTT" or game.home_team == "OTT":
            async with MyClient("sens_today", int(SENS_CHANNEL_ID), game=game) as client:
                await client.start(TOKEN)

            await period_tracker(game)


async def period_tracker(game: Game):
    """
    Waits until the game's start time in EST and performs actions.
    :param game: A Game object containing the start time in UTC.
    """
    # Parse the game's start time (UTC) 2025-04-03T23:00:00Z
    utc_time = datetime.strptime(game.start_time, "%Y-%m-%dT%H:%M:%SZ")
    utc_time = utc_time.replace(tzinfo=pytz.UTC)

    # Convert to EST
    est_time = utc_time.astimezone(pytz.timezone("US/Eastern"))

    # Wait until the game's start time in EST
    now = datetime.now(pytz.timezone("US/Eastern"))
    if est_time > now:
        await wait_until(est_time)

    game.period += 1

    async with MyClient("game", int(SENS_CHANNEL_ID), game=game) as client:
        await client.start(TOKEN)

    while True:
        print("Game Loop Started")
        await asyncio.sleep(25*60)

        game = get_game(game.id)

        while (game.game_state != "OFF" or game.game_state == "FINAL") and not game.inIntermission:
            await asyncio.sleep(15*60)
            game = get_game(game.id)

        if game.game_state == "OFF" or game.game_state == "FINAL":
            break

        await asyncio.sleep(game.secondsRemaining)
        game.period += 1

        async with MyClient("game", int(SENS_CHANNEL_ID), game=game) as client:
            await client.start(TOKEN)

asyncio.run(get_today())
