import logging
import voluptuous as vol # Used for schema validation

from homeassistant import config_entries
from homeassistant.const import CONF_NAME # We'll still use CONF_NAME for the instance title
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector # Used for UI selectors in the schema

from .const import DOMAIN # Import your integration's domain

_LOGGER = logging.getLogger(__name__)

class NHLTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for My NHL Tracker integration."""

    VERSION = 1 # Keep version, increment if you change the schema later
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL # Indicates it polls a cloud service

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step of the configuration flow."""
        errors = {}

        # Check if an instance of this integration is already configured
        # This is common for integrations that track global data rather than per-device data.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            # If user_input exists, it means the form was submitted.
            # Perform any validation if necessary (none really needed for just a name)

            # Create a unique ID for the config entry.
            # For a single-instance integration, you can use the domain itself.
            unique_id = DOMAIN # This makes sure only one config entry can exist.
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured() # Abort if this unique_id is already configured

            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "NHL Game Tracker"), # Use user-provided name or default
                data={
                    CONF_NAME: user_input.get(CONF_NAME, "NHL Game Tracker"),
                    # No scan_interval or other user-chosen settings needed in data now
                },
            )

        # If user_input is None, it means the form needs to be displayed.
        data_schema = vol.Schema({
            vol.Required(
                CONF_NAME,
                default="NHL Game Tracker" # Default name for the integration instance in the UI
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
            ),
        })

        # Show the configuration form to the user
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "instructions": "This integration tracks NHL game data for the selected day via an input_datetime helper.",
                "note": "Configuration for the daily update time and specific games for notifications will be done via Home Assistant automations and the date helper."
            }
        )

    # Since there are no options to configure via the UI, you don't need a separate OptionsFlow class.
    # The async_get_options_flow method from __init__.py can also be removed if there are truly no options.
    # However, if you previously had one and don't remove the reference, it won't break things if the class is gone.