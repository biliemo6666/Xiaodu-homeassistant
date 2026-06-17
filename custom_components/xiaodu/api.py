"""API client for Xiaodu."""
import json
import logging

import aiohttp

HOST = 'https://xiaodu.baidu.com'

_LOGGER = logging.getLogger(__name__)


class XiaoDuAPI:
    def __init__(self, cookie: str, session: aiohttp.ClientSession, houseId: str = None, applianceId: str = None,
                 applianceTypes: list = []) -> None:
        self.cookie = cookie
        self.Session = session
        self.Header = self._common_header()
        self.applianceId = applianceId
        self.houseId = houseId
        self.applianceTypes = applianceTypes

    async def checkSession(self):
        submit = {"url": "dueros://smarthome.bot.dueros.ai/gateway/myspeaker"}
        try:
            res = await self.Session.post(HOST + "/appserver/gateway/app/v1", json=submit, headers=self.Header)
            json_data = await res.json()
            if json_data['status'] != 0:
                return [False, "invalid_auth"]
            return [True, None]
        except Exception as e:
            logging.error("检查cookie 请求小度出错")
            logging.error(str(e))
            return [False, "cannot_xiaodu"]

    async def auth(self) -> bool:
        return True

    async def doDeviceList(self):
        api = "/saiya/smarthome/devicelist?from=h5_control&withscene=1&generalscene=3"
        try:
            res = await self.Session.get(HOST + api, headers=self.Header)
            json_data = await res.json()
            return json_data['data']['appliances']
        except Exception as e:
            logging.error("请求小度出错")
            return []

    async def switch_on(self):
        return await self.switch_toggle(True)

    async def switch_off(self):
        return await self.switch_toggle(False)

    async def switch_status(self):
        detail = await self.get_detail()
        if not detail or not isinstance(detail, dict):
            return False
        if 'appliance' not in detail:
            return False
        appliance = detail['appliance']
        if not isinstance(appliance, dict):
            return False
        if 'stateSetting' not in appliance:
            return False
        stateSetting = appliance['stateSetting']
        if not isinstance(stateSetting, dict):
            return False
        if 'turnOnState' not in stateSetting:
            return False
        turnOnState = stateSetting['turnOnState']
        if not isinstance(turnOnState, dict) or 'value' not in turnOnState:
            return False
        turnOnStateValue = str(turnOnState['value']).lower()
        if turnOnStateValue == "on":
            return True
        return False

    async def get_detail(self):
        api = "/saiya/smarthome/appliancedetails"
        submit = {"applianceId": self.applianceId, "version": 2, "from": "h5"}
        try:
            res = await self.Session.get(HOST + api, headers=self.Header, json=submit,
                                         cookies={"HOUSE_ID": self.houseId})
            json_data = await res.json()
            if json_data['status'] == 0:
                return json_data['data']
            return {}
        except Exception as e:
            logging.error("请求小度出错")
            return {}

    async def get_details(self, houseId: str, applianceIds: list):
        api = "/saiya/smarthome/appliance"
        submit = {"enableCancelToken": True, "method": "GET_APPLIANCES_BY_ID",
                  "params": {"from": "h5_control", "applianceIdList": applianceIds, "clientCuidList": [],
                             "enablecache": True}}
        try:
            res = await self.Session.get(HOST + api, headers=self.Header, json=submit, cookies={"HOUSE_ID": houseId})
            json_data = await res.json()
            if json_data['status'] == 0:
                return json_data['data']
            return {}
        except Exception as e:
            logging.error("请求小度出错")
            logging.error(str(e))
            return {}

    async def switch_toggle(self, method: bool):
        methodS = "ON"
        methodS2 = "TurnOnRequest"
        if not method:
            methodS = "OFF"
            methodS2 = "TurnOffRequest"
        submit = {
            "header": {"namespace": "DuerOS.ConnectedHome.Control", "name": methodS2, "payloadVersion": 3},
            "payload": {"applianceId": self.applianceId,
                        "parameters": {"attribute": "turnOnState", "attributeValue": methodS,
                                       "proxyConnectStatus": False},
                        "appliance": {"applianceId": [self.applianceId]}, "turnOnState": {"value": methodS}}}
        return await self.send_command(submit)

    async def brightness(self, attributeValue: int):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "SetBrightnessPercentageRequest",
                             "payloadVersion": 3}, "payload": {"applianceId": self.applianceId,
                                                               "parameters": {"attribute": "brightness",
                                                                              "attributeValue": attributeValue,
                                                                              "proxyConnectStatus": False},
                                                               "appliance": {"applianceId": [self.applianceId]},
                                                               "brightness": {"value": attributeValue}}}
        return await self.send_command(submit)

    async def colorTemperatureInKelvin(self, attributeValue: int):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "SetColorTemperatureRequest",
                             "payloadVersion": 3}, "payload": {"applianceId": self.applianceId,
                                                               "parameters": {"attribute": "colorTemperatureInKelvin",
                                                                              "attributeValue": attributeValue,
                                                                              "proxyConnectStatus": False},
                                                               "appliance": {"applianceId": [self.applianceId]},
                                                               "colorTemperatureInKelvin": attributeValue}}
        return await self.send_command(submit)

    async def light_set_mode(self, mode: str):
        submit = {
            "header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "SetModeRequest", "payloadVersion": 3},
            "payload": {"applianceId": self.applianceId,
                        "parameters": {"attribute": "mode", "attributeValue": mode, "proxyConnectStatus": False},
                        "appliance": {"applianceId": [self.applianceId]}, "mode": {"value": mode}}}
        return await self.send_command(submit)

    async def set_curtain_stop(self):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "PauseRequest", "payloadVersion": 3},
                  "payload": {"applianceId": self.applianceId, "parameters": {"proxyConnectStatus": False},
                              "appliance": {"applianceId": [self.applianceId]}}}
        return await self.send_command(submit)

    async def set_curtain_open(self):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "TurnOnRequest", "payloadVersion": 3},
                  "payload": {"applianceId": self.applianceId, "parameters": {"proxyConnectStatus": False},
                              "appliance": {"applianceId": [self.applianceId]}}}
        return await self.send_command(submit)

    async def set_curtain_close(self):
        submit = {
            "header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "TurnOffRequest", "payloadVersion": 3},
            "payload": {"applianceId": self.applianceId, "parameters": {"proxyConnectStatus": False},
                        "appliance": {"applianceId": [self.applianceId]}}}
        return await self.send_command(submit)

    async def set_ac_mode(self, mode: str):
        submit = {
            "header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "SetModeRequest", "payloadVersion": 1},
            "payload": {"mode": {"value": mode.upper()}, "applianceId": self.applianceId,
                        "appliance": {"applianceId": [self.applianceId]},
                        "parameters": {"proxyConnectStatus": False}}}
        return await self.send_command(submit)

    async def set_ac_off(self):
        submit = {
            "header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "TurnOffRequest", "payloadVersion": 1},
            "payload": {"applianceId": self.applianceId, "appliance": {"applianceId": [self.applianceId]},
                        "parameters": {"proxyConnectStatus": False}}}
        return await self.send_command(submit)

    async def set_ac_on(self):
        submit = {
            "header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "TurnOnRequest", "payloadVersion": 1},
            "payload": {"applianceId": self.applianceId, "appliance": {"applianceId": [self.applianceId]},
                        "parameters": {"proxyConnectStatus": False}}}
        return await self.send_command(submit)

    async def set_ac_temperature_jia(self):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "IncrementTemperatureRequest",
                             "payloadVersion": 1}, "payload": {"applianceId": self.applianceId,
                                                               "appliance": {"applianceId": [self.applianceId]},
                                                               "parameters": {"proxyConnectStatus": False}}}
        return await self.send_command(submit)

    async def set_ac_temperature_jian(self):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "DecrementTemperatureRequest",
                             "payloadVersion": 1}, "payload": {"applianceId": self.applianceId,
                                                               "appliance": {"applianceId": [self.applianceId]},
                                                               "parameters": {"proxyConnectStatus": False}}}
        return await self.send_command(submit)

    async def set_ac_fan_jia(self):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "IncrementFanSpeedRequest",
                             "payloadVersion": 1}, "payload": {"applianceId": self.applianceId,
                                                               "appliance": {"applianceId": [self.applianceId]},
                                                               "parameters": {"proxyConnectStatus": False}}}
        return await self.send_command(submit)

    async def set_ac_fan_jian(self):
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "DecrementFanSpeedRequest",
                             "payloadVersion": 1},
                  "payload": {"applianceId": self.applianceId, "appliance": {"applianceId": [self.applianceId]},
                              "parameters": {"proxyConnectStatus": False}}}
        return await self.send_command(submit)

    async def set_fan_speed(self, speed: int):
        """设置风扇速度 (1-3)"""
        submit = {"header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "SetFanSpeedRequest",
                             "payloadVersion": 1},
                  "payload": {"applianceId": self.applianceId,
                              "appliance": {"applianceId": [self.applianceId]},
                              "parameters": {"proxyConnectStatus": False},
                              "fanSpeed": {"value": speed}}}
        return await self.send_command(submit)

    async def get_home_id_list(self):
        api = "/saiya/smarthome/multihouse"
        submit = {"method": "HOUSE_LIST"}
        try:
            res = await self.Session.post(HOST + api, json=submit, headers=self.Header)
            json_data = await res.json()
            houseList = json_data['data']['houseList']
            houseList_2 = {}
            for i in houseList:
                houseList_2[i['houseId']] = i['houseName']
            return houseList_2
        except Exception as e:
            logging.error("获取房屋 请求小度出错")
            logging.error(str(e))
            return []

    async def get_device_wifi_id(self, houseId: str):
        api = "/saiya/smarthome/appliance"
        try:
            submit = {"method": "GET_USER_ALL_APPLIANCES",
                      "params": {"from": "h5_control", "withscene": 1, "generalscene": 3}}
            res = await self.Session.post(HOST + api, headers=self.Header, cookies={"HOUSE_ID": houseId}, json=submit)
            json_data = await res.json()
            return json_data['data']['appliances']
        except Exception as e:
            logging.error("请求小度出错")
            logging.error(str(e))
            return []

    async def get_device_wifi_id_dict(self, houseId: str):
        devices = await self.get_device_wifi_id(houseId)
        device_dict = {}
        for i in devices:
            device_dict[i['applianceId']] = i['friendlyName']
        return device_dict

    async def switch_panel_status(self, switchType, typeValue, headerNameOn, headerNameOff, payloadObject):
        detail = await self.get_detail()
        if not detail or not isinstance(detail, dict):
            return False
        if 'appliance' not in detail:
            return False
        appliance = detail['appliance']
        if not isinstance(appliance, dict):
            return False
        if 'stateSetting' not in appliance:
            return False
        stateSetting = appliance['stateSetting']
        if not isinstance(stateSetting, dict):
            return False
        if switchType not in stateSetting:
            return False
        stateValue = stateSetting[switchType]
        if not isinstance(stateValue, dict) or 'value' not in stateValue:
            return False
        if stateValue['value'] != typeValue:
            return False
        else:
            return True

    async def switch_panel_off(self, switchType, typeValue, headerNameOn, headerNameOff, payloadObject):
        if payloadObject is not None:
            payload = json.loads("""
                            {
                                %s,
                                "applianceId": %s,
                                "parameters": {
                                    "attribute": %s,
                                    "attributeValue": %s,
                                    "proxyConnectStatus": false
                                },
                                "appliance": {
                                    "applianceId": [
                                        %s
                                    ]
                                },
                                %s: {
                                    "value": %s
                                }
                            }
                            """ % (
            payloadObject[1:-1], '"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"',
            '"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"'))
        else:
            payload = json.loads("""
                            {
                                "applianceId": %s,
                                "parameters": {
                                    "attribute": %s,
                                    "attributeValue": %s,
                                    "proxyConnectStatus": false
                                },
                                "appliance": {
                                    "applianceId": [
                                        %s
                                    ]
                                },
                                %s: {
                                    "value": %s
                                }
                            }
                            """ % ('"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"',
            '"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"'))
        submit = {
            "header": {
                "namespace": "DuerOS.ConnectedHome.Control",
                "name": headerNameOff,
                "payloadVersion": 3
            },
            "payload": payload
        }
        flag = await self.send_command(submit)
        return flag[0]

    async def switch_panel_on(self, switchType, typeValue, headerNameOn, headerNameOff, payloadObject):
        if payloadObject is not None:
            payload = json.loads("""
                            {
                                %s,
                                "applianceId": %s,
                                "parameters": {
                                    "attribute": %s,
                                    "attributeValue": %s,
                                    "proxyConnectStatus": false
                                },
                                "appliance": {
                                    "applianceId": [
                                        %s
                                    ]
                                },
                                %s: {
                                    "value": %s
                                }
                            }
                            """ % (
            payloadObject[1:-1], '"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"',
            '"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"'))
        else:
            payload = json.loads("""
                            {
                                "applianceId": %s,
                                "parameters": {
                                    "attribute": %s,
                                    "attributeValue": %s,
                                    "proxyConnectStatus": false
                                },
                                "appliance": {
                                    "applianceId": [
                                        %s
                                    ]
                                },
                                %s: {
                                    "value": %s
                                }
                            }
                            """ % ('"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"',
            '"' + self.applianceId + '"', '"' + switchType + '"', '"' + typeValue + '"'))
        submit = {
            "header": {
                "namespace": "DuerOS.ConnectedHome.Control",
                "name": headerNameOn,
                "payloadVersion": 3
            },
            "payload": payload
        }
        flag = await self.send_command(submit)
        return flag[0]

    async def button_panel(self, switchType, typeValue, headerName):
        payload = json.loads("""
                        {
                            "applianceId": %s,
                            "parameters": {
                                "attribute": %s,
                                "proxyConnectStatus": false
                            },
                            "appliance": {
                                "applianceId": [
                                    %s
                                ]
                            },
                            %s: {}
                        }
                        """ % ('"' + self.applianceId + '"', '"' + switchType + '"',
        '"' + self.applianceId + '"', '"' + switchType + '"'))
        submit = {
            "header": {
                "namespace": "DuerOS.ConnectedHome.Control",
                "name": headerName,
                "payloadVersion": 3
            },
            "payload": payload
        }
        flag = await self.send_command(submit)
        return flag[0]

    async def press_ir_button(self, button_name: str, button_id: int = None, support_actions: list = None):
        """按下红外按钮 - 使用抓包得到的正确格式"""
        _LOGGER.warning("press_ir_button 调用: button_name=%s, button_id=%s", button_name, button_id)

        # 使用抓包得到的正确格式: PressLearnedBtnRequest + btnIndex
        submit = {
            "header": {"namespace": "DuerOS.ConnectedHome.Control", "name": "PressLearnedBtnRequest", "payloadVersion": 1},
            "payload": {"btnIndex": button_id, "applianceId": self.applianceId,
                        "parameters": {"proxyConnectStatus": False}}}
        _LOGGER.warning("press_ir_button 发送: %s", str(submit))
        result = await self.send_command(submit)
        _LOGGER.warning("press_ir_button 结果: %s", result)
        return result

    async def send_command(self, submit: dict):
        api = "/saiya/smarthome/directivesend?from=h5_control"
        try:
            _LOGGER.warning("send_command 发送URL: %s", HOST + api)
            _LOGGER.warning("send_command 发送数据: %s", str(submit))
            res = await self.Session.post(HOST + api, headers=self.Header, json=submit,
                                         cookies={"HOUSE_ID": self.houseId})
            text = await res.text()
            _LOGGER.warning("send_command 返回状态码: %s, 内容: %s", res.status, text)
            json_data = await res.json()
            if json_data['status'] == 0:
                return [True, None]
            if json_data['msg'] == 'not login':
                return [False, "cookie失效喔，请及时更新"]
            return [False, json_data['msg']]
        except Exception as e:
            logging.error("请求小度出错: %s", e)
            return [False, "请求小度出错"]

    def _common_header(self):
        return {
            "Cookie": f"BDUSS={self.cookie};BDUSS_BFESS={self.cookie}",
            "User-Agent": 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
            "content-type": "application/json",
            "device-id": "deviceid",
            "host": "xiaodu.baidu.com",
        }
