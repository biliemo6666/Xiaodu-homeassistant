import logging

from homeassistant import core
from .const import DOMAIN
from . import XiaoDuAPI, ApplianceTypes
from homeassistant.components.cover import CoverEntity, CoverEntityFeature

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: core.HomeAssistant, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    A = ApplianceTypes()
    for device_id in api:
        aapi: XiaoDuAPI = api[device_id]
        applianceTypes = aapi.applianceTypes
        if not A.is_cover(applianceTypes):
            continue
        try:
            detail = await aapi.get_detail()
            if not detail or not isinstance(detail, dict) or 'appliance' not in detail:
                continue
            appliance = detail['appliance']
            if not isinstance(appliance, dict):
                continue
            name = appliance.get('friendlyName', 'Unknown')
            if_on = False
            if 'stateSetting' in appliance and isinstance(appliance['stateSetting'], dict):
                stateSetting = appliance['stateSetting']
                if 'turnOnState' in stateSetting and isinstance(stateSetting['turnOnState'], dict):
                    turnOnState = stateSetting['turnOnState']
                    if 'value' in turnOnState:
                        if_onS = str(turnOnState['value']).lower()
                        if_on = if_onS == "on"
            entities.append(XiaoDuCover(api[device_id], name, if_on, appliance))
        except Exception as e:
            _LOGGER.error("加载窗帘设备失败: %s", e)
            continue
    async_add_entities(entities, update_before_add=True)


class XiaoDuCover(CoverEntity):
    def __init__(self, api: XiaoDuAPI, name: str, if_on: bool, detail):
        self._api = api
        self._attr_name = name
        self._attr_unique_id = f"{api.applianceId}_cover"
        self._attr_supported_features = CoverEntityFeature(CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
                                                           CoverEntityFeature.STOP)
        self._attr_is_closed = not if_on
        if if_on:
            self._attr_icon = "mdi:curtains"
        else:
            self._attr_icon = "mdi:curtains-closed"

    async def async_open_cover(self, **kwargs):
        flag = await self._api.set_curtain_open()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        flag = await self._api.set_curtain_close()
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs):
        flag = await self._api.set_curtain_stop()
        self.async_write_ha_state()

    async def async_update(self):
        try:
            if_on = await self._api.switch_status()
            self._attr_is_closed = not if_on
            if if_on:
                self._attr_icon = "mdi:curtains"
            else:
                self._attr_icon = "mdi:curtains-closed"
        except Exception as e:
            _LOGGER.error("更新窗帘状态失败 %s: %s", self._attr_name, e)
