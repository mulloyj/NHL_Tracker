import discord
import os
from dotenv import load_dotenv
from api_utils import Game

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
TODAY_CHANNEL_ID = int(os.getenv('TODAYS_GAMES_CHANNEL_ID'))
SENS_CHANNEL_ID = int(os.getenv('SENS_GAMES_CHANNEL_ID'))

# Enable intents
intents = discord.Intents.default()
intents.messages = True  # Ensure message-related intents are enabled
intents.guilds = True  # Ensure guild-related intents are enabled


class MyClient(discord.Client):
    def __init__(self, action, channel_id: int, game: Game = None, games: list[Game] = None):
        super().__init__(intents=intents)  # Pass intents here
        self.channel_id = channel_id
        self.action = action
        self.game = game
        self.games = games

    async def on_ready(self):
        print(f'Logged in as {self.user}')

        match self.action:
            case "today":
                await self.todays_games()
            case "game":
                await self.period_start()
            case "sens_today":
                await self.sens_game_today()

        await self.close()

    async def todays_games(self):
        channel = self.get_channel(self.channel_id)
        if channel:
            print(f'Found channel: {channel.name}')
            todays_games = "Today's Games: \n"
            for game in self.games:
                todays_games += str(game)+'\n'

            await channel.send(todays_games)
        else:
            print(f'Channel with ID {TODAY_CHANNEL_ID} not found.')

    async def sens_game_today(self):
        channel = self.get_channel(self.channel_id)
        if channel:
            print(f'Found channel: {channel.name}')

            await channel.send(self.game)
        else:
            print(f'Channel with ID {self.channel_id} not found.')

    async def period_start(self):
        channel = self.get_channel(self.channel_id)
        if channel:
            print(f'Found channel: {channel.name}')

            await channel.send(str(self.game.period_starting()))
        else:
            print(f'Channel with ID {self.channel_id} not found.')
