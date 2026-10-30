package main

import (
	"bufio"
	"embed"
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"time"
)

//go:embed web/index.html
var webFS embed.FS

type TunnelConfig struct {
	Protocol  string `json:"protocol"`
	Host      string `json:"host"`
	Port      int    `json:"port"`
	Username  string `json:"username"`
	Password  string `json:"password"`
	Stack     string `json:"stack"`
	Interface string `json:"interface"`
	BypassLAN bool   `json:"bypass_lan"`
}

type TunnelManager struct {
	mu        sync.Mutex
	cmd       *exec.Cmd
	running   bool
	target    string
	listeners map[chan string]bool
}

var manager = &TunnelManager{
	listeners: make(map[chan string]bool),
}

func (m *TunnelManager) broadcast(msg string) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for ch := range m.listeners {
		select {
		case ch <- msg:
		default:
		}
	}
}

func getCorePath() string {
	execName := "sing-box"
	if runtime.GOOS == "windows" {
		execName = "sing-box.exe"
	}

	selfPath, err := os.Executable()
	var baseDir string
	if err == nil {
		baseDir = filepath.Dir(selfPath)
	}

	candidates := []string{
		filepath.Join(baseDir, execName),
		filepath.Join(baseDir, "bin", execName),
		filepath.Join(".", execName),
		filepath.Join(".", "bin", execName),
		execName,
	}

	for _, c := range candidates {
		if fi, err := os.Stat(c); err == nil && !fi.IsDir() {
			abs, err := filepath.Abs(c)
			if err == nil {
				return abs
			}
			return c
		}
	}
	return execName
}

func (m *TunnelManager) Start(cfg TunnelConfig) error {
	m.mu.Lock()
	if m.running {
		m.mu.Unlock()
		return fmt.Errorf("tunnel already running")
	}
	m.mu.Unlock()

	corePath := getCorePath()
	if _, err := exec.LookPath(corePath); err != nil {
		if _, statErr := os.Stat(corePath); statErr != nil {
			return fmt.Errorf("sing-box core not found (searched: %s)", corePath)
		}
	}

	// Validate target port
	if cfg.Port <= 0 || cfg.Port > 65535 {
		return fmt.Errorf("invalid port number: %d", cfg.Port)
	}
	if cfg.Host == "" {
		return fmt.Errorf("proxy host cannot be empty")
	}

	// Build outbound config
	var outbound map[string]interface{}
	switch cfg.Protocol {
	case "HTTP":
		outbound = map[string]interface{}{
			"type":        "http",
			"tag":         "proxy-out",
			"server":      cfg.Host,
			"server_port": cfg.Port,
		}
		if cfg.Username != "" {
			outbound["username"] = cfg.Username
		}
		if cfg.Password != "" {
			outbound["password"] = cfg.Password
		}
	case "SOCKS4":
		outbound = map[string]interface{}{
			"type":        "socks",
			"tag":         "proxy-out",
			"server":      cfg.Host,
			"server_port": cfg.Port,
			"version":     "4",
		}
		if cfg.Username != "" {
			outbound["username"] = cfg.Username
		}
	default: // SOCKS5
		outbound = map[string]interface{}{
			"type":        "socks",
			"tag":         "proxy-out",
			"server":      cfg.Host,
			"server_port": cfg.Port,
			"version":     "5",
		}
		if cfg.Username != "" {
			outbound["username"] = cfg.Username
		}
		if cfg.Password != "" {
			outbound["password"] = cfg.Password
		}
	}

	rules := []map[string]interface{}{
		{"action": "hijack-dns", "protocol": "dns"},
		{"action": "sniff"},
	}
	if cfg.BypassLAN {
		rules = append(rules, map[string]interface{}{
			"ip_is_private": true,
			"outbound":      "direct",
		})
	}

	stack := cfg.Stack
	if stack == "" {
		stack = "gvisor"
	}

	ifaceName := cfg.Interface
	if ifaceName == "" {
		if runtime.GOOS == "windows" {
			ifaceName = "wintun"
		} else {
			ifaceName = "tun0"
		}
	}

	singboxJSON := map[string]interface{}{
		"log": map[string]interface{}{
			"level":     "info",
			"timestamp": true,
		},
		"inbounds": []map[string]interface{}{
			{
				"type":           "tun",
				"tag":            "tun-in",
				"interface_name": ifaceName,
				"address":        []string{"172.19.0.1/30"},
				"auto_route":     true,
				"strict_route":   true,
				"stack":          stack,
			},
		},
		"outbounds": []interface{}{
			outbound,
			map[string]interface{}{
				"type": "direct",
				"tag":  "direct",
			},
		},
		"route": map[string]interface{}{
			"rules":                 rules,
			"auto_detect_interface": true,
		},
		"dns": map[string]interface{}{
			"servers": []map[string]interface{}{
				{
					"tag":    "proxy-dns",
					"type":   "tcp",
					"server": "1.1.1.1",
					"detour": "proxy-out",
				},
			},
		},
	}

	configBytes, err := json.MarshalIndent(singboxJSON, "", "  ")
	if err != nil {
		return err
	}

	tmpConfig, err := os.CreateTemp("", "p2tun_config_*.json")
	if err != nil {
		return err
	}
	if _, err := tmpConfig.Write(configBytes); err != nil {
		tmpConfig.Close()
		return err
	}
	tmpPath := tmpConfig.Name()
	tmpConfig.Close()

	// Dry check config first
	checkCmd := exec.Command(corePath, "check", "-c", tmpPath)
	if out, err := checkCmd.CombinedOutput(); err != nil {
		os.Remove(tmpPath)
		return fmt.Errorf("configuration verification failed: %s (%v)", string(out), err)
	}

	cmd := exec.Command(corePath, "run", "-c", tmpPath)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		os.Remove(tmpPath)
		return err
	}
	cmd.Stderr = cmd.Stdout

	if err := cmd.Start(); err != nil {
		os.Remove(tmpPath)
		return fmt.Errorf("start failed: %w (ensure root/administrator)", err)
	}

	m.mu.Lock()
	m.cmd = cmd
	m.running = true
	m.target = fmt.Sprintf("%s %s:%d", cfg.Protocol, cfg.Host, cfg.Port)
	m.mu.Unlock()

	m.broadcast(fmt.Sprintf("[*] sing-box core started (PID: %d) -> %s", cmd.Process.Pid, m.target))

	go func() {
		defer os.Remove(tmpPath)
		reader := bufio.NewReader(stdout)
		for {
			line, err := reader.ReadString('\n')
			if len(line) > 0 {
				m.broadcast(line)
			}
			if err != nil {
				break
			}
		}
		cmd.Wait()

		m.mu.Lock()
		m.running = false
		m.cmd = nil
		m.mu.Unlock()
		m.broadcast("[*] Tunnel disconnected.")
	}()

	return nil
}

