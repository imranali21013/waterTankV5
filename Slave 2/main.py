# ============================================================
# WATER TANK SYSTEM V5
# SLAVE 2 - VALVE CONTROL FOR TANKS 1, 2 AND 3
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

DEVICE_ID = "slave2"

FLASK_BASE_URL = "http://water.nubeera.com"
SLAVE_API_URL = FLASK_BASE_URL + "/api/slave"
COMMANDS_URL = FLASK_BASE_URL + "/api/commands?device=slave2"

WIFI_SSID = "Airtel_NubeEra_Airtel"
WIFI_PASSWORD = "NubeEra@7"

REPORT_INTERVAL_MS = 3000
WIFI_RETRY_INTERVAL_MS = 5000
WIFI_CONNECT_TIMEOUT_MS = 10000
COMMAND_POLL_INTERVAL_MS = 1000

VALVE_OPEN_TIME_MS = {
    1: 30000,
    2: 30000,
    3: 30000
}

VALVE_CLOSE_TIME_MS = {
    1: 30000,
    2: 30000,
    3: 30000
}


# ============================================================
# 2. GPIO CONFIGURATION (L293D Motor Drivers)
# ============================================================

# Valve 1 (Tank 1)
VALVE1_EN_PIN = 25
VALVE1_IN1_PIN = 26
VALVE1_IN2_PIN = 27

# Valve 2 (Tank 2)
# NOTE: Pin 12 is a strapping pin (MTDI). Keep L293D input low at power-up.
VALVE2_EN_PIN = 14
VALVE2_IN1_PIN = 12
VALVE2_IN2_PIN = 13

# Valve 3 (Tank 3)
VALVE3_EN_PIN = 32
VALVE3_IN1_PIN = 33
VALVE3_IN2_PIN = 23


# ============================================================
# 3. NETWORK INITIALIZATION
# ============================================================

wifi = network.WLAN(network.STA_IF)
wifi.active(True)

last_wifi_attempt = time.ticks_add(
    time.ticks_ms(), -WIFI_RETRY_INTERVAL_MS
)

last_report = time.ticks_add(
    time.ticks_ms(), -REPORT_INTERVAL_MS
)

last_command_poll = time.ticks_add(
    time.ticks_ms(), -COMMAND_POLL_INTERVAL_MS
)


# ============================================================
# 4. GLOBAL STATE
# ============================================================

valves = {}

valve_states = {
    1: "CLOSED",
    2: "CLOSED",
    3: "CLOSED"
}

valve_errors = {
    1: False,
    2: False,
    3: False
}

valve_deadlines = {
    1: 0,
    2: 0,
    3: 0
}

valve_command_sequences = {
    1: -1,
    2: -1,
    3: -1
}

system_command_sequence = -1

flask_connected = False
system_fault = None
last_network_info = None


# ============================================================
# 5. HARDWARE INITIALIZATION
# ============================================================

def initialize_valves():
    configurations = {
        1: (VALVE1_EN_PIN, VALVE1_IN1_PIN, VALVE1_IN2_PIN),
        2: (VALVE2_EN_PIN, VALVE2_IN1_PIN, VALVE2_IN2_PIN),
        3: (VALVE3_EN_PIN, VALVE3_IN1_PIN, VALVE3_IN2_PIN)
    }

    for valve_id, pins in configurations.items():
        enable_pin, in1_pin, in2_pin = pins

        enable = Pin(enable_pin, Pin.OUT, value=0)
        in1 = Pin(in1_pin, Pin.OUT, value=0)
        in2 = Pin(in2_pin, Pin.OUT, value=0)

        valves[valve_id] = {
            "enable": enable,
            "in1": in1,
            "in2": in2
        }

    stop_all_valves()


# ============================================================
# 6. VALVE CONTROL (Direct & Non-blocking)
# ============================================================

def stop_valve(valve_id):
    if valve_id not in valves:
        return

    motor = valves[valve_id]
    motor["enable"].value(0)
    motor["in1"].value(0)
    motor["in2"].value(0)

    if valve_states[valve_id] in ("OPENING", "CLOSING"):
        valve_states[valve_id] = "STOPPED"
    valve_deadlines[valve_id] = 0


def stop_all_valves():
    for valve_id in valves:
        stop_valve(valve_id)


