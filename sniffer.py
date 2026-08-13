import serial

PORT = '/dev/ttyUSB0'
BAUD = 9600

def start_sniffer():
    try:
        with serial.Serial(PORT, BAUD) as ser:
            print("Sniffer läuft. Warte auf Befehle vom Bedienteil...")
            print("Bitte drücken Sie jetzt den Bypass-Knopf an der Wand!\n")
            
            while True:
                # Suche nach dem Start-Byte
                if ser.read(1) == b'\x01':
                    rest = ser.read(5)
                    
                    if len(rest) == 5:
                        sender = rest[0]
                        empfaenger = rest[1]
                        register = rest[2]
                        wert = rest[3]
                        
                        # Die Hauptplatine hat meist die Adresse 0x11.
                        # Wir ignorieren alles, was von 0x11 gesendet wird, 
                        # um die Temperatur-Updates auszublenden.
                        if sender != 0x11:
                            print(f"Knopfdruck erkannt! -> Register: 0x{register:02X} | Gesendeter Wert: {wert}")
                            
    except KeyboardInterrupt:
        print("\nSniffer beendet.")
    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == '__main__':
    start_sniffer()
