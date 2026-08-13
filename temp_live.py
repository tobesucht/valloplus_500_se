import serial
import time

PORT = '/dev/ttyUSB0'
BAUD = 9600
OFFSET = 151

def scan_registers():
    seen_registers = {}
    try:
        with serial.Serial(PORT, BAUD, timeout=1) as ser:
            print("Scanne den Bus nach allen Temperatur-Sensoren...")
            print("Bitte ca. 15 Sekunden warten...\n")
            
            end_time = time.time() + 15
            while time.time() < end_time:
                if ser.read(1) == b'\x01':
                    rest = ser.read(5)
                    if len(rest) == 5:
                        reg = rest[2]
                        raw = rest[3]
                        
                        # Wir filtern: Alles, was nach der 151-Formel realistische 
                        # Temperaturen zwischen -20°C und +50°C ergibt
                        if 131 <= raw <= 201:
                            seen_registers[reg] = raw

            print("--- GEFUNDENE REGISTER ---")
            print("Reg(Hex) | Rohwert | Berechnet (°C)")
            print("-----------------------------------")
            
            for reg, raw in sorted(seen_registers.items()):
                calc = raw - OFFSET
                print(f"  0x{reg:02X}   |   {raw}   |   {calc} °C")

    except Exception as e:
        print(f"Fehler: {e}")

if __name__ == '__main__':
    scan_registers()
