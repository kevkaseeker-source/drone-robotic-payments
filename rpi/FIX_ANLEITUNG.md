# SSH-Drop Fix — Anleitung (2026-05-23)

## MORGEN ZUERST: Option A (5 Minuten)

SSH rein, dann:

```bash
# 1. Globale pppd-Option fixen (Hauptursache SSH-Drop)
sudo sed -i 's/^defaultroute/#defaultroute/' /etc/ppp/options

# 2. Alle alten pppd-Fixes bereinigen
sudo sed -i '/noresolv/d; /nodefaulroute/d' /etc/ppp/peers/4g
grep -q 'nodefaultroute' /etc/ppp/peers/4g || echo 'nodefaultroute' | sudo tee -a /etc/ppp/peers/4g

# 3. dhcpcd.conf static IP Tippfehler korrigieren
sudo sed -i 's/ip_adress/ip_address/g' /etc/dhcpcd.conf

# 4. Prüfen ob NetworkManager UND dhcpcd laufen (Konflikt)
systemctl is-active NetworkManager dhcpcd

echo "=== OPTION A FIXES ANGEWENDET ==="
```

Dann startup.sh starten:
```bash
nohup bash ~/startup.sh > ~/startup.log 2>&1 &
```

**Wenn SSH nach 2 Minuten zurückkommt und ppp0 aktiv ist → Option A hat funktioniert, fertig!**

---

## Option B: RNDIS-Modus (wenn Option A nicht hilft)

RNDIS = Modem verhält sich wie eine USB-Netzwerkkarte (usb0).
Kein pppd → kein SSH-Drop → viel stabiler.

Neue Dateien liegen in: `G:\Meine Ablage\Kevin's stuff\progress\rpi\`
- `startup_rndis.sh` → ersetzt startup.sh
- `start_tunnel_rndis.sh` → ersetzt start_tunnel.sh

### Einmalige Einrichtung (RNDIS-Modus aktivieren):

SSH rein, dann:
```bash
# Modem einschalten
cd /home/kevkaakvek && source drone-env/bin/activate
python3 modem_on.py
sleep 15

# AT-Befehl senden: RNDIS-Modus aktivieren
echo -e 'AT+CUSBPIDSWITCH=9011,1,1\r' | sudo tee /dev/ttyUSB2
```

Modem bootet neu (~10 Sekunden). Danach:
```bash
ip link show usb0
```
→ usb0 muss erscheinen.

Dann in `/etc/dhcpcd.conf` hinzufügen:
```
interface usb0
metric 400
```

Neue Scripts hochladen (WinSCP), dann:
```bash
chmod +x ~/startup_rndis.sh ~/start_tunnel_rndis.sh
```

### Outdoor-Prozedur mit RNDIS:
```bash
bash ~/startup_rndis.sh    # Modem an, warten auf usb0
# Ethernet abziehen
bash ~/start_tunnel_rndis.sh  # Flask + ngrok via usb0
```
