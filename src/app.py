#!/usr/bin/env python3
"""
P2TUN - Compact, Pixel-Fit Responsive Desktop GUI
Obsidian Black, Metallic Gold & Crisp White.
Fits screen cleanly without clipping or overflow.
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

class P2TUNDesktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("P2TUN — Proxy to TUN Interface")
        self.geometry("480x620")
        self.minsize(440, 560)

        # Palette
        self.c_bg = "#07070a"
        self.c_card = "#101117"
        self.c_card_inner = "#171822"
        self.c_input = "#1e202e"
        self.c_gold = "#e5b842"
        self.c_gold_light = "#fbe69b"
        self.c_gold_border = "#aa8214"
        self.c_white = "#ffffff"
        self.c_muted = "#9ca3af"
        self.c_danger = "#ef4444"

        self.configure(bg=self.c_bg)

        self.process = None
        self.running = False
        self.config_path = os.path.join(get_app_dir(), "p2tun_runtime_config.json")
        self.show_adv = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        # Outer Container with 1px gold border
        outer = tk.Frame(self, bg=self.c_card, highlightthickness=1.5,
                         highlightbackground=self.c_gold_border, highlightcolor=self.c_gold)
        outer.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        # Top Header Bar
        hdr = tk.Frame(outer, bg=self.c_card, padx=14, pady=10)
        hdr.pack(fill=tk.X)

        title_box = tk.Frame(hdr, bg=self.c_card)
        title_box.pack(side=tk.LEFT)
        tk.Label(title_box, text="P 2 T U N", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 15, "bold")).pack(anchor=tk.W)
        tk.Label(title_box, text="Proxy to TUN VPN • sing-box core", bg=self.c_card, fg=self.c_muted, font=("Segoe UI", 8)).pack(anchor=tk.W)

        self.badge_core = tk.Label(hdr, text="READY", bg="#1a1c26", fg=self.c_gold_light,
                                   font=("Segoe UI", 8, "bold"), padx=10, pady=3,
                                   highlightthickness=1, highlightbackground=self.c_gold_border)
        self.badge_core.pack(side=tk.RIGHT)

        # Body Container
        body = tk.Frame(outer, bg=self.c_card, padx=14, pady=4)
        body.pack(fill=tk.BOTH, expand=True)

        # Protocol Selectors
        proto_box = tk.Frame(body, bg=self.c_card)
        proto_box.pack(fill=tk.X, pady=(0, 10))

        tk.Label(proto_box, text="PROTOCOL", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 4))
        p_row = tk.Frame(proto_box, bg=self.c_card)
        p_row.pack(fill=tk.X)

        self.proto_var = tk.StringVar(value="SOCKS5")
        self.proto_btns = {}
        for p in ["SOCKS5", "SOCKS4", "HTTP"]:
            b = tk.Button(p_row, text=p, font=("Segoe UI", 8, "bold"), bd=0, relief=tk.FLAT,
                          bg=self.c_gold if p == "SOCKS5" else self.c_input,
                          fg="#000000" if p == "SOCKS5" else self.c_muted,
                          activebackground=self.c_gold_light, activeforeground="#000000",
                          padx=14, pady=5, cursor="hand2", command=lambda val=p: self.set_proto(val))
            b.pack(side=tk.LEFT, padx=(0, 6))
            self.proto_btns[p] = b

        # Target Host & Port Box
        target_box = tk.Frame(body, bg=self.c_card_inner, padx=10, pady=8, highlightthickness=1, highlightbackground=self.c_gold_border)
        target_box.pack(fill=tk.X, pady=(0, 8))

        top_tgt = tk.Frame(target_box, bg=self.c_card_inner)
        top_tgt.pack(fill=tk.X, pady=(0, 4))
        tk.Label(top_tgt, text="TARGET PROXY", bg=self.c_card_inner, fg=self.c_gold, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)

        btn_probe = tk.Button(top_tgt, text="Probe Port Latency", bg=self.c_card_inner, fg=self.c_gold_light,
                              activebackground=self.c_card_inner, activeforeground=self.c_white, bd=0, cursor="hand2",
                              font=("Segoe UI", 8, "underline"), command=self.probe_port)
        btn_probe.pack(side=tk.RIGHT)

        input_row = tk.Frame(target_box, bg=self.c_card_inner)
        input_row.pack(fill=tk.X)

        tk.Label(input_row, text="Host", bg=self.c_card_inner, fg=self.c_white, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.e_host = self._entry(input_row, self.host_var, width=16)
        self.e_host.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=2)

        tk.Label(input_row, text="Port", bg=self.c_card_inner, fg=self.c_white, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.port_var = tk.StringVar(value="1080")
        self.e_port = self._entry(input_row, self.port_var, width=6)
        self.e_port.pack(side=tk.LEFT, ipady=2)

        # Advanced Settings Accordion
        self.btn_adv = tk.Button(body, text="▼ Optional Settings (Auth, TUN Stack, LAN)", bg=self.c_card, fg=self.c_muted,
                                 activebackground=self.c_card, activeforeground=self.c_gold_light, bd=0, cursor="hand2",
                                 font=("Segoe UI", 8, "bold"), command=self.toggle_adv)
        self.btn_adv.pack(anchor=tk.W, pady=(0, 4))

        self.adv_frame = tk.Frame(body, bg=self.c_card_inner, padx=10, pady=8, highlightthickness=1, highlightbackground=self.c_gold_border)

        row_a = tk.Frame(self.adv_frame, bg=self.c_card_inner)
        row_a.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row_a, text="User", bg=self.c_card_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.user_var = tk.StringVar(value="")
        self._entry(row_a, self.user_var, width=12).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=1)

        tk.Label(row_a, text="Pass", bg=self.c_card_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.pass_var = tk.StringVar(value="")
        self._entry(row_a, self.pass_var, width=12, show="*").pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=1)

        row_b = tk.Frame(self.adv_frame, bg=self.c_card_inner)
        row_b.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row_b, text="Stack", bg=self.c_card_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.stack_var = tk.StringVar(value="gvisor")
        combo = ttk.Combobox(row_b, textvariable=self.stack_var, values=["gvisor", "system", "mixed"], state="readonly", width=8)
        combo.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(row_b, text="Adapter", bg=self.c_card_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.iface_var = tk.StringVar(value="wintun" if platform.system() == "Windows" else "tun0")
        self._entry(row_b, self.iface_var, width=8).pack(side=tk.LEFT, ipady=1)

        self.bypass_lan_var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(self.adv_frame, text="Bypass LAN (192.168.x.x, 10.x.x.x)",
                            variable=self.bypass_lan_var, bg=self.c_card_inner, fg=self.c_white,
                            selectcolor="#000000", activebackground=self.c_card_inner, activeforeground=self.c_gold_light,
                            font=("Segoe UI", 8))
        cb.pack(anchor=tk.W)

        # Status Capsule
        stat_bar = tk.Frame(body, bg=self.c_card_inner, padx=10, pady=6, highlightthickness=1, highlightbackground=self.c_gold_border)
        stat_bar.pack(fill=tk.X, pady=(0, 8))

        self.status_var = tk.StringVar(value="● DISCONNECTED")
        self.lbl_status = tk.Label(stat_bar, textvariable=self.status_var, bg=self.c_card_inner, fg=self.c_muted, font=("Segoe UI", 8, "bold"))
        self.lbl_status.pack(side=tk.LEFT)

        self.target_var = tk.StringVar(value="")
        self.lbl_target = tk.Label(stat_bar, textvariable=self.target_var, bg=self.c_card_inner, fg=self.c_white, font=("Consolas", 8))
        self.lbl_target.pack(side=tk.RIGHT)

        # Hero Action Button
        self.btn_toggle = tk.Button(body, text="CONNECT TUN INTERFACE", font=("Segoe UI", 10, "bold"),
                                    bg=self.c_gold, fg="#000000", activebackground=self.c_gold_light, activeforeground="#000000",
                                    bd=0, relief=tk.FLAT, pady=9, cursor="hand2", command=self.toggle_vpn)
        self.btn_toggle.pack(fill=tk.X, pady=(0, 8))

        # Terminal Box (Fit & Responsive)
        term_top = tk.Frame(body, bg=self.c_card)
        term_top.pack(fill=tk.X, pady=(0, 2))
        tk.Label(term_top, text="ENGINE OUTPUT", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT)
        tk.Button(term_top, text="Clear", bg=self.c_card, fg=self.c_muted, bd=0, cursor="hand2",
                  font=("Segoe UI", 7), command=self.clear_logs).pack(side=tk.RIGHT)

        term_box = tk.Frame(body, bg="#060609", highlightthickness=1, highlightbackground=self.c_gold_border)
        term_box.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(term_box, wrap=tk.WORD, height=6, bg="#060609", fg="#fbe69b",
                                                  font=("Consolas", 8), insertbackground="white", relief=tk.FLAT, bd=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _entry(self, parent, variable, width=15, show=None):
        return tk.Entry(parent, textvariable=variable, bg=self.c_input, fg=self.c_white,
                        insertbackground=self.c_gold, relief=tk.FLAT, highlightthickness=1,
                        highlightbackground=self.c_gold_border, highlightcolor=self.c_gold,
                        width=width, font=("Segoe UI", 9), show=show)

    def toggle_adv(self):
        if self.show_adv:
            self.adv_frame.pack_forget()
            self.btn_adv.config(text="▼ Optional Settings (Auth, TUN Stack, LAN)")
            self.show_adv = False
        else:
            self.adv_frame.pack(fill=tk.X, pady=(0, 8), before=self.btn_toggle)
            self.btn_adv.config(text="▲ Hide Optional Settings")
            self.show_adv = True

    def set_proto(self, p):
        self.proto_var.set(p)
        for name, btn in self.proto_btns.items():
            if name == p:
                btn.config(bg=self.c_gold, fg="#000000")
            else:
                btn.config(bg=self.c_input, fg=self.c_muted)
        self.log(f"[i] Protocol switched: {p}")

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
        self.log(f"[*] Checking latency for {host}:{port}...")

        def _run():
            start = time.time()
            try:
                s = socket.create_connection((host, port), timeout=2.0)
                s.close()
                lat = int((time.time() - start) * 1000)
                self.after(0, self.log, f"[✓] Reachable! Handshake: {lat}ms")
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

        self.log(f"[*] Starting TUN tunnel: {core_exec}")
        self.log(f"[*] Outbound: {self.proto_var.get()} {self.host_var.get()}:{self.port_var.get()}")

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
            self.badge_core.config(text="ACTIVE", fg="#86efac")
            self.target_var.set(f"{self.proto_var.get()} {self.host_var.get()}:{self.port_var.get()}")
            self.btn_toggle.config(text="DISCONNECT TUN INTERFACE", bg=self.c_danger, fg=self.c_white, activebackground="#dc2626")

            threading.Thread(target=self._stream_output, daemon=True).start()
        except PermissionError:
            self.log("[!] Root/Administrator required for TUN creation.")
            messagebox.showerror("Elevation Required", "Administrator/Root privileges are required to create a TUN device.")
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
        self.badge_core.config(text="READY", fg=self.c_gold_light)
        self.target_var.set("")
        self.btn_toggle.config(text="CONNECT TUN INTERFACE", bg=self.c_gold, fg="#000000", activebackground=self.c_gold_light)
        self.log("[*] Tunnel offline.")

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
