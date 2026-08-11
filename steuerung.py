import serial
import time
import logging

# --- KONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'  # Ihr FTDI-Adapter
BAUD_RATE = 9600              # Vallox Standard

# Temperaturen
TEMP_MIN = 10.0      # Unter 10°C: Wintermodus (WRG)
TEMP_MAX = 22.0      # Über 22°C: Sommermodus (Kälterückgewinnung)
TEMP_INNEN_ZU_WARM = 23.0  # Ab hier wird gekühlt
TEMP_INNEN_KUEHL = 22.0    # Ab hier wird die Kühlung gestoppt

# Lüfterstufen (Vallox Skala 1-8)
FAN_NORMAL = 3       # Normale Stufe am Tag
FAN_BOOST = 6        # Erhöhte Stufe für die Nachtauskühlung

# Vallox Hex-Register (Digit SED Protokoll)
REG_TEMP_OUT = 0x32  # Außenluft (Beispiel-Register)
REG_TEMP_IN = 0x33   # Abluft / Innentemperatur (Beispiel-Register)
REG_BYPASS = 0x33    # Bypass (Hinweis: Register weichen je nach Baujahr ab!)
REG_FAN = 0x29       # Lüfterstufe

# --- LOGGING EINRICHTEN ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def checksum(msg):
    """Berechnet die Checksumme für das Vallox-Protokoll (Modulo 256)"""
    return sum(msg) % 256

def send_command(ser, register, value):
    """Sendet einen Befehl an die Vallox-Platine"""
    # 0x01 (Domain), 0x22 (Sender: PC), 0x11 (Empfänger: Mainboard)
    msg = [0x01, 0x22, 0x11, register, value]
    msg.append(checksum(msg))
    
    try:
        ser.write(bytearray(msg))
        time.sleep(0.5) # Kurz warten, damit der Bus nicht überlastet wird
    except Exception as e:
        logging.error(f"Fehler beim Senden: {e}")

def read_temperature(ser, register):
    """
    Liest eine Temperatur aus. (Hinweis: In der Realität sendet 
    die Vallox die Werte oft zyklisch (Broadcast) von selbst auf den Bus.
    Dieses Skript fängt diese zur Vereinfachung fiktiv ab.)
    """
    # HIER MÜSSTE DER LESE-CODE FÜR IHR SPEZIFISCHES MODELL REIN.
    # Da wir ohne Anlage nicht messen können, simulieren wir den Wert 
    # in diesem Grundgerüst für die Logik-Demonstration.
    return 0.0 

def main():
    logging.info("Vallox RS485 Steuerung gestartet...")
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    except Exception as e:
        logging.error(f"Konnte {SERIAL_PORT} nicht öffnen: {e}")
        return

    # Letzten Zustand speichern, um unnötige Befehle zu vermeiden
    last_bypass_state = None
    last_fan_state = None

    while True:
        try:
            # 1. Temperaturen vom Bus lesen
            temp_out = read_temperature(ser, REG_TEMP_OUT)
            temp_in = read_temperature(ser, REG_TEMP_IN)
            
            # (Für Testzwecke feste Werte eintragen, um die Logik zu prüfen)
            # temp_out = 15.0
            # temp_in = 24.0

            new_bypass_state = last_bypass_state
            new_fan_state = last_fan_state

            # --- DIE LOGIK ---
            if temp_out < TEMP_MIN:
                logging.info(f"Wintermodus (Außen: {temp_out}°C). WRG AN.")
                new_bypass_state = 0 # 0 = Geschlossen
                new_fan_state = FAN_NORMAL

            elif temp_out > TEMP_MAX:
                logging.info(f"Hitzeschutz (Außen: {temp_out}°C). WRG AN (Kälterückgewinnung).")
                new_bypass_state = 0
                new_fan_state = FAN_NORMAL

            elif TEMP_MIN <= temp_out <= TEMP_MAX:
                if temp_in > TEMP_INNEN_ZU_WARM:
                    logging.info(f"Nachtauskühlung aktiv! (Außen: {temp_out}°C, Innen: {temp_in}°C). Bypass OFFEN, Lüfter HOCH.")
                    new_bypass_state = 1 # 1 = Offen
                    new_fan_state = FAN_BOOST
                
                elif temp_in < TEMP_INNEN_KUEHL:
                    logging.info(f"Haus ist kühl genug (Innen: {temp_in}°C). WRG AN, Lüfter NORMAL.")
                    new_bypass_state = 0
                    new_fan_state = FAN_NORMAL
            
            # --- BEFEHLE SENDEN (nur bei Änderung) ---
            if new_bypass_state != last_bypass_state:
                send_command(ser, REG_BYPASS, new_bypass_state)
                last_bypass_state = new_bypass_state
            
            if new_fan_state != last_fan_state:
                send_command(ser, REG_FAN, new_fan_state)
                last_fan_state = new_fan_state

        except Exception as e:
            logging.error(f"Fehler in der Schleife: {e}")

        # Warte 5 Minuten bis zur nächsten Überprüfung
        time.sleep(300)

if __name__ == '__main__':
    main()
