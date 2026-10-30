import socket, subprocess, re, concurrent.futures, platform

def detect_proxy(host, port):
    types = []
    # SOCKS5
    try:
        s = socket.create_connection((host, port), timeout=0.25)
        s.sendall(b'\x05\x01\x00')
        r = s.recv(2)
        s.close()
        if r == b'\x05\x00': types.append('SOCKS5')
    except: pass

    # SOCKS4
    try:
        s = socket.create_connection((host, port), timeout=0.25)
        s.sendall(b'\x04\x01\x00\x50\x01\x02\x03\x04\x00')
        r = s.recv(2)
        s.close()
        if len(r) >= 2 and r[0] == 0: types.append('SOCKS4')
    except: pass

    # HTTP CONNECT
    try:
        s = socket.create_connection((host, port), timeout=0.25)
        s.sendall(b'CONNECT 127.0.0.1:80 HTTP/1.1\r\nHost: 127.0.0.1:80\r\n\r\n')
        r = s.recv(12)
        s.close()
        if b'HTTP/' in r: types.append('HTTP')
    except: pass
    return types

def scan_local_proxies():
    ports_map = {}
    is_win = platform.system() == "Windows"
    if not is_win:
        try:
            out = subprocess.check_output(['ss', '-tulpn'], text=True)
            for line in out.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 5 and parts[1] == 'LISTEN':
                    local = parts[4]
                    proc = parts[6] if len(parts) > 6 else ''
                    pname = ''
                    m = re.search(r'users:\(\(\"([^\"]+)\"', proc)
                    if m: pname = m.group(1)
                    if ':' in local:
                        h, p_s = local.rsplit(':', 1)
                        if h in ('0.0.0.0', '*', '[::]', '::'): h = '127.0.0.1'
                        elif '%' in h: h = h.split('%')[0]
                        elif h in ('[::1]', '::1'): h = '127.0.0.1'
                        try:
                            p = int(p_s)
                            if p not in ports_map: ports_map[p] = (h, pname)
                        except: pass
        except: pass
    else:
        try:
            out = subprocess.check_output(['netstat', '-ano'], text=True)
            for line in out.splitlines():
                if 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        local = parts[1]
                        pid = parts[-1] if len(parts) >= 5 else ''
                        if ':' in local:
                            h, p_s = local.rsplit(':', 1)
                            if h in ('0.0.0.0', '*', '[::]', '::'): h = '127.0.0.1'
                            try:
                                p = int(p_s)
                                if p not in ports_map: ports_map[p] = (h, f"PID:{pid}")
                            except: pass
        except: pass

    common = [1080, 10808, 10809, 2080, 7890, 7891, 8080, 8888, 8889, 9050, 9051, 9999, 11111, 20128, 4747]
    for cp in common:
        if cp not in ports_map: ports_map[cp] = ('127.0.0.1', '')

    proxies = []
    def check_one(p, info):
        h, app_name = info
        types = detect_proxy(h, p)
        if types:
            for pt in types:
                proxies.append({'protocol': pt, 'host': h, 'port': p, 'app': app_name or 'Local App'})

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
        futures = [ex.submit(check_one, p, info) for p, info in ports_map.items()]
        concurrent.futures.wait(futures)

    proxies.sort(key=lambda x: (x['host'], x['port'], x['protocol']))
    return proxies
