# Vallox ValloPlus 500 SE: Automatik über RS485

Dieses Projekt steuert eine Vallox ValloPlus 500 SE mit dem Bedienteil Digit SED über den RS485-Bus. Ein Python-Skript liest die Temperaturfühler der Anlage. Es stellt den Bypass und die Lüfterstufe ein. Im Sommer kühlt es das Haus nachts mit Außenluft. Bei starkem Frost schaltet es die Anlage aus, damit sie nicht elektrisch vorheizen muss.

Der Bypass leitet die Außenluft am Wärmetauscher vorbei. Ist der Bypass auf, kommt die kühle Nachtluft ohne Erwärmung ins Haus.

Das Skript liest den Zustand der Anlage nicht zurück. Es sendet einen Befehl, wenn sich sein Sollzustand ändert. Zusätzlich sendet es den Sollzustand etwa alle 15 Minuten erneut. Eine Änderung am Bedienteil bleibt darum bis zu 15 Minuten bestehen.

## Hardware

* Raspberry Pi (getestet mit DietPi)
* USB-RS485-Adapter, zum Beispiel mit dem Chip FTDI FT232RL
* Ein Kabel mit zwei Adern, zum Beispiel ein verdrilltes Paar aus einem Netzwerkkabel oder Klingeldraht

### Verkabelung

Der Adapter braucht nur zwei Adern:

* Klemme A (oder D+) am Adapter an Klemme A der Vallox-Platine oder des Bedienteils
* Klemme B (oder D-) am Adapter an Klemme B der Vallox-Platine oder des Bedienteils

Schließen Sie GND und VCC am Adapter nicht an.

## Installation

Das Skript braucht Python 3 und die Bibliothek `pyserial`. Unter Debian oder DietPi installieren Sie beide so:

```bash
sudo apt update
sudo apt install python3 python3-serial
```

## Regeln der Automatik

Das Skript `vallox_automatik.py` prüft die Temperaturen etwa einmal pro Minute. Als Innentemperatur nimmt es die Ablufttemperatur. Es prüft die Regeln in dieser Reihenfolge. Die erste Regel, die zutrifft, gilt.

| Nr. | Modus | Bedingung | Bypass | Lüfter |
|---|---|---|---|---|
| 1 | Frost-Stopp | außen unter -5 °C | Anlage aus | Anlage aus |
| 2 | Nachtauskühlung | innen ab 24 °C, außen mindestens 2 °C kühler als innen und über 10 °C | auf | Stufe 4 |
| 3 | Normalbetrieb | innen unter 23 °C | zu | Stufe 2 |
| 4 | Hitzeschutz | außen gleich warm wie innen oder wärmer | zu | Stufe 2 |
| 5 | Winterbetrieb | außen 10 °C oder kälter | zu | Stufe 2 |
| 6 | Wartezone | keine andere Regel trifft zu | unverändert | unverändert |

Die Grenzwerte stehen am Anfang von `vallox_automatik.py`.

### Wartezone

In der Wartezone ändert das Skript nichts. Eine laufende Nachtauskühlung läuft darum weiter, auch wenn der Abstand zwischen innen und außen unter 2 °C fällt. Die Nachtauskühlung endet erst, wenn Regel 1, 3, 4 oder 5 zutrifft. So schaltet die Anlage nicht ständig hin und her.

Direkt nach dem Start kennt das Skript keinen Sollzustand. Fällt die erste Messung in die Wartezone, sendet es nichts.

### Frost-Stopp

Die Anlage läuft wieder an, wenn außen mindestens -3 °C sind. Sie bleibt aber mindestens 30 Minuten aus. Bei stehender Anlage misst der Außenfühler die Luft im Kanal, und diese Luft erwärmt sich. Die Mindestzeit verhindert, dass die Anlage darum ständig an- und ausgeht.

Im ausgeschalteten Zustand zeigt das Bedienteil „0“ und zeitweise „X-e“. Das ist die normale Anzeige.

### Messgenauigkeit

