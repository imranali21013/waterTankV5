# ============================================================
# WATER TANK SYSTEM V5 - MASTER ESP32
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

DEVICE_ID = "master"

FLASK_BASE_URL = "http://water.nubeera.com"
COMMANDS_URL = FLASK_BASE_URL + "/api/commands?device=master"
MASTER_URL = FLASK_BASE_URL + "/api/master"
VALVE_COMMAND_URL = FLASK_BASE_URL + "/api/valve-command"

WIFI_SSID = "Airtel_NubeEra_Airtel"
WIFI_PASSWORD = "NubeEra@7"

FULL_CM = {1: 10, 2: 10, 3: 10, 4: 10}
EMPTY_CM = {1: 150, 2: 150, 3: 150, 4: 150}

VALVE_OPEN_MS = {1: 30000, 2: 30000, 3: 30000, 4: 30000}
VALVE_CLOSE_MS = {1: 30000, 2: 30000, 3: 30000, 4: 30000}

TANK_FULL_THRESHOLD = 95
WATER_SENSOR_ACTIVE_LEVEL = 1

COMMAND_POLL_MS = 1000
TELEMETRY_INTERVAL_MS = 1000
SENSOR_INTERVAL_MS = 1000
BUTTON_DEBOUNCE_MS = 50
WIFI_RETRY_MS = 5000
HTTP_TIMEOUT_SECONDS = 3


# ============================================================
# 2. GPIO ASSIGNMENTS
# ============================================================

# Ultrasonic Sensor Tank 4
TANK4_TRIG_PIN = 18
TANK4_ECHO_PIN = 34

# Physical Tank Selection Switches (External pull-down required on 35, 36, 39)
SWITCH_PINS = {
    1: 35,
    2: 36,
    3: 39,
    4: 33
}

# Water Availability Sensor (Source Water)
WATER_SENSOR_PIN = 32

# Pump Relay (Active LOW: 0 = ON, 1 = OFF)
PUMP_PIN = 23

# Physical Push Buttons
START_BUTTON_PIN = 16
STOP_BUTTON_PIN = 19

# Valve 4 Motor Driver (L293D)
VALVE4_ENA_PIN = 25
VALVE4_IN1_PIN = 26
VALVE4_IN2_PIN = 27


# ============================================================
# 3. GLOBAL STATE
# ============================================================

wifi = network.WLAN(network.STA_IF)
wifi_info_printed = False
last_wifi_attempt = 0

switches = {}
physical_switch_state = {t: 0 for t in range(1, 5)}
selected_tanks = []

physical_selection_initialized = False
physical_selection_changed = False
selection_source = "PHYSICAL"

tank_levels = {t: None for t in range(1, 5)}
tank_distances = {t: None for t in range(1, 5)}
tank_sensor_ok = {t: False for t in range(1, 5)}

valve_states = {t: "CLOSED" for t in range(1, 5)}
valve_errors = {t: False for t in range(1, 5)}
valve_deadlines = {1: None, 2: None, 3: None, 4: None}

pump_running = False
water_available = True

slave1_online = False
slave2_online = False
flask_connected = False



current_filling_tank = None
system_mode = "STARTING"
system_fault = None
faults = []

start_requested = False
stop_requested = False

command_sequence = -1
command_sequence_initialized = False
last_valve4_sequence = -1

start_button = None
stop_button = None
pump = None
water_sensor = None
tank4_trig = None
tank4_echo = None

valve4_ena = None
valve4_in1 = None
valve4_in2 = None

last_sensor_read = time.ticks_ms()
last_command_poll = time.ticks_ms()
last_telemetry = time.ticks_ms()

last_start_button = 1
last_stop_button = 1
start_edge_time = 0
stop_edge_time = 0

http_error = None
valve4_deadline = None
valve4_target_state = None


# ============================================================
# 4. FAULT MANAGEMENT (Centralized & Deduplicated)
# ============================================================

