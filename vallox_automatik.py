import serial
import time
import logging

# --- KONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

# --- TEMPERATUR-GRENZEN ---
TEMP_MIN = 10.0            # Unter 10°C: Zu kalt für Nachtauskühlung (Frostgefahr)
TEMP_INNEN_ZU_WARM = 23.0  # Ab hier wird nachts gekühlt
TEMP_INNEN_KUEHL = 22.0    # Ab hier wird die Kühlung wieder gestoppt

# NEU: Der Puffer für die Nachtauskühlung
TEMP_DIFF_COOLING = 2.0    # Außenluft muss mind. 2.0 °C kühler sein als die Innenluft, damit der Boost startet

# --- REGISTER & WERTE ---
REG_TEMP_AUSSEN = 0x32     # Außentemperatur (Auss)
REG_TEMP_ABLUFT = 0x34     # Innentemperatur (Abl)

REG_FAN = 0x29             # Lüfter-Register
FAN_NORMAL = 3             # Stufe 2 (Tagesbetrieb)
FAN_BOOST = 31             # Stufe 5 (Nachtauskühlung)

REG_BYPASS = 0xA3          # Bypass-Register
WT_AKTIV = 137             # Wärmetauscher AN (Bypass ZU)
WT_DEAKTIVIERT = 129       # Wärmetauscher AUS (Bypass AUF = Freie Kühlung)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def checksum(msg):
    return sum(msg) % 256

def send_command(ser, register, value):
    """Sendet einen Befehl wie das Original-Bedienteil 3x hintereinander"""
    msg = [0x01, 0x22, 0x11, register, value]
    msg.append(checksum(msg))
    
    try:
        for _ in range(3):
            ser.write(bytearray(msg))
            time.sleep(0.1)
    except Exception as e:
        logging.error(f"Fehler beim Senden: {e}")

def get_celsius(raw_value):
    """Rechnet den Hex-Rohwert in echte Grad Celsius um"""
    return round((raw_value / 2.5) - 44.0, 1)

def main():
    logging.info("Vallox Smart-Automatik gestartet. Warte auf Sensordaten...")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        logging.error(f"Konnte {SERIAL_PORT} nicht öffnen: {e}")
        return

    temp_in = None
    temp_out = None
    last_wt_state = None
    last_fan_state = None
    last_check_time = 0

    while True:
        try:
            # 1. Bus live abhören
            if ser.read(1) == b'\x01':
                rest = ser.read(5)
                if len(rest) == 5:
                    reg = rest[2]
                    raw_val = rest[3]
                    
                    if reg == REG_TEMP_ABLUFT:
                        temp_in = get_celsius(raw_val)
                    elif reg == REG_TEMP_AUSSEN:
                        temp_out = get_celsius(raw_val)

            # 2. Logik prüfen (alle 60 Sekunden, sobald wir Werte haben)
            current_time = time.time()
            if temp_in is not None and temp_out is not None and (current_time - last_check_time) > 60:
                last_check_time = current_time
                
                new_wt = last_wt_state
                new_fan = last_fan_state

                # --- DIE SMARTE LOGIK ---
                
                # SZENARIO A: Draußen ist DEUTLICH kühler als drinnen UND drinnen ist es zu warm
                if TEMP_MIN < temp_out <= (temp_in - TEMP_DIFF_COOLING) and temp_in >= TEMP_INNEN_ZU_WARM:
                    new_wt = WT_DEAKTIVIERT
                    new_fan = FAN_BOOST
                    modus = "Nachtauskühlung AKTIV"
                
                # SZENARIO B: Haus ist kühl genug (oder zu kalt)
                elif temp_in < TEMP_INNEN_KUEHL:
                    new_wt = WT_AKTIV
                    new_fan = FAN_NORMAL
                    modus = "Normalbetrieb (Haus ist kühl)"
                    
                # SZENARIO C: Draußen ist es heißer oder fast genauso warm wie drinnen (Hitzeschutz)
                elif temp_out >= temp_in:
                    new_wt = WT_AKTIV
                    new_fan = FAN_NORMAL
                    modus = "Hitzeschutz (Kälterückgewinnung)"
                    
                # SZENARIO D: Draußen Frostgefahr
                elif temp_out <= TEMP_MIN:
                    new_wt = WT_AKTIV
                    new_fan = FAN_NORMAL
                    modus = "Winterbetrieb (Wärmerückgewinnung)"
                else:
                    modus = "Wartezone (keine Änderung nötig)"

                # --- BEFEHLE SENDEN ---
                if new_wt != last_wt_state or new_fan != last_fan_state:
                    logging.info(f"Modus-Wechsel: {modus} | Außen: {temp_out}°C, Innen: {temp_in}°C")
                    
                    if new_wt != last_wt_state and new_wt is not None:
                        send_command(ser, REG_BYPASS, new_wt)
                        last_wt_state = new_wt
                        state_str = "AKTIV (Bypass zu)" if new_wt == WT_AKTIV else "DEAKTIVIERT (Bypass auf)"
                        logging.info(f"-> Wärmetauscher geschaltet auf: {state_str}")
                        
                    if new_fan != last_fan_state and new_fan is not None:
                        send_command(ser, REG_FAN, new_fan)
                        last_fan_state = new_fan
                        lvl = "5 (Boost)" if new_fan == FAN_BOOST else "2 (Normal)"
                        logging.info(f"-> Lüfterstufe geändert auf: {lvl}")
                        
                # Sicherheits-Sync: Alle 15 Minuten den Status erneut senden
                elif int(current_time) % 900 < 60:
                    if last_wt_state is not None:
                        send_command(ser, REG_BYPASS, last_wt_state)
                    if last_fan_state is not None:
                        send_command(ser, REG_FAN, last_fan_state)

        except Exception as e:
            logging.error(f"Fehler in Hauptschleife: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
