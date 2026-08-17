#!/usr/bin/env python3
"""macOS 串口工具：友好菜单封装 minicom。"""

from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CONFIG_DIR = Path.home() / ".config" / "serialTool"
LAST_CONFIG_PATH = CONFIG_DIR / "last.json"
PROFILES_PATH = CONFIG_DIR / "profiles.json"
MINICOM_PROFILE = "serialTool"
MINICOM_PROFILE_PATH = Path.home() / f".minirc.{MINICOM_PROFILE}"

IGNORED_PORT_SUFFIXES = (
    "Bluetooth-Incoming-Port",
    "debug-console",
)

COMMON_BAUD_RATES = (
    "9600",
    "19200",
    "38400",
    "57600",
    "115200",
    "230400",
    "460800",
    "921600",
    "1500000",
)


def printError(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr, flush=True)


def ensureMinicomAvailable() -> str:
    minicomPath = shutil.which("minicom")
    if minicomPath:
        return minicomPath
    printError("未找到 minicom，请先安装：brew install minicom")
    sys.exit(1)


def listSerialPorts(showAll: bool = False) -> list[str]:
    ports = sorted(glob.glob("/dev/cu.*"))
    if showAll:
        return ports
    return [
        port
        for port in ports
        if not any(port.endswith(suffix) for suffix in IGNORED_PORT_SUFFIXES)
    ]


