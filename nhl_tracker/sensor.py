import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.const import ATTR_ATTRIBUTION

from .const import DOMAIN  # Import constants
from .__init__ import NHLDataUpdateCoordinator  # Import coordinator
from .api_client import NHLAPIClient  # Import API client

_LOGGER = logging.getLogger(__name__)

ATTRIBUTION = "Data provided by the unofficial NHL API"


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Dynamically create sensors based on initial data
    # This list will be maintained by `async_update_arg` later
    current_game_sensors = {}

    @callback
    def async_update_coordinator_data():
        """Update entities when the coordinator updates."""
        # Get current entities managed by this integration
        current_entities = hass.states.async_entity_ids("sensor", DOMAIN)

        new_entities = []
        entities_to_remove = []

        # Check for new games and add sensors
        for game_id, game_data in coordinator.data.items():
            unique_id = f"nhl_game_{game_id}"
            # Consistent entity ID generation
            entity_id = generate_entity_id(
                "sensor.{}", f"{game_data['teams']['away']['team']['name']}_vs_{game_data['teams']['home']['team']['name']}_game", hass=hass)

            if unique_id not in current_game_sensors and entity_id not in current_entities:  # Check if sensor already exists
                _LOGGER.debug(f"Adding new NHL game sensor: {entity_id}")
                sensor = NHLGameSensor(coordinator, game_id, game_data)
                new_entities.append(sensor)
                # Keep track of created sensors
                current_game_sensors[unique_id] = sensor

        if new_entities:
            async_add_entities(new_entities)

        # Check for games that are no longer present and remove sensors
        # Iterate over a copy as we might modify
        for unique_id, sensor_obj in list(current_game_sensors.items()):
            if sensor_obj._game_id not in coordinator.data:
                _LOGGER.debug(
                    f"Removing NHL game sensor: {sensor_obj.entity_id}")
                entities_to_remove.append(sensor_obj)
                del current_game_sensors[unique_id]

        # This part is tricky. Directly removing entities is generally done via entity registry.
        # For dynamic removal, you'd usually mark them unavailable, or rely on HA's registry cleanup
        # This is simplified. Proper removal involves `async_remove()` on the entity and registry cleanup.
        # For now, if a game disappears, its sensor might remain but become unavailable if it relies on _game_data from coord.data.
        # More robust removal would involve `async_remove_entities` on the ConfigEntry.

    # Listen for coordinator updates to add/remove sensors
    coordinator.async_add_listener(async_update_coordinator_data)

    # Initial sensor setup based on initial data
    async_update_coordinator_data()  # Call once at startu


