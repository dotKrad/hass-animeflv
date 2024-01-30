"""Sensor platform for animeflv."""
from __future__ import annotations

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN
from .coordinator import AnimeFlvDataUpdateCoordinator
from .entity import AnimeFlvEntity

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="animeflv",
        name="AnimeFlv Sensor",
        icon="mdi:clock",
    ),
)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    sensors = []
    for key in coordinator.data.keys():
        sensors.append(AnimeFlvSensor(coordinator=coordinator,animeKey=key))

    async_add_entities(sensors)

    @callback
    def async_add_sensor(info) -> None:
        print(info)

    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            f"{DOMAIN}_{config_entry.entry_id}_add_{DOMAIN}",
            async_add_sensor,
        )
    )


class AnimeFlvSensor(AnimeFlvEntity, SensorEntity):
    """integration_blueprint Sensor class."""

    def __init__(self, coordinator: AnimeFlvDataUpdateCoordinator, animeKey: str) -> None:
        """Initialize the sensor class."""
        self.anime = animeKey
        super().__init__(animeKey, coordinator)


    @property
    def unique_id(self):
        """Return the ID of this device."""
        sensorName = self.anime.lower().replace(" ", "")
        return f"{DOMAIN}_{self.coordinator.config_entry.title}_{sensorName}"

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        if self.coordinator.data.get(self.anime).get("progress") is not None:
            self._attr_native_value = self.coordinator.data.get(self.anime).get("progress")
        return self._attr_native_value

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.coordinator.data.get(self.anime) is None:
            return None

        attributes = {
            "episodesCount": self.coordinator.data.get(self.anime).get("episodesCount"),
            "lastSeen": self.coordinator.data.get(self.anime).get("lastSeen"),
            "inEmission": self.coordinator.data.get(self.anime).get("inEmission"),
            "nextEpisode": self.coordinator.data.get(self.anime).get("nextEpisode"),
            "today": self.coordinator.data.get(self.anime).get("today"),
            "nextToWatch": self.coordinator.data.get(self.anime).get("nextToWatch"),
            "description": self.coordinator.data.get(self.anime).get("description"),
            "cover": self.coordinator.data.get(self.anime).get("cover"),
            "title": self.coordinator.data.get(self.anime).get("title"),
        }
        return attributes