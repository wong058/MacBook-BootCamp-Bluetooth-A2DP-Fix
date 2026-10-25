# Boot Camp 蓝牙耳机 A2DP 无声修复（BCM20703）

> **原创：三亚0038**
>
> 适用场景：2015 款 MacBook Pro（及类似 Boot Camp 机型）装 Windows 10 后，蓝牙耳机显示"已连接"，但声音始终从扬声器播出，且输出设备列表里没有耳机（只有 `-LE` 结尾的条目）。

## 问题现象

- 蓝牙耳机（如 JBL Tune 770NC）在 Windows 10 下配对成功、状态"已连接"
- 但系统里**没有任何蓝牙音频播放端点**（A2DP "Stereo" 端点不出现）
- 耳机只以 BLE（低功耗）模式注册了 GATT 服务，经典蓝牙音频层（A2DP/AVRCP）协商失败
- 同一副耳机在 macOS 下完全正常

## 根本原因

Boot Camp 的 Apple 蓝牙驱动 `AppleBTBC`（版本 6.0.6100.0，2015 年 7 月）**从未更新过**——经解包验证，Apple 官方 Boot Camp 6.0 与 6.1 驱动包内的蓝牙驱动完全相同。这套 11 年前的协议栈无法与新式耳机（BLE 优先配对流程）协商建立 A2DP 音频通道。

修复思路：用**戴尔官方发布的博通蓝牙 12.0.1.944 驱动**（同样支持 BCM20703 芯片，协议栈新得多）替换 Apple 的老驱动。但 Dell 的 INF 只认博通自家 VID（`0A5C`），Apple 硬件是 Apple VID（`05AC`），因此需要**修改 INF 加入 Apple 硬件 ID**。

## 适用硬件

- 蓝牙芯片：Broadcom BCM20703（2015 款 MacBook Pro 12,1 / 13,1 / 11,x 等 Boot Camp 机型）
- 确认方法：设备管理器 → 蓝牙 → "Apple Broadcom Built-in Bluetooth" → 属性 → 详细信息 → 硬件 ID，应看到 `USB\VID_05AC&PID_8290`（或相近 PID）

## 修复步骤

### 第 1 步：备份当前驱动（可回滚）

管理员 PowerShell：

```powershell
# 查看当前驱动 INF 名称（记下 oemXX.inf）
pnputil /enum-drivers | Select-String -Context 2,0 "applebtbc"

# 导出备份（把 oem0.inf 换成你查到的名称）
mkdir C:\bt-backup
pnputil /export-driver oem0.inf C:\bt-backup
```

### 第 2 步：下载戴尔官方驱动包

下载 Dell Wireless 1820A/1830 蓝牙驱动 12.0.1.944（约 14 MB）：

- 官方页面：https://www.dell.com/support/home/drivers/driversdetails?driverid=7x3jx
- 直链：https://dl.dell.com/FOLDER04632447M/3/Win10_12.0.1.944_USB_x86-x64_Installer_SETUP_ZPE.exe
- SHA-256：`e9fe762a679932ac62df8882d911fd44fa2308df474ed871e1eec5c0127e4ef7`

用 7-Zip 等工具直接解压该 EXE，得到 `Win10_12.0.1.944_USB_Driver_Package\64\` 目录。

### 第 3 步：修改 INF（运行本仓库的脚本）

```powershell
python patch_bcbtums.py "解压路径\Win10_12.0.1.944_USB_Driver_Package\64"
```

脚本做两件事（也可手动改）：

1. 在 `bcbtums.inf` 的 `[Broadcom.NTamd64.10.0]` 和 `[Broadcom.NTamd64.6.3]` 设备清单中，紧跟 DW1830 条目后加入一行：
   ```ini
   %AppleMBP.DeviceDesc%=RAMUSB6410,             USB\VID_05AC&PID_8290       ; 20703A1 Apple MacBookPro
   ```
2. 在 `[Strings]` 节加入：
   ```ini
   AppleMBP.DeviceDesc=                              "Apple MacBook Pro Bluetooth (BCM20703A1)"
   ```

原理：把 Apple 的硬件 ID 指向 `RAMUSB6410` 安装节——这是 Dell DW1830（同为 BCM20703A1 芯片）的配置，含对应固件 `BCM20703A1_001.001.005.0214.0422.hex`。

> 如果你的 PID 不是 8290，把脚本中的 PID 改成你查到的值即可。

### 第 4 步：关闭驱动签名强制并安装（一次性）

修改过的 INF 不再匹配戴尔的 CAT 签名，需要关闭签名校验安装：

1. 按住 `Shift` 点击开始菜单「重启」（或 设置 → 恢复 → 高级启动）
2. 疑难解答 → 高级选项 → **启动设置** → 重启
3. 按 **7**（禁用驱动程序强制签名）
4. 进入系统后打开设备管理器 → 蓝牙 → 右键 **Apple Broadcom Built-in Bluetooth** → 更新驱动程序 → **浏览我的电脑** → 选择修改后的 `64` 目录
5. 弹出"无法验证发布者"警告时点「**仍要安装此驱动程序软件**」
6. 正常重启

### 第 5 步：重新配对耳机

删除耳机后重新配对。配对成功后，输出设备里应出现 **"耳机 (XXX Stereo)"** 而不再只是 `-LE` 结尾的条目。

## 回滚方法

设备管理器 → 蓝牙适配器 → 更新驱动程序 → 浏览我的电脑 → 指向第 1 步备份的目录（含 `applebtbc.inf`），即可还原原驱动。

## 常见问题

- **装完设备报错（代码 10/28）**：固件变体不匹配，把 `RAMUSB6410.CopyList` 和 `RAMUSB6410.NT.hw.reg` 里的 `0422.hex` 换成包内其他 BCM20703A1 固件（0414/0473/0481）再试
- **每次开机签名失效**：此方法仅在"禁用签名强制"的那次开机内有效，之后正常重启不影响已装驱动；若驱动被系统更新覆盖，重新执行第 4 步
- **配对后只有 LE**：长按耳机配对键约 10 秒清空耳机端配对记录后再配对

## 致谢与声明

- **方案原创：三亚0038**（实测验证于 MacBook Pro 12,1 + Windows 10 22H2 + JBL Tune 770NC，2026 年 10 月）
- 驱动文件版权归 Broadcom / Dell 所有，本仓库只提供 INF 修改脚本与教程，请从戴尔官方渠道下载驱动包
- 操作有风险，请务必备份；因使用本方案造成的任何问题由使用者自行承担
