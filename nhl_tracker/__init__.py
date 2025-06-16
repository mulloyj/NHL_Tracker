import logging
from datetime import timedelta, datetime
import async_timeout
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN
from .api_client import NHLAPIClient

_LOGGER = logging.getLogger(__name__)

DATE_SELECTOR_ENTITY_ID = "input_datetime.nhl_game_date_selector"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):  # Pass hass
    """Set up My NHL Tracker from a config entry."""
    scan_interval_minutes = entry.data.get(CONF_SCAN_INTERVAL, 5)

    coordinator = NHLDataUpdateCoordinator(
        hass,  # Pass hass
        entry,
        timedelta(minutes=scan_interval_minutes)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(
            hass, entry, "sensor")  # Pass hass
    )

    @callback
    def _date_selector_changed(event):
        """Handle date selector state changes."""
        _LOGGER.debug(
            f"Date selector {DATE_SELECTOR_ENTITY_ID} changed, refreshing NHL schedule data.")
        coordinator.async_request_refresh()

    entry.async_on_unload(
        async_track_state_change_event(
            hass,
            DATE_SELECTOR_ENTITY_ID,
            _date_selector_changed
        )
    )

    entry.add_update_listener(async_reload_entry)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_forward_entry_unload(entry, "sensor")
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


class NHLDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages fetching NHL schedule data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, update_interval: timedelta):  # Pass hass
        """Initialize data updater."""
        self.hass = hass
        self.entry = entry
        self.api_client = NHLAPIClient(hass)
        self.tracked_games = {}

        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch daily NHL schedule data."""
        try:
            async with async_timeout.timeout(30):
                date_state = self.hass.states.get(DATE_SELECTOR_ENTITY_ID)
                if not date_state or date_state.state == "unknown":
                    _LOGGER.warning(
                        f"Date selector {DATE_SELECTOR_ENTITY_ID} not available or unknown, defaulting to today.")
                    target_date = self.hass.config.time_zone.localize(
                        datetime.now()).date()
                else:
                    try:
                        target_date = datetime.strptime(
                            date_state.state, "%Y-%m-%d").date()
                    except ValueError:
                        _LOGGER.error(
                            f"Invalid date format from {DATE_SELECTOR_ENTITY_ID}: {date_state.state}, defaulting to today.")
                        target_date = self.hass.config.time_zone.localize(
                            datetime.now()).date()

                target_date_str = target_date.strftime("%Y-%m-%d")
                _LOGGER.info(
                    f"Fetching NHL schedule for date: {target_date_str}")

                schedule_data = await self.api_client.get_schedule(target_date_str)

                games_for_day = {}
                if schedule_data and schedule_data.get("dates"):
                    for date_entry in schedule_data["dates"]:
                        if date_entry.get("date") == target_date_str:
                            for game in date_entry.get("games", []):
                                game_id = game["gamePk"]
                                games_for_day[game_id] = game

                if not games_for_day:
                    _LOGGER.info(f"No NHL games found for {target_date_str}.")

                return games_for_day

        except Exception as err:
            _LOGGER.exception("Unexpected error during NHL data update")
            raise UpdateFailed(
                f"Unexpected error updating daily NHL schedule: {err}") from err
