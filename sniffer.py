import serial
import sys
import time

PORT = '/dev/ttyUSB0'
BAUD = 9600

# Diese Register zeigen wir auch an, wenn die Hauptplatine (0x11) sie sendet
INTERESSANT = (0xA3, 0x29)

def start_sniffer(alle=False):
    try:
        with serial.Serial(PORT, BAUD) as ser:
            print("Sniffer läuft. Warte auf Befehle vom Bedienteil...")
            print("Abfragen (Register 0x00) werden ausgeblendet. Mit --alle alles anzeigen.\n")

            while True:
                # Suche nach dem Start-Byte
                if ser.read(1) == b'\x01':
                    rest = ser.read(5)

                    if len(rest) == 5:
                        sender = rest[0]
                        empfaenger = rest[1]
                        register = rest[2]
                        wert = rest[3]
                        ok = (0x01 + sum(rest[:4])) % 256 == rest[4]

                        if not alle:
                            if not ok or register == 0x00:
                                continue
                            # Temperatur-Updates der Hauptplatine ausblenden
                            if sender == 0x11 and register not in INTERESSANT:
                                continue

                        zeit = time.strftime('%H:%M:%S')
                        roh = ' '.join(f'{b:02X}' for b in b'\x01' + rest)
                        pruef = '' if ok else '  (Prüfsumme FALSCH)'
                        print(f"{zeit}  0x{sender:02X} -> 0x{empfaenger:02X} | Register: 0x{register:02X} | Wert: {wert:3d} (0x{wert:02X}) | Roh: {roh}{pruef}")

    except KeyboardInterrupt:
        print("\nSniffer beendet.")
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == '__main__':
    start_sniffer(alle='--alle' in sys.argv)