def open_valve(valve_id):
    if valve_id not in valves:
        return False

    motor = valves[valve_id]
    motor["enable"].value(0)
    motor["in1"].value(1)
    motor["in2"].value(0)
    motor["enable"].value(1)

    valve_states[valve_id] = "OPENING"
    valve_deadlines[valve_id] = time.ticks_add(
        time.ticks_ms(),
        VALVE_OPEN_TIME_MS[valve_id]
    )

    valve_errors[valve_id] = False
    print("Valve", valve_id, "is OPENING...")
    return True


def close_valve(valve_id):
    if valve_id not in valves:
        return False

    motor = valves[valve_id]
    motor["enable"].value(0)
    motor["in1"].value(0)
    motor["in2"].value(1)
    motor["enable"].value(1)

    valve_states[valve_id] = "CLOSING"
    valve_deadlines[valve_id] = time.ticks_add(
        time.ticks_ms(),
        VALVE_CLOSE_TIME_MS[valve_id]
    )

    valve_errors[valve_id] = False
    print("Valve", valve_id, "is CLOSING...")
    return True


def process_valve_timers():
    now = time.ticks_ms()

    for valve_id in valves:
        state = valve_states[valve_id]

        if state not in ("OPENING", "CLOSING"):
            continue

        if time.ticks_diff(now, valve_deadlines[valve_id]) >= 0:
            motor = valves[valve_id]
            motor["enable"].value(0)
            motor["in1"].value(0)
            motor["in2"].value(0)

            if state == "OPENING":
                valve_states[valve_id] = "OPEN"
            else:
                valve_states[valve_id] = "CLOSED"

            print("Valve", valve_id, "movement complete ->", valve_states[valve_id])


# ============================================================
# 7. WIFI CONNECTION
# ============================================================

def wifi_connect_step():
    global last_wifi_attempt, last_network_info, system_fault

    if wifi.isconnected():
        current_info = wifi.ifconfig()
        if current_info != last_network_info:
            last_network_info = current_info
            print("Wi-Fi connected! Slave 2 IP:", current_info[0])
        return True

    now = time.ticks_ms()
    if time.ticks_diff(now, last_wifi_attempt) < WIFI_RETRY_INTERVAL_MS:
        return False

    last_wifi_attempt = now

    if not WIFI_SSID or WIFI_SSID == "YOUR_WIFI_SSID":
        print("Configure Wi-Fi credentials in main.py")
        return False

    try:
        try:
            wifi.disconnect()
        except Exception:
            pass

        wifi.connect(WIFI_SSID, WIFI_PASSWORD)
        start_time = time.ticks_ms()

        while not wifi.isconnected():
            if time.ticks_diff(time.ticks_ms(), start_time) >= WIFI_CONNECT_TIMEOUT_MS:
                print("Wi-Fi connection timeout")
                return False
            time.sleep_ms(200)

        current_info = wifi.ifconfig()
        last_network_info = current_info
        print("Wi-Fi connected! Slave 2 IP:", current_info[0])
        return True

    except Exception as exc:
        print("Wi-Fi connection error:", exc)
        return False


# ============================================================
# 8. HTTP HELPERS
# ============================================================

def http_get_json(url):
    global flask_connected

    if urequests is None or not wifi.isconnected():
        flask_connected = False
        return None

    response = None

    try:
        response = urequests.get(url, timeout=3)
        if response.status_code != 200:
            flask_connected = False
            return None

        result = response.json()
        flask_connected = True
        return result

    except Exception:
        flask_connected = False
        return None

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def http_post_json(url, payload):
    global flask_connected

    if urequests is None or not wifi.isconnected():
        flask_connected = False
        return False

    response = None

    try:
        response = urequests.post(
            url,
            data=ujson.dumps(payload),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=3
        )

        if response.status_code not in (200, 201):
            flask_connected = False
            return False

        try:
            result = response.json()
        except Exception:
            result = {}

        flask_connected = True
        return isinstance(result, dict) and result.get("success", True)

    except Exception:
        flask_connected = False
        return False

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


# ============================================================
# 9. COMMAND PARSING
# ============================================================

def normalize_valve_command(command):
    if not isinstance(command, str):
        return ""
    command = command.strip().upper()
    if command in ("OPEN", "CLOSE", "STOP"):
        return command
    return ""


def get_valve_command_entries(result):
    commands = result.get("valveCommands", {})
    if isinstance(commands, dict):
        return commands
    return {}


def process_system_command(result):
    global system_command_sequence

    sequence = result.get("sequence", -1)
    try:
        sequence = int(sequence)
    except Exception:
        sequence = -1

    if sequence == system_command_sequence:
        return

    system_command_sequence = sequence
    command = str(result.get("command", "")).strip().upper()
    should_stop = bool(result.get("stop", False)) or command == "STOP"

    if should_stop:
        stop_all_valves()
        print("System STOP command received")


