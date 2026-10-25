#!/usr/bin/env python3
"""
patch_bcbtums.py - 给戴尔博通蓝牙驱动包的 bcbtums.inf 加入 Apple Boot Camp 硬件 ID
原创：三亚0038

用法: python patch_bcbtums.py <解压后的驱动64位目录路径>
示例: python patch_bcbtums.py "C:\\Downloads\\Win10_12.0.1.944_USB_Driver_Package\\64"
可选参数: --pid 8290  (Apple 蓝牙的 PID，默认 8290，见设备管理器硬件 ID)
"""
import argparse
import shutil
import sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("driver_dir", help="解压后的驱动 64 位目录")
    ap.add_argument("--pid", default="8290", help="Apple 蓝牙 USB PID（默认 8290）")
    ap.add_argument("--vid", default="05AC", help="Apple 蓝牙 USB VID（默认 05AC）")
    args = ap.parse_args()

    d = Path(args.driver_dir)
    inf_path = d / "bcbtums.inf"
    if not inf_path.exists():
        sys.exit(f"[错误] 找不到 {inf_path}，请确认目录正确")

    hwid = f"USB\\VID_{args.vid.upper()}&PID_{args.pid.upper()}"
    raw = inf_path.read_bytes()
    text = raw.decode("utf-8") if b"\x00" not in raw[:200] else raw.decode("utf-16")
    if "VID_" + args.vid.upper() in text:
        print("[跳过] INF 中已存在 Apple 硬件 ID，无需重复修改")
        return

    if not text.count("USB\\VID_0A5C&PID_6410"):
        sys.exit("[错误] 未找到 BCM20703A1 (RAMUSB6410/DW1830) 条目，驱动包版本可能不符")

    backup = inf_path.with_suffix(".inf.bak")
    shutil.copy2(inf_path, backup)
    print(f"[备份] {backup}")

    lines = text.splitlines()
    out = []
    anchor = "USB\\VID_0A5C&PID_6410"  # DW1830 行，同一芯片的安装节
    for line in lines:
        out.append(line)
        if anchor in line and line.strip().startswith("%DW1830.DeviceDesc%"):
            indent = " " * 13
            out.append(f"%AppleMBP.DeviceDesc%=RAMUSB6410,{indent}{hwid}       ; 20703A1 Apple MacBookPro (patched)")
            print(f"[加入] 设备条目 -> {hwid} => RAMUSB6410")

    # Strings 节加设备描述
    for i, line in enumerate(out):
        if line.strip() == "[Strings]":
            # 找到 [Strings] 节末尾（下一个节开始前）
            j = i + 1
            while j < len(out) and not out[j].strip().startswith("["):
                j += 1
            out.insert(j, 'AppleMBP.DeviceDesc=                              "Apple MacBook Pro Bluetooth (BCM20703A1)"')
            print("[加入] Strings 节设备描述")
            break

    new_text = "\r\n".join(out) + "\r\n"
    inf_path.write_text(new_text, encoding="utf-8", newline="")
    print(f"[完成] {inf_path} 已修改，共修改 2 处")
    print("下一步：按 README 第 4 步，在禁用驱动签名的模式下用设备管理器安装该目录")

if __name__ == "__main__":
    main()