Das Skript rechnet den Rohwert linear in Grad Celsius um: `Rohwert / 2,5 - 44`. Es misst die Temperatur darum nur in Schritten von 0,4 °C. Die Schwelle von 23 °C liegt in der Praxis zwischen 22,8 °C und 23,2 °C.

## Einrichtung als systemd-Dienst

Ein systemd-Dienst startet das Skript im Hintergrund und nach jedem Neustart des Raspberry Pi.

1. Legen Sie die Dienstdatei an:
   ```bash
   sudo nano /etc/systemd/system/vallox.service
   ```

2. Fügen Sie diesen Inhalt ein. Wenn Ihr Projekt in einem anderen Verzeichnis liegt, passen Sie die Pfade an.
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

3. Aktivieren und starten Sie den Dienst:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable vallox.service
   sudo systemctl start vallox.service
   ```

## Befehle für den Dienst

| Zweck | Befehl |
|---|---|
| Zustand und letzte Fehlermeldungen anzeigen | `sudo systemctl status vallox.service` |
| Laufende Ausgabe des Skripts anzeigen (Ende mit Strg+C) | `sudo journalctl -u vallox.service -f` |
| Automatik anhalten | `sudo systemctl stop vallox.service` |
| Automatik starten | `sudo systemctl start vallox.service` |
| Automatik nach einer Änderung am Code neu laden | `sudo systemctl restart vallox.service` |

## Hilfsskripte

Stoppen Sie den Dienst, bevor Sie ein Hilfsskript starten. Sonst greifen zwei Programme gleichzeitig auf den Adapter zu.

| Datei | Zweck |
|---|---|
| `sniffer.py` | Zeigt Befehle auf dem Bus mit Absender, Empfänger, Register und Wert. Abfragen und Temperaturmeldungen der Hauptplatine blendet es aus. Mit `--alle` zeigt es jedes Paket. |
| `test_steuerung.py` | Menü zum Senden einzelner Befehle: Lüfterstufe, Bypass, Anlage aus und ein. |
| `temp_now.py` | Liest die Temperaturen einmal und zeigt die passende Regel. Die Grenzwerte in dieser Datei weichen von `vallox_automatik.py` ab, und der Frost-Stopp fehlt. |
| `temp_live.py` | Sucht 15 Sekunden lang nach Registern mit Temperaturwerten. Es nutzt noch die alte Formel `Rohwert - 151`. |

Der USB-Adapter gibt gesendete Bytes nicht an den Empfang zurück. Der Sniffer zeigt die Befehle dieses Projekts darum nicht an.

## Protokoll

Der Bus arbeitet mit 9600 Baud. Jedes Paket hat 6 Bytes:

| Byte | Inhalt |
|---|---|
| 1 | Startbyte `0x01` |
| 2 | Absender |
| 3 | Empfänger |
| 4 | Register |
| 5 | Wert |
| 6 | Prüfsumme: Summe der Bytes 1 bis 5 modulo 256 |

Ein Paket mit Register `0x00` ist eine Abfrage. Sein Wert ist das abgefragte Register.

### Adressen

| Adresse | Gerät |
|---|---|
| `0x10` | alle Hauptplatinen |
| `0x11` | Hauptplatine |
| `0x20` | alle Bedienteile |
| `0x21` | Bedienteil an der Wand |
| `0x22` | dieses Projekt |

### Register

| Register | Inhalt | Werte |
|---|---|---|
| `0x29` | Lüfterstufe | 1, 3, 7, 15, 31, 63, 127, 255 für Stufe 1 bis 8 (siehe `temp_bits.txt`) |
| `0x32` | Außentemperatur | Rohwert |
| `0x34` | Ablufttemperatur | Rohwert |
| `0xA3` | Ein/Aus und Bypass | 137 = ein, Bypass zu. 129 = ein, Bypass auf. 136 = aus. |

Senden Sie Aus (136) und Ein (137) an `0x11` und zusätzlich an `0x20`. Wenn das Aus nur an `0x11` geht, lässt sich die Anlage danach nur noch am Bedienteil einschalten.

Ändert ein Bedienteil die Lüfterstufe, meldet die Hauptplatine den neuen Wert selbst an `0x10` und `0x20`. Für `0xA3` tut sie das nicht.