def process_valve_commands(result):
    entries = get_valve_command_entries(result)

    for valve_id in (1, 2, 3):
        item = entries.get(valve_id) or entries.get(str(valve_id))

        if not isinstance(item, dict):
            continue

        sequence = item.get("sequence", -1)
        try:
            sequence = int(sequence)
        except Exception:
            continue

        if sequence == valve_command_sequences[valve_id]:
            continue

        valve_command_sequences[valve_id] = sequence
        command = normalize_valve_command(item.get("command", ""))

        if not command:
            continue

        if command == "STOP":
            stop_valve(valve_id)
        elif command == "OPEN":
            open_valve(valve_id)
        elif command == "CLOSE":
            close_valve(valve_id)


def process_master_commands():
    result = http_get_json(COMMANDS_URL)
    if not isinstance(result, dict):
        return

    process_system_command(result)
    process_valve_commands(result)


# ============================================================
# 10. STATUS PAYLOAD
# ============================================================

def build_payload():
    ip_address = wifi.ifconfig()[0] if wifi.isconnected() else "--"
    faults = []

    if not wifi.isconnected():
        faults.append({
            "code": "SLAVE2_WIFI_DISCONNECTED",
            "device": "SLAVE2",
            "source": "network",
            "severity": "CRITICAL",
            "message": "Slave 2 is disconnected from Wi-Fi.",
            "cause": "Wi-Fi signal weak or credentials mismatch.",
            "steps": ["Verify router is powered on.", "Confirm credentials in main.py."],
            "active": True
        })

    for valve_id in (1, 2, 3):
        if valve_errors[valve_id]:
            faults.append({
                "code": "VALVE_" + str(valve_id) + "_ERROR",
                "device": "SLAVE2",
                "source": "valve" + str(valve_id),
                "severity": "WARNING",
                "message": "Valve " + str(valve_id) + " operation error.",
                "cause": "Motor driver issue or mechanical obstruction.",
                "steps": ["Inspect L293D wiring.", "Check motor power supply."],
                "active": True
            })

    return {
        "device": DEVICE_ID,
        "ip": ip_address,
        "valves": [
            {
                "id": valve_id,
                "state": valve_states[valve_id],
                "error": valve_errors[valve_id]
            }
            for valve_id in (1, 2, 3)
        ],
        "system": {
            "online": wifi.isconnected(),
            "flaskConnected": flask_connected,
        },
        "faults": faults,
        "timestamp": time.time()
    }


# ============================================================
# 11. SERIAL STATUS
# ============================================================

def print_status():
    print()
    print("========== SLAVE 2 STATUS ==========")
    if wifi.isconnected():
        print("Wi-Fi: CONNECTED (" + wifi.ifconfig()[0] + ")")
    else:
        print("Wi-Fi: DISCONNECTED")

    print("Flask:", "CONNECTED" if flask_connected else "DISCONNECTED")

    for valve_id in (1, 2, 3):
        print(
            "Valve",
            valve_id,
            "| State:",
            valve_states[valve_id],
            "| Error:",
            valve_errors[valve_id]
        )
    print("====================================")
    print()


# ============================================================
# 12. MAIN LOOP
# ============================================================

def main():
    global last_report, last_command_poll

    initialize_valves()
    stop_all_valves()

    print("================================")
    print("WATER TANK SYSTEM V5 - SLAVE 2")
    print("Valve Control for Tanks 1, 2 & 3")
    print("Hardware: Live and Connected")
    print("================================")

    while True:
        wifi_connect_step()
        now = time.ticks_ms()

        process_valve_timers()

        if time.ticks_diff(now, last_command_poll) >= COMMAND_POLL_INTERVAL_MS:
            last_command_poll = now
            if wifi.isconnected():
                process_master_commands()

        if time.ticks_diff(now, last_report) >= REPORT_INTERVAL_MS:
            last_report = now
            print_status()

            if wifi.isconnected():
                payload = build_payload()
                http_post_json(SLAVE_API_URL, payload)

        time.sleep_ms(50)


# ============================================================
# 13. START
# ============================================================

try:
    main()

except KeyboardInterrupt:
    stop_all_valves()
    print("Slave 2 stopped safely.")

except Exception as exc:
    try:
        stop_all_valves()
    except Exception:
        pass
    print("Slave 2 fatal error:", exc)
    raise
