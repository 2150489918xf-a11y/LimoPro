# LIMO Pro 网络故障排查与恢复

2026-11-18 实车记录。本次先用静态 IPv4 恢复 Windows 与小车之间的有线 SSH，再通过重新加载无线驱动恢复手机热点连接。

## 本次故障和处理结果

| 现象 | 查到的原因或失败阶段 | 实测奏效的处理 |
| --- | --- | --- |
| `ssh agilex@192.168.137.101` 报 `Connection refused` | `.101` 是 Windows「以太网 3」自己的地址，请求打到了 Windows 的 TCP 22 | 将车端直连地址设为 `.102`，再连车端地址 |
| 网线显示 1 Gbps，SSH 仍超时 | 车端 `eth0` 默认等待 DHCP，直连时没有获得 IPv4。曾通过链路本地 IPv6 登录，随后该连接也超时 | 电脑和小车各用一个同网段的静态 IPv4。已从 Windows 实际 SSH 登录 `.102` |
| 校园网 `ECUT-STUD` 和手机热点 `1` 都连不上 | `wlan0` 已启用、能扫描，尝试时反复记录 `ASSOC-REJECT status_code=1`。手机热点已确认是 2.4 GHz、信道 6、WPA2 | 关开 Wi‑Fi 后仍失败。重新加载 `rtl8822ce` 后，手机热点的关联、WPA2 握手和 DHCP 均成功 |
| 输入热点密码后仍报 `Secrets were required, but not provided` | NetworkManager 已收到首次输入，随后无线关联超时。它再次请求密码时没有可用的交互代理，最终报 `no-secrets` | 重载驱动后使用同一个热点和连接配置重试，握手成功 |

重载会让驱动重新初始化无线网卡。实测支持无线驱动或网卡的运行状态异常这一判断，最初的触发原因尚未确认。恢复后已从小车通过 `wlan0` ping 通手机热点网关。校园网重连和无线长期稳定性仍待验证。

## 1. 网线直连，先恢复 SSH

1. 用网线直连电脑和小车。在 Windows 的「以太网 3」设置 `192.168.137.101`、掩码 `255.255.255.0`，网关和 DNS 留空。
2. 在**小车本地终端**激活直连配置。现有 DHCP 配置可以继续用于通过路由器接入网络。

```bash
# 仅在直连配置不存在时创建一次
if ! nmcli connection show id 'LIMO USB wired direct' >/dev/null 2>&1; then
    sudo nmcli connection add type ethernet ifname eth0 \
        con-name 'LIMO USB wired direct' connection.autoconnect no \
        ipv4.method manual ipv4.addresses 192.168.137.102/24 \
        ipv4.never-default yes ipv6.method link-local ipv6.never-default yes
fi

sudo nmcli connection up id 'LIMO USB wired direct' ifname eth0
sudo systemctl start ssh
ip -br -4 address show dev eth0
systemctl is-active ssh
```

正常时显示 `eth0` 的 `192.168.137.102/24` 和 SSH 服务状态 `active`。直连配置关闭了自动连接，重启或重插网线后若 `.102` 丢失，可从小车本地终端再次执行 `nmcli connection up`。

3. 回到 **Windows PowerShell**，测试端口并登录。

```powershell
Test-NetConnection 192.168.137.102 -Port 22
ssh agilex@192.168.137.102
```

本次排查时 `ssh LimoPro` 仍指向旧的无线地址 `192.168.137.175`。有线直连用 `.102`，手机热点分配的地址用 `ip -br -4 address show dev wlan0` 查询。

## 2. 通过有线 SSH 排查并恢复 Wi‑Fi

保持网线接通，在小车终端检查无线状态、热点扫描结果和近期日志。

```bash
nmcli device status
rfkill list
nmcli -f SSID,CHAN,SIGNAL,SECURITY device wifi list ifname wlan0
sudo journalctl -b -u NetworkManager -u wpa_supplicant \
    --since '5 minutes ago' --no-pager | grep -E 'wlan0|nl80211' | tail -n 40
```

能扫到热点时，按日志定位失败阶段。`ASSOC-REJECT` 对应无线关联，`4-way handshake` 对应 WPA2 密钥协商，`dhcp4 (wlan0)` 对应获取 IPv4。先看日志发生的顺序，再判断是否需要检查密码或 DHCP。

本车**持续在关联阶段失败且关开 Wi‑Fi 无效**时，实测有效的是重新加载无线驱动。`rtl8822ce` 是车端核实的无线模块名。有线 `eth0` 使用独立的 `r8168` 驱动。

```bash
sudo modprobe -r rtl8822ce && sudo modprobe rtl8822ce
```

等几秒，确认手机热点仍开启，再重连已保存的热点 `1`。终端提示时输入热点密码。

```bash
sudo nmcli --ask --wait 45 connection up id '1' ifname wlan0
nmcli -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS,IP4.GATEWAY device show wlan0
```

如果小车尚未保存热点配置，首次连接使用 `sudo nmcli --ask --wait 45 device wifi connect '1' ifname wlan0`。连接后确认状态为 `connected`，有 IPv4 地址和网关，再通过无线接口测试网关。

```bash
gateway=$(nmcli -g IP4.GATEWAY device show wlan0)
ping -I wlan0 -c 2 "$gateway"
```

本次手机热点分配了 `172.23.239.170/24`，网关是 `172.23.239.226`，重连后以现场显示为准。

## 3. SSH 进不去时用 U 盘

本次使用的 `limo-network-recovery.sh` 放在 Windows 的 `D:\` U 盘根目录。将 U 盘插到小车，在 U 盘目录打开终端并执行：

```bash
bash ./limo-network-recovery.sh
```

脚本会尝试配置有线直连、检查 TCP 22 监听并收集网络日志。扫到热点 `1` 后，输入 `y` 再按提示输入热点密码，才会执行热点连接测试。报告默认写到 U 盘同一目录，文件名为 `limo-network-*.txt`。可以用报告里的 `eth0` 地址、SSH 状态和关联日志继续定位。