def add_fault(code, source, severity, message, cause, steps):
    for fault in faults:
        if fault["code"] == code and fault["source"] == source:
            fault["message"] = message
            fault["cause"] = cause
            fault["steps"] = steps
            fault["lastSeen"] = time.time()
            fault["status"] = "ACTIVE"
            return

    faults.append({
        "code": code,
        "source": source,
        "severity": severity,
        "message": message,
        "cause": cause,
        "steps": steps,
        "status": "ACTIVE",
        "firstSeen": time.time(),
        "lastSeen": time.time()
    })


def clear_fault(code, source):
    global faults
    faults = [
        fault for fault in faults
        if not (fault["code"] == code and fault["source"] == source)
    ]


def update_faults():
    if not wifi.isconnected():
        add_fault(
            "MASTER_WIFI_DISCONNECTED",
            "MASTER",
            "CRITICAL",
            "Master ESP32 is disconnected from Wi-Fi.",
            "Weak signal, router offline, or credentials changed.",
            [
                "Verify Wi-Fi router is powered and SSID/Password match.",
                "Ensure ESP32 is within Wi-Fi range."
            ]
        )
    else:
        clear_fault("MASTER_WIFI_DISCONNECTED", "MASTER")

    if not flask_connected:
        add_fault(
            "FLASK_UNREACHABLE",
            "MASTER",
            "CRITICAL",
            "Master cannot communicate with the Flask server.",
            "Flask server offline, domain unreachable, or internet disconnected.",
            [
                "Confirm Wi-Fi router has internet access.",
                "Verify FLASK_BASE_URL points to http://water.nubeera.com.",
                "Check server status in browser."
            ]
        )
    else:
        clear_fault("FLASK_UNREACHABLE", "MASTER")

    if not slave1_online:
        add_fault(
            "SLAVE1_OFFLINE",
            "MASTER",
            "WARNING",
            "Slave 1 (Tanks 1-3 sensor node) is offline.",
            "Slave 1 power loss or Wi-Fi disconnection.",
            [
                "Inspect Slave 1 power supply.",
                "Check Slave 1 Serial output for Wi-Fi status."
            ]
        )
    else:
        clear_fault("SLAVE1_OFFLINE", "MASTER")

    if not slave2_online:
        add_fault(
            "SLAVE2_OFFLINE",
            "MASTER",
            "WARNING",
            "Slave 2 (Valves 1-3 actuator node) is offline.",
            "Slave 2 power loss or Wi-Fi disconnection.",
            [
                "Inspect Slave 2 power supply.",
                "Check Slave 2 Serial output for Wi-Fi status."
            ]
        )
    else:
        clear_fault("SLAVE2_OFFLINE", "MASTER")

    for tank in range(1, 5):
        if not tank_sensor_ok[tank]:
            add_fault(
                "TANK_SENSOR_" + str(tank),
                "MASTER" if tank == 4 else "SLAVE1",
                "WARNING",
                "Tank " + str(tank) + " water level reading is invalid.",
                "Ultrasonic sensor timeout, wiring fault, or echo pulse missing.",
                [
                    "Inspect sensor VCC (5V) and GND wiring.",
                    "Verify TRIG and ECHO connections.",
                    "Check 5V-to-3.3V voltage divider on ECHO."
                ]
            )
        else:
            clear_fault(
                "TANK_SENSOR_" + str(tank),
                "MASTER" if tank == 4 else "SLAVE1"
            )

    if water_available is False:
        add_fault(
            "WATER_SOURCE_EMPTY",
            "MASTER",
            "CRITICAL",
            "Water source is empty; pump activation is inhibited.",
            "Dry run condition detected at the water supply sensor.",
            [
                "Check primary water inlet pipe / sump water level.",
                "Inspect water sensor wiring on Pin 32."
            ]
        )
    else:
        clear_fault("WATER_SOURCE_EMPTY", "MASTER")

    if http_error:
        add_fault(
            "MASTER_HTTP_ERROR",
            "MASTER",
            "WARNING",
            "Master HTTP communication error: " + str(http_error),
            "Request timeout or HTTP status error from Flask.",
            ["Verify network traffic and Flask server responsiveness."]
        )
    else:
        clear_fault("MASTER_HTTP_ERROR", "MASTER")


