# Xiaodu-HomeAssistant 集成（改版）

本项目基于 [apgmer/hass-xiaodu](https://github.com/apgmer/hass-xiaodu) 二次开发，主要新增了对**风扇**及**自定义设备**的支持，让更多设备类型可以接入小度。

---

## 主要改进

- ✅ 支持风扇设备（开关、风速、模式等）
- ✅ 支持用户自定义设备类型，灵活扩展
- ✅ 继承原版所有基础功能

---

## 安装步骤

### 1. 通过 HACS 安装

1. 打开 Home Assistant，进入 **HACS** 界面。
2. 点击右上角三个点（更多菜单），选择 **“自定义仓库”**（Custom repositories）。
3. 填写以下信息：
   - **仓库地址**：`https://github.com/biliemo6666/Xiaodu-homeassistant`
   - **类型**：选择 **“集成”**（Integration）
4. 点击 **“新增”**，稍等片刻，列表中会出现 **“小度 Home Assistant 集成”**。
5. 关闭窗口，在 HACS 集成列表中找到该条目，点击进入，然后点击 **“下载”** 按钮，在弹出窗口中确认下载。
6. 下载完成后，**重启 Home Assistant** 使集成生效。

### 2. 添加集成

1. 重启后，进入 **设置 → 设备与服务**，点击右下角的 **“添加集成”**。
2. 在搜索框中输入 **“小度”**，找到并点击该集成。
3. 系统会提示输入 **Cookie**（获取方法见下文第 3 步）。

### 3. 获取小度 Cookie

1. 使用浏览器访问 [小度智能家居官网](https://xiaodu.baidu.com/saiya/smarthome/index.html)，并登录您的小度账号。
2. 按 **F12** 键（或通过浏览器右上角菜单 → 更多工具 → 开发者工具）打开开发者工具。
3. 切换到 **“网络”**（Network）选项卡，然后刷新当前页面。
4. 在请求列表中找到最下方的 `weirwood?type=perf` 请求，点击它。
5. 在打开的详情中，切换到 **“Cookie”** 标签，找到名为 **`BDUSS_BFESS`** 的条目，**复制其值**——这就是您需要的 Cookie。
6. 将复制的 Cookie 粘贴到 Home Assistant 集成配置框中，然后按提示选择 **`houseid`** 和 **`device_id`**，即可完成接入。

---

## 注意事项（引用自原项目）

> - Cookie 具有时效性，过期后需重新获取并更新集成配置。
> - **在小度 App 或其他厂商 App 中直接操作设备开关后，小度可能无法自动同步最新状态**，请以 Home Assistant 中的状态为准。
> - 本项目为作者边学习边开发，可能存在一些未知问题，欢迎反馈和 PR。

---

## 反馈与贡献

如遇到问题或有改进建议，欢迎在 [GitHub Issues](https://github.com/biliemo6666/Xiaodu-homeassistant/issues) 中提出。也欢迎提交 Pull Request 共同完善。

祝使用愉快！🎉
