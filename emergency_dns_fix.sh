#!/bin/bash

# Emergency DNS Fix Script for Linux Servers
# Solves persistent DNS resolution issues with YouTube downloader

echo "🚨 Emergency DNS Fix Script Starting..."
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root (use sudo)"
   exit 1
fi

# Step 1: Backup current configuration
print_step "1. Backing up current DNS configuration..."
cp /etc/resolv.conf /etc/resolv.conf.emergency_backup_$(date +%Y%m%d_%H%M%S)
cp /etc/systemd/resolved.conf /etc/systemd/resolved.conf.emergency_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
print_status "Backup completed"

# Step 2: Stop conflicting services
print_step "2. Stopping conflicting DNS services..."
systemctl stop systemd-resolved 2>/dev/null || true
systemctl stop dnsmasq 2>/dev/null || true
systemctl stop NetworkManager 2>/dev/null || true
print_status "Services stopped"

# Step 3: Clear DNS cache
print_step "3. Clearing DNS cache..."
systemd-resolve --flush-caches 2>/dev/null || true
resolvectl flush-caches 2>/dev/null || true
echo 3 > /proc/sys/vm/drop_caches
print_status "DNS cache cleared"

# Step 4: Configure emergency DNS
print_step "4. Configuring emergency DNS settings..."
cat > /etc/resolv.conf << 'EOF'
# Emergency DNS Configuration
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
nameserver 1.0.0.1
nameserver 208.67.222.222
nameserver 208.67.220.220
options timeout:2
options attempts:5
options rotate
options single-request-reopen
options edns0
options trust-ad
EOF

# Make resolv.conf immutable to prevent overwriting
chattr +i /etc/resolv.conf 2>/dev/null || true
print_status "Emergency DNS configured"

# Step 5: Configure systemd-resolved
print_step "5. Configuring systemd-resolved..."
mkdir -p /etc/systemd/resolved.conf.d/
cat > /etc/systemd/resolved.conf.d/emergency-dns.conf << 'EOF'
[Resolve]
DNS=8.8.8.8 8.8.4.4 1.1.1.1 1.0.0.1 208.67.222.222 208.67.220.220
FallbackDNS=9.9.9.9 149.112.112.112
Domains=~.
DNSSEC=no
DNSOverTLS=no
Cache=yes
DNSStubListener=no
ReadEtcHosts=yes
ResolveUnicastSingleLabel=yes
EOF
print_status "systemd-resolved configured"

# Step 6: Network optimization
print_step "6. Optimizing network parameters..."
cat > /etc/sysctl.d/99-emergency-network.conf << 'EOF'
# Emergency Network Optimization
net.core.rmem_default = 262144
net.core.rmem_max = 16777216
net.core.wmem_default = 262144
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 65536 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
net.ipv4.tcp_keepalive_time = 120
net.ipv4.tcp_keepalive_intvl = 30
net.ipv4.tcp_keepalive_probes = 3
net.ipv4.tcp_retries2 = 8
net.ipv4.tcp_syn_retries = 3
net.ipv4.tcp_synack_retries = 3
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_tw_reuse = 1
net.ipv4.ip_local_port_range = 1024 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr
EOF

sysctl -p /etc/sysctl.d/99-emergency-network.conf
print_status "Network parameters optimized"

# Step 7: Configure hosts file with YouTube IPs
print_step "7. Adding YouTube IP addresses to hosts file..."
# Backup hosts file
cp /etc/hosts /etc/hosts.emergency_backup_$(date +%Y%m%d_%H%M%S)

# Add YouTube IPs (these are some known YouTube server IPs)
cat >> /etc/hosts << 'EOF'

# Emergency YouTube DNS entries
142.250.191.14 youtube.com
142.250.191.14 www.youtube.com
142.250.191.14 m.youtube.com
172.217.16.110 youtubei.googleapis.com
172.217.16.110 www.googleapis.com
216.58.194.174 googlevideo.com
216.58.194.174 r1---sn-4g5e6nls.googlevideo.com
216.58.194.174 r2---sn-4g5e6nls.googlevideo.com
216.58.194.174 r3---sn-4g5e6nls.googlevideo.com
216.58.194.174 r4---sn-4g5e6nls.googlevideo.com
EOF
print_status "YouTube IPs added to hosts file"

# Step 8: Restart services
print_step "8. Restarting network services..."
systemctl restart systemd-resolved 2>/dev/null || true
systemctl restart networking 2>/dev/null || true
systemctl restart NetworkManager 2>/dev/null || true
sleep 3
print_status "Services restarted"