# ============================================================
# 5. SAFE OUTPUTS & VALVE CONTROL
# ============================================================

def set_pump(enabled):
    global pump_running
    # Active LOW Relay (0 = Energized/ON, 1 = De-energized/OFF)
    pump.value(0 if enabled else 1)
    pump_running = bool(enabled)
    return True


def stop_valve4():
    global valve4_deadline, valve4_target_state
    valve4_ena.value(0)
    valve4_in1.value(0)
    valve4_in2.value(0)

    if valve_states[4] in ("OPENING", "CLOSING"):
        valve_states[4] = "STOPPED"

    valve4_deadline = None
    valve4_target_state = None
    valve_deadlines[4] = None


def set_valve4(direction):
    global valve4_deadline, valve4_target_state
    direction = str(direction).strip().upper()

    if direction == "STOP":
        stop_valve4()
        return True

    if direction not in ("OPEN", "CLOSE"):
        return False

    if direction == "OPEN":
        valve4_in1.value(1)
        valve4_in2.value(0)
        valve4_ena.value(1)
        valve_states[4] = "OPENING"
        valve4_deadline = time.ticks_add(
            time.ticks_ms(),
            VALVE_OPEN_MS[4]
        )
        valve_deadlines[4] = time.ticks_add(
            time.ticks_ms(),
            VALVE_OPEN_MS[4] + 10000
        )
        valve4_target_state = "OPEN"
    else:
        valve4_in1.value(0)
        valve4_in2.value(1)
        valve4_ena.value(1)
        valve_states[4] = "CLOSING"
        valve4_deadline = time.ticks_add(
            time.ticks_ms(),
            VALVE_CLOSE_MS[4]
        )
        valve_deadlines[4] = time.ticks_add(
            time.ticks_ms(),
            VALVE_CLOSE_MS[4] + 10000
        )
        valve4_target_state = "CLOSED"

    return True


def process_valve4_timer():
    global valve4_deadline, valve4_target_state
    if valve4_deadline is None:
        return

    if time.ticks_diff(time.ticks_ms(), valve4_deadline) >= 0:
        target = valve4_target_state
        valve4_ena.value(0)
        valve4_in1.value(0)
        valve4_in2.value(0)
        valve_states[4] = target or "STOPPED"
        valve4_deadline = None
        valve4_target_state = None
        valve_deadlines[4] = None


def send_slave_valve_command(tank, command):
    command = str(command).strip().upper()
    if tank not in (1, 2, 3):
        return False

    if command not in ("OPEN", "CLOSE", "STOP"):
        return False

    if not slave2_online or not wifi.isconnected():
        return False

    payload = {
        "device": "master",
        "valve": tank,
        "command": command
    }
    return http_post_json(VALVE_COMMAND_URL, payload)


def command_valve(tank, command):
    command = str(command).strip().upper()
    if tank == 4:
        return set_valve4(command)
    elif tank in (1, 2, 3):
        return send_slave_valve_command(tank, command)
    return False


def stop_all_outputs():
    set_pump(False)
    stop_valve4()

    # Prevent spamming Flask when already stopped
    if slave2_online and wifi.isconnected():
        for tank in (1, 2, 3):
            if valve_states.get(tank) not in ("CLOSED", "STOPPED"):
                send_slave_valve_command(tank, "STOP")
                valve_states[tank] = "STOPPED"


# ============================================================
# 6. HARDWARE INITIALIZATION
# ============================================================