func (m *TunnelManager) Stop() {
	m.mu.Lock()
	cmd := m.cmd
	m.mu.Unlock()

	if cmd != nil && cmd.Process != nil {
		m.broadcast("[*] Stopping tunnel...")
		if runtime.GOOS == "windows" {
			cmd.Process.Kill()
		} else {
			cmd.Process.Signal(syscall.SIGINT)
			time.AfterFunc(2*time.Second, func() {
				if cmd.Process != nil {
					cmd.Process.Kill()
				}
			})
		}
	}
}

func openBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	_ = cmd.Start()
}

func main() {
	mux := http.NewServeMux()

	// Serve UI
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		content, err := webFS.ReadFile("web/index.html")
		if err != nil {
			http.Error(w, "Asset not found", 500)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write(content)
	})

	// Status API
	mux.HandleFunc("/api/status", func(w http.ResponseWriter, r *http.Request) {
		manager.mu.Lock()
		res := map[string]interface{}{
			"running": manager.running,
			"target":  manager.target,
		}
		manager.mu.Unlock()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(res)
	})

	// Test Connectivity API
	mux.HandleFunc("/api/test", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", 405)
			return
		}
		var req struct {
			Host string `json:"host"`
			Port int    `json:"port"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}

		start := time.Now()
		conn, err := net.DialTimeout("tcp", fmt.Sprintf("%s:%d", req.Host, req.Port), 2*time.Second)
		w.Header().Set("Content-Type", "application/json")
		if err != nil {
			json.NewEncoder(w).Encode(map[string]interface{}{
				"ok":    false,
				"error": err.Error(),
			})
			return
		}
		conn.Close()
		latency := time.Since(start).Milliseconds()
		json.NewEncoder(w).Encode(map[string]interface{}{
			"ok":      true,
			"latency": latency,
		})
	})

	// Scan Local Proxies API
	mux.HandleFunc("/api/scan", func(w http.ResponseWriter, r *http.Request) {
		type DiscoveredProxy struct {
			Protocol string `json:"protocol"`
			Host     string `json:"host"`
			Port     int    `json:"port"`
			App      string `json:"app"`
		}

		var discovered []DiscoveredProxy
		var mu sync.Mutex
		var wg sync.WaitGroup

		ports := make(map[int]string)
		if runtime.GOOS != "windows" {
			out, err := exec.Command("ss", "-tulpn").Output()
			if err == nil {
				for _, line := range strings.Split(string(out), "\n") {
					parts := strings.Fields(line)
					if len(parts) >= 5 && parts[1] == "LISTEN" {
						addr := parts[4]
						pname := ""
						if len(parts) > 6 && strings.Contains(parts[6], `users:(("`) {
							sub := strings.Split(parts[6], `users:(("`)
							if len(sub) > 1 {
								pname = strings.Split(sub[1], `"`)[0]
							}
						}
						idx := strings.LastIndex(addr, ":")
						if idx != -1 {
							var p int
							if _, err := fmt.Sscanf(addr[idx+1:], "%d", &p); err == nil {
								if _, ok := ports[p]; !ok {
									ports[p] = pname
								}
							}
						}
					}
				}
			}
		}

		common := []int{1080, 10808, 10809, 2080, 7890, 7891, 8080, 8888, 8889, 9050, 9051, 9999, 11111, 20128, 4747}
		for _, cp := range common {
			if _, ok := ports[cp]; !ok {
				ports[cp] = ""
			}
		}

		sem := make(chan struct{}, 25)
		for p, app := range ports {
			wg.Add(1)
			sem <- struct{}{}
			go func(port int, appName string) {
				defer wg.Done()
				defer func() { <-sem }()

				// 1. Check SOCKS5
				if c, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 250*time.Millisecond); err == nil {
					c.SetDeadline(time.Now().Add(250 * time.Millisecond))
					c.Write([]byte{0x05, 0x01, 0x00})
					buf := make([]byte, 2)
					if n, _ := c.Read(buf); n == 2 && buf[0] == 0x05 && buf[1] == 0x00 {
						mu.Lock()
						discovered = append(discovered, DiscoveredProxy{
							Protocol: "SOCKS5", Host: "127.0.0.1", Port: port, App: appName,
						})
						mu.Unlock()
					}
					c.Close()
				}

				// 2. Check SOCKS4
				if c, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 250*time.Millisecond); err == nil {
					c.SetDeadline(time.Now().Add(250 * time.Millisecond))
					c.Write([]byte{0x04, 0x01, 0x00, 0x50, 0x01, 0x02, 0x03, 0x04, 0x00})
					buf := make([]byte, 2)
					if n, _ := c.Read(buf); n >= 2 && buf[0] == 0x00 {
						mu.Lock()
						discovered = append(discovered, DiscoveredProxy{
							Protocol: "SOCKS4", Host: "127.0.0.1", Port: port, App: appName,
						})
						mu.Unlock()
					}
					c.Close()
				}

				// 3. Check HTTP Connect
				if c, err := net.DialTimeout("tcp", fmt.Sprintf("127.0.0.1:%d", port), 250*time.Millisecond); err == nil {
					c.SetDeadline(time.Now().Add(250 * time.Millisecond))
					c.Write([]byte("CONNECT 127.0.0.1:80 HTTP/1.1\r\nHost: 127.0.0.1:80\r\n\r\n"))
					buf := make([]byte, 16)
					if n, _ := c.Read(buf); n > 0 && strings.Contains(string(buf[:n]), "HTTP/") {
						mu.Lock()
						discovered = append(discovered, DiscoveredProxy{
							Protocol: "HTTP", Host: "127.0.0.1", Port: port, App: appName,
						})
						mu.Unlock()
					}
					c.Close()
				}
			}(p, app)
		}
		wg.Wait()

		w.Header().Set("Content-Type", "application/json")
		if discovered == nil {
			discovered = []DiscoveredProxy{}
		}
		json.NewEncoder(w).Encode(discovered)
	})

	// Start API
	mux.HandleFunc("/api/start", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", 405)
			return
		}
		var cfg TunnelConfig
		if err := json.NewDecoder(r.Body).Decode(&cfg); err != nil {
			http.Error(w, err.Error(), 400)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if err := manager.Start(cfg); err != nil {
			json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
			return
		}
		json.NewEncoder(w).Encode(map[string]bool{"ok": true})
	})

	// Stop API
	mux.HandleFunc("/api/stop", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", 405)
			return
		}
		manager.Stop()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]bool{"ok": true})
	})

	// Event stream for logs
	mux.HandleFunc("/api/events", func(w http.ResponseWriter, r *http.Request) {
		flusher, ok := w.(http.Flusher)
		if !ok {
			http.Error(w, "Streaming unsupported", 500)
			return
		}

		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("Connection", "keep-alive")

		logChan := make(chan string, 100)
		manager.mu.Lock()
		manager.listeners[logChan] = true
		manager.mu.Unlock()
		defer func() {
			manager.mu.Lock()
			delete(manager.listeners, logChan)
			close(logChan)
			manager.mu.Unlock()
		}()

		notify := r.Context().Done()
		for {
			select {
			case <-notify:
				return
			case msg := <-logChan:
				fmt.Fprintf(w, "data: %s\n\n", msg)
				flusher.Flush()
			}
		}
	})

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		fmt.Printf("Failed to bind port: %v\n", err)
		return
	}
	port := listener.Addr().(*net.TCPAddr).Port
	url := fmt.Sprintf("http://127.0.0.1:%d", port)

	fmt.Println("====================================================")
	fmt.Printf(" P2TUN Modern GUI Ready at: %s\n", url)
	fmt.Println(" Automatic browser launch triggered.")
	fmt.Println(" Press Ctrl+C to terminate.")
	fmt.Println("====================================================")

	go openBrowser(url)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigChan
		manager.Stop()
		os.Exit(0)
	}()

	server := &http.Server{Handler: mux}
	if err := server.Serve(listener); err != nil && err != http.ErrServerClosed {
		fmt.Printf("Server error: %v\n", err)
	}
}
