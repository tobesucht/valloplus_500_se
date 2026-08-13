import serial
import time

PORT = '/dev/ttyUSB0'
BAUD = 9600

def checksum(msg):
    return sum(msg) % 256

def send_command(ser, register, value):
    # 0x01=Start, 0x22=Wir(PC), 0x11=Vallox Mainboard
    msg = [0x01, 0x22, 0x11, register, value]
    msg.append(checksum(msg))
    
    try:
        # Wir senden den Befehl wie das Original-Bedienteil 3x hintereinander
        for _ in range(3):
            ser.write(bytearray(msg))
            time.sleep(0.1)
            
        print(f"\n>>> Befehl 3x gesendet: Register 0x{register:02X}, Wert {value}")
        print(">>> Bitte horchen Sie an der Anlage oder prüfen Sie das Display.")
    except Exception as e:
        print(f"\nFehler beim Senden: {e}")

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=1)
    except Exception as e:
        print(f"Fehler beim Öffnen des Ports: {e}")
        return

    while True:
        print("\n" + "="*30)
        print("   VALLOX TEST-MENÜ (V2)")
        print("="*30)
        print("[1] Lüfter auf Stufe 2 (Sende 3 an 0x29)")
        print("[2] Lüfter auf Stufe 6 (Sende 63 an 0x29)")
        print("-" * 30)
        print("[3] Bypass ÖFFNEN (Sende 137 an 0xA3)")
        print("[4] Bypass SCHLIESSEN (Sende 129 an 0xA3)")
        print("[0] Beenden")
        
        auswahl = input("\nIhre Wahl (0-4): ")
        
        if auswahl == '1':
            send_command(ser, 0x29, 3)
        elif auswahl == '2':
            send_command(ser, 0x29, 63)
        elif auswahl == '3':
            send_command(ser, 0xA3, 137)
        elif auswahl == '4':
            send_command(ser, 0xA3, 129)
        elif auswahl == '0':
            print("Test beendet.")
            break
        else:
            print("Ungültige Eingabe.")
            
        time.sleep(2) # Kurz warten, damit man Ergebnisse in Ruhe beobachten kann

if __name__ == '__main__':
    main()
