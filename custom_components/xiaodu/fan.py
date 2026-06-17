import asyncio
import json
import logging

from homeassistant import core
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components.switch import SwitchEntity
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
        if not A.is_fan(applianceTypes):
            continue
        try:
            detail = await aapi.get_detail()
            if not detail or detail == []:
                continue
            if not isinstance(detail, dict) or 'appliance' not in detail:
                continue
            appliance = detail['appliance']
            if not isinstance(appliance, dict):
                continue
            name = appliance.get('friendlyName', 'Unknown')
            group_name = appliance.get('groupName', 'Unknown')
            bot_name = appliance.get('botName', 'Unknown')

            # 检查是否有 panels（多按钮红外设备）
            has_panels = A.has_panels(appliance)

            if has_panels:
                # 多按钮设备：为每个面板按钮创建独立开关
                _LOGGER.info("设备 %s 检测到多按钮面板，创建按钮开关", name)
                for panel_group in appliance.get('panels', []):
                    if not isinstance(panel_group, dict) or 'list' not in panel_group:
                        continue
                    panels = panel_group.get('list', [])
                    for panel in panels:
                        if not isinstance(panel, dict):
                            continue
                        payload = None
                        headerNameOn = None
                        headerNameOff = None
                        TypeStr = panel.get('name')
                        TypeValue = panel.get('value')
                        switchName = panel.get('label', '')
                        if_on = False
                        actions = panel.get('actions', [])
                        for i, p in enumerate(actions):
                            if not isinstance(p, dict):
                                continue
                            if 'payload' in p:
                                payload = json.dumps(p['payload'])
                            if i == 0:
                                headerNameOn = p.get('headerName')
                            if i == 1:
                                headerNameOff = p.get('headerName')
                        entities.append(
                            XiaoDuFanSwitch(api[device_id], name + "_" + switchName, if_on, group_name, bot_name,
                                            TypeStr, TypeValue, headerNameOn, headerNameOff, payload))
            else:
                # 普通风扇设备：创建风扇实体
                if_on = False
                can_query_status = True
                if 'stateSetting' not in appliance:
                    if_on = False
                    can_query_status = False
                else:
                    stateSetting = appliance['stateSetting']
                    if not isinstance(stateSetting, dict) or 'turnOnState' not in stateSetting:
                        if_on = False
                        can_query_status = False
                    else:
                        turnOnState = stateSetting['turnOnState']
                        if not isinstance(turnOnState, dict) or 'value' not in turnOnState:
                            if_on = False
                            can_query_status = False
                        else:
                            if_onS = str(turnOnState['value']).lower()
                            if_on = if_onS == "on"
                entities.append(XiaoDuFan(api[device_id], name, if_on, group_name, bot_name, can_query_status))
        except Exception as e:
            _LOGGER.error("加载风扇设备失败: %s", e)
            continue
    async_add_entities(entities, True)


class XiaoDuFan(FanEntity):
    def __init__(self, api: XiaoDuAPI, name: str, if_on: bool, groupName: str, botName: str, can_query_status: bool = True):
        self._api = api
        self._attr_unique_id = f"{api.applianceId}_fan"
        self._attr_name = name
        self._is_on = if_on
        self._group_name = botName
        self._percentage = 0
        self._attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        self._attr_speed_count = 3
        self._can_query_status = can_query_status
        if if_on:
            self._attr_icon = "mdi:fan"
        else:
            self._attr_icon = "mdi:fan-off"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._api.applianceId)},
            "name": self._attr_name,
            "manufacturer": self._group_name,
        }

    @property
    def is_on(self):
        return self._is_on

    @property
    def percentage(self):
        return self._percentage

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        await self._api.switch_on()
        self._is_on = True
        self._attr_icon = "mdi:fan"
        if percentage is not None:
            await self.async_set_percentage(percentage)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._api.switch_off()
        self._is_on = False
        self._attr_icon = "mdi:fan-off"
        self._percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int):
        self._percentage = percentage
        if percentage > 66:
            await self._api.set_fan_speed(3)
        elif percentage > 33:
            await self._api.set_fan_speed(2)
        else:
            await self._api.set_fan_speed(1)
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str):
        pass

    async def async_update(self):
        # 如果设备不支持状态查询，跳过更新
        if not self._can_query_status:
            return
        try:
            self._is_on = await self._api.switch_status()
            if self._is_on:
                self._attr_icon = "mdi:fan"
            else:
                self._attr_icon = "mdi:fan-off"
        except Exception as e:
            _LOGGER.error("更新风扇状态失败: %s", e)

    async def async_added_to_hass(self):
        await self.async_update()


class XiaoDuFanSwitch(SwitchEntity):
    """红外多按钮风扇的单个按钮开关"""

    def __init__(self, api: XiaoDuAPI, name: str, if_on: bool, groupName: str, botName: str,
                 switchType: str = None, typeValue: str = None, headerNameOn: str = None,
                 headerNameOff: str = None, payloadObject: str = None):
        self._api = api
        self._attr_unique_id = f"{api.applianceId}_switch_{switchType}_{typeValue}"
        self._is_on = if_on
        self._name = name
        self._group_name = botName
        self.switchType = switchType
        self.typeValue = typeValue
        self.headerNameOn = headerNameOn
        self.headerNameOff = headerNameOff
        self.payloadObject = payloadObject
        self._attr_icon = "mdi:remote-tv"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._api.applianceId)},
            "name": self._api.applianceId,
            "manufacturer": self._group_name,
        }

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        await self._api.switch_panel_on(self.switchType, self.typeValue, self.headerNameOn,
                                        self.headerNameOff, self.payloadObject)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        await self._api.switch_panel_off(self.switchType, self.typeValue, self.headerNameOn,
                                         self.headerNameOff, self.payloadObject)
        self._is_on = False
        self.async_write_ha_state()

    async def async_update(self):
        # 红外设备无法查询状态，跳过更新
        pass

    async def async_added_to_hass(self):
        await self.async_update()
