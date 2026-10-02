import serial
import time
import logging

# --- KONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 9600

# --- TEMPERATUR-GRENZEN ---
TEMP_MIN = 10.0            # Unter 10°C: Zu kalt für Nachtauskühlung (Frostgefahr)
TEMP_INNEN_ZU_WARM = 24.0  # Ab hier wird nachts gekühlt
TEMP_INNEN_KUEHL = 23.0    # Ab hier wird die Kühlung wieder gestoppt

# NEU: Der Puffer für die Nachtauskühlung
TEMP_DIFF_COOLING = 2.0    # Außenluft muss mind. 2.0 °C kühler sein als die Innenluft, damit der Boost startet

# Frost-Stopp: Bei sehr kalter Außenluft Anlage ausschalten (keine elektrische Vorheizung)
TEMP_FROST_STOP = -5.0     # Unter -5°C: Luftaustausch stoppen
TEMP_FROST_RESTART = -3.0  # Ab hier läuft die Anlage wieder an
FROST_MIN_AUS = 1800       # Mindest-Stillstand in Sekunden (Außenfühler driftet bei stehender Anlage)

# --- REGISTER & WERTE ---
REG_TEMP_AUSSEN = 0x32     # Außentemperatur (Auss)
REG_TEMP_ABLUFT = 0x34     # Innentemperatur (Abl)

REG_FAN = 0x29             # Lüfter-Register
FAN_NORMAL = 3             # Stufe 2 (Tagesbetrieb)
FAN_BOOST = 15             # Stufe 4 (Nachtauskühlung)

REG_BYPASS = 0xA3          # Bypass-Register
WT_AKTIV = 137             # Wärmetauscher AN (Bypass ZU)
WT_DEAKTIVIERT = 129       # Wärmetauscher AUS (Bypass AUF = Freie Kühlung)
ANLAGE_AUS = 136           # Wie WT_AKTIV, aber Bit 0 (Power) gelöscht -> Anlage AUS

ADR_HAUPTPLATINE = 0x11
ADR_BEDIENTEILE = 0x20     # Broadcast an alle Bedienteile

WT_TEXT = {
    WT_AKTIV: "AKTIV (Bypass zu)",
    WT_DEAKTIVIERT: "DEAKTIVIERT (Bypass auf)",
    ANLAGE_AUS: "ANLAGE AUS (Frost-Stopp)",
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def checksum(msg):
    return sum(msg) % 256

def send_command(ser, register, value, empfaenger=ADR_HAUPTPLATINE):
    """Sendet einen Befehl wie das Original-Bedienteil 3x hintereinander"""
    msg = [0x01, 0x22, empfaenger, register, value]
    msg.append(checksum(msg))
    
    try:
        for _ in range(3):
            ser.write(bytearray(msg))
            time.sleep(0.1)
    except Exception as e:
        logging.error(f"Fehler beim Senden: {e}")

def send_ein_aus(ser, value):
    """Ein/Aus an Hauptplatine UND Bedienteile senden.
    Geht das Aus nur an die Hauptplatine, lässt sich die Anlage danach nur
    noch über die Taste am Bedienteil wieder einschalten (getestet)."""
    send_command(ser, REG_BYPASS, value)
    send_command(ser, REG_BYPASS, value, empfaenger=ADR_BEDIENTEILE)

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
    frost_stop_since = None

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

                # --- FROST-STOPP ---
                if frost_stop_since is not None:
                    if temp_out >= TEMP_FROST_RESTART and (current_time - frost_stop_since) >= FROST_MIN_AUS:
                        frost_stop_since = None
                        # Wiederanlauf: Default EIN, damit die Wartezone die Anlage nicht AUS lässt
                        new_wt = WT_AKTIV
                        new_fan = FAN_NORMAL
                elif temp_out < TEMP_FROST_STOP:
                    frost_stop_since = current_time

                # --- DIE SMARTE LOGIK ---

                # SZENARIO F: Frost-Stopp hat Vorrang vor allem anderen
                if frost_stop_since is not None:
                    new_wt = ANLAGE_AUS
                    modus = "Frost-Stopp (Anlage AUS)"

                # SZENARIO A: Draußen ist DEUTLICH kühler als drinnen UND drinnen ist es zu warm
                elif TEMP_MIN < temp_out <= (temp_in - TEMP_DIFF_COOLING) and temp_in >= TEMP_INNEN_ZU_WARM:
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
                        if ANLAGE_AUS in (new_wt, last_wt_state):
                            send_ein_aus(ser, new_wt)
                        else:
                            send_command(ser, REG_BYPASS, new_wt)
                        last_wt_state = new_wt
                        logging.info(f"-> Wärmetauscher geschaltet auf: {WT_TEXT[new_wt]}")
                        
                    if new_fan != last_fan_state and new_fan is not None:
                        send_command(ser, REG_FAN, new_fan)
                        last_fan_state = new_fan
                        lvl = "4 (Boost)" if new_fan == FAN_BOOST else "2 (Normal)"
                        logging.info(f"-> Lüfterstufe geändert auf: {lvl}")
                        
                # Sicherheits-Sync: Alle 15 Minuten den Status erneut senden
                elif int(current_time) % 900 < 60:
                    if last_wt_state == ANLAGE_AUS:
                        send_ein_aus(ser, last_wt_state)
                    elif last_wt_state is not None:
                        send_command(ser, REG_BYPASS, last_wt_state)
                    # Während Frost-Stopp keinen Lüfterbefehl, der die Anlage evtl. wieder einschaltet
                    if last_fan_state is not None and frost_stop_since is None:
                        send_command(ser, REG_FAN, last_fan_state)

        except Exception as e:
            logging.error(f"Fehler in Hauptschleife: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