class NHLGameSensor(CoordinatorEntity, SensorEntity):
    """Representation of an NHL game sensor."""

    def __init__(self, coordinator: NHLDataUpdateCoordinator, game_id: int, initial_game_data: dict):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._game_id = game_id
        # This will hold the entire game object from the API
        self._game_data = initial_game_data

        # New way to get team names and generate entity ID:
        away_name = self._game_data.get('awayTeam', {}).get(
            'commonName', {}).get('default', 'Unknown Away')
        home_name = self._game_data.get('homeTeam', {}).get(
            'commonName', {}).get('default', 'Unknown Home')

        self._attr_name = f"{away_name} vs {home_name} Game"
        self._attr_unique_id = f"nhl_game_{game_id}"
        self.entity_id = generate_entity_id(
            "sensor.{}", self._attr_name, hass=coordinator.hass)

    @property
    def native_value(self):
        """Return the state of the sensor (e.g., game state like 'OFF', 'LIVE', 'PRE')."""
        return self._game_data.get('gameState', 'UNKNOWN')  # Use 'gameState' now

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "game_id": self._game_id,
            "season": self._game_data.get('season'),
            # You might map this to a string like 'Regular Season', 'Playoff'
            "game_type": self._game_data.get('gameType'),
            # Access 'default' property
            "venue": self._game_data.get('venue', {}).get('default'),

            # Team information - updated paths
            "away_team_name": self._game_data.get('awayTeam', {}).get('commonName', {}).get('default'),
            "away_team_place": self._game_data.get('awayTeam', {}).get('placeName', {}).get('default'),
            "away_team_abbrev": self._game_data.get('awayTeam', {}).get('abbrev'),
            "away_score": self._game_data.get('awayTeam', {}).get('score'),

            "home_team_name": self._game_data.get('homeTeam', {}).get('commonName', {}).get('default'),
            "home_team_place": self._game_data.get('homeTeam', {}).get('placeName', {}).get('default'),
            "home_team_abbrev": self._game_data.get('homeTeam', {}).get('abbrev'),
            "home_score": self._game_data.get('homeTeam', {}).get('score'),

            # Game State and Period Information - updated paths
            # Full game state (PRE, LIVE, OFF)
            "game_state": self._game_data.get('gameState'),
            # OK, POSTPONED, etc.
            "game_schedule_state": self._game_data.get('gameScheduleState'),
            "current_period": self._game_data.get('periodDescriptor', {}).get('number'),
            # REG, OT, SO
            "period_type": self._game_data.get('periodDescriptor', {}).get('periodType'),

            # Time information
            "start_time_utc": self._game_data.get('startTimeUTC'),
            "eastern_utc_offset": self._game_data.get('easternUTCOffset'),
            "venue_utc_offset": self._game_data.get('venueUTCOffset'),
            "venue_timezone": self._game_data.get('venueTimezone'),

            # New attributes from the v2 API
            "winning_goalie_id": self._game_data.get('winningGoalie', {}).get('playerId'),
            "winning_goalie_name": f"{self._game_data.get('winningGoalie', {}).get('firstInitial', {}).get('default', '')} {self._game_data.get('winningGoalie', {}).get('lastName', {}).get('default', '')}".strip() if self._game_data.get('winningGoalie') else None,
            "winning_goal_scorer_id": self._game_data.get('winningGoalScorer', {}).get('playerId'),
            "winning_goal_scorer_name": f"{self._game_data.get('winningGoalScorer', {}).get('firstInitial', {}).get('default', '')} {self._game_data.get('winningGoalScorer', {}).get('lastName', {}).get('default', '')}".strip() if self._game_data.get('winningGoalScorer') else None,

            # Series Status (Playoffs)
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

            # TV Broadcasts (list of dictionaries, might need more complex parsing if you want a specific network)
            # For simplicity, let's just get the first US and first CA national network found
            "tv_broadcasts_us": ", ".join([b.get('network') for b in self._game_data.get('tvBroadcasts', []) if b.get('countryCode') == 'US' and b.get('market') == 'N']),
            "tv_broadcasts_ca": ", ".join([b.get('network') for b in self._game_data.get('tvBroadcasts', []) if b.get('countryCode') == 'CA' and b.get('market') == 'N']),

            # Links to recap/condensed game (these are relative paths, you'd need to prepend the NHL.com base URL)
            "three_min_recap_link": self._game_data.get('threeMinRecap'),
            "condensed_game_link": self._game_data.get('condensedGame'),
            # This is also a relative URL
            "game_center_link": self._game_data.get('gameCenterLink'),
        }

        # Current period time remaining is NOT in the schedule endpoint data.
        # It would only be available from the 'game_feed' endpoint when the game is LIVE.
        # You'll need to check the structure returned by game_feed and potentially update
        # this attribute within the `async_update` method if `self._game_data` is being
        # fully overwritten or augmented with live_details.
        # For now, if the _game_data is only from the schedule, this will be None.
        # Assuming liveData is merged in async_update
        if self.native_value == "LIVE" and self._game_data.get("liveData"):
            attrs["current_period_time_remaining"] = self._game_data.get(
                "liveData", {}).get("linescore", {}).get("currentPeriodTimeRemaining")

        return attrs

    async def async_update(self):
        """Update the sensor. This is called by the coordinator."""
        # The coordinator's _async_update_data will have already fetched the daily schedule
        # We just need to update our internal _game_data from the coordinator's data

        # If the game_id is no longer in coordinator.data (e.g., date changed, game finished/disappeared)
        # then mark this specific sensor as unavailable.
        if self._game_id not in self.coordinator.data:
            self._game_data = None  # Or some indicator of being gone
            self._attr_available = False  # Mark as unavailable
            _LOGGER.debug(
                f"Game {self._game_id} not found in coordinator data, marking {self.entity_id} unavailable.")
            return

        self._game_data = self.coordinator.data.get(
            self._game_id, self._game_data)
        self._attr_available = True

        # IF the game is LIVE, we want to fetch the full game_feed for real-time updates
        if self._game_data and self._game_data.get("gameState") == "LIVE":
            try:
                _LOGGER.debug(
                    f"Fetching live details for game {self._game_id} using nhlpy.")
                live_details = await self.coordinator.api_client.get_game_details(self._game_id)

                # The 'game_feed' endpoint (what nhlpy.game_feed returns) provides a lot more detail.
                # It contains a top-level 'gameData' and 'liveData' key.
                # For `extra_state_attributes` to have the most current values, you should merge or update
                # `self._game_data` with the relevant parts from `live_details`.

                # A simple approach: Overwrite _game_data with the more comprehensive live_details.
                # This assumes 'live_details' contains all fields from the initial schedule data plus live fields.
                # From your example, the schedule data has top-level keys like 'id', 'season', 'venue', 'awayTeam', etc.
                # The game_feed also has these. So, merging or replacing is usually fine.
                # Merge the new data into the existing _game_data
                self._game_data.update(live_details)

                # If you want more granular control, you could do:
                # self._game_data['liveData'] = live_details.get('liveData', {})
                # self._game_data['gameData'] = live_details.get('gameData', {}) # (If gameData is also updated)
                # self._game_data['linescore'] = live_details.get('liveData', {}).get('linescore', {})
                # This would allow you to be more selective, but updating the entire dict is often simpler.

            except Exception as e:
                _LOGGER.warning(
                    f"Failed to fetch live details for game {self._game_id} using nhlpy: {e}")

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        # Customize icon based on game state (using 'gameState')
        if self.native_value == "LIVE":
            return "mdi:hockey-sticks"
        elif self.native_value == "PRE":  # Or 'FUT' for Future
            return "mdi:timer-sand"
        elif self.native_value == "OFF":  # Official/Final
            return "mdi:hockey-puck"
        else:
            return "mdi:hockey-puck"  # Default icon

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self._game_data is not None