def initialize_gpio():
    global pump, water_sensor
    global tank4_trig, tank4_echo
    global valve4_ena, valve4_in1, valve4_in2
    global start_button, stop_button

    tank4_trig = Pin(TANK4_TRIG_PIN, Pin.OUT, value=0)
    tank4_echo = Pin(TANK4_ECHO_PIN, Pin.IN)

    for tank, gpio in SWITCH_PINS.items():
        switches[tank] = Pin(gpio, Pin.IN)

    water_sensor = Pin(WATER_SENSOR_PIN, Pin.IN)

    # Pump Relay: Active LOW (Initial 1 = Relay OFF)
    pump = Pin(PUMP_PIN, Pin.OUT, value=1)

    # Physical Buttons with internal Pull-up (Active LOW)
    start_button = Pin(START_BUTTON_PIN, Pin.IN, Pin.PULL_UP)
    stop_button = Pin(STOP_BUTTON_PIN, Pin.IN, Pin.PULL_UP)

    # Valve 4 L293D Pins
    valve4_ena = Pin(VALVE4_ENA_PIN, Pin.OUT, value=0)
    valve4_in1 = Pin(VALVE4_IN1_PIN, Pin.OUT, value=0)
    valve4_in2 = Pin(VALVE4_IN2_PIN, Pin.OUT, value=0)

    stop_all_outputs()


# ============================================================
# 7. PHYSICAL BUTTONS
# ============================================================

def process_physical_buttons():
    global start_requested, stop_requested
    global last_start_button, last_stop_button
    global start_edge_time, stop_edge_time
    global system_mode, system_fault

    now = time.ticks_ms()
    start_value = start_button.value()
    stop_value = stop_button.value()

    # STOP button pressed
    if stop_value == 0 and last_stop_button == 1:
        if time.ticks_diff(now, stop_edge_time) >= BUTTON_DEBOUNCE_MS:
            stop_requested = True
            start_requested = False
            system_mode = "STOPPED"
            system_fault = None
            stop_all_outputs()
            stop_edge_time = now

    # START button pressed
    if start_value == 0 and last_start_button == 1:
        if time.ticks_diff(now, start_edge_time) >= BUTTON_DEBOUNCE_MS:
            if stop_button.value() == 1:  # Not physically held down
                stop_requested = False
                start_requested = True
                system_mode = "START REQUEST"
            start_edge_time = now

    last_start_button = start_value
    last_stop_button = stop_value


# ============================================================
# 8. WIFI & HTTP COMMUNICATION
# ============================================================

def wifi_connect_step():
    global last_wifi_attempt, http_error, wifi_info_printed

    if wifi.isconnected():
        if not wifi_info_printed:
            print("Connected to Wi-Fi network!")
            ip, subnet, gateway, dns = wifi.ifconfig()
            print("Master IP:", ip)
            wifi_info_printed = True
        return True

    wifi_info_printed = False
    now = time.ticks_ms()

    if time.ticks_diff(now, last_wifi_attempt) < WIFI_RETRY_MS:
        return False

    last_wifi_attempt = now

    try:
        if not wifi.active():
            wifi.active(True)

        if WIFI_SSID and WIFI_SSID != "YOUR_WIFI_SSID":
            wifi.connect(WIFI_SSID, WIFI_PASSWORD)

    except Exception as exc:
        http_error = "Wi-Fi error"
        print("Wi-Fi error:", exc)

    return wifi.isconnected()


def http_get_json(url):
    global http_error

    if urequests is None:
        http_error = "urequests unavailable"
        return None

    if not wifi.isconnected():
        http_error = "Wi-Fi disconnected"
        return None

    response = None

    try:
        response = urequests.get(
            url,
            timeout=HTTP_TIMEOUT_SECONDS
        )

        if response.status_code != 200:
            http_error = "GET HTTP " + str(response.status_code)
            return None

        result = response.json()
        http_error = None
        return result

    except Exception as exc:
        http_error = "GET failed"
        return None

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def http_post_json(url, payload):
    global http_error

    if urequests is None:
        http_error = "urequests unavailable"
        return False

    if not wifi.isconnected():
        http_error = "Wi-Fi disconnected"
        return False

    response = None

    try:
        response = urequests.post(
            url,
            data=ujson.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=HTTP_TIMEOUT_SECONDS
        )

        if response.status_code not in (200, 201):
            http_error = "POST HTTP " + str(response.status_code)
            return False

        result = response.json()
        if not isinstance(result, dict) or not result.get("success", False):
            http_error = "API rejected"
            return False

        http_error = None
        return True

    except Exception as exc:
        http_error = "POST failed"
        return False

    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


