# ============================================================
# WATER TANK SYSTEM V5
# SLAVE 1 - TANK 1, TANK 2, TANK 3 WATER LEVEL MONITORING
# Platform: ESP32 DevKit V1 - MicroPython (Thonny IDE)
# ============================================================

import machine
import network
import time
import ujson
from machine import Pin

try:
    import urequests
except ImportError:
    urequests = None


# ============================================================
# 1. CONFIGURATION
# ============================================================

DEVICE_ID = "slave1"

FLASK_BASE_URL = "http://water.nubeera.com"
SLAVE_API_URL = FLASK_BASE_URL + "/api/slave"

WIFI_SSID = "Airtel_NubeEra_Airtel"
WIFI_PASSWORD = "NubeEra@7"

REPORT_INTERVAL_MS = 3000
WIFI_RETRY_INTERVAL_MS = 5000
WIFI_CONNECT_TIMEOUT_MS = 10000

ECHO_TIMEOUT_US = 30000
SENSOR_GAP_MS = 250


# ============================================================
# 2. GPIO CONFIGURATION
# ============================================================

# Tank 1 (HC-SR04)
TANK1_TRIG_PIN = 16
TANK1_ECHO_PIN = 34

# Tank 2 (HC-SR04)
TANK2_TRIG_PIN = 17
TANK2_ECHO_PIN = 35

# Tank 3 (HC-SR04)
TANK3_TRIG_PIN = 18
TANK3_ECHO_PIN = 36


# ============================================================
# 3. TANK CALIBRATION
# ============================================================

TANK1_FULL_CM = 10
TANK1_EMPTY_CM = 150

TANK2_FULL_CM = 10
TANK2_EMPTY_CM = 150

TANK3_FULL_CM = 10
TANK3_EMPTY_CM = 150


# ============================================================
# 4. HARDWARE INITIALIZATION
# ============================================================

tank1_trig = Pin(TANK1_TRIG_PIN, Pin.OUT)
tank1_echo = Pin(TANK1_ECHO_PIN, Pin.IN)

tank2_trig = Pin(TANK2_TRIG_PIN, Pin.OUT)
tank2_echo = Pin(TANK2_ECHO_PIN, Pin.IN)

tank3_trig = Pin(TANK3_TRIG_PIN, Pin.OUT)
tank3_echo = Pin(TANK3_ECHO_PIN, Pin.IN)

for trigger in (tank1_trig, tank2_trig, tank3_trig):
    trigger.value(0)

sensors = {
    "tank1": {
        "trig": tank1_trig,
        "echo": tank1_echo,
        "full_cm": TANK1_FULL_CM,
        "empty_cm": TANK1_EMPTY_CM,
    },
    "tank2": {
        "trig": tank2_trig,
        "echo": tank2_echo,
        "full_cm": TANK2_FULL_CM,
        "empty_cm": TANK2_EMPTY_CM,
    },
    "tank3": {
        "trig": tank3_trig,
        "echo": tank3_echo,
        "full_cm": TANK3_FULL_CM,
        "empty_cm": TANK3_EMPTY_CM,
    },
}


# ============================================================
# 5. WIFI INITIALIZATION
# ============================================================

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

last_wifi_attempt = time.ticks_add(
    time.ticks_ms(),
    -WIFI_RETRY_INTERVAL_MS
)


# ============================================================
# 6. WIFI CONNECTION
# ============================================================

def wifi_connect_step():
    global last_wifi_attempt

    if wifi.isconnected():
        return True

    if not WIFI_SSID or WIFI_SSID == "YOUR_WIFI_SSID":
        print("Configure Wi-Fi credentials in main.py.")
        return False

    now = time.ticks_ms()

    if time.ticks_diff(now, last_wifi_attempt) < WIFI_RETRY_INTERVAL_MS:
        return False

    last_wifi_attempt = now

    try:
        print("Connecting to Wi-Fi...")
        try:
            wifi.disconnect()
        except Exception:
            pass

        wifi.connect(WIFI_SSID, WIFI_PASSWORD)
        start_time = time.ticks_ms()

        while not wifi.isconnected():
            if time.ticks_diff(time.ticks_ms(), start_time) >= WIFI_CONNECT_TIMEOUT_MS:
                print("Wi-Fi connection timed out.")
                return False
            time.sleep_ms(200)

        print("Wi-Fi connected:", wifi.ifconfig()[0])
        return True

    except Exception as exc:
        print("Wi-Fi connection error:", exc)
        return False


# ============================================================
# 7. ULTRASONIC DISTANCE
# ============================================================

def read_distance_cm(trig, echo):
    try:
        trig.value(0)
        time.sleep_us(3)

        trig.value(1)
        time.sleep_us(10)
        trig.value(0)

        pulse_us = machine.time_pulse_us(
            echo,
            1,
            ECHO_TIMEOUT_US
        )

        if pulse_us <= 0:
            return None

        distance_cm = pulse_us / 58.0

        if distance_cm < 2 or distance_cm > 400:
            return None

        return round(distance_cm, 1)

    except Exception as exc:
        print("Distance reading error:", exc)
        return None


