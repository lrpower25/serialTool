# serialTool

macOS 串口工具，通过友好交互菜单封装 [minicom](https://salsa.debian.org/minicom-team/minicom)，简化串口调试流程。

## 环境要求

- macOS
- Python 3.9+
- minicom（通过 Homebrew 安装）

```bash
brew install minicom
```

## 快速开始

```bash
# 交互式选择串口、波特率并连接
python3 serialTool.py

# 使用上次配置直接重连
python3 serialTool.py -r

# 指定设备与波特率直连
python3 serialTool.py -d /dev/cu.usbserial-xxx -b 115200
```

## 命令行参数

| 参数 | 说明 |
|------|------|
| `-r`, `--reconnect` | 使用上次保存的配置直接连接 |
| `-p NAME`, `--profile NAME` | 使用已保存的命名连接 |
| `-s`, `--select` | 从已保存的连接中交互选择 |
| `-l`, `--list` | 列出所有已保存的连接 |
| `--save NAME` | 将当前参数保存为命名连接 |
| `--delete NAME` | 删除已保存的命名连接 |
| `-d PATH`, `--device PATH` | 串口设备路径，如 `/dev/cu.usbserial-xxx` |
| `-b RATE`, `--baud RATE` | 波特率，如 `115200` |
| `--flow-control` | 启用硬件流控 (RTS/CTS) |
| `--capture` | 开启会话日志 |
| `--log-dir DIR` | 日志保存目录（指定后自动开启日志） |

### 使用示例

```bash
# 列出已保存的连接
python3 serialTool.py -l

# 保存一条命名连接（设备未插入时也可仅保存配置）
python3 serialTool.py -d /dev/cu.usbserial-xxx -b 115200 --save my-board

# 使用命名连接
python3 serialTool.py -p my-board

# 直连并开启日志
python3 serialTool.py -d /dev/cu.usbserial-xxx -b 115200 --capture --log-dir ~/serial-logs

# 删除命名连接
python3 serialTool.py --delete my-board
```

## 配置文件

工具会在以下位置读写配置：

| 路径 | 说明 |
|------|------|
| `~/.config/serialTool/last.json` | 上次连接参数 |
| `~/.config/serialTool/profiles.json` | 已保存的命名连接 |
| `~/.minirc.serialTool` | 自动生成的 minicom 配置文件 |

## minicom 快捷键

minicom 使用 **前缀键** 机制：先按 `Ctrl+A`，松开后按下一个键。

> 如需向设备发送字面量 `Ctrl+A`，连续按两次 `Ctrl+A`。

### 常用操作

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+A` `X` | 退出 minicom |
| `Ctrl+A` `Z` | 打开帮助菜单（列出所有快捷键） |
| `Ctrl+A` `C` | 清屏 |
| `Ctrl+A` `L` | 开关会话日志捕获 |
| `Ctrl+A` `Q` | 开始/停止录制会话日志 |
| `Ctrl+A` `U` | 暂停/恢复输出显示 |
| `Ctrl+A` `W` | 开关自动换行 |

### 通信与参数

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+A` `P` | 通信参数（波特率、数据位、校验位、流控等） |
| `Ctrl+A` `T` | 终端设置（终端类型、换行等） |
| `Ctrl+A` `F` | 开关硬件流控 (RTS/CTS) |
| `Ctrl+A` `A` | 开关本地回显 |
| `Ctrl+A` `I` | 开关自动换行（CR → CRLF） |
| `Ctrl+A` `J` | 开关 CR/LF 转换 |
| `Ctrl+A` `M` | 发送 Break 信号 |
| `Ctrl+A` `N` | 发送较长 Break 信号 |

### 文件传输

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+A` `S` | 发送文件（ZMODEM 等协议） |
| `Ctrl+A` `R` | 接收文件（ZMODEM 等协议） |

### 滚动与书签

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+A` `↑` | 向上滚动 |
| `Ctrl+A` `↓` | 向下滚动 |
| `Ctrl+A` `B` | 添加书签 |
| `Ctrl+A` `G` | 跳转到书签 |
| `Ctrl+A` `K` | 清除书签 |

### 其他

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+A` `O` | 打开 minicom 配置菜单 |
| `Ctrl+A` `V` | 查看版本信息 |
| `Ctrl+A` `E` | 切换到后台（挂起 minicom） |
| `Ctrl+A` `H` | 挂断（Hangup） |

## 常见问题

**未检测到串口设备**

1. 确认 USB 串口线已插入
2. 安装对应驱动（CH340 / CP210x / FTDI 等）
3. 检查设备是否出现在 `/dev/cu.*` 下

**权限不足**

确保当前用户有权限访问串口设备，必要时重新插拔设备或检查驱动状态。

**串口设备不存在**

保存的命名连接中设备路径可能已变化（如重新插拔后后缀改变），请重新运行交互菜单选择可用设备。