# ============================================================
# 9. TANK SELECTION LOGIC
# ============================================================

def read_physical_switches():
    global physical_switch_state, selected_tanks
    global physical_selection_initialized
    global physical_selection_changed, selection_source

    new_state = {}
    new_selection = []

    for tank in range(1, 5):
        value = switches[tank].value()
        new_state[tank] = value
        if value:
            new_selection.append(tank)

    if not physical_selection_initialized:
        physical_selection_initialized = True
        physical_switch_state = new_state
        selected_tanks = new_selection
        physical_selection_changed = True
        selection_source = "PHYSICAL"
        return

    if new_state != physical_switch_state:
        physical_switch_state = new_state
        selected_tanks = new_selection
        physical_selection_changed = True
        selection_source = "PHYSICAL"


def selection_dictionary(selection):
    return {
        "s1": 1 in selection,
        "s2": 2 in selection,
        "s3": 3 in selection,
        "s4": 4 in selection
    }


# ============================================================
# 10. TANK 4 SENSOR & WATER SENSOR
# ============================================================

def calculate_level(distance, full_cm, empty_cm):
    if distance is None or empty_cm <= full_cm:
        return None

    value = (empty_cm - distance) * 100 / (empty_cm - full_cm)
    return int(max(0, min(100, value)))


def read_tank4_distance():
    tank4_trig.value(0)
    time.sleep_us(3)
    tank4_trig.value(1)
    time.sleep_us(10)
    tank4_trig.value(0)

    try:
        pulse_us = machine.time_pulse_us(tank4_echo, 1, 30000)

        if pulse_us <= 0:
            raise ValueError("Invalid echo pulse")

        distance = pulse_us / 58.0

        if distance < 2 or distance > 400:
            raise ValueError("Distance out of range")

        tank_distances[4] = round(distance, 1)
        tank_levels[4] = calculate_level(
            distance,
            FULL_CM[4],
            EMPTY_CM[4]
        )
        tank_sensor_ok[4] = tank_levels[4] is not None

    except Exception:
        tank_distances[4] = None
        tank_levels[4] = None
        tank_sensor_ok[4] = False


def read_water_sensor():
    global water_available

    try:
        water_available = (
            water_sensor.value() == WATER_SENSOR_ACTIVE_LEVEL
        )
    except Exception:
        water_available = True


# ============================================================
# 11. FLASK COMMANDS & SLAVE INTEGRATION
# ============================================================

