import logging

from homeassistant import core
from homeassistant.components.lock import LockEntity
from . import XiaoDuAPI, ApplianceTypes

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: core.HomeAssistant, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    A = ApplianceTypes()
    for device_id in api:
        aapi: XiaoDuAPI = api[device_id]
        applianceTypes = aapi.applianceTypes
        if not A.is_lock(applianceTypes):
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
            if 'attributes' in appliance and isinstance(appliance['attributes'], dict):
                attributes = appliance['attributes']
                try:
                    if 'turnOnState' not in attributes:
                        if 'lockState' in attributes and isinstance(attributes['lockState'], dict):
                            lockState = attributes['lockState']
                            if 'value' in lockState:
                                if_onS = str(lockState['value']).lower()
                                if_onS = "on" if if_onS == "unlocked" else "off"
                        else:
                            if_onS = "off"
                    else:
                        if 'turnOnState' in attributes and isinstance(attributes['turnOnState'], dict):
                            turnOnState = attributes['turnOnState']
                            if 'value' in turnOnState:
                                if_onS = str(turnOnState['value']).lower()
                        else:
                            if_onS = "off"
                    if if_onS == "on":
                        if_on = True
                    else:
                        if_on = False
                except Exception as e:
                    _LOGGER.error("解析门锁状态失败: %s", e)
                    continue
            entities.append(XiaoDuLock(api[device_id], name, if_on, appliance))
        except Exception as e:
            _LOGGER.error("加载门锁设备失败: %s", e)
            continue
    async_add_entities(entities, update_before_add=True)


class XiaoDuLock(LockEntity):

    def __init__(self, api: XiaoDuAPI, name: str, if_on: bool, detail):
        self._api = api
        self._attr_unique_id = f"{api.applianceId}_lock"
        self._attr_is_open = if_on
        self._attr_is_locked = not if_on
        self._attr_name = name
        self._group_name = detail['groupName']
        self.pColorMode = None
        self.effectList = {}
        if if_on:
            self._attr_icon = "mdi:lock-open-outline"
        else:
            self._attr_icon = "mdi:lock"

    async def async_update(self):
        try:
            detail = await self._api.get_detail()
            if not detail or 'appliance' not in detail:
                return
            detail = detail['appliance']
            if 'turnOnState' not in detail['attributes']:
                if_onS = str(detail['attributes']['lockState']['value']).lower()
                if_onS = "on" if if_onS == "unlocked" else "off"
            else:
                if_onS = str(detail['attributes']['turnOnState']['value']).lower()
            if if_onS == "on":
                if_on = True
            else:
                if_on = False
            self._attr_is_open = if_on
            self._attr_is_locked = not if_on
        except Exception as e:
            _LOGGER.error("更新门锁状态失败 %s: %s", self._attr_name, e)