# Step 9: Test DNS resolution
print_step "9. Testing DNS resolution..."
test_domains=("youtube.com" "www.youtube.com" "googlevideo.com" "googleapis.com")
dns_servers=("8.8.8.8" "1.1.1.1" "208.67.222.222")

for domain in "${test_domains[@]}"; do
    print_status "Testing $domain..."
    for dns in "${dns_servers[@]}"; do
        if nslookup $domain $dns >/dev/null 2>&1; then
            print_status "✓ $domain resolves via $dns"
            break
        else
            print_warning "✗ $domain failed via $dns"
        fi
    done
done

# Step 10: Test connectivity
print_step "10. Testing connectivity..."
if ping -c 2 youtube.com >/dev/null 2>&1; then
    print_status "✓ YouTube connectivity test passed"
else
    print_warning "✗ YouTube connectivity test failed"
fi

if curl -s --connect-timeout 10 https://www.youtube.com >/dev/null 2>&1; then
    print_status "✓ HTTPS connectivity test passed"
else
    print_warning "✗ HTTPS connectivity test failed"
fi

# Step 11: Create environment variables
print_step "11. Creating environment variables..."
cat > /tmp/emergency_youtube_env.sh << 'EOF'
#!/bin/bash
# Emergency YouTube Downloader Environment

# DNS and Network Settings
export PYTHONHTTPSVERIFY=0
export CURL_CA_BUNDLE=""
export REQUESTS_CA_BUNDLE=""
export SSL_VERIFY=false

# Timeout Settings
export SOCKET_TIMEOUT=300
export CONNECT_TIMEOUT=120
export READ_TIMEOUT=600

# Python Settings
export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

# Network Settings
export RES_OPTIONS="timeout:2 attempts:5 rotate single-request-reopen"
export RESOLV_MULTI=on

# yt-dlp specific settings
export YT_DLP_SOCKET_TIMEOUT=300
export YT_DLP_RETRIES=10
export YT_DLP_FRAGMENT_RETRIES=10

# Force IPv4
export FORCE_IPV4=1

echo "Emergency environment variables loaded!"
EOF

chmod +x /tmp/emergency_youtube_env.sh
print_status "Environment variables created"

# Step 12: Create recovery script
print_step "12. Creating recovery script..."
cat > /tmp/emergency_recovery.sh << 'EOF'
#!/bin/bash
# Emergency Recovery Script

echo "Recovering original DNS settings..."

# Remove immutable flag
chattr -i /etc/resolv.conf 2>/dev/null || true

# Restore backups
LATEST_RESOLV_BACKUP=$(ls -t /etc/resolv.conf.emergency_backup_* 2>/dev/null | head -1)
LATEST_RESOLVED_BACKUP=$(ls -t /etc/systemd/resolved.conf.emergency_backup_* 2>/dev/null | head -1)
LATEST_HOSTS_BACKUP=$(ls -t /etc/hosts.emergency_backup_* 2>/dev/null | head -1)

if [ -f "$LATEST_RESOLV_BACKUP" ]; then
    cp "$LATEST_RESOLV_BACKUP" /etc/resolv.conf
    echo "Restored resolv.conf"
fi

if [ -f "$LATEST_RESOLVED_BACKUP" ]; then
    cp "$LATEST_RESOLVED_BACKUP" /etc/systemd/resolved.conf
    echo "Restored resolved.conf"
fi

if [ -f "$LATEST_HOSTS_BACKUP" ]; then
    cp "$LATEST_HOSTS_BACKUP" /etc/hosts
    echo "Restored hosts file"
fi

# Remove emergency configurations
rm -f /etc/systemd/resolved.conf.d/emergency-dns.conf
rm -f /etc/sysctl.d/99-emergency-network.conf

# Restart services
systemctl restart systemd-resolved
systemctl restart networking

echo "Recovery completed!"
EOF

chmod +x /tmp/emergency_recovery.sh
print_status "Recovery script created at /tmp/emergency_recovery.sh"

# Final status
echo ""
echo "========================================"
print_status "🎉 Emergency DNS Fix Completed!"
echo "========================================"
echo ""
print_status "Next steps:"
echo "1. Run: source /tmp/emergency_youtube_env.sh"
echo "2. Test: python3 run_on_linux_server.py test"
echo "3. If issues persist, try: python3 emergency_youtube_test.py"
echo "4. To recover original settings: sudo /tmp/emergency_recovery.sh"
echo ""
print_warning "Note: This is an aggressive fix. Monitor your system!"