def poll_flask_commands():
    global command_sequence, command_sequence_initialized
    global start_requested, stop_requested
    global selected_tanks, selection_source
    global flask_connected, system_mode
    global last_valve4_sequence
    global slave1_online, slave2_online

    result = http_get_json(COMMANDS_URL)

    if not isinstance(result, dict):
        flask_connected = False
        return

    flask_connected = True

    # 1. Tank Selection Sync
    source = result.get("selectionSource", "PHYSICAL")
    selection = result.get("tankSelection", {})

    if isinstance(selection, dict):
        if source == "DASHBOARD" and not physical_selection_changed:
            selected_tanks = [
                tank for tank in range(1, 5)
                if bool(selection.get("s" + str(tank), False))
            ]
            selection_source = "DASHBOARD"
        elif source == "PHYSICAL":
            selection_source = "PHYSICAL"

    # 2. START / STOP System Command
    sequence = result.get(
        "commandSequence",
        result.get("sequence", command_sequence)
    )

    command = str(result.get("command", "NONE")).upper()

    if bool(result.get("stop", False)):
        command = "STOP"
    elif bool(result.get("start", False)):
        command = "START"

    if not command_sequence_initialized:
        command_sequence = sequence
        command_sequence_initialized = True
        if command == "STOP":
            execute_stop_command()
    elif sequence != command_sequence:
        command_sequence = sequence
        if command == "STOP":
            execute_stop_command()
        elif command == "START":
            stop_requested = False
            start_requested = True
            system_mode = "START REQUEST"

    # 3. Manual Valve 4 Command from Dashboard
    v4_cmd = result.get("valve4Command")
    if isinstance(v4_cmd, dict):
        v4_seq = v4_cmd.get("sequence", -1)
        if v4_seq != last_valve4_sequence:
            last_valve4_sequence = v4_seq
            v4_action = str(v4_cmd.get("command", "")).upper()
            if v4_action in ("OPEN", "CLOSE", "STOP"):
                set_valve4(v4_action)

    # 4. Ingest Slave Data (Bundled in commands response to save HTTP roundtrips)
    if "slave1Online" in result and "slave2Online" in result:
        slave1_online = bool(result.get("slave1Online", False))
        slave2_online = bool(result.get("slave2Online", False))

        slave_tanks = result.get("slaveTanks", {})
        for tank in (1, 2, 3):
            key = "tank" + str(tank)
            tdata = slave_tanks.get(key, {})
            if isinstance(tdata, dict) and tdata.get("sensor", False):
                lvl = tdata.get("level")
                if lvl is not None:
                    tank_levels[tank] = max(0, min(100, int(lvl)))
                    tank_sensor_ok[tank] = True
                tank_distances[tank] = tdata.get("distance", -1)
            else:
                tank_levels[tank] = None
                tank_sensor_ok[tank] = False

        slave_valves = result.get("slaveValves", [])
        for vitem in slave_valves:
            if isinstance(vitem, dict):
                vid = int(vitem.get("id", 0))
                if vid in (1, 2, 3):
                    remote_state = str(vitem.get("state", "CLOSED")).upper()
                    current_local = valve_states.get(vid, "CLOSED")

                    # Prevent in-flight overwrite while Slave 2 is picking up command
                    if current_local == "OPENING" and remote_state == "CLOSED":
                        pass
                    elif current_local == "CLOSING" and remote_state in ("OPEN", "OPENING"):
                        pass
                    else:
                        valve_states[vid] = remote_state

                    valve_errors[vid] = bool(vitem.get("error", False))


def execute_stop_command():
    global start_requested, stop_requested
    global current_filling_tank, system_mode, system_fault

    stop_requested = True
    start_requested = False
    current_filling_tank = None
    system_mode = "STOPPED"
    system_fault = None

    stop_all_outputs()


# ============================================================
# 12. AUTOMATIC FILLING CONTROLLER
# Logic: Lowest water level first, deadhead protection,
# dynamic sensor exclusion.
# ============================================================

