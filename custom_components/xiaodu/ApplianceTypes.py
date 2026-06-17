class ApplianceTypes:
    def __init__(self):
        pass

    def LIGHT(self):
        return ['LIGHT']

    def SWITCH(self):
        return ['SOCKET', 'WASHING_MACHINE', 'SWITCH', 'HEATER', 'WINDOW_OPENER', 'FAN', 'AIR_FRESHER']

    def COVER(self):
        return ['CURTAIN']

    def CLIMATE(self):
        return ['AIR_CONDITION']

    def BUTTON(self):
        return ['CLOTHES_RACK']

    def LOCK(self):
        return ['DOOR_LOCK']

    def is_switch(self, applianceTypes):
        for i in applianceTypes:
            if i in self.SWITCH():
                return True
        return False

    def is_fan(self, applianceTypes):
        # 风扇不再单独分类，都归为开关（因为大多数是红外多按钮设备）
        return False

    def is_light(self, applianceTypes):
        for i in applianceTypes:
            if i in self.LIGHT():
                return True
        return False

    def is_cover(self, applianceTypes):
        for i in applianceTypes:
            if i in self.COVER():
                return True
        return False

    def is_climate(self, applianceTypes):
        for i in applianceTypes:
            if i in self.CLIMATE():
                return True
        return False

    def is_button(self, applianceTypes):
        for i in applianceTypes:
            if i in self.BUTTON():
                return True
        return False

    def is_lock(self, applianceTypes):
        for i in applianceTypes:
            if i in self.LOCK():
                return True
        return False

    def has_panels(self, appliance):
        """检查设备是否有多按钮面板"""
        if 'panels' in appliance and isinstance(appliance['panels'], list):
            for panel_group in appliance['panels']:
                if isinstance(panel_group, dict) and 'list' in panel_group:
                    panel_list = panel_group['list']
                    if isinstance(panel_list, list) and len(panel_list) > 0:
                        return True
        return False

    def has_ir_btns(self, appliance):
        """检查设备是否有红外按钮（自定义红外学习设备）"""
        return 'irBtns' in appliance and isinstance(appliance['irBtns'], list) and len(appliance['irBtns']) > 0
