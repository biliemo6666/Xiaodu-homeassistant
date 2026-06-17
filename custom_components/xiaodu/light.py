import asyncio
import logging

from homeassistant import core
from homeassistant.components.light import LightEntity, ColorMode, ATTR_BRIGHTNESS, \
    ATTR_COLOR_TEMP_KELVIN, LightEntityFeature, ATTR_EFFECT
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
        if not A.is_light(applianceTypes):
            continue
        detail = await aapi.get_detail()
        if detail == []:
            continue
        name = detail['appliance']['friendlyName']
        if_onS = str(detail['appliance']['stateSetting']['turnOnState']['value']).lower()
        if if_onS == "on":
            if_on = True
        else:
            if_on = False
        entities.append(XiaoDuLight(api[device_id], name, if_on, detail['appliance']))
    async_add_entities(entities, update_before_add=True)


class XiaoDuLight(LightEntity):

    def __init__(self, api: XiaoDuAPI, name: str, if_on: bool, detail):
        self._api = api
        self._attr_unique_id = f"{api.applianceId}_light"
        self._attr_is_on = if_on
        self._attr_name = name
        self._group_name = detail['groupName']
        self.pColorMode = None
        self.effectList = {}
        if if_on:
            self._attr_icon = "mdi:lightbulb"
        else:
            self._attr_icon = "mdi:lightbulb-off"

        if 'brightness' in detail['stateSetting'] and 'colorTemperatureInKelvin' in detail['stateSetting']:
            self._attr_supported_color_modes = {ColorMode.COLOR_TEMP}
            self._attr_color_mode = ColorMode.COLOR_TEMP
            self.pColorMode = ColorMode.COLOR_TEMP
        if 'brightness' in detail['stateSetting'] and 'colorTemperatureInKelvin' not in detail['stateSetting']:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self.pColorMode = ColorMode.BRIGHTNESS
        if 'mode' in detail['stateSetting']:
            self._attr_supported_features = LightEntityFeature(
                LightEntityFeature.EFFECT)
            effect_list = []
            valueRangeMap = detail['stateSetting']['mode']['valueRangeMap']
            for i in valueRangeMap:
                effect_list.append(valueRangeMap[i])
            self._attr_effect_list = effect_list

        if 'mode' not in detail['stateSetting'] and 'brightness' not in detail[
            'stateSetting'] and 'colorTemperatureInKelvin' not in detail['stateSetting']:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
            self.pColorMode = ColorMode.ONOFF
        if self.pColorMode is None:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
            self.pColorMode = ColorMode.ONOFF

    @property
    def color_temp_kelvin(self) -> int | None:
        return self._color_temp_kelvin

    async def async_turn_on(self, **kwargs):
        if kwargs == {}:
            flag = await self._api.switch_on()
        if 'brightness' in kwargs:
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            attributeValue = round(brightness / 255 * 100)
            self._brightness = brightness
            flag = await self._api.brightness(attributeValue)
        if 'color_temp_kelvin' in kwargs:
            color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN, 4614)
            self._attr_color_temp_kelvin = color_temp_kelvin
            mddile = self.max_color_temp_kelvin - self.min_color_temp_kelvin
            attributeValue = round((color_temp_kelvin - self.min_color_temp_kelvin) / mddile * 100)
            flag = await self._api.colorTemperatureInKelvin(attributeValue)
        if 'effect' in kwargs:
            effect = kwargs.get(ATTR_EFFECT, "读写")
            mode = "READING"
            for i in self.effectList:
                if self.effectList[i] == effect:
                    mode = i
            flag = await self._api.light_set_mode(mode)
        self._is_on = True
        self._attr_icon = "mdi:lightbulb"
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        flag = await self._api.switch_off()
        self._is_on = False
        self._attr_icon = "mdi:lightbulb-off"
        self.async_write_ha_state()
        if not flag:
            self._is_on = True
            self._attr_icon = "mdi:lightbulb"
            self.async_write_ha_state()

    async def async_update(self):
        try:
            detail = await self._api.get_detail()
            if not detail or not isinstance(detail, dict) or 'appliance' not in detail:
                return
            detail = detail['appliance']
            if not isinstance(detail, dict):
                return
            if 'stateSetting' not in detail:
                return
            stateSetting = detail['stateSetting']
            if not isinstance(stateSetting, dict):
                return
            if 'turnOnState' not in stateSetting:
                return
            turnOnState = stateSetting['turnOnState']
            if not isinstance(turnOnState, dict) or 'value' not in turnOnState:
                return
            turnOnStateValue = str(turnOnState['value']).lower()
            if turnOnStateValue == "on":
                turnOnState = True
            else:
                turnOnState = False
            self._attr_is_on = turnOnState
            if 'mode' in stateSetting and isinstance(stateSetting['mode'], dict):
                self.effectList = stateSetting['mode'].get('valueRangeMap', {})
            if self.pColorMode == ColorMode.BRIGHTNESS:
                if 'brightness' in stateSetting and isinstance(stateSetting['brightness'], dict):
                    brightness = stateSetting['brightness'].get('value', 0)
                    self._attr_brightness = round(brightness / 100 * 255)
            elif self.pColorMode == ColorMode.COLOR_TEMP:
                if 'brightness' in stateSetting and isinstance(stateSetting['brightness'], dict):
                    brightness = stateSetting['brightness'].get('value', 0)
                    self._attr_brightness = round(brightness / 100 * 255)
                if 'colorTemperatureInKelvin' in stateSetting and isinstance(stateSetting['colorTemperatureInKelvin'], dict):
                    colorTemperatureInKelvin = stateSetting['colorTemperatureInKelvin'].get('value', 4614)
                    if 'valueKelvinRangeMap' in stateSetting['colorTemperatureInKelvin']:
                        kelvinRange = stateSetting['colorTemperatureInKelvin']['valueKelvinRangeMap']
                        colorTemperatureInKelvinMin = kelvinRange.get('min', 2700)
                        colorTemperatureInKelvinMax = kelvinRange.get('max', 6500)
                    else:
                        colorTemperatureInKelvinMin = 2700
                        colorTemperatureInKelvinMax = 6500
                    self._attr_min_color_temp_kelvin = colorTemperatureInKelvinMin
                    self._attr_min_mireds = colorTemperatureInKelvinMin
                    self._attr_max_color_temp_kelvin = colorTemperatureInKelvinMax
                    self._attr_max_mireds = colorTemperatureInKelvinMax
                    mddile = colorTemperatureInKelvinMax - colorTemperatureInKelvinMin
                    colorTemperatureInKelvin = round(colorTemperatureInKelvin / 100 * mddile) + colorTemperatureInKelvinMin
                    self._attr_color_temp_kelvin = colorTemperatureInKelvin
                    self._color_temp_kelvin = colorTemperatureInKelvin
                    if 'mode' in stateSetting and isinstance(stateSetting['mode'], dict):
                        self._attr_supported_features = LightEntityFeature(
                            LightEntityFeature.EFFECT)
                        effect_list = []
                        valueRangeMap = stateSetting['mode'].get('valueRangeMap', {})
                        for i in valueRangeMap:
                            effect_list.append(valueRangeMap[i])
                        self._attr_effect_list = effect_list
                        if 'value' not in stateSetting['mode']:
                            mode = "NIGHT_UP"
                        else:
                            mode = stateSetting['mode']['value']
                        self._attr_effect = valueRangeMap.get(mode, mode)
        except Exception as e:
            _LOGGER.error("更新灯光状态失败 %s: %s", self._attr_name, e)