def automatic_controller():
    global start_requested, stop_requested
    global current_filling_tank, system_mode, system_fault

    now = time.ticks_ms()

    if stop_requested:
        stop_all_outputs()
        current_filling_tank = None
        system_mode = "STOPPED"
        start_requested = False
        return

    if not start_requested:
        if system_mode not in ("STOPPED", "FAULT"):
            system_mode = "IDLE"
        if pump_running:
            set_pump(False)
        return

    # Dynamic Safety Interlocks
    if water_available is False:
        stop_all_outputs()
        system_mode = "FAULT"
        system_fault = "Water source empty"
        return

    if not wifi.isconnected() or not flask_connected:
        stop_all_outputs()
        system_mode = "FAULT"
        system_fault = "Flask or Wi-Fi offline"
        return

    need_slave1 = any(t in (1, 2, 3) for t in selected_tanks)
    need_slave2 = any(t in (1, 2, 3) for t in selected_tanks)

    if need_slave1 and not slave1_online:
        stop_all_outputs()
        system_mode = "FAULT"
        system_fault = "Slave 1 (Sensors) offline"
        return

    if need_slave2 and not slave2_online:
        stop_all_outputs()
        system_mode = "FAULT"
        system_fault = "Slave 2 (Valves) offline"
        return

    if not selected_tanks:
        stop_all_outputs()
        system_mode = "IDLE"
        system_fault = "No tanks selected"
        return

    # A tank is currently in the filling process
    if current_filling_tank is not None:
        tank = current_filling_tank

        # Sensor failure during fill
        if not tank_sensor_ok[tank] or tank_levels[tank] is None:
            stop_all_outputs()
            system_mode = "FAULT"
            system_fault = "Tank " + str(tank) + " sensor failed during filling"
            current_filling_tank = None
            return

        # Movement timeout check on opening valve
        dl = valve_deadlines.get(tank)
        if dl is not None and time.ticks_diff(now, dl) >= 0 and valve_states[tank] == "OPENING":
            stop_all_outputs()
            system_mode = "FAULT"
            system_fault = "Valve " + str(tank) + " opening timed out"
            valve_errors[tank] = True
            current_filling_tank = None
            return

        # Target reached (>= 95%)
        if tank_levels[tank] >= TANK_FULL_THRESHOLD:
            # SAFETY INTERLOCK: Cut pump FIRST!
            set_pump(False)
            command_valve(tank, "CLOSE")
            valve_states[tank] = "CLOSING"
            valve_deadlines[tank] = time.ticks_add(now, VALVE_CLOSE_MS[tank] + 10000)
            current_filling_tank = None
            system_mode = "TANK COMPLETE"
            return

        # DEADHEAD PROTECTION: Pump stays OFF while motorized valve is opening
        if valve_states[tank] == "OPENING":
            set_pump(False)
            system_mode = "OPENING VALVE " + str(tank)
            return
        else:
            # Valve is confirmed open, run pump
            if not pump_running:
                set_pump(True)
            system_mode = "FILLING TANK " + str(tank)
            return

    # Rule 5: Ensure any closing valve is fully closed before opening the next valve
    closing_valves = [t for t in range(1, 5) if valve_states.get(t) == "CLOSING"]
    if closing_valves:
        for t in closing_valves:
            dl = valve_deadlines.get(t)
            if dl is not None and time.ticks_diff(now, dl) >= 0:
                valve_states[t] = "ERROR"
                valve_errors[t] = True
                system_mode = "FAULT"
                system_fault = "Valve " + str(t) + " closing timed out"
                stop_all_outputs()
                return
        system_mode = "WAITING FOR VALVE TO CLOSE"
        set_pump(False)
        return

    # Select next tank to fill: LOWEST WATER LEVEL FIRST
    candidates = []
    for tank in selected_tanks:
        if not tank_sensor_ok[tank] or tank_levels[tank] is None:
            # Exclude tanks with sensor errors from filling decisions
            continue

        if tank_levels[tank] < TANK_FULL_THRESHOLD:
            candidates.append((tank_levels[tank], tank))

    if not candidates:
        stop_all_outputs()
        system_mode = "ALL TANKS FULL"
        system_fault = None
        start_requested = False
        return

    # Sort ascending by water level percentage (lowest level first)
    candidates.sort(key=lambda item: item[0])
    next_tank = candidates[0][1]

    # Close any other open valves before opening the target valve
    for tank in selected_tanks:
        if tank != next_tank and valve_states.get(tank) != "CLOSED":
            command_valve(tank, "CLOSE")

    # Command target valve to open
    if not command_valve(next_tank, "OPEN"):
        stop_all_outputs()
        system_mode = "FAULT"
        system_fault = "Failed to open Valve " + str(next_tank)
        return

    valve_states[next_tank] = "OPENING"
    valve_deadlines[next_tank] = time.ticks_add(now, VALVE_OPEN_MS[next_tank] + 10000)
    current_filling_tank = next_tank
    set_pump(False)  # Pump remains OFF until valve is fully open
    system_mode = "OPENING VALVE " + str(next_tank)
    system_fault = None


