import logging
import asyncio
from datetime import datetime, timezone, timedelta

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, LIVE_GAME_POLL_INTERVAL_SECONDS
from .__init__ import NHLDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by the NHL API (v2)"


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):  # Pass hass
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    current_game_sensors = {}

    @callback
    def async_update_coordinator_data():
        """Update entities when the coordinator updates."""
        new_entities = []
        for game_id, game_data in coordinator.data.items():
            unique_id = f"nhl_game_{game_id}"
            if unique_id not in current_game_sensors:
                _LOGGER.debug(f"Adding new NHL game sensor: {game_id}")
                sensor = NHLGameSensor(
                    hass, coordinator, game_id, game_data)  # Pass hass
                new_entities.append(sensor)
                current_game_sensors[unique_id] = sensor
        if new_entities:
            async_add_entities(new_entities)

        entities_to_remove = []
        for unique_id, sensor_obj in list(current_game_sensors.items()):
            if sensor_obj._game_id not in coordinator.data:
                _LOGGER.debug(
                    f"Removing NHL game sensor: {sensor_obj.entity_id}")
                entities_to_remove.append(sensor_obj.entity_id)
                sensor_obj.async_will_remove_from_hass()
                del current_game_sensors[unique_id]
            else:
                sensor_obj._game_data = coordinator.data[sensor_obj._game_id]
                sensor_obj.async_schedule_update_ha_state(True)

        if entities_to_remove:
            pass

    coordinator.async_add_listener(async_update_coordinator_data)
    async_update_coordinator_data()


