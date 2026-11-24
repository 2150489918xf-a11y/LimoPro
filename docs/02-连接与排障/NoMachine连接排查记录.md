# NoMachine 连接 LIMO Pro 的排查记录

记录日期：2026 年 11 月 19 日。目标是在 Windows 电脑上使用 NoMachine 查看和操作 LIMO Pro 的 Ubuntu 桌面。

截至本次记录，**NoMachine 尚未成功接入桌面**。Wi‑Fi 和网线两种连接都曾建立 NoMachine 网络连接，但在接入桌面会话时断开。根因仍待确认。

## 环境

| 项目 | 排查时的情况 |
| --- | --- |
| 小车 | NVIDIA Jetson Orin Nano，Ubuntu 20.04.6 LTS，ARM64，主机名 `master`，系统账户 `agilex` |
| 小车端 NoMachine | `8.10.1-1`，排查时 `nxserver`、`nxnode`、`nxd` 均显示启用 |
| Windows 客户端 | NoMachine `10.2.3`，使用 NX 协议、端口 `4000` |
| Wi‑Fi | 排查时小车地址曾为 `192.168.137.207`，地址可能随网络变化 |
| 网线直连 | Windows 为 `192.168.137.101/24`，小车 `eth0` 为 `192.168.137.102/24` |
| 小车桌面 | `agilex` 的 X11 图形会话处于活动状态，能看到 Xorg 和 GNOME Shell 进程 |

## 连接和排查经过

1. **Wi‑Fi 连接及证书确认。** NoMachine 连接 `192.168.137.207:4000` 时提示确认主机身份。通过已知 SSH 主机密钥登录小车，核实了 NoMachine 证书的 SHA-256 指纹与弹窗一致。随后客户端接受了证书，开始查询服务。
2. **接入桌面时断开。** 10:09 的客户端日志显示 `Going to attach default active session` 后立即出现 `The connection with the server was lost`。重试一次得到相同结果。
3. **检查网络。** 排查过程中 Wi‑Fi 地址一度无法连接，后来又恢复。为排除无线链路影响，启用 `LIMO USB wired direct`，将小车有线地址设为 `192.168.137.102`。从 Windows 实际验证 SSH 和 TCP 4000 可以连通。
4. **改用系统账户。** 原有连接日志中出现 `NX desktop guest` 来宾登录。新建有线连接并使用 `agilex` 系统账户后，客户端记录 `Hello on board agilex (admin)`，确认账户认证成功，但接入桌面时仍立即断开。
5. **重启服务。** 在小车执行 `sudo /usr/NX/bin/nxserver --restart` 后，服务重新启用。10:34 的系统账户重试仍在接入桌面时断开。
6. **重新写入安装数据。** 执行 `sudo /etc/NX/nxserver --addtoredis` 并重启服务。随后 `nxserver --list` 显示空会话列表。本地 X11 桌面仍在运行。10:38 的再次连接仍然断开，这次客户端日志显示使用了来宾身份。

## 日志里的线索

在 10:32 和 10:34 的**系统账户**连接中，小车端 `nxserver.log` 均先记录 `agilex` 登录成功，随后出现：

```text
NXSERVER ERROR! Wrong session type physicalDesktop. Cannot set limits for this session.
NXSERVER ERROR! Cannot specify is local node base on ':'
```

这说明故障发生在小车端处理物理桌面会话和节点时。日志中的错误尚不足以单独确定是节点登记、安装状态还是客户端与服务端版本差异造成的。服务重启和 `--addtoredis` 都没有得到已验证的成功连接。

`sudo /usr/NX/bin/nxserver --nodelist` 返回 `Support for multi-node is not permitted on this server`。当前安装版本不支持通过该命令查看多节点列表，因此这一结果不能证明本地节点是否正常。

服务启动日志还出现过 `ufw` 规则检查或添加失败的警告。有线测试中 TCP 4000 可连接，账户也已认证成功；仅凭这些警告不能确定防火墙是本次桌面会话断开的原因。

## 当前可复用的检查

在 Windows 上确认有线端口和 SSH：

```powershell
Test-NetConnection 192.168.137.102 -Port 4000
ssh agilex@192.168.137.102
```

如果小车端 `.102` 不存在，可在小车本地终端重新启用已有的有线配置：

```bash
sudo nmcli connection up id 'LIMO USB wired direct' ifname eth0
ip -br -4 address show eth0
```

小车上检查 NoMachine 和桌面会话，再读取最近的服务端日志：

```bash
/usr/NX/bin/nxserver --status
loginctl list-sessions
sudo tail -n 120 /usr/NX/var/log/nxserver.log
```

客户端日志位于 Windows 用户目录下的 `.nx` 会话目录。本次导出的 10:09 日志在 Windows 下载目录中。该日志和小车端 `nxserver.log` 可按连接时间对照。

## 后续待验证

- 用 `agilex` 系统账户再次测试，并同时查看新的服务端日志，确认重新写入安装数据后的系统账户连接是否仍报同样错误。
- 核对 NoMachine `10.2.3` 客户端与 `8.10.1` 服务端的实际兼容性。更新小车端曾被提出作为排查方向，但本次记录没有确认小车端已经更新，也没有证明版本差异是根因。
- 如需更新或修复安装，先保留当前配置和日志，再验证服务状态、系统账户登录及桌面画面。

有线连接配置和 Wi‑Fi 故障的完整过程见[网络故障排查与恢复](网络故障排查与恢复.md)。