# ============================================================
# 13. TELEMETRY
# ============================================================

def build_master_telemetry():
    tanks = {}

    for tank in range(1, 5):
        tanks["tank" + str(tank)] = {
            "distance": tank_distances[tank],
            "level": tank_levels[tank],
            "sensor": tank_sensor_ok[tank]
        }

    ip = wifi.ifconfig()[0] if wifi.isconnected() else "--"

    return {
        "device": DEVICE_ID,
        "ip": ip,
        "tank4": tanks["tank4"],

        "controller": {
            "state": system_mode,
            "cycleRunning": current_filling_tank is not None,
            "activeTank": current_filling_tank or 0
        },

        "pump": {
            "running": pump_running,
            "state": "ON" if pump_running else "OFF"
        },

        "switches": selection_dictionary(selected_tanks),

        "physicalSwitches": selection_dictionary([
            tank for tank in range(1, 5)
            if physical_switch_state[tank]
        ]),

        "physicalSelectionChanged": physical_selection_changed,

        "buttons": {
            "start": start_requested,
            "stop": stop_requested
        },

        "tanks": tanks,

        "valves": [
            {
                "id": tank,
                "state": valve_states[tank],
                "selected": tank in selected_tanks,
                "error": valve_errors[tank]
            }
            for tank in range(1, 5)
        ],

        "system": {
            "healthy": (
                wifi.isconnected()
                and flask_connected
                and slave1_online
                and slave2_online
                and all(tank_sensor_ok[t] for t in range(1, 5))
            ),
            "warning": bool(system_fault),
            "flaskConnected": flask_connected,
            "slaveConnected": slave1_online and slave2_online,
            "fault": system_fault
        },

        "faults": faults,
        "waterAvailable": water_available,
        "timestamp": time.time(),
        "masterOnline": True
    }


def send_master_telemetry():
    global physical_selection_changed

    if not wifi.isconnected():
        return

    update_faults()

    if http_post_json(MASTER_URL, build_master_telemetry()):
        physical_selection_changed = False


# ============================================================
# 14. MAIN LOOP
# ============================================================

def main():
    global system_mode
    global last_sensor_read, last_command_poll, last_telemetry

    print("================================")
    print("WATER TANK SYSTEM V5 - MASTER")
    print("Flask Server:", FLASK_BASE_URL)
    print("Hardware: Live and Connected")
    print("================================")

    initialize_gpio()
    system_mode = "IDLE"

    while True:
        now = time.ticks_ms()

        process_physical_buttons()
        read_physical_switches()
        read_water_sensor()

        wifi_connect_step()

        if time.ticks_diff(now, last_sensor_read) >= SENSOR_INTERVAL_MS:
            last_sensor_read = now
            read_tank4_distance()

        if time.ticks_diff(now, last_command_poll) >= COMMAND_POLL_MS:
            last_command_poll = now
            poll_flask_commands()

        process_valve4_timer()
        automatic_controller()
        update_faults()

        if time.ticks_diff(now, last_telemetry) >= TELEMETRY_INTERVAL_MS:
            last_telemetry = now
            send_master_telemetry()

        time.sleep_ms(50)


try:
    main()

except KeyboardInterrupt:
    try:
        stop_all_outputs()
    except Exception:
        pass
    print("Master stopped safely.")

except Exception as exc:
    try:
        stop_all_outputs()
    except Exception:
        pass

    add_fault(
        "MASTER_FATAL_ERROR",
        "MASTER",
        "CRITICAL",
        str(exc),
        "An unexpected firmware exception occurred.",
        [
            "Check exception traceback in Serial Monitor.",
            "Restart the ESP32 after correcting the cause."
        ]
    )
    print("MASTER FATAL ERROR:", exc)
    raise