class NHLGameSensor(CoordinatorEntity, SensorEntity):
    """Representation of an NHL game sensor."""

    def __init__(self, hass: HomeAssistant, coordinator: NHLDataUpdateCoordinator, game_id: int, initial_game_data: dict):  # Pass hass
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.hass = hass  # Store hass
        self._game_id = game_id
        self._game_data = initial_game_data
        self._live_update_task: asyncio.Task | None = None

        away_name = self._game_data.get('awayTeam', {}).get(
            'commonName', {}).get('default', 'Unknown Away')
        home_name = self._game_data.get('homeTeam', {}).get(
            'commonName', {}).get('default', 'Unknown Home')

        self._attr_name = f"{away_name} vs {home_name} Game"
        self._attr_unique_id = f"nhl_game_{game_id}"
        self.entity_id = generate_entity_id(
            "sensor.{}", self._attr_name, hass=coordinator.hass)
        self._attr_available = True

        # Schedule live polling start
        self.async_on_remove(self.hass.async_create_task(
            self._async_schedule_live_polling()))

    async def _async_schedule_live_polling(self):
        """Schedule live polling to start at the game's start time."""
        start_time_utc_str = self._game_data.get('startTimeUTC')
        if not start_time_utc_str:
            _LOGGER.warning(
                f"No startTimeUTC found for game {self.entity_id}.  Starting live polling immediately.")
            await self._start_live_game_polling()  # Start immediately if no start time
            return

        try:
            start_time_utc = datetime.fromisoformat(
                # Ensure UTC timezone
                start_time_utc_str.replace('Z', '+00:00'))
            local_timezone = self.hass.config.time_zone  # Get Home Assistant's timezone
            start_time_local = start_time_utc.astimezone(
                local_timezone)  # Convert to local time

            # Current time in local timezone
            now_local = datetime.now(local_timezone)
            time_until_start = (start_time_local - now_local).total_seconds()

            if time_until_start > 0:
                _LOGGER.debug(
                    f"Game {self.entity_id} starts in {time_until_start:.0f} seconds. Scheduling live polling.")
                await asyncio.sleep(time_until_start)  # Wait until start time
                await self._start_live_game_polling()
            else:
                _LOGGER.debug(
                    f"Game {self.entity_id} already started. Starting live polling immediately.")
                await self._start_live_game_polling()
        except ValueError as e:
            _LOGGER.warning(
                f"Invalid startTimeUTC format for game {self.entity_id}: {start_time_utc_str}. Starting live polling immediately. Error: {e}")
            await self._start_live_game_polling()  # Start immediately on error
        except Exception as e:
            _LOGGER.exception(
                f"Error scheduling live polling for {self.entity_id}: {e}")
            await self._start_live_game_polling()  # Start immediately on error

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._game_data.get('gameState', 'UNKNOWN')

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "game_id": self._game_id,
            "season": self._game_data.get('season'),
            "game_type": self._game_data.get('gameType'),
            "venue": self._game_data.get('venue', {}).get('default'),

            "away_team_name": self._game_data.get('awayTeam', {}).get('commonName', {}).get('default'),
            "away_team_place": self._game_data.get('awayTeam', {}).get('placeName', {}).get('default'),
            "away_team_abbrev": self._game_data.get('awayTeam', {}).get('abbrev'),
            "away_score": self._game_data.get('awayTeam', {}).get('score'),

            "home_team_name": self._game_data.get('homeTeam', {}).get('commonName', {}).get('default'),
            "home_team_place": self._game_data.get('homeTeam', {}).get('placeName', {}).get('default'),
            "home_team_abbrev": self._game_data.get('homeTeam', {}).get('abbrev'),
            "home_score": self._game_data.get('homeTeam', {}).get('score'),

            "game_state": self._game_data.get('gameState'),
            "game_schedule_state": self._game_data.get('gameScheduleState'),
            "current_period": self._game_data.get('periodDescriptor', {}).get('number'),
            "period_type": self._game_data.get('periodDescriptor', {}).get('periodType'),

            "start_time_utc": self._game_data.get('startTimeUTC'),
            "eastern_utc_offset": self._game_data.get('easternUTCOffset'),
            "venue_utc_offset": self._game_data.get('venueUTCOffset'),
            "venue_timezone": self._game_data.get('venueTimezone'),

            "winning_goalie_id": self._game_data.get('winningGoalie', {}).get('playerId'),
            "winning_goalie_name": f"{self._game_data.get('winningGoalie', {}).get('firstInitial', {}).get('default', '')} {self._game_data.get('winningGoalie', {}).get('lastName', {}).get('default', '')}".strip() if self._game_data.get('winningGoalie') else None,
            "winning_goal_scorer_id": self._game_data.get('winningGoalScorer', {}).get('playerId'),
            "winning_goal_scorer_name": f"{self._game_data.get('winningGoalScorer', {}).get('firstInitial', {}).get('default', '')} {self._game_data.get('winningGoalScorer', {}).get('lastName', {}).get('default', '')}".strip() if self._game_data.get('winningGoalScorer') else None,

            "series_round": self._game_data.get('seriesStatus', {}).get('round'),
            "series_abbreviation": self._game_data.get('seriesStatus', {}).get('seriesAbbrev'),
            "series_title": self._game_data.get('seriesStatus', {}).get('seriesTitle'),
            "series_needed_to_win": self._game_data.get('seriesStatus', {}).get('neededToWin'),
            "top_seed_team_abbrev": self._game_data.get('seriesStatus', {}).get('topSeedTeamAbbrev'),
            "top_seed_wins": self._game_data.get('seriesStatus', {}).get('topSeedWins'),
            "bottom_seed_team_abbrev": self._game_data.get('seriesStatus', {}).get('bottomSeedTeamAbbrev'),
            "bottom_seed_wins": self._game_data.get('seriesStatus', {}).get('bottomSeedWins'),
            "game_number_of_series": self._game_data.get('seriesStatus', {}).get('gameNumberOfSeries'),
            "series_url": self._game_data.get('seriesUrl'),

            "tv_broadcasts_us": ", ".join([b.get('network') for b in self._game_data.get('tvBroadcasts', []) if b.get('countryCode') == 'US' and b.get('market') == 'N']),
            "tv_broadcasts_ca": ", ".join([b.get('network') for b in self._game_data.get('tvBroadcasts', []) if b.get('countryCode') == 'CA' and b.get('market') == 'N']),

            "three_min_recap_link": self._game_data.get('threeMinRecap'),
            "condensed_game_link": self._game_data.get('condensedGame'),
            "game_center_link": self._game_data.get('gameCenterLink'),

            # This attribute will be populated ONLY when the game is LIVE and game_feed is fetched
            "current_period_time_remaining": self._game_data.get("liveData", {}).get("linescore", {}).get("currentPeriodTimeRemaining")
        }
        return attrs

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to Home Assistant."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()
        self.async_on_remove(self.coordinator.async_add_listener(
            self._handle_coordinator_update))

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from Home Assistant."""
        self._stop_live_game_polling()
        await super().async_will_remove_from_hass()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        updated_game_data = self.coordinator.data.get(self._game_id)

        if updated_game_data is None:
            self._attr_available = False
            self._game_data = {}
            self._stop_live_game_polling()
            self.async_write_ha_state()
            return

        old_game_state = self._game_data.get("gameState")
        new_game_state = updated_game_data.get("gameState")

        self._game_data = updated_game_data
        self._attr_available = True

        # No need to start live polling here.  It's started in __init__ at the scheduled time.
        # Only stop it if the game transitions away from LIVE
        if new_game_state != "LIVE" and self._live_update_task:
            _LOGGER.debug(
                f"Game {self.entity_id} transitioned away from LIVE. Stopping live polling.")
            self._stop_live_game_polling()

        self.async_write_ha_state()

    async def _start_live_game_polling(self) -> None:
        """Start an asyncio task to poll for live game details."""
        if self._live_update_task:
            self._stop_live_game_polling()

        async def _poll_live_game_data():
            _LOGGER.debug(f"Starting live polling loop for {self.entity_id}")
            while True:
                try:
                    live_details = await self.coordinator.api_client.get_game_details(self._game_id)
                    self._game_data.update(live_details)
                    self.async_write_ha_state()
                    _LOGGER.debug(
                        f"Updated live data for {self.entity_id}: {self._game_data.get('awayTeam', {}).get('score')} - {self._game_data.get('homeTeam', {}).get('score')}")

                except asyncio.CancelledError:
                    _LOGGER.debug(
                        f"Live polling for {self.entity_id} was cancelled.")
                    break
                except Exception as e:
                    _LOGGER.exception(
                        f"Unhandled exception during live polling for {self.entity_id}: {e}")

                await asyncio.sleep(LIVE_GAME_POLL_INTERVAL_SECONDS)

        self._live_update_task = self.hass.async_create_task(
            _poll_live_game_data())
        self.async_on_remove(lambda: self._live_update_task.cancel())

    @callback
    def _stop_live_game_polling(self) -> None:
        """Stop the asyncio task for live game polling."""
        if self._live_update_task:
            self._live_update_task.cancel()
            self._live_update_task = None
            _LOGGER.debug(f"Stopped live polling for {self.entity_id}.")

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        if self.native_value == "LIVE":
            return "mdi:hockey-sticks"
        elif self.native_value == "PRE":
            return "mdi:timer-sand"
        elif self.native_value == "OFF":
            return "mdi:hockey-puck"
        return "mdi:hockey-puck"
