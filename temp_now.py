import serial
import time

# --- KONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

TEMP_MIN = 10.0
TEMP_INNEN_ZU_WARM = 23.0
TEMP_INNEN_KUEHL = 22.0
TEMP_DIFF_COOLING = 2.0  # NEU: Der Puffer!

REG_TEMP_AUSSEN = 0x32  # Außentemperatur (Auss)
REG_TEMP_ABLUFT = 0x34  # Innentemperatur (Abl)

def get_celsius(raw_value):
    """Rechnet den Hex-Rohwert in echte Grad Celsius um"""
    return round((raw_value / 2.5) - 44.0, 1)

def check_status():
    print("Sammle aktuelle Sensordaten vom Vallox-Bus (bitte warten)...\n")
    
    temp_in = None
    temp_out = None
    
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            # Wir lauschen, bis wir BEIDE Temperaturen haben
            while temp_in is None or temp_out is None:
                if ser.read(1) == b'\x01':
                    rest = ser.read(5)
                    if len(rest) == 5:
                        reg = rest[2]
                        raw_val = rest[3]
                        
                        if reg == REG_TEMP_ABLUFT:
                            temp_in = get_celsius(raw_val)
                        elif reg == REG_TEMP_AUSSEN:
                            temp_out = get_celsius(raw_val)
                            
    except Exception as e:
        print(f"Fehler beim Zugriff auf den Bus: {e}")
        return

    # --- AUSWERTUNG ---
    print("=" * 45)
    print(" 🌡️  AKTUELLE TEMPERATUREN")
    print("=" * 45)
    print(f" Außentemperatur:   {temp_out} °C")
    print(f" Innentemperatur:   {temp_in} °C")
    print("-" * 45)
    
    # --- LOGIK-SIMULATION ---
    print(" 🤖 ENTSCHEIDUNG DER AUTOMATIK")
    print("-" * 45)
    
    if TEMP_MIN < temp_out <= (temp_in - TEMP_DIFF_COOLING) and temp_in >= TEMP_INNEN_ZU_WARM:
        print("Szenario: 🌙 NACHTAUSKÜHLUNG")
        print(f"Bedingung erfüllt: Draußen ist mind. {TEMP_DIFF_COOLING}°C kühler als drinnen UND Haus zu warm (>= 23°C).")
        print("Folgeaktion:       -> Bypass ÖFFNEN, Lüfter auf BOOST (Stufe 5)")
        
    elif temp_in < TEMP_INNEN_KUEHL:
        print("Szenario: 😌 NORMALBETRIEB (Haus ist kühl)")
        print(f"Bedingung erfüllt: Haus ist unter der Kühlschwelle (< {TEMP_INNEN_KUEHL}°C).")
        print("Folgeaktion:       -> Bypass SCHLIESSEN, Lüfter auf NORMAL (Stufe 2)")
        
    elif temp_out >= temp_in:
        print("Szenario: ☀️ HITZESCHUTZ")
        print("Bedingung erfüllt: Draußen ist es heißer oder gleich warm wie drinnen.")
        print("Folgeaktion:       -> Bypass SCHLIESSEN, Lüfter auf NORMAL (Stufe 2)")
        
    elif temp_out <= TEMP_MIN:
        print("Szenario: ❄️ FROSTSCHUTZ (Winter)")
        print(f"Bedingung erfüllt: Draußen ist es zu kalt (<= {TEMP_MIN}°C).")
        print("Folgeaktion:       -> Bypass SCHLIESSEN, Lüfter auf NORMAL (Stufe 2)")
        
    else:
        print("Szenario: ⏸️ WARTEZONE")
        print(f"Grund: Draußen ({temp_out}°C) ist zwar kühler als Innen ({temp_in}°C), aber der Temperaturunterschied ist kleiner als {TEMP_DIFF_COOLING}°C.")
        print("Folgeaktion:       -> KEINE ÄNDERUNG (Aktueller Zustand wird beibehalten um 'Ping-Pong' zu vermeiden)")

    print("=" * 45)

if __name__ == '__main__':
    check_status()