def loadJsonFile(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def saveJsonFile(path: Path, data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def loadLastConfig() -> dict[str, Any]:
    return loadJsonFile(LAST_CONFIG_PATH)


def saveLastConfig(config: dict[str, Any]) -> None:
    saveJsonFile(LAST_CONFIG_PATH, config)


def loadProfiles() -> dict[str, dict[str, Any]]:
    data = loadJsonFile(PROFILES_PATH)
    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for name, config in profiles.items():
        if isinstance(name, str) and isinstance(config, dict):
            result[name] = config
    return result


def saveProfiles(profiles: dict[str, dict[str, Any]]) -> None:
    saveJsonFile(PROFILES_PATH, {"profiles": profiles})


def normalizeLogDir(logDir: Any) -> str:
    if not isinstance(logDir, str):
        return ""
    return logDir.strip()


def normalizeConnectionConfig(config: dict[str, Any]) -> dict[str, Any]:
    capture = bool(config.get("capture", False))
    logDir = normalizeLogDir(config.get("logDir", ""))
    result = {
        "port": config["port"],
        "baudRate": str(config["baudRate"]),
        "flowControl": bool(config.get("flowControl", False)),
        "capture": capture,
        "logDir": logDir if capture else "",
    }
    return result


def formatProfileSummary(name: str, config: dict[str, Any]) -> str:
    flow = "流控开" if config.get("flowControl") else "流控关"
    if config.get("capture"):
        logDir = normalizeLogDir(config.get("logDir", "")) or "."
        capture = f"日志:{logDir}"
    else:
        capture = "日志关"
    return (
        f"{name}  ({config.get('port', '?')}, "
        f"{config.get('baudRate', '?')}, {flow}, {capture})"
    )


def resolveCapturePath(logDir: str = "") -> str:
    directory = Path(logDir).expanduser() if logDir.strip() else Path.cwd()
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        printError(f"无法创建日志目录：{directory}")
        printError(str(error))
        sys.exit(1)
    if not directory.is_dir():
        printError(f"日志路径不是目录：{directory}")
        sys.exit(1)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return str(directory / f"LOG-{timestamp}.log")


def validateProfileName(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        printError("连接名称不能为空")
        sys.exit(1)
    if any(ch in cleaned for ch in ("/", "\\", "\0")):
        printError("连接名称不能包含路径分隔符")
        sys.exit(1)
    return cleaned


def saveNamedProfile(name: str, config: dict[str, Any]) -> None:
    profileName = validateProfileName(name)
    profiles = loadProfiles()
    profiles[profileName] = normalizeConnectionConfig(config)
    saveProfiles(profiles)
    print(f"已保存连接：{profileName}", flush=True)


def deleteNamedProfile(name: str) -> None:
    profileName = validateProfileName(name)
    profiles = loadProfiles()
    if profileName not in profiles:
        printError(f"未找到连接：{profileName}")
        sys.exit(1)
    del profiles[profileName]
    saveProfiles(profiles)
    print(f"已删除连接：{profileName}", flush=True)


def getNamedProfile(name: str) -> dict[str, Any]:
    profileName = validateProfileName(name)
    profiles = loadProfiles()
    config = profiles.get(profileName)
    if not config:
        printError(f"未找到连接：{profileName}")
        printError("可用连接可用 --list 查看。")
        sys.exit(1)
    return normalizeConnectionConfig(config)


def listNamedProfiles() -> None:
    profiles = loadProfiles()
    if not profiles:
        print("暂无已保存的连接。")
        print("新建连接后可选择保存，或使用：")
        print("  python3 serialTool.py -d /dev/cu.xxx -b 115200 --save 名称")
        return
    print("已保存的连接：")
    for name in sorted(profiles):
        print(f"  {formatProfileSummary(name, profiles[name])}")
    print("\n使用方式：")
    print("  python3 serialTool.py -p 名称")
    print("  python3 serialTool.py --select")


def promptChoice(prompt: str, options: list[str], defaultIndex: int | None = None) -> int:
    if not options:
        raise ValueError("选项列表不能为空")

    for index, option in enumerate(options, start=1):
        marker = " *" if defaultIndex is not None and index - 1 == defaultIndex else ""
        print(f"  {index}. {option}{marker}")

    defaultHint = ""
    if defaultIndex is not None and 0 <= defaultIndex < len(options):
        defaultHint = f"，直接回车使用 [{defaultIndex + 1}]"

    while True:
        raw = input(f"{prompt}{defaultHint}: ").strip()
        if not raw and defaultIndex is not None and 0 <= defaultIndex < len(options):
            return defaultIndex
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(options):
                return choice - 1
        print(f"请输入 1-{len(options)} 之间的数字")


def promptYesNo(prompt: str, defaultYes: bool = False) -> bool:
    defaultText = "Y/n" if defaultYes else "y/N"
    while True:
        raw = input(f"{prompt} [{defaultText}]: ").strip().lower()
        if not raw:
            return defaultYes
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("请输入 y 或 n")


def selectSerialPort(lastPort: str | None = None) -> str:
    ports = listSerialPorts(showAll=False)
    showAll = False

    while True:
        if not ports:
            if not showAll:
                allPorts = listSerialPorts(showAll=True)
                if allPorts:
                    print("未找到常用串口设备，以下为全部 /dev/cu.*：")
                    ports = allPorts
                    showAll = True
                    continue
            printError("未检测到串口设备。")
            print("请检查：")
            print("  1. USB 串口线是否已插入")
            print("  2. 驱动是否已安装（如 CH340 / CP210x / FTDI）")
            print("  3. 设备是否出现在 /dev/cu.*")
            sys.exit(1)

        print("\n可用串口：")
        options = list(ports)
        if not showAll:
            options.append("显示全部设备")

        defaultIndex = None
        if lastPort and lastPort in ports:
            defaultIndex = ports.index(lastPort)

        choice = promptChoice("请选择串口", options, defaultIndex)
        if not showAll and choice == len(ports):
            ports = listSerialPorts(showAll=True)
            showAll = True
            continue
        return ports[choice]


def selectBaudRate(lastBaud: str | None = None) -> str:
    print("\n波特率：")
    options = list(COMMON_BAUD_RATES) + ["自定义"]
    defaultIndex = None
    if lastBaud in COMMON_BAUD_RATES:
        defaultIndex = COMMON_BAUD_RATES.index(lastBaud)
    elif lastBaud:
        defaultIndex = len(COMMON_BAUD_RATES)

    choice = promptChoice("请选择波特率", options, defaultIndex)
    if choice < len(COMMON_BAUD_RATES):
        return COMMON_BAUD_RATES[choice]

    defaultCustom = lastBaud if lastBaud and lastBaud not in COMMON_BAUD_RATES else ""
    while True:
        hint = f"，直接回车使用 [{defaultCustom}]" if defaultCustom else ""
        raw = input(f"请输入自定义波特率{hint}: ").strip()
        if not raw and defaultCustom:
            raw = defaultCustom
        if raw.isdigit() and int(raw) > 0:
            return raw
        print("请输入正整数波特率，例如 921600")


def selectLogDir(lastLogDir: str = "") -> str:
    defaultDir = lastLogDir.strip() or str(Path.cwd())
    while True:
        raw = input(f"日志保存目录，直接回车使用 [{defaultDir}]: ").strip()
        chosen = raw or defaultDir
        directory = Path(chosen).expanduser()
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            print(f"无法创建目录：{error}")
            continue
        if not directory.is_dir():
            print("路径不是目录，请重新输入")
            continue
        return str(directory.resolve())


def selectOptions(lastConfig: dict[str, Any]) -> tuple[bool, bool, str]:
    print("\n可选设置：")
    lastFlowControl = bool(lastConfig.get("flowControl", False))
    lastCapture = bool(lastConfig.get("capture", False))
    lastLogDir = normalizeLogDir(lastConfig.get("logDir", ""))
    flowControl = promptYesNo("启用硬件流控 (RTS/CTS)", defaultYes=lastFlowControl)
    capture = promptYesNo("开启会话日志", defaultYes=lastCapture)
    logDir = selectLogDir(lastLogDir) if capture else ""
    return flowControl, capture, logDir


def writeMinicomProfile(port: str, baudRate: str, flowControl: bool) -> None:
    rtscts = "Yes" if flowControl else "No"
    content = (
        "# Generated by serialTool.py — do not edit by hand\n"
        f"pu port             {port}\n"
        f"pu baudrate         {baudRate}\n"
        "pu bits             8\n"
        "pu parity           N\n"
        "pu stopbits         1\n"
        f"pu rtscts           {rtscts}\n"
        "pu xonxoff          No\n"
    )
    MINICOM_PROFILE_PATH.write_text(content, encoding="utf-8")


def buildMinicomCommand(
    port: str,
    baudRate: str,
    capture: bool,
    capturePath: str | None = None,
    logDir: str = "",
) -> list[str]:
    command = [
        "minicom",
        "-D",
        port,
        "-b",
        baudRate,
        "-c",
        "on",
        "-o",
    ]
    if capture:
        if not capturePath:
            capturePath = resolveCapturePath(logDir)
        command.extend(["-C", capturePath])
    command.append(MINICOM_PROFILE)
    return command


def printMinicomTips(port: str, baudRate: str, flowControl: bool, capturePath: str | None) -> None:
    print("\n即将启动 minicom")
    print(f"  设备：{port}")
    print(f"  波特率：{baudRate}")
    print(f"  硬件流控：{'开' if flowControl else '关'}")
    if capturePath:
        print(f"  日志文件：{capturePath}")
    print("\n常用快捷键（先按 Ctrl+A，再按下一个键）：")
    print("  X  退出")
    print("  Z  帮助")
    print("  C  清屏")
    print()


def launchMinicom(command: list[str]) -> None:
    print(f"执行：{' '.join(command)}\n")
    try:
        os.execvp(command[0], command)
    except OSError as error:
        printError(f"启动 minicom 失败：{error}")
        print("请检查串口线缆、驱动，以及当前用户是否有权限访问该设备。")
        sys.exit(1)


def connectWithConfig(
    config: dict[str, Any],
    profileName: str | None = None,
    saveAs: str | None = None,
) -> None:
    port = config.get("port")
    baudRate = str(config.get("baudRate", ""))
    flowControl = bool(config.get("flowControl", False))
    capture = bool(config.get("capture", False))
    logDir = normalizeLogDir(config.get("logDir", ""))

    if not port or not baudRate:
        printError("配置不完整，缺少端口或波特率")
        sys.exit(1)
    if not Path(port).exists():
        printError(f"串口设备不存在：{port}")
        printError("请重新运行交互菜单选择可用设备。")
        sys.exit(1)
    if not baudRate.isdigit() or int(baudRate) <= 0:
        printError(f"无效波特率：{baudRate}")
        sys.exit(1)

    connection = normalizeConnectionConfig(
        {
            "port": port,
            "baudRate": baudRate,
            "flowControl": flowControl,
            "capture": capture,
            "logDir": logDir,
        }
    )

    if saveAs:
        saveNamedProfile(saveAs, connection)
    if profileName:
        print(f"使用连接：{profileName}", flush=True)

    capturePath = resolveCapturePath(connection["logDir"]) if capture else None

    writeMinicomProfile(port, baudRate, flowControl)
    lastConfig = dict(connection)
    if profileName or saveAs:
        lastConfig["profileName"] = profileName or saveAs
    saveLastConfig(lastConfig)
    command = buildMinicomCommand(
        port,
        baudRate,
        capture,
        capturePath=capturePath,
        logDir=connection["logDir"],
    )
    printMinicomTips(port, baudRate, flowControl, capturePath)
    launchMinicom(command)


def promptSaveProfile(config: dict[str, Any]) -> str | None:
    if not promptYesNo("保存为命名连接", defaultYes=False):
        return None
    profiles = loadProfiles()
    while True:
        name = input("连接名称: ").strip()
        if not name:
            print("名称不能为空")
            continue
        if any(ch in name for ch in ("/", "\\", "\0")):
            print("名称不能包含路径分隔符")
            continue
        if name in profiles and not promptYesNo(f"连接「{name}」已存在，是否覆盖", defaultYes=False):
            continue
        saveNamedProfile(name, config)
        return name


def collectNewConnection(lastConfig: dict[str, Any] | None = None) -> dict[str, Any]:
    base = lastConfig or {}
    port = selectSerialPort(base.get("port"))
    baudRate = selectBaudRate(str(base["baudRate"]) if "baudRate" in base else None)
    flowControl, capture, logDir = selectOptions(base)
    return normalizeConnectionConfig(
        {
            "port": port,
            "baudRate": baudRate,
            "flowControl": flowControl,
            "capture": capture,
            "logDir": logDir,
        }
    )


def selectSavedProfile(requireChoice: bool = False) -> tuple[str, dict[str, Any]] | None:
    profiles = loadProfiles()
    if not profiles:
        if requireChoice:
            printError("暂无已保存的连接。")
            printError("请先新建并保存连接，或使用 --save 保存。")
            sys.exit(1)
        return None

    names = sorted(profiles)
    lastConfig = loadLastConfig()
    defaultIndex = None
    lastName = lastConfig.get("profileName")
    if isinstance(lastName, str) and lastName in names:
        defaultIndex = names.index(lastName)

    print("\n已保存的连接：")
    options = [formatProfileSummary(name, profiles[name]) for name in names]
    if not requireChoice:
        options.append("新建连接")

    choice = promptChoice("请选择连接", options, defaultIndex)
    if not requireChoice and choice == len(names):
        return None
    name = names[choice]
    return name, normalizeConnectionConfig(profiles[name])


def runInteractive() -> None:
    profiles = loadProfiles()
    if profiles:
        selected = selectSavedProfile(requireChoice=False)
        if selected:
            name, config = selected
            connectWithConfig(config, profileName=name)
            return

    lastConfig = loadLastConfig()
    config = collectNewConnection(lastConfig)
    profileName = promptSaveProfile(config)
    connectWithConfig(config, profileName=profileName, saveAs=None)


def runSelectProfile() -> None:
    selected = selectSavedProfile(requireChoice=True)
    assert selected is not None
    name, config = selected
    connectWithConfig(config, profileName=name)


def runReconnect() -> None:
    lastConfig = loadLastConfig()
    if not lastConfig:
        printError("没有上次连接记录，请先运行交互菜单完成一次连接。")
        sys.exit(1)
    profileName = lastConfig.get("profileName")
    if isinstance(profileName, str) and profileName:
        print(f"使用上次连接重连：{profileName}", flush=True)
        connectWithConfig(lastConfig, profileName=profileName)
        return
    print("使用上次配置重连…", flush=True)
    connectWithConfig(lastConfig)


def parseArgs(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="macOS 串口工具：通过友好菜单启动 minicom",
    )
    parser.add_argument(
        "-r",
        "--reconnect",
        action="store_true",
        help="使用上次保存的配置直接连接",
    )
    parser.add_argument(
        "-p",
        "--profile",
        help="使用已保存的命名连接直接连接",
    )
    parser.add_argument(
        "-s",
        "--select",
        action="store_true",
        help="从已保存的连接中交互选择",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="列出已保存的连接",
    )
    parser.add_argument(
        "--save",
        metavar="NAME",
        help="将当前连接参数保存为命名连接（可与 -d/-b 或连接时一起使用）",
    )
    parser.add_argument(
        "--delete",
        metavar="NAME",
        help="删除已保存的命名连接",
    )
    parser.add_argument(
        "-d",
        "--device",
        help="串口设备路径，例如 /dev/cu.usbserial-xxx",
    )
    parser.add_argument(
        "-b",
        "--baud",
        dest="baudRate",
        help="波特率，例如 115200",
    )
    parser.add_argument(
        "--flow-control",
        action="store_true",
        help="启用硬件流控 (RTS/CTS)",
    )
    parser.add_argument(
        "--capture",
        action="store_true",
        help="开启会话日志",
    )
    parser.add_argument(
        "--log-dir",
        dest="logDir",
        metavar="DIR",
        help="会话日志保存目录（指定后自动开启日志）",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parseArgs(argv)

    if args.list:
        listNamedProfiles()
        return

    if args.delete:
        deleteNamedProfile(args.delete)
        return

    ensureMinicomAvailable()

    exclusiveFlags = [
        flag
        for flag, enabled in (
            ("-r/--reconnect", args.reconnect),
            ("-p/--profile", bool(args.profile)),
            ("-s/--select", args.select),
            ("-d/-b", bool(args.device or args.baudRate)),
        )
        if enabled
    ]
    if len(exclusiveFlags) > 1:
        printError(f"不能同时使用：{', '.join(exclusiveFlags)}")
        sys.exit(1)

    if args.reconnect:
        runReconnect()
        return

    if args.profile:
        config = getNamedProfile(args.profile)
        connectWithConfig(config, profileName=args.profile)
        return

    if args.select:
        runSelectProfile()
        return

    if args.device or args.baudRate:
        if not args.device or not args.baudRate:
            printError("直连模式需要同时指定 -d 与 -b")
            sys.exit(1)
        logDir = normalizeLogDir(args.logDir or "")
        capture = args.capture or bool(logDir)
        config = {
            "port": args.device,
            "baudRate": args.baudRate,
            "flowControl": args.flow_control,
            "capture": capture,
            "logDir": logDir,
        }
        if args.save and not Path(args.device).exists():
            # 允许仅保存配置、设备当前未插入
            saveNamedProfile(args.save, config)
            return
        connectWithConfig(config, saveAs=args.save)
        return

    if args.save:
        printError("--save 需配合 -d/-b 使用，或在交互新建连接时选择保存")
        sys.exit(1)

    runInteractive()


if __name__ == "__main__":
    main()
