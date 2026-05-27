#!/bin/bash
# RPi4 startup — nur 4G + main.py (Flask und ngrok laufen auf dem PC)

cd /home/kevkaakvek
source drone-env/bin/activate

echo "=== pppd starten (4G) ==="
# Im Hintergrund starten — SSH-Drop ist normal danach
sudo pppd call 4g &
PPPD_PID=$!
echo "pppd PID: $PPPD_PID"

echo "Warte auf ppp0 ..."
for i in $(seq 1 30); do
    if ip link show ppp0 > /dev/null 2>&1; then
        echo "OK: ppp0 ist UP"
        break
    fi
    sleep 2
done

if ! ip link show ppp0 > /dev/null 2>&1; then
    echo "FEHLER: ppp0 nicht hochgekommen. pppd-Log prüfen."
    exit 1
fi

echo "=== DNS sicherstellen ==="
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null

echo "=== main.py starten (pollt PC-Server über 4G) ==="
nohup /home/kevkaakvek/drone-env/bin/python3 /home/kevkaakvek/main.py > /home/kevkaakvek/main.log 2>&1 &
echo "main.py PID: $!"
echo ""
echo "Alles läuft. SSH kann jetzt getrennt werden."
echo "Log: tail -f ~/main.log"
