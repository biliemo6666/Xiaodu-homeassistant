import logging

from homeassistant import core
from homeassistant.components.button import ButtonEntity
from . import XiaoDuAPI, ApplianceTypes
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: core.HomeAssistant, config_entry, async_add_entities):
    _LOGGER.warning("===== button.py async_setup_entry 开始 =====")
    api = hass.data[DOMAIN][config_entry.entry_id]
    entities = []
    A = ApplianceTypes()
    _LOGGER.warning("设备总数: %d", len(api))

    for device_id in api:
        aapi: XiaoDuAPI = api[device_id]
        applianceTypes = aapi.applianceTypes
        _LOGGER.warning("遍历设备 device_id=%s, applianceTypes=%s", device_id, applianceTypes)
        try:
            detail = await aapi.get_detail()
            _LOGGER.warning("设备 %s get_detail() 返回类型: %s, 内容: %s", device_id, type(detail).__name__,
                          str(detail)[:1000] if detail else "None/Empty")
            if not detail or detail == []:
                _LOGGER.warning("设备 %s detail 为空，跳过", device_id)
                continue
            if not isinstance(detail, dict) or 'appliance' not in detail:
                _LOGGER.warning("设备 %s detail 结构不正确，跳过", device_id)
                continue
            appliance = detail['appliance']
            if not isinstance(appliance, dict):
                _LOGGER.warning("设备 %s appliance 不是字典，跳过", device_id)
                continue

            name = appliance.get('friendlyName', 'Unknown')
            group_name = appliance.get('groupName', 'Unknown')
            bot_name = appliance.get('botName', 'Unknown')
            support_actions = appliance.get('supportActions', [])
            _LOGGER.warning("设备 %s: name=%s, supportActions=%s", name, name, support_actions)

            # 检查 irBtns
            ir_btns = appliance.get('irBtns', None)
            _LOGGER.warning("设备 %s (%s) irBtns: %s", device_id, name, str(ir_btns)[:500] if ir_btns else "None")
            has_ir_btns = A.has_ir_btns(appliance)
            _LOGGER.warning("设备 %s (%s) has_ir_btns=%s", device_id, name, has_ir_btns)

            # 处理红外学习设备的按钮
            if has_ir_btns:
                _LOGGER.warning("设备 %s (%s) 检测到红外按钮，创建按钮实体", device_id, name)
                for btn in appliance.get('irBtns', []):
                    if not isinstance(btn, dict):
                        _LOGGER.warning("设备 %s 按钮数据不是字典: %s", name, btn)
                        continue
                    btn_name = btn.get('name', '')
                    btn_index = btn.get('index')
                    if not btn_name:
                        _LOGGER.warning("设备 %s 按钮名称为空", name)
                        continue
                    _LOGGER.warning("设备 %s 创建按钮: %s (index=%s)", name, btn_name, btn_index)
                    entities.append(
                        XiaoDuIrButton(api[device_id], name + "_" + btn_name, group_name, bot_name, btn_name, btn_index, support_actions))
            else:
                _LOGGER.warning("设备 %s (%s) 没有 irBtns，跳过", device_id, name)
        except Exception as e:
            _LOGGER.error("加载按钮设备失败 %s: %s", device_id, e)
            import traceback
            _LOGGER.error(traceback.format_exc())
            continue

    _LOGGER.warning("button.py 共创建 %d 个按钮实体", len(entities))
    async_add_entities(entities, True)


class XiaoDuIrButton(ButtonEntity):
    """红外学习设备的按钮"""

    def __init__(self, api: XiaoDuAPI, name: str, groupName: str, botName: str, button_name: str, button_id: int = None, support_actions: list = None):
        self._api = api
        self._attr_unique_id = f"{api.applianceId}_ir_btn_{button_name}"
        self._attr_name = name
        self._group_name = groupName
        self._bot_name = botName
        self._button_name = button_name
        self._button_id = button_id
        self._support_actions = support_actions or []
        self._attr_icon = "mdi:remote"
        _LOGGER.warning("XiaoDuIrButton 初始化: name=%s, unique_id=%s, button=%s, id=%s, support_actions=%s", name, self._attr_unique_id, button_name, button_id, self._support_actions)

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._api.applianceId)},
            "name": self._group_name,
            "manufacturer": self._bot_name,
        }

    async def async_press(self):
        """按下红外按钮"""
        _LOGGER.warning("按下按钮: %s (button=%s, id=%s)", self._attr_name, self._button_name, self._button_id)
        result = await self._api.press_ir_button(self._button_name, self._button_id, self._support_actions)
        _LOGGER.warning("按钮 %s 结果: %s", self._attr_name, result)
