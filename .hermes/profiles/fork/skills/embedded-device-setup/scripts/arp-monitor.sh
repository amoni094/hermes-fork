#!/bin/bash
# ARP network monitor - run every 5 minutes via cron on the Pi
# Logs all active devices (IP, MAC, vendor) with timestamp to /var/log/arp-monitor.log
# Install: sudo cp arp-monitor.sh /usr/local/bin/arp-monitor.sh && sudo chmod +x /usr/local/bin/arp-monitor.sh
# Cron:    */5 * * * * /usr/local/bin/arp-monitor.sh
# Requires: nmap (sudo apt-get install -y nmap)

LOGFILE="/var/log/arp-monitor.log"

while IFS= read -r line; do
    if [[ "$line" =~ "report for" ]]; then
        IP=$(echo "$line" | awk '{print $NF}')
    elif [[ "$line" =~ "MAC Address" ]]; then
        MAC=$(echo "$line" | awk '{print $3}')
        VENDOR=$(echo "$line" | sed 's/.*[(]\(.*\)[)]/\1/')
        echo "$(date '+%Y-%m-%d %H:%M:%S')  $IP  $MAC  $VENDOR" >> "$LOGFILE"
    fi
done < <(sudo nmap -sn 192.168.0.0/24 -T4 2>/dev/null | grep -E "report for|MAC Address")
