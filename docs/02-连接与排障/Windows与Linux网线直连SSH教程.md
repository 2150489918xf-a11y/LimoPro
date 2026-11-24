# Windows 与 Linux 网线直连 SSH 教程

本教程介绍如何用网线直连一台 Windows 电脑和一台 Linux 设备，再从 Windows 通过 SSH 登录 Linux。示例使用静态 IPv4，适用于直连时没有路由器、没有 DHCP 自动分配地址的情况。

## 连接方案和准备

| 设备 | 示例 IP 地址 | 子网掩码 | 用途 |
| --- | --- | --- | --- |
| Windows | `192.168.50.101` | `255.255.255.0` | SSH 客户端 |
| Linux | `192.168.50.102` | `255.255.255.0` | SSH 服务端 |

两台设备的地址要在同一网段，且不能相同。示例中的 `/24` 等价于子网掩码 `255.255.255.0`。本教程只建立两台设备之间的连接，不配置网关、DNS 或互联网共享。

准备一根网线；如果 Windows 电脑没有网口，可以使用 USB 转网口适配器。需要知道 Linux 的用户名和密码，并在首次配置时能操作 Linux 终端，例如通过本地显示器和键盘，或已有的远程连接。

**地址冲突：**如果 Windows 或 Linux 的其他网络已经使用 `192.168.50.0/24` 网段，应选择其他未使用的网段，例如将两端分别改为 `192.168.60.101` 和 `192.168.60.102`，并同步替换下面的示例地址，避免路由冲突。

## 一、连接网线并配置 Windows

1. 用网线直接连接两台设备的网口。
2. 在 Windows 按 `Win + R`，输入 `ncpa.cpl` 并回车，打开网络连接。
3. 找到连接 Linux 设备的以太网适配器；如有多个网卡，可以通过拔插网线观察状态变化。
4. 右键该适配器，选择 **属性**，双击 **Internet 协议版本 4（TCP/IPv4）**。
5. 选择“使用下面的 IP 地址”，填写：

   ```text
   IP 地址：      192.168.50.101
   子网掩码：    255.255.255.0
   默认网关：    留空
   DNS：         留空
   ```

6. 点击“确定”保存。

在 Windows PowerShell 中可使用 `ipconfig` 检查该网卡的 IPv4 地址。`192.168.50.101` 是 Windows 自己的地址；之后 SSH 要连接 Linux 的 `192.168.50.102`。

## 二、配置 Linux 有线网络

以下命令在 **Linux 终端**中运行。示例使用 NetworkManager；如果系统没有 `nmcli`，请按该发行版的网络管理方式配置相同的静态 IP，或参考下方的临时配置方法。

### 1. 确认有线接口名称

```bash
nmcli device status
ip -br link
```

查找连接网线的以太网接口。名称可能是 `eth0`、`enp1s0` 或 `enx...`。下面以 `eth0` 为例，实际操作时请替换为自己的接口名称。

### 2. 创建并启用连接配置

首次配置时创建一次：

```bash
sudo nmcli connection add type ethernet ifname eth0 \
  con-name "Windows wired direct" \
  connection.autoconnect no \
  ipv4.method manual \
  ipv4.addresses 192.168.50.102/24 \
  ipv4.never-default yes \
  ipv6.method link-local \
  ipv6.never-default yes
```

然后启用该配置：

```bash
sudo nmcli connection up id "Windows wired direct" ifname eth0
```

提示 `Connection successfully activated` 后，检查地址：

```bash
ip -br -4 address show dev eth0
```

输出中应包含 `192.168.50.102/24`。以后无需重复创建配置；如果重启或重插网线后地址消失，重新执行上面的 `nmcli connection up` 命令即可。本示例关闭了自动连接，避免自动替换设备原有的有线网络配置。

### 没有 NetworkManager 时：临时配置

如果 Linux 没有 `nmcli`，也可以用 `ip` 临时配置，接口名称同样要替换：

```bash
sudo ip link set dev eth0 up
sudo ip address add 192.168.50.102/24 dev eth0
ip -br -4 address show dev eth0
```

此配置通常不会在重启后保留，也可能被系统的网络管理程序覆盖；需要长期使用时，应通过该发行版的网络管理工具创建持久配置。若提示地址已存在，先用上面的 `ip -br` 命令核对现有地址。

## 三、启动 Linux SSH 服务

在 Linux 中检查服务。Ubuntu / Debian 通常使用 `ssh` 服务名：

```bash
sudo systemctl start ssh
systemctl is-active ssh
sudo ss -ltnp | grep ':22 '
```

`systemctl is-active` 输出 `active` 表示服务正在运行；`ss` 可检查 TCP 22 端口是否监听。

如果提示服务不存在，Ubuntu / Debian 可以在设备能够访问软件源时安装：

```bash
sudo apt update
sudo apt install openssh-server
sudo systemctl enable --now ssh
```

其他发行版的软件包或服务可能叫 `openssh-server`、`sshd`，请按其文档安装和启动。直接用网线连接 Windows 不等于 Linux 已能访问互联网；安装软件包可能需要另外接入可访问软件源的网络。

## 四、从 Windows 测试和登录

在 Windows 打开 PowerShell：

```powershell
Test-NetConnection 192.168.50.102 -Port 22
```

输出中出现 `TcpTestSucceeded : True`，表示 Windows 可以访问 Linux 的 SSH 端口。接着登录：

```powershell
ssh 用户名@192.168.50.102
```

将“用户名”替换为 Linux 上的实际账户名。例如用户为 `ubuntu` 时：

```powershell
ssh ubuntu@192.168.50.102
```

首次连接会提示确认服务器身份。可先在 Linux 本地终端查看主机公钥指纹：

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

如果 Windows 显示的是 ED25519 主机密钥，核对双方显示的 SHA256 指纹一致后，在 Windows 输入 `yes`。若提示的是其他密钥类型，需要在 Linux 上查看对应类型的主机公钥指纹。

随后按提示输入 Linux 用户密码。输入密码时屏幕通常不显示字符或星号，输入完成后按回车。成功后会出现 Linux 的命令提示符。

## 五、可选：设置 SSH 别名

在 Windows 的 `C:\Users\你的用户名\.ssh\config` 文件中加入以下内容；如文件或 `.ssh` 目录不存在，可自行创建：

```sshconfig
Host linux-wired
    HostName 192.168.50.102
    User ubuntu
```

把 `User` 改为实际 Linux 用户名，保存后就可以运行：

```powershell
ssh linux-wired
```

## 六、常见问题

| 现象 | 检查方法 |
| --- | --- |
| `Connection refused` | 确认连接的是 Linux 地址而非 Windows 地址；检查 Linux SSH 服务是否运行、22 端口是否监听。 |
| `Connection timed out` | 检查网线、网卡链路状态、两端地址和掩码；检查是否与其他网卡的网段冲突，以及防火墙是否允许 SSH。 |
| `Permission denied` | 核对 Linux 用户名、密码以及服务器是否允许当前认证方式。 |
| 找不到 `ssh` 命令 | 在 Windows 的“可选功能”中安装 OpenSSH 客户端。 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | 可能是系统重装、主机密钥变化或 IP 指向了另一台设备。先通过可信渠道核实当前主机指纹，再处理 Windows 中的旧主机记录。 |
| 重启后无法连接 | 检查 Linux 地址是否仍存在；NetworkManager 示例默认不自动连接，临时 `ip` 配置通常也不会保留。 |

`ping` 可辅助检查连通性，但 ICMP 可能被防火墙拦截；SSH 是否可用以 TCP 22 端口测试和实际登录结果为准。
