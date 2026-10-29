# P2TUN — Proxy to TUN VPN Adapter

Convert any local or remote SOCKS4, SOCKS5, or HTTP proxy into a virtual TUN interface routing system traffic like a VPN tunnel.

Powered by `sing-box` core with `gVisor` userspace network stack.

---

## Features

- **Proxy Protocols**: SOCKS5, SOCKS4, HTTP.
- **Authentication**: Optional username / password support.
- **TUN Engines**: gVisor (userspace), System TUN, or Mixed.
- **DNS Protection**: Hijacks system DNS to proxy DNS detour.
- **LAN Bypass**: Option to exempt private RFC1918 CIDRs from tunnel.
- **Cross-Platform**: Compiled standalone packages for Linux and Windows x86_64.
- **Theme**: Obsidian Black, Luxury Gold & White with rounded pill controls.

---

## Repository Structure

- `src/app.py`: Native desktop GUI implementation (Tkinter + Canvas rounded pill widgets).
- `go-app/main.go`: Go standalone cross-platform GUI & daemon controller with embedded UI.
- `go-app/web/index.html`: Web dashboard interface styled in Black, Gold & White.

---

## Privileges

TUN device creation and system route modification require root privileges on Linux and Administrator privileges on Windows.