# ============================================================
# 8. WATER LEVEL CALCULATION
# ============================================================

def calculate_level(distance_cm, full_cm, empty_cm):
    if distance_cm is None or empty_cm <= full_cm:
        return None

    percentage = (
        (empty_cm - distance_cm)
        / (empty_cm - full_cm)
    ) * 100

    percentage = max(0, min(100, percentage))
    return int(round(percentage))


# ============================================================
# 9. READ ONE TANK
# ============================================================

def read_tank(sensor_config):
    distance = read_distance_cm(
        sensor_config["trig"],
        sensor_config["echo"]
    )

    sensor_ok = distance is not None
    level = calculate_level(
        distance,
        sensor_config["full_cm"],
        sensor_config["empty_cm"]
    )

    return {
        "distance": distance,
        "level": level,
        "sensor": sensor_ok,
    }


# ============================================================
# 10. READ ALL THREE TANKS
# ============================================================

def read_all_tanks():
    readings = {}

    readings["tank1"] = read_tank(sensors["tank1"])
    time.sleep_ms(SENSOR_GAP_MS)

    readings["tank2"] = read_tank(sensors["tank2"])
    time.sleep_ms(SENSOR_GAP_MS)

    readings["tank3"] = read_tank(sensors["tank3"])

    return readings


# ============================================================
# 11. BUILD FLASK PAYLOAD
# ============================================================

def build_payload(readings):
    ip = wifi.ifconfig()[0] if wifi.isconnected() else "--"
    faults = []

    for t_id, tank_key in enumerate(("tank1", "tank2", "tank3"), 1):
        if not readings[tank_key]["sensor"]:
            faults.append({
                "code": "TANK_SENSOR_" + str(t_id),
                "device": "SLAVE1",
                "source": tank_key,
                "severity": "WARNING",
                "message": "Tank " + str(t_id) + " water level reading is invalid.",
                "cause": "Ultrasonic sensor timeout, wiring fault, or echo pulse missing.",
                "steps": [
                    "Inspect Tank " + str(t_id) + " sensor VCC (5V) and GND.",
                    "Verify TRIG and ECHO connections.",
                    "Verify voltage divider on ECHO line (5V to 3.3V)."
                ],
                "active": True
            })

    return {
        "device": DEVICE_ID,
        "ip": ip,
        "tank1": readings["tank1"],
        "tank2": readings["tank2"],
        "tank3": readings["tank3"],
        "faults": faults,
        "timestamp": time.time(),
    }


# ============================================================
# 12. POST JSON TO FLASK
# ============================================================

def post_slave_data(payload):
    if urequests is None:
        print("ERROR: urequests module is unavailable.")
        return False

    response = None

    try:
        body = ujson.dumps(payload)
        response = urequests.post(
            SLAVE_API_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        if response.status_code not in (200, 201):
            print("Flask HTTP error:", response.status_code)
            return False

        try:
            result = response.json()
        except Exception:
            print("Flask returned an invalid JSON response.")
            return False

        if not result.get("success", False):
            print("Flask did not confirm data receipt.")
            return False

        print("Slave 1 data reported successfully.")
        return True

    except Exception as exc:
        print("Flask POST error:", exc)
        return False

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


# ============================================================
# 13. SERIAL STATUS
# ============================================================

def print_status(readings):
    print()
    print("========== SLAVE 1 STATUS ==========")

    for tank_name in ("tank1", "tank2", "tank3"):
        data = readings[tank_name]
        if data["sensor"]:
            distance_text = str(data["distance"]) + " cm"
            level_text = str(data["level"]) + "%"
            sensor_text = "OK"
        else:
            distance_text = "INVALID"
            level_text = "UNKNOWN"
            sensor_text = "ERROR"

        print(
            tank_name.upper(),
            "| Distance:", distance_text,
            "| Level:", level_text,
            "| Sensor:", sensor_text
        )

    print(
        "Wi-Fi:",
        "CONNECTED (" + wifi.ifconfig()[0] + ")" if wifi.isconnected()
        else "DISCONNECTED"
    )
    print("====================================")
    print()


# ============================================================
# 14. MAIN LOOP
# ============================================================

def main():
    print()
    print("WATER TANK SYSTEM V5")
    print("SLAVE 1 STARTING")
    print("Monitoring Tanks 1, 2 and 3")
    print("Flask endpoint:", SLAVE_API_URL)

    last_report = time.ticks_add(
        time.ticks_ms(),
        -REPORT_INTERVAL_MS
    )

    while True:
        wifi_connect_step()
        now = time.ticks_ms()

        if time.ticks_diff(now, last_report) >= REPORT_INTERVAL_MS:
            last_report = now
            readings = read_all_tanks()
            print_status(readings)

            if wifi.isconnected():
                payload = build_payload(readings)
                post_slave_data(payload)
            else:
                print("Data not sent: Wi-Fi unavailable.")

        time.sleep_ms(50)


# ============================================================
# 15. START
# ============================================================

try:
    main()

except KeyboardInterrupt:
    print("Slave 1 stopped.")

except Exception as exc:
    print("Slave 1 fatal error:", exc)
    raise
