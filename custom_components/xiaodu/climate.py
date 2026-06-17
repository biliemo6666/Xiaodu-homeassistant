import logging

from homeassistant import core
from . import ApplianceTypes, XiaoDuAPI
from .const import DOMAIN
from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, FAN_LOW, FAN_MEDIUM, FAN_HIGH, \
    HVACMode, FAN_MIDDLE, FAN_FOCUS, FAN_DIFFUSE
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: core.HomeAssistant, config_entry, async_add_entities):
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    A = ApplianceTypes()
    for device_id in api:
        aapi: XiaoDuAPI = api[device_id]
        applianceTypes = aapi.applianceTypes
        if not A.is_climate(applianceTypes):
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
        entities.append(XiaoDuClimate(api[device_id], name, if_on, detail['appliance']))
    async_add_entities(entities, update_before_add=True)


class XiaoDuClimate(ClimateEntity):
    def __init__(self, api: XiaoDuAPI, name: str, if_on: bool, detail):
        self._api = api
        self._attr_name = name
        self._attr_unique_id = f"{api.applianceId}_climate"
        self._attr_supported_features = (
                ClimateEntityFeature.TURN_ON |
                ClimateEntityFeature.TURN_OFF |
                ClimateEntityFeature.TARGET_TEMPERATURE |
                ClimateEntityFeature.FAN_MODE
        )
        self._attr_fan_modes = [
            FAN_LOW, FAN_MEDIUM, FAN_HIGH, FAN_MIDDLE, FAN_FOCUS, FAN_DIFFUSE]
        self._attr_hvac_modes = [
            HVACMode.COOL, HVACMode.HEAT, HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.OFF, HVACMode.AUTO]
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_min_temp = 16
        self._attr_max_temp = 32
        self._attr_target_temperature_step = 1
        self._attr_hvac_mode = None
        self._attr_fan_mode = None
        self._fan_mode_lookup = {
            1: FAN_LOW,
            2: FAN_MEDIUM,
            3: FAN_HIGH,
            4: FAN_MIDDLE,
            5: FAN_FOCUS,
            6: FAN_DIFFUSE,
            7: FAN_DIFFUSE,
            8: FAN_DIFFUSE,
            9: FAN_DIFFUSE,
            10: FAN_DIFFUSE
        }
        self._ac_mode_lookup = {
            "dry": "dehumidification",
            "fan_only": "fan"
        }
        self._ac_mode_lookup2 = {
            "dehumidification": HVACMode.DRY,
            "fan": HVACMode.FAN_ONLY
        }
        self.detail = None

    async def async_turn_on(self):
        flag = await self._api.set_ac_on()
        self.async_write_ha_state()

    async def async_turn_off(self):
        flag = await self._api.set_ac_off()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        if fan_mode == FAN_LOW:
            await self._api.set_ac_fan_jian()
        if fan_mode == FAN_HIGH:
            await self._api.set_ac_fan_jia()
        if fan_mode == FAN_MEDIUM:
            pass

    async def async_set_temperature(self, **kwargs):
        temperature = kwargs.get(ATTR_TEMPERATURE, 26.0)
        if self.target_temperature < temperature:
            num = int(temperature - self.target_temperature)
            for i in range(num):
                await self._api.set_ac_temperature_jia()
        else:
            num = int(self.target_temperature - temperature)
            for i in range(num):
                await self._api.set_ac_temperature_jian()

    async def async_set_hvac_mode(self, hvac_mode):
        mode = self._ac_mode_lookup.get(hvac_mode, hvac_mode)
        if mode == "off":
            flag = await self._api.set_ac_off()
        else:
            try:
                detail = self.detail['appliance']
                stateSetting = detail.get('stateSetting', {})
                if isinstance(stateSetting, dict) and 'turnOnState' in stateSetting:
                    turnOnState = stateSetting['turnOnState']
                    if isinstance(turnOnState, dict) and 'value' in turnOnState:
                        if str(turnOnState['value']).lower() == "off":
                            flag = await self._api.set_ac_on()
            except Exception:
                pass
            flag = await self._api.set_ac_mode(mode)
        self.async_write_ha_state()

    async def async_update(self):
        try:
            self.detail = await self._api.get_detail()
            if not self.detail or not isinstance(self.detail, dict) or 'appliance' not in self.detail:
                return
            detail = self.detail['appliance']
            if not isinstance(detail, dict):
                return
            stateSetting = detail.get('stateSetting', {})
            if not isinstance(stateSetting, dict):
                return
            fanSpeed = FAN_MEDIUM
            if 'fanSpeed' in stateSetting and isinstance(stateSetting['fanSpeed'], dict):
                fanSpeed = stateSetting['fanSpeed'].get('value', FAN_MEDIUM)
            temperature = 26
            if 'temperature' in stateSetting and isinstance(stateSetting['temperature'], dict):
                temperature = stateSetting['temperature'].get('value', 26)
            mode = 'cool'
            if 'mode' in stateSetting and isinstance(stateSetting['mode'], dict):
                mode = stateSetting['mode'].get('value', 'cool')
            turnOnState = stateSetting.get('turnOnState', {})
            if isinstance(turnOnState, dict) and 'value' in turnOnState:
                if str(turnOnState['value']).lower() == 'on':
                    self._attr_hvac_mode = self._ac_mode_lookup2.get(str(mode).lower(), str(mode).lower())
                else:
                    self._attr_hvac_mode = HVACMode.OFF
            else:
                self._attr_hvac_mode = HVACMode.OFF

            self._attr_fan_mode = self._fan_mode_lookup.get(fanSpeed, FAN_MEDIUM)
            self._attr_target_temperature = temperature
        except Exception as e:
            _LOGGER.error("更新空调状态失败 %s: %s", self._attr_name, e)
