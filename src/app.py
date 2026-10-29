#!/usr/bin/env python3
"""
P2TUN - Luxury Black, Gold & White Desktop GUI
Rounded pills, borders, and inputs.
Converts SOCKS4, SOCKS5, or HTTP proxy to TUN VPN interface.
"""

import sys
import os
import json
import subprocess
import threading
import time
import platform
import signal
import socket
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

def get_bundle_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_core_path():
    is_windows = platform.system() == "Windows"
    core_name = "sing-box.exe" if is_windows else "sing-box"

    search_paths = [
        os.path.join(get_bundle_dir(), "bin", core_name),
        os.path.join(get_bundle_dir(), core_name),
        os.path.join(get_app_dir(), "bin", core_name),
        os.path.join(get_app_dir(), core_name),
        os.path.join(os.path.dirname(get_app_dir()), "bin", core_name),
        core_name
    ]

    for p in search_paths:
        if os.path.isfile(p):
            return os.path.abspath(p)
    return core_name

class RoundedContainer(tk.Canvas):
    """Draws sleek curved-corner pill/card container"""
    def __init__(self, parent, bg="#08080a", border="#d4af37", fill="#111116", radius=16, border_w=1.5, **kwargs):
        super().__init__(parent, bg=bg, highlightthickness=0, **kwargs)
        self.fill_color = fill
        self.border_color = border
        self.radius = radius
        self.border_w = border_w
        self.bind("<Configure>", self._redraw)

    def _redraw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        r = min(self.radius, h // 2, w // 2)
        bw = self.border_w

        points = [
            r, bw,
            w - r, bw,
            w - bw, bw,
            w - bw, r,
            w - bw, h - r,
            w - bw, h - bw,
            w - r, h - bw,
            r, h - bw,
            bw, h - bw,
            bw, h - r,
            bw, r,
            bw, bw,
            r, bw
        ]
        self.create_polygon(points, smooth=True, fill=self.fill_color, outline=self.border_color, width=bw)

class P2TUNDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("P2TUN — Luxury Black & Gold VPN Engine")
        self.geometry("600x730")
        self.minsize(560, 680)

        self.c_bg = "#07070a"
        self.c_card = "#0f0f14"
        self.c_card_inner = "#15151e"
        self.c_gold = "#d4af37"
        self.c_gold_light = "#fcedb6"
        self.c_gold_border = "#aa8214"
        self.c_white = "#ffffff"
        self.c_muted = "#a1a1aa"
        self.c_danger = "#e11d48"

        self.configure(bg=self.c_bg)

        self.process = None
        self.running = False
        self.config_path = os.path.join(get_app_dir(), "p2tun_runtime_config.json")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        pad = tk.Frame(self, bg=self.c_bg, padx=20, pady=16)
        pad.pack(fill=tk.BOTH, expand=True)

        top_bar = tk.Frame(pad, bg=self.c_bg)
        top_bar.pack(fill=tk.X, pady=(0, 14))

        title_lbl = tk.Label(top_bar, text="P 2 T U N", bg=self.c_bg, fg=self.c_gold, font=("Cinzel", 18, "bold"))
        title_lbl.pack(anchor=tk.W)

        sub_lbl = tk.Label(top_bar, text="Proxy to Virtual TUN Interface • Sing-box Core", bg=self.c_bg, fg=self.c_muted, font=("Segoe UI", 9))
        sub_lbl.pack(anchor=tk.W, pady=(2, 0))

        card_box = RoundedContainer(pad, bg=self.c_bg, border=self.c_gold_border, fill=self.c_card, radius=22, border_w=1.5)
        card_box.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(card_box, bg=self.c_card, padx=18, pady=16)
        card_box.create_window(0, 0, anchor="nw", window=inner, tags="inner_win")

        def _resize_inner(e):
            card_box.coords("inner_win", 0, 0)
            inner.config(width=card_box.winfo_width(), height=card_box.winfo_height())
        card_box.bind("<Configure>", lambda e: _resize_inner(e))

        self._section_title(inner, "PROXY PROTOCOL")
        proto_frame = tk.Frame(inner, bg=self.c_card)
        proto_frame.pack(fill=tk.X, pady=(0, 12))

        self.proto_var = tk.StringVar(value="SOCKS5")
        self.proto_btns = {}
        for p in ["SOCKS5", "SOCKS4", "HTTP"]:
            b = tk.Button(proto_frame, text=p, font=("Segoe UI", 9, "bold"), bd=1, relief=tk.FLAT,
                          bg=self.c_gold if p == "SOCKS5" else self.c_card_inner,
                          fg="#000000" if p == "SOCKS5" else self.c_muted,
                          activebackground=self.c_gold_light, activeforeground="#000000",
                          padx=16, pady=6, cursor="hand2", command=lambda val=p: self.set_proto(val))
            b.pack(side=tk.LEFT, padx=(0, 8))
            self.proto_btns[p] = b

        target_hdr = tk.Frame(inner, bg=self.c_card)
        target_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(target_hdr, text="PROXY TARGET", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        btn_probe = tk.Button(target_hdr, text="Probe Port Latency", bg=self.c_card, fg=self.c_gold_light,
                              activebackground=self.c_card, activeforeground=self.c_white, bd=0, cursor="hand2",
                              font=("Segoe UI", 8, "underline"), command=self.probe_port)
        btn_probe.pack(side=tk.RIGHT)

        row_target = tk.Frame(inner, bg=self.c_card)
        row_target.pack(fill=tk.X, pady=(0, 10))

        tk.Label(row_target, text="Host", bg=self.c_card, fg=self.c_white, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.e_host = self._create_rounded_entry(row_target, self.host_var, width=22)
        self.e_host.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        tk.Label(row_target, text="Port", bg=self.c_card, fg=self.c_white, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.port_var = tk.StringVar(value="1080")
        self.e_port = self._create_rounded_entry(row_target, self.port_var, width=8)
        self.e_port.pack(side=tk.LEFT)

        self._section_title(inner, "AUTHENTICATION (OPTIONAL)")
        row_auth = tk.Frame(inner, bg=self.c_card)
        row_auth.pack(fill=tk.X, pady=(0, 10))

        tk.Label(row_auth, text="User", bg=self.c_card, fg=self.c_white, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.user_var = tk.StringVar(value="")
        self.e_user = self._create_rounded_entry(row_auth, self.user_var, width=16)
        self.e_user.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 12))

        tk.Label(row_auth, text="Pass", bg=self.c_card, fg=self.c_white, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.pass_var = tk.StringVar(value="")
        self.e_pass = self._create_rounded_entry(row_auth, self.pass_var, width=16, show="*")
        self.e_pass.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._section_title(inner, "TUN ADAPTER CONFIGURATION")
        row_tun = tk.Frame(inner, bg=self.c_card)
        row_tun.pack(fill=tk.X, pady=(0, 8))

        tk.Label(row_tun, text="Stack", bg=self.c_card, fg=self.c_white, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.stack_var = tk.StringVar(value="gvisor")
        combo = ttk.Combobox(row_tun, textvariable=self.stack_var, values=["gvisor", "system", "mixed"], state="readonly", width=12)
        combo.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(row_tun, text="Interface", bg=self.c_card, fg=self.c_white, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.iface_var = tk.StringVar(value="wintun" if platform.system() == "Windows" else "tun0")
        self.e_iface = self._create_rounded_entry(row_tun, self.iface_var, width=10)
        self.e_iface.pack(side=tk.LEFT)

        self.bypass_lan_var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(inner, text="Bypass Private LAN subnets (10.0.0.0/8, 192.168.0.0/16)",
                            variable=self.bypass_lan_var, bg=self.c_card, fg=self.c_white,
                            selectcolor="#000000", activebackground=self.c_card, activeforeground=self.c_gold_light,
                            font=("Segoe UI", 8))
        cb.pack(anchor=tk.W, pady=(0, 10))

        status_box = RoundedContainer(inner, bg=self.c_card, border=self.c_gold_border, fill=self.c_card_inner, radius=16, border_w=1, height=36)
        status_box.pack(fill=tk.X, pady=(0, 10))

        self.status_var = tk.StringVar(value="● DISCONNECTED")
        self.lbl_status = tk.Label(status_box, textvariable=self.status_var, bg=self.c_card_inner, fg=self.c_muted, font=("Segoe UI", 9, "bold"))
        self.lbl_status.place(relx=0.04, rely=0.5, anchor=tk.W)

        self.target_var = tk.StringVar(value="")
        self.lbl_target = tk.Label(status_box, textvariable=self.target_var, bg=self.c_card_inner, fg=self.c_white, font=("Consolas", 8))
        self.lbl_target.place(relx=0.96, rely=0.5, anchor=tk.E)

        self.btn_toggle = tk.Button(inner, text="CONNECT TUN INTERFACE", font=("Cinzel", 11, "bold"),
                                    bg=self.c_gold, fg="#000000", activebackground=self.c_gold_light, activeforeground="#000000",
                                    bd=0, relief=tk.FLAT, pady=10, cursor="hand2", command=self.toggle_vpn)
        self.btn_toggle.pack(fill=tk.X, pady=(0, 12))

        term_hdr = tk.Frame(inner, bg=self.c_card)
        term_hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(term_hdr, text="ENGINE LIVE STREAM", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)
        btn_clr = tk.Button(term_hdr, text="Clear", bg=self.c_card, fg=self.c_muted, bd=0, cursor="hand2",
                            font=("Segoe UI", 8), command=self.clear_logs)
        btn_clr.pack(side=tk.RIGHT)

        term_wrap = RoundedContainer(inner, bg=self.c_card, border=self.c_gold_border, fill="#050507", radius=16, border_w=1)
        term_wrap.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(term_wrap, wrap=tk.WORD, height=6, bg="#050507", fg="#fcedb6",
                                                  font=("Consolas", 8), insertbackground="white", relief=tk.FLAT, bd=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

    def _section_title(self, parent, text):
        lbl = tk.Label(parent, text=text, bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 8, "bold"))
        lbl.pack(anchor=tk.W, pady=(4, 4))

    def _create_rounded_entry(self, parent, variable, width=15, show=None):
        e = tk.Entry(parent, textvariable=variable, bg=self.c_card_inner, fg=self.c_white,
                     insertbackground=self.c_gold, relief=tk.FLAT, highlightthickness=1.5,
                     highlightbackground=self.c_gold_border, highlightcolor=self.c_gold,
                     width=width, font=("Segoe UI", 9), show=show)
        return e

    def set_proto(self, p):
        self.proto_var.set(p)
        for name, btn in self.proto_btns.items():
            if name == p:
                btn.config(bg=self.c_gold, fg="#000000")
            else:
                btn.config(bg=self.c_card_inner, fg=self.c_muted)
        self.log(f"[i] Selected protocol: {p}")

    def log(self, msg):
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)

    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)

    def probe_port(self):
        host = self.host_var.get().strip()
        port_s = self.port_var.get().strip()
        if not host or not port_s.isdigit():
            messagebox.showwarning("Input Error", "Please provide valid host and port.")
            return

        port = int(port_s)
        self.log(f"[*] Probing proxy target {host}:{port}...")

        def _run():
            start = time.time()
            try:
                s = socket.create_connection((host, port), timeout=2.0)
                s.close()
                lat = int((time.time() - start) * 1000)
                self.after(0, self.log, f"[✓] Target reachable! TCP latency: {lat}ms")
            except Exception as e:
                self.after(0, self.log, f"[!] Probe failed: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def generate_config(self):
        proto = self.proto_var.get().strip().upper()
        host = self.host_var.get().strip()
        port_s = self.port_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get().strip()
        stack = self.stack_var.get().strip()
        iface = self.iface_var.get().strip() or ("wintun" if platform.system() == "Windows" else "tun0")

        if not host:
            raise ValueError("Host cannot be empty")
        if not port_s.isdigit() or not (1 <= int(port_s) <= 65535):
            raise ValueError("Port must be between 1 and 65535")

        port = int(port_s)

        if proto == "HTTP":
            outbound = {"type": "http", "tag": "proxy-out", "server": host, "server_port": port}
            if user: outbound["username"] = user
            if pwd: outbound["password"] = pwd
        elif proto == "SOCKS4":
            outbound = {"type": "socks", "tag": "proxy-out", "server": host, "server_port": port, "version": "4"}
            if user: outbound["username"] = user
        else: # SOCKS5
            outbound = {"type": "socks", "tag": "proxy-out", "server": host, "server_port": port, "version": "5"}
            if user: outbound["username"] = user
            if pwd: outbound["password"] = pwd

        rules = [
            {"action": "hijack-dns", "protocol": "dns"},
            {"action": "sniff"}
        ]
        if self.bypass_lan_var.get():
            rules.append({"ip_is_private": True, "outbound": "direct"})

        cfg = {
            "log": {"level": "info", "timestamp": True},
            "inbounds": [
                {
                    "type": "tun",
                    "tag": "tun-in",
                    "interface_name": iface,
                    "address": ["172.19.0.1/30"],
                    "auto_route": True,
                    "strict_route": True,
                    "stack": stack
                }
            ],
            "outbounds": [
                outbound,
                {"type": "direct", "tag": "direct"}
            ],
            "route": {
                "rules": rules,
                "auto_detect_interface": True
            },
            "dns": {
                "servers": [
                    {
                        "tag": "proxy-dns",
                        "type": "tcp",
                        "server": "1.1.1.1",
                        "detour": "proxy-out"
                    }
                ]
            }
        }
        return cfg

    def toggle_vpn(self):
        if self.running:
            self.stop_vpn()
        else:
            self.start_vpn()

    def start_vpn(self):
        try:
            cfg = self.generate_config()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return

        core_exec = get_core_path()
        if not os.path.isfile(core_exec):
            messagebox.showerror("Core Missing", f"sing-box engine not found:\n{core_exec}")
            return

        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            messagebox.showerror("File Error", f"Cannot write config: {e}")
            return

        chk = subprocess.run([core_exec, "check", "-c", self.config_path], capture_output=True, text=True)
        if chk.returncode != 0:
            messagebox.showerror("Check Failed", chk.stderr or chk.stdout)
            return

        self.log(f"[*] Engine startup: {core_exec}")
        self.log(f"[*] Forwarding to {self.proto_var.get()} {self.host_var.get()}:{self.port_var.get()}")

        try:
            cflags = subprocess.CREATE_NO_WINDOW if (platform.system() == "Windows" and hasattr(subprocess, 'CREATE_NO_WINDOW')) else 0
            self.process = subprocess.Popen(
                [core_exec, "run", "-c", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=cflags
            )
            self.running = True
            self.status_var.set("● ROUTING ACTIVE")
            self.lbl_status.config(fg=self.c_gold)
            self.target_var.set(f"{self.proto_var.get()} {self.host_var.get()}:{self.port_var.get()}")
            self.btn_toggle.config(text="DISCONNECT TUN INTERFACE", bg=self.c_danger, fg=self.c_white, activebackground="#be123c")

            threading.Thread(target=self._stream_output, daemon=True).start()
        except PermissionError:
            self.log("[!] Root/Administrator privileges required for TUN adapter creation.")
            messagebox.showerror("Privilege Error", "Root or Administrator privileges are required to create a TUN device.")
            self.stop_vpn()
        except Exception as e:
            self.log(f"[!] Launch error: {e}")
            messagebox.showerror("Startup Error", str(e))
            self.stop_vpn()

    def _stream_output(self):
        proc = self.process
        if not proc or not proc.stdout:
            return

        for line in iter(proc.stdout.readline, ''):
            if not line: break
            self.after(0, self.log, line.strip())

        proc.poll()
        self.after(0, self._on_proc_stop)

    def _on_proc_stop(self):
        if self.running:
            self.log("[*] Engine stopped.")
            self.stop_vpn()

    def stop_vpn(self):
        self.running = False
        if self.process:
            self.log("[*] Stopping TUN VPN interface...")
            try:
                if platform.system() == "Windows":
                    self.process.terminate()
                else:
                    self.process.send_signal(signal.SIGINT)
                self.process.wait(timeout=3)
            except Exception:
                try: self.process.kill()
                except: pass
            self.process = None

        self.status_var.set("● DISCONNECTED")
        self.lbl_status.config(fg=self.c_muted)
        self.target_var.set("")
        self.btn_toggle.config(text="CONNECT TUN INTERFACE", bg=self.c_gold, fg="#000000", activebackground=self.c_gold_light)
        self.log("[*] Tunnel disconnected.")

    def on_close(self):
        if self.running:
            self.stop_vpn()
        if os.path.exists(self.config_path):
            try: os.remove(self.config_path)
            except: pass
        self.destroy()

if __name__ == "__main__":
    app = P2TUNDesktop()
    app.mainloop()
