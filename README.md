# Vallox ValloPlus 500 SE - Smart Automatik (RS485)

Dieses Projekt steuert eine Vallox ValloPlus 500 SE Lüftungsanlage (Digit SED Bedienfeld) vollautomatisch über den RS485-Bus. Es wertet die internen Temperaturfühler der Anlage aus und regelt den Bypass (Wärmetauscher) sowie die Lüfterdrehzahl, um im Sommer eine effiziente Nachtauskühlung und einen Hitzeschutz zu gewährleisten.

Das Skript ist so konzipiert, dass es manuelle Eingriffe am Wandbedienteil erkennt und fehlerhafte Einstellungen (z. B. versehentlich offener Bypass bei 30 °C Außentemperatur) innerhalb von 60 Sekunden automatisch korrigiert.

## 🛠 Hardware-Voraussetzungen

*   **Raspberry Pi** (getestet mit DietPi OS, sehr ressourcenschonend)
*   **USB-zu-RS485 Adapter** (Empfehlung: FTDI FT232RL Chipsatz)
*   Ein 2-adriges Kabel (z. B. ein Twisted-Pair aus einem Cat-Netzwerkkabel oder Klingeldraht)

### Verkabelung
Die Anlage kommuniziert über den RS485-Bus. Es werden nur zwei Adern benötigt:
*   Klemme **A** (oder D+) am USB-Adapter -> an Klemme **A** der Vallox-Platine / des Bedienteils
*   Klemme **B** (oder D-) am USB-Adapter -> an Klemme **B** der Vallox-Platine / des Bedienteils
*   *Hinweis: GND / VCC bleiben am USB-Stick zwingend unbelegt!*

## 📦 Installation & Abhängigkeiten

Auf dem System muss Python 3 und die Bibliothek `pyserial` installiert sein.
Unter Debian/DietPi erfolgt die Installation mit:

```bash
sudo apt update
sudo apt install python3 python3-serial
```

## ⚙️ Logik der Automatik

Das Skript liest die Temperaturen der Abluft (Innen) und Außenluft und schaltet nach folgenden Regeln:

1.  **Nachtauskühlung:** Draußen kühler als drinnen UND drinnen wärmer als 23 °C 
    -> *Wärmetauscher DEAKTIVIERT (Klappe auf), Lüfter auf Stufe 6 (Boost).*
2.  **Hitzeschutz:** Draußen wärmer als drinnen 
    -> *Wärmetauscher AKTIV (Klappe zu, Kälterückgewinnung), Lüfter Stufe 2.*
3.  **Normalbetrieb:** Haus ist auf Wohlfühltemperatur (unter 22 °C) 
    -> *Wärmetauscher AKTIV, Lüfter Stufe 2.*
4.  **Frostschutz:** Außentemperatur unter 10 °C 
    -> *Wärmetauscher AKTIV (Wärmerückgewinnung), Lüfter Stufe 2.*

## 🚀 Einrichtung als Systemd-Service (Autostart)

Damit das Skript im Hintergrund läuft und bei einem Neustart automatisch startet, wird ein Systemd-Service genutzt.

1. Datei erstellen: 
```bash
sudo nano /etc/systemd/system/vallox.service
```

2. Folgenden Inhalt einfügen (Pfade ggf. anpassen!):
```ini
[Unit]
Description=Vallox Smart Steuerung
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/dietpi/valloplus_500_se/vallox_automatik.py
WorkingDirectory=/home/dietpi/valloplus_500_se/
Restart=always
RestartSec=10
User=root

[Install]
WantedBy=multi-user.target
```

3. Service aktivieren und starten:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vallox.service
sudo systemctl start vallox.service
```

## 💻 Service-Befehle (Cheatsheet)

Hier sind die wichtigsten Befehle, um den Hintergrunddienst zu steuern und zu überwachen:

**Status überprüfen:**
Zeigt an, ob der Dienst läuft, und gibt die letzten Fehlermeldungen aus.
```bash
sudo systemctl status vallox.service
```

**Live-Logs ansehen (WICHTIG):**
Zeigt in Echtzeit an, was das Skript gerade tut (Temperaturänderungen, Modus-Wechsel). Beenden Sie die Ansicht jederzeit mit `Strg + C`.
```bash
sudo journalctl -u vallox.service -f
```

**Service stoppen:**
Pausiert die Automatik (z. B. wenn Sie das Skript bearbeiten wollen).
```bash
sudo systemctl stop vallox.service
```

**Service starten:**
Startet die Automatik wieder.
```bash
sudo systemctl start vallox.service
```

**Service neu starten:**
Lädt das Skript neu (notwendig, nachdem Sie Änderungen am Python-Code vorgenommen haben).
```bash
sudo systemctl restart vallox.service
```
