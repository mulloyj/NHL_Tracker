import logging
from nhlpy import NHLClient  # Import the NHLClient

_LOGGER = logging.getLogger(__name__)


class NHLAPIClient:
    """Client for fetching NHL data using nhl-api-py."""

    def __init__(self, hass):
        """Initialize the client."""
        self.hass = hass
        # Initialize NHLClient. nhlpy handles the underlying HTTP client.
        # You might consider making verbose configurable if you want detailed logs from nhlpy
        self._nhl_client = NHLClient(timeout=10, verbose=False)

    async def get_schedule(self, date_str: str):
        """Fetch the daily NHL schedule."""
        try:
            # nhlpy's schedule endpoint takes a datetime object or date string
            # It returns the raw JSON structure from the NHL API.
            schedule_data = await self.hass.async_add_executor_job(
                self._nhl_client.schedule, date_str
            )
            return schedule_data
        except Exception as err:
            _LOGGER.error(
                f"Error fetching NHL schedule for {date_str} using nhlpyr: {err}")
            raise  # Re-raise to be caught by DataUpdateCoordinator

    async def get_game_details(self, game_id: int):
        """Fetch detailed live data for a specific game."""
        try:
            # nhlpy's game_feed endpoint takes the gamePk
            game_details_data = await self.hass.async_add_executor_job(
                self._nhl_client.game_feed, game_id
            )
            return game_details_data
        except Exception as err:
            _LOGGER.error(
                f"Error fetching game details for {game_id} using nhlpy: {err}")
            raise  # Re-raise to be caught by DataUpdateCoordinator

    # Add other nhlpy methods if needed, e.g., get_team_roster, get_standings etc.
    # Check nhlpy documentation for available methods.
    # Example:
    # async def get_standings(self, date_str: str):
    #     try:
    #         standings_data = await self.hass.async_add_executor_job(
    #             self._nhl_client.standings, date_str
    #         )
    #         return standings_data
    #     except NHLPyError as e:
    #         _LOGGER.error(f"Error fetching standings for {date_str} using nhlpy: {e}")
    #         raise
