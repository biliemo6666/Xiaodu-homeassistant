"""Support for Xiaodu media players."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import XiaoduApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Xiaodu media player from a config entry."""
    api: XiaoduApiClient = hass.data[DOMAIN][entry.entry_id]
    devices = await api.get_device_list()
    
    entities = []
    for device in devices:
        entities.append(XiaoduMediaPlayer(api, device))
    
    async_add_entities(entities)


class XiaoduMediaPlayer(MediaPlayerEntity):
    """Representation of a Xiaodu Media Player."""

    _attr_has_entity_name = True
    _attr_media_content_type = MediaType.MUSIC
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY
        | MediaPlayerEntityFeature.PAUSE
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, api: XiaoduApiClient, device: dict[str, Any]) -> None:
        """Initialize the media player."""
        self._api = api
        self._device = device
        self._device_id = device.get("deviceId")
        self._attr_unique_id = self._device_id
        self._attr_name = device.get("deviceName", "小度")
        self._state = MediaPlayerState.IDLE
        self._volume = 50
        self._media_title = None
        self._media_artist = None

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        return self._state

    @property
    def volume_level(self) -> float:
        """Return the volume level."""
        return self._volume / 100.0

    @property
    def media_title(self) -> str | None:
        """Return the title of the current media."""
        return self._media_title

    @property
    def media_artist(self) -> str | None:
        """Return the artist of the current media."""
        return self._media_artist

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level."""
        volume_int = int(volume * 100)
        await self._api.set_volume(self._device_id, volume_int)
        self._volume = volume_int
        self.async_write_ha_state()

    async def async_media_play(self) -> None:
        """Send play command."""
        await self._api.player_control(self._device_id, "play")
        self._state = MediaPlayerState.PLAYING
        self.async_write_ha_state()

    async def async_media_pause(self) -> None:
        """Send pause command."""
        await self._api.player_control(self._device_id, "pause")
        self._state = MediaPlayerState.PAUSED
        self.async_write_ha_state()

    async def async_media_stop(self) -> None:
        """Send stop command."""
        await self._api.player_control(self._device_id, "stop")
        self._state = MediaPlayerState.IDLE
        self.async_write_ha_state()

    async def async_play_media(
        self, media_type: str, media_id: str, **kwargs: Any
    ) -> None:
        """Play media via TTS or URL."""
        if media_type == MediaType.MUSIC:
            await self._api.player_control(self._device_id, f"play:{media_id}")
            self._state = MediaPlayerState.PLAYING
            self.async_write_ha_state()
        else:
            await self._api.send_tts(self._device_id, media_id)

    async def async_update(self) -> None:
        """Update the media player state."""
        pass
