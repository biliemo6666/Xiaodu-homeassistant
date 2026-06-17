import asyncio
import json
import random

from homeassistant import core
from homeassistant.components.switch import SwitchEntity
from . import XiaoDuAPI, ApplianceTypes
from .const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: core.HomeAssistant, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    A = ApplianceTypes()
    for device_id in api:
        aapi: XiaoDuAPI = api[device_id]
        applianceTypes = aapi.applianceTypes
        if not A.is_switch(applianceTypes):
            continue
        try:
            detail = await aapi.get_detail()
            if detail == []:
                continue
            # 检查 detail 是否为字典
            if not isinstance(detail, dict):
                _LOGGER.warning("设备 %s 返回的数据不是字典类型，跳过", device_id)
                continue
            if 'appliance' not in detail:
                _LOGGER.warning("设备 %s 数据中缺少 appliance 字段", device_id)
                continue
            appliance = detail['appliance']
            if not isinstance(appliance, dict):
                _LOGGER.warning("设备 %s 的 appliance 字段不是字典类型", device_id)
                continue
            name = appliance.get('friendlyName', 'Unknown')
            group_name = appliance.get('groupName', 'Unknown')
            bot_name = appliance.get('botName', 'Unknown')

            # 检查是否有 irBtns（红外学习设备，由 button.py 处理）
            if A.has_ir_btns(appliance):
                _LOGGER.warning("设备 %s 有 irBtns，由 button.py 处理，跳过 switch", name)
                continue

            # 检查是否有 panels（多按钮红外设备）
            has_panels = A.has_panels(appliance)

            # 处理多按钮设备（红外学习设备等）
            if has_panels or 'CLOTHES_RACK' in appliance.get('applianceTypes', []):
                panels = []
                for panel_group in appliance.get('panels', []):
                    if isinstance(panel_group, dict) and 'list' in panel_group:
                        panels.extend(panel_group['list'])
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
                    for i, p in enumerate(panel.get('actions', [])):
                        if not isinstance(p, dict):
                            continue
                        if 'payload' in p:
                            payload = json.dumps(p['payload'])
                        if i == 0:
                            headerNameOn = p.get('headerName')
                        if i == 1:
                            headerNameOff = p.get('headerName')
                    entities.append(
                        XiaoduSwitch(api[device_id], name + "_" + switchName, if_on, group_name, bot_name, TypeStr,
                                     TypeValue, headerNameOn, headerNameOff, payload))
            else:
                # 普通开关设备：创建单个开关实体
                # 检查 stateSetting 是否存在
                if 'stateSetting' not in appliance:
                    _LOGGER.warning("设备 %s 缺少 stateSetting 字段，尝试使用默认值", device_id)
                    if_on = False
                else:
                    stateSetting = appliance['stateSetting']
                    if not isinstance(stateSetting, dict):
                        _LOGGER.warning("设备 %s 的 stateSetting 不是字典类型", device_id)
                        if_on = False
                    elif 'turnOnState' not in stateSetting:
                        _LOGGER.warning("设备 %s 缺少 turnOnState 字段", device_id)
                        if_on = False
                    else:
                        turnOnState = stateSetting['turnOnState']
                        if not isinstance(turnOnState, dict) or 'value' not in turnOnState:
                            _LOGGER.warning("设备 %s 的 turnOnState 格式不正确", device_id)
                            if_on = False
                        else:
                            if_onS = str(turnOnState['value']).lower()
                            if_on = if_onS == "on"
                entities.append(XiaoduSwitch(api[device_id], name, if_on, group_name, bot_name))
        except Exception as e:
            _LOGGER.error("加载开关设备失败: %s", e)
            continue
    async_add_entities(entities, True)


class XiaoduSwitch(SwitchEntity):
    def __init__(self, api: XiaoDuAPI, name: str, if_on: bool, groupName: str, botName: str, switchType: str = "switch",
                 typeValue: str = None, headerNameOn: str = None, headerNameOff: str = None, payloadObject: str = None):
        self._api = api
        if switchType != "switch":
            self._attr_unique_id = f"{api.applianceId}_switch_{switchType}_{typeValue}"
        else:
            self._attr_unique_id = f"{api.applianceId}_switch"
        self._is_on = if_on
        self._name = name
        self._group_name = botName
        self.switchType = switchType
        self.typeValue = typeValue
        self.headerNameOn = headerNameOn
        self.headerNameOff = headerNameOff
        self.payloadObject = payloadObject
        if if_on:
            self._attr_icon = "mdi:toggle-switch-variant"
        else:
            self._attr_icon = "mdi:toggle-switch-variant-off"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._api.applianceId)},
            "name": self._name,
            "manufacturer": self._group_name,
        }

    @property
    def name(self):
        return self._name

    @property
    def is_on(self):
        return self._is_on

    async def async_turn_on(self, **kwargs):
        if self.switchType == "switch":
            flag = await self._api.switch_on()
        else:
            flag = await self._api.switch_panel_on(self.switchType, self.typeValue, self.headerNameOn,
                                                   self.headerNameOff, self.payloadObject)
        self._is_on = True
        self._attr_icon = "mdi:toggle-switch-variant"
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        if self.switchType == "switch":
            flag = await self._api.switch_off()
        else:
            flag = await self._api.switch_panel_off(self.switchType, self.typeValue, self.headerNameOn,
                                                    self.headerNameOff, self.payloadObject)
        self._is_on = False
        self._attr_icon = "mdi:toggle-switch-variant-off"
        self.async_write_ha_state()

    async def async_update(self):
        try:
            if self.switchType == "switch":
                self._is_on = await self._api.switch_status()
            else:
                self._is_on = await self._api.switch_panel_status(self.switchType, self.typeValue, self.headerNameOn,
                                                                  self.headerNameOff, self.payloadObject)
        except Exception as e:
            _LOGGER.error("更新开关状态失败 %s: %s", self._name, e)

    async def async_added_to_hass(self):
        await self.async_update()
