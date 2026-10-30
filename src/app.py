#!/usr/bin/env python3
"""
P2TUN - Clean, Modern & Responsive Desktop GUI
Obsidian Black, Metallic Gold & Crisp White.
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

from proxy_scanner import scan_local_proxies

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
        self.title("P2TUN — VPN Tunnel")
        self.geometry("460x610")
        self.minsize(420, 560)

        # Theme Colors
        self.c_bg = "#07070a"
        self.c_card = "#0f1016"
        self.c_inner = "#151620"
        self.c_input = "#1b1c28"
        self.c_gold = "#e5b842"
        self.c_gold_light = "#fce89f"
        self.c_gold_border = "#997312"
        self.c_white = "#ffffff"
        self.c_muted = "#9ca3af"
        self.c_danger = "#e11d48"

        self.configure(bg=self.c_bg)

        self.process = None
        self.running = False
        self.config_path = os.path.join(get_app_dir(), "p2tun_runtime_config.json")
        self.show_adv = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        # Outer Card with gold accent border
        card = tk.Frame(self, bg=self.c_card, highlightthickness=1.5,
                        highlightbackground=self.c_gold_border, highlightcolor=self.c_gold)
        card.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        # Header
        hdr = tk.Frame(card, bg=self.c_card, padx=14, pady=10)
        hdr.pack(fill=tk.X)

        h_left = tk.Frame(hdr, bg=self.c_card)
        h_left.pack(side=tk.LEFT)
        tk.Label(h_left, text="P 2 T U N", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 16, "bold")).pack(anchor=tk.W)
        tk.Label(h_left, text="Proxy to Virtual TUN Interface", bg=self.c_card, fg=self.c_muted, font=("Segoe UI", 8)).pack(anchor=tk.W)

        self.badge = tk.Label(hdr, text="READY", bg=self.c_inner, fg=self.c_gold_light,
                              font=("Segoe UI", 8, "bold"), padx=10, pady=3,
                              highlightthickness=1, highlightbackground=self.c_gold_border)
        self.badge.pack(side=tk.RIGHT)

        body = tk.Frame(card, bg=self.c_card, padx=14, pady=2)
        body.pack(fill=tk.BOTH, expand=True)

        # Protocol Row
        tk.Label(body, text="PROTOCOL", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, pady=(0, 4))
        p_row = tk.Frame(body, bg=self.c_card)
        p_row.pack(fill=tk.X, pady=(0, 10))

        self.proto_var = tk.StringVar(value="SOCKS5")
        self.proto_btns = {}
        for p in ["SOCKS5", "SOCKS4", "HTTP"]:
            b = tk.Button(p_row, text=p, font=("Segoe UI", 8, "bold"), bd=0, relief=tk.FLAT,
                          bg=self.c_gold if p == "SOCKS5" else self.c_input,
                          fg="#000000" if p == "SOCKS5" else self.c_muted,
                          activebackground=self.c_gold_light, activeforeground="#000000",
                          padx=14, pady=6, cursor="hand2", command=lambda val=p: self.set_proto(val))
            b.pack(side=tk.LEFT, padx=(0, 8))
            self.proto_btns[p] = b

        # Target Proxy Box
        tgt_box = tk.Frame(body, bg=self.c_inner, padx=12, pady=10, highlightthickness=1, highlightbackground=self.c_gold_border)
        tgt_box.pack(fill=tk.X, pady=(0, 10))

        tgt_top = tk.Frame(tgt_box, bg=self.c_inner)
        tgt_top.pack(fill=tk.X, pady=(0, 6))
        tk.Label(tgt_top, text="TARGET PROXY", bg=self.c_inner, fg=self.c_gold, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT)

        btn_probe = tk.Button(tgt_top, text="Ping Port", bg=self.c_inner, fg=self.c_gold_light,
                              activebackground=self.c_inner, activeforeground=self.c_white, bd=0, cursor="hand2",
                              font=("Segoe UI", 8, "underline"), command=self.probe_port)
        btn_probe.pack(side=tk.RIGHT)

        btn_scan = tk.Button(tgt_top, text="🔍 Scan Proxies", bg=self.c_inner, fg=self.c_gold,
                             activebackground=self.c_inner, activeforeground=self.c_white, bd=0, cursor="hand2",
                             font=("Segoe UI", 8, "bold underline"), command=self.open_proxy_scanner)
        btn_scan.pack(side=tk.RIGHT, padx=(0, 12))

        in_row = tk.Frame(tgt_box, bg=self.c_inner)
        in_row.pack(fill=tk.X)

        tk.Label(in_row, text="Host", bg=self.c_inner, fg=self.c_white, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.e_host = tk.Entry(in_row, textvariable=self.host_var, bg=self.c_input, fg=self.c_white,
                               insertbackground=self.c_gold, relief=tk.FLAT, highlightthickness=1,
                               highlightbackground=self.c_gold_border, highlightcolor=self.c_gold,
                               font=("Segoe UI", 9))
        self.e_host.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=3)

        tk.Label(in_row, text="Port", bg=self.c_inner, fg=self.c_white, font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.port_var = tk.StringVar(value="10808")
        self.e_port = tk.Entry(in_row, textvariable=self.port_var, width=8, bg=self.c_input, fg=self.c_white,
                               insertbackground=self.c_gold, relief=tk.FLAT, highlightthickness=1,
                               highlightbackground=self.c_gold_border, highlightcolor=self.c_gold,
                               font=("Segoe UI", 9))
        self.e_port.pack(side=tk.LEFT, ipady=3)

        # Advanced Settings Toggle
        self.btn_adv = tk.Button(body, text="▼ Advanced Options (Auth, TUN Stack, LAN)", bg=self.c_card, fg=self.c_muted,
                                 activebackground=self.c_card, activeforeground=self.c_gold_light, bd=0, cursor="hand2",
                                 font=("Segoe UI", 8, "bold"), command=self.toggle_adv)
        self.btn_adv.pack(anchor=tk.W, pady=(0, 4))

        self.adv_frame = tk.Frame(body, bg=self.c_inner, padx=10, pady=8, highlightthickness=1, highlightbackground=self.c_gold_border)

        row_auth = tk.Frame(self.adv_frame, bg=self.c_inner)
        row_auth.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row_auth, text="User", bg=self.c_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.user_var = tk.StringVar(value="")
        tk.Entry(row_auth, textvariable=self.user_var, bg=self.c_input, fg=self.c_white,
                 insertbackground=self.c_gold, relief=tk.FLAT, highlightthickness=1,
                 highlightbackground=self.c_gold_border, font=("Segoe UI", 8)).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=2)

        tk.Label(row_auth, text="Pass", bg=self.c_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.pass_var = tk.StringVar(value="")
        tk.Entry(row_auth, textvariable=self.pass_var, bg=self.c_input, fg=self.c_white, show="*",
                 insertbackground=self.c_gold, relief=tk.FLAT, highlightthickness=1,
                 highlightbackground=self.c_gold_border, font=("Segoe UI", 8)).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)

        row_tun = tk.Frame(self.adv_frame, bg=self.c_inner)
        row_tun.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row_tun, text="Stack", bg=self.c_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.stack_var = tk.StringVar(value="gvisor")
        combo = ttk.Combobox(row_tun, textvariable=self.stack_var, values=["gvisor", "system", "mixed"], state="readonly", width=8)
        combo.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(row_tun, text="Adapter", bg=self.c_inner, fg=self.c_white, font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 4))
        self.iface_var = tk.StringVar(value="wintun" if platform.system() == "Windows" else "tun0")
        tk.Entry(row_tun, textvariable=self.iface_var, width=8, bg=self.c_input, fg=self.c_white,
                 insertbackground=self.c_gold, relief=tk.FLAT, highlightthickness=1,
                 highlightbackground=self.c_gold_border, font=("Segoe UI", 8)).pack(side=tk.LEFT, ipady=2)

        self.bypass_lan_var = tk.BooleanVar(value=True)
        cb = tk.Checkbutton(self.adv_frame, text="Bypass LAN (192.168.x.x, 10.x.x.x)",
                            variable=self.bypass_lan_var, bg=self.c_inner, fg=self.c_white,
                            selectcolor="#000000", activebackground=self.c_inner, activeforeground=self.c_gold_light,
                            font=("Segoe UI", 8))
        cb.pack(anchor=tk.W)

        # Status Bar
        stat_bar = tk.Frame(body, bg=self.c_inner, padx=10, pady=6, highlightthickness=1, highlightbackground=self.c_gold_border)
        stat_bar.pack(fill=tk.X, pady=(0, 10))

        self.status_var = tk.StringVar(value="● DISCONNECTED")
        self.lbl_status = tk.Label(stat_bar, textvariable=self.status_var, bg=self.c_inner, fg=self.c_muted, font=("Segoe UI", 8, "bold"))
        self.lbl_status.pack(side=tk.LEFT)

        self.target_var = tk.StringVar(value="")
        self.lbl_target = tk.Label(stat_bar, textvariable=self.target_var, bg=self.c_inner, fg=self.c_white, font=("Consolas", 8))
        self.lbl_target.pack(side=tk.RIGHT)

        # Hero Connect Button
        self.btn_toggle = tk.Button(body, text="CONNECT TUN INTERFACE", font=("Segoe UI", 10, "bold"),
                                    bg=self.c_gold, fg="#000000", activebackground=self.c_gold_light, activeforeground="#000000",
                                    bd=0, relief=tk.FLAT, pady=10, cursor="hand2", command=self.toggle_vpn)
        self.btn_toggle.pack(fill=tk.X, pady=(0, 10))

        # Terminal
        term_hdr = tk.Frame(body, bg=self.c_card)
        term_hdr.pack(fill=tk.X, pady=(0, 2))
        tk.Label(term_hdr, text="ENGINE STREAM", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 7, "bold")).pack(side=tk.LEFT)
        tk.Button(term_hdr, text="Clear", bg=self.c_card, fg=self.c_muted, bd=0, cursor="hand2",
                  font=("Segoe UI", 7), command=self.clear_logs).pack(side=tk.RIGHT)

        term_box = tk.Frame(body, bg="#060609", highlightthickness=1, highlightbackground=self.c_gold_border)
        term_box.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(term_box, wrap=tk.WORD, height=6, bg="#060609", fg="#fbe69b",
                                                  font=("Consolas", 8), insertbackground="white", relief=tk.FLAT, bd=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def toggle_adv(self):
        if self.show_adv:
            self.adv_frame.pack_forget()
            self.btn_adv.config(text="▼ Advanced Options (Auth, TUN Stack, LAN)")
            self.show_adv = False
        else:
            self.adv_frame.pack(fill=tk.X, pady=(0, 8), before=self.btn_toggle)
            self.btn_adv.config(text="▲ Hide Advanced Options")
            self.show_adv = True

    def set_proto(self, p):
        self.proto_var.set(p)
        for name, btn in self.proto_btns.items():
            if name == p:
                btn.config(bg=self.c_gold, fg="#000000")
            else:
                btn.config(bg=self.c_input, fg=self.c_muted)
        self.log(f"[i] Protocol: {p}")

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
                self.after(0, self.log, f"[✓] Reachable! Latency: {lat}ms")
            except Exception as e:
                self.after(0, self.log, f"[!] Probe failed: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def open_proxy_scanner(self):
        win = tk.Toplevel(self)
        win.title("Local Proxy Finder")
        win.geometry("450x360")
        win.minsize(400, 300)
        win.configure(bg=self.c_bg)
        win.transient(self)

        panel = tk.Frame(win, bg=self.c_card, padx=12, pady=10, highlightthickness=1.5, highlightbackground=self.c_gold_border)
        panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_f = tk.Frame(panel, bg=self.c_card)
        top_f.pack(fill=tk.X, pady=(0, 6))
        tk.Label(top_f, text="ACTIVE LOCAL PROXIES", bg=self.c_card, fg=self.c_gold, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        status_lbl = tk.Label(top_f, text="Scanning...", bg=self.c_card, fg=self.c_gold_light, font=("Segoe UI", 8))
        status_lbl.pack(side=tk.RIGHT)

        list_frame = tk.Frame(panel, bg=self.c_inner, highlightthickness=1, highlightbackground=self.c_gold_border)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        style = ttk.Style(win)
        style.theme_use("clam")
        style.configure("Treeview", background=self.c_input, foreground=self.c_white, fieldbackground=self.c_input, rowheight=22)
        style.configure("Treeview.Heading", background=self.c_inner, foreground=self.c_gold, font=("Segoe UI", 8, "bold"))
        style.map("Treeview", background=[("selected", self.c_gold_border)])

        cols = ("proto", "host", "port", "app")
        tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse")
        tree.heading("proto", text="Protocol")
        tree.heading("host", text="Host")
        tree.heading("port", text="Port")
        tree.heading("app", text="App / Process")
        tree.column("proto", width=70, anchor="center")
        tree.column("host", width=90, anchor="center")
        tree.column("port", width=60, anchor="center")
        tree.column("app", width=140, anchor="w")
        tree.pack(fill=tk.BOTH, expand=True)

        def apply_sel():
            sel = tree.selection()
            if not sel: return
            item = tree.item(sel[0])["values"]
            proto_val, host_val, port_val = str(item[0]), str(item[1]), str(item[2])
            if proto_val in self.proto_btns:
                self.set_proto(proto_val)
            self.host_var.set(host_val)
            self.port_var.set(port_val)
            self.log(f"[✓] Auto-configured {proto_val} -> {host_val}:{port_val} ({item[3]})")
            win.destroy()

        tree.bind("<Double-1>", lambda e: apply_sel())

        b_row = tk.Frame(panel, bg=self.c_card)
        b_row.pack(fill=tk.X)

        tk.Button(b_row, text="USE PROXY", font=("Segoe UI", 8, "bold"),
                  bg=self.c_gold, fg="#000000", activebackground=self.c_gold_light,
                  bd=0, relief=tk.FLAT, padx=14, pady=5, cursor="hand2", command=apply_sel).pack(side=tk.LEFT)

        def do_scan():
            status_lbl.config(text="Scanning...")
            found = scan_local_proxies()
            def update():
                for r in tree.get_children(): tree.delete(r)
                for item in found:
                    tree.insert("", tk.END, values=(item['protocol'], item['host'], item['port'], item['app']))
                status_lbl.config(text=f"Found {len(found)}")
            win.after(0, update)

        tk.Button(b_row, text="RESCAN", font=("Segoe UI", 8, "bold"),
                  bg=self.c_input, fg=self.c_white, activebackground=self.c_inner,
                  bd=0, relief=tk.FLAT, padx=10, pady=5, cursor="hand2",
                  command=lambda: threading.Thread(target=do_scan, daemon=True).start()).pack(side=tk.RIGHT)

        threading.Thread(target=do_scan, daemon=True).start()

    def generate_config(self):
        proto = self.proto_var.get().strip().upper()
        host = self.host_var.get().strip()
        port_s = self.port_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get().strip()
        stack = self.stack_var.get().strip()
        iface = self.iface_var.get().strip() or ("wintun" if platform.system() == "Windows" else "tun0")

        if not host: raise ValueError("Host cannot be empty")
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

        return {
            "log": {"level": "info", "timestamp": True},
            "inbounds": [{
                "type": "tun", "tag": "tun-in", "interface_name": iface,
                "address": ["172.19.0.1/30"], "auto_route": True, "strict_route": True, "stack": stack
            }],
            "outbounds": [outbound, {"type": "direct", "tag": "direct"}],
            "route": {"rules": rules, "auto_detect_interface": True},
            "dns": {"servers": [{"tag": "proxy-dns", "type": "tcp", "server": "1.1.1.1", "detour": "proxy-out"}]}
        }

    def toggle_vpn(self):
        if self.running: self.stop_vpn()
        else: self.start_vpn()

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
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=cflags
            )
            self.running = True
            self.status_var.set("● ROUTING ACTIVE")
            self.lbl_status.config(fg=self.c_gold)
            self.badge.config(text="ACTIVE", fg="#86efac")
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
        if not proc or not proc.stdout: return
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
                if platform.system() == "Windows": self.process.terminate()
                else: self.process.send_signal(signal.SIGINT)
                self.process.wait(timeout=3)
            except Exception:
                try: self.process.kill()
                except: pass
            self.process = None

        self.status_var.set("● DISCONNECTED")
        self.lbl_status.config(fg=self.c_muted)
        self.badge.config(text="READY", fg=self.c_gold_light)
        self.target_var.set("")
        self.btn_toggle.config(text="CONNECT TUN INTERFACE", bg=self.c_gold, fg="#000000", activebackground=self.c_gold_light)
        self.log("[*] Tunnel disconnected.")

    def on_close(self):
        if self.running: self.stop_vpn()
        if os.path.exists(self.config_path):
            try: os.remove(self.config_path)
            except: pass
        self.destroy()

if __name__ == "__main__":
    app = P2TUNDesktop()
    app.mainloop()
