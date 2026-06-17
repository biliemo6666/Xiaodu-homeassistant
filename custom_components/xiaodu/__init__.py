import asyncio
import logging

from homeassistant import core, config_entries
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .ApplianceTypes import ApplianceTypes
from .api import XiaoDuAPI
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.FAN,
    Platform.COVER,
    Platform.CLIMATE,
    Platform.BUTTON,
    Platform.LOCK,
]


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    return True


async def async_setup_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {}
    session = async_get_clientsession(hass)
    
    # 检查配置数据是否完整
    if "applianceTypes" not in entry.data or "devices" not in entry.data:
        _LOGGER.error("配置数据不完整，请删除集成后重新添加")
        return False
    
    applianceTypes = entry.data["applianceTypes"]
    for i, device_info in enumerate(entry.data["devices"]):
        applianceId = device_info["applianceId"]
        houseId = device_info["houseId"]
        cookie = device_info["cookie"]
        hass.data[DOMAIN][entry.entry_id][applianceId] = XiaoDuAPI(
            applianceId=applianceId,
            houseId=houseId,
            cookie=cookie,
            session=session,
            applianceTypes=applianceTypes[i]['applianceTypes']
        )
    if not entry.update_listeners:
        entry.add_update_listener(async_update_options)

    await hass.config_entries.async_forward_entry_setups(
        entry, PLATFORMS
    )

    return True


async def async_unload_entry(hass: core.HomeAssistant, entry: config_entries.ConfigEntry) -> bool:
    _LOGGER.info("卸载")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_update_options(hass: core.HomeAssistant, entry: config_entries.ConfigEntry):
    entry1 = {**entry.data, **entry.options}
    _LOGGER.info("更新:%s", entry1)
    await hass.config_entries.async_reload(entry.entry_id)
