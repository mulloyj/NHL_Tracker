import logging
from datetime import timedelta, datetime
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_SCAN_INTERVAL

from .const import DOMAIN  # Import your constants
from .api_client import NHLAPIClient  # Import your API client class

_LOGGER = logging.getLogger(__name__)

# Default scan interval (e.g., 5 minutes for schedule, faster for live games)
DEFAULT_SCHEDULE_SCAN_INTERVAL = timedelta(HOURS=24)
DEFAULT_LIVE_SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up My NHL Tracker from a config entry."""
    coordinator = NHLDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()  # Initial data fetch

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up sensor platform
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(
        entry, "sensor"
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class NHLDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        """Initialize data updater."""
        self.hass = hass
        self.api_client = NHLAPIClient(hass)  # <--- USE THE IMPORTED CLIENT
        self.tracked_games = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCHEDULE_SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch data from NHL API."""
        try:
            async with async_timeout.timeout(30):
                date_state = self.hass.states.get(
                    "input_datetime.nhl_tracker_date")

                target_date = None
                if not date_state or date_state.state == "unknown":
                    _LOGGER.warning(
                        f"Date selector input_datetime.nhl_tracker_date not available or unknown, defaulting to today.")
                    target_date = self.hass.config.time_zone.localize(
                        datetime.now()).date()
                else:
                    # Input datetime state is usually 'YYYY-MM-DD' string
                    try:
                        target_date = datetime.strptime(
                            date_state.state, "%Y-%m-%d").date()
                    except ValueError:
                        _LOGGER.error(
                            f"Invalid date format from input_datetime.nhl_tracker_date: {date_state.state}, defaulting to today.")
                        target_date = self.hass.config.time_zone.localize(
                            datetime.now()).date()

                # Fetch schedule
                date_str = target_date.strftime("%Y-%m-%d")
                schedule_data = await self.api_client.get_schedule(date_str)

                # Process schedule to get games.
                # You might want to filter for games that are 'LIVE' or 'PRE'
                games = {}
                if schedule_data:
                    for game in schedule_data["games"]:
                        game_id = game["id"]
                        # PRE, LIVE, FINAL
                        game_status = game["gameState"]

                        # For 'LIVE' games, you might want more frequent updates
                        if game_status == "LIVE" or game_status == "PRE":
                            # Fetch detailed live game data if needed, or store basic schedule info
                            # For simplicity, let's just store the game object for now
                            games[game_id] = game

                # You could also add logic here to fetch detailed data for "tracked" teams if configured
                # Or, the sensor platform itself can request detailed data for *its* specific game.

                # Return the data to be stored by the coordinator
                return games  # This dictionary will be available to your sensors

        except UpdateFailed:  # Catch the specific UpdateFailed from coordinator
            raise
        except Exception as err:
            # Catch other potential errors from nhlpy or general processing
            _LOGGER.exception("Unexpected error during NHL data update")
            raise UpdateFailed(
                f"Unexpected error updating NHL data: {err}") from err
