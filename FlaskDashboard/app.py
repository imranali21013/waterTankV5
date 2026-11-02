# ============================================================
# WATER TANK SYSTEM V5 - FLASK SERVER
# ============================================================

from flask import Flask, jsonify, request, render_template
import copy
import time
import threading

app = Flask(__name__)
DEVICE_TIMEOUT = 10
data_lock = threading.RLock()


# ============================================================
# DEVICE DATA
# ============================================================

def default_tank():
    return {"distance": -1, "level": 0, "sensor": False}


def default_valve(valve_id):
    return {"id": valve_id, "state": "CLOSED", "selected": False, "error": False}


def default_device(device_name):
    return {
        "device": device_name,
        "ip": "--",
        "system": {"online": False, "healthy": False, "flaskConnected": False, "fault": None},
        "faults": [],
        "timestamp": 0,
        "last_received": 0
    }


master_data = default_device("master")
master_data.update({
    "controller": {"state": "OFFLINE", "cycleRunning": False, "activeTank": 0},
    "pump": {"running": False, "state": "OFF"},
    "switches": {"s1": False, "s2": False, "s3": False, "s4": False},
    "physicalSwitches": {"s1": False, "s2": False, "s3": False, "s4": False},
    "tank4": default_tank(),
    "tanks": {"tank1": default_tank(), "tank2": default_tank(), "tank3": default_tank(), "tank4": default_tank()},
    "valves": [default_valve(1), default_valve(2), default_valve(3), default_valve(4)],
    "masterOnline": False
})

slave1_data = default_device("slave1")
slave1_data.update({"tank1": default_tank(), "tank2": default_tank(), "tank3": default_tank()})

slave2_data = default_device("slave2")
slave2_data.update({"valves": [default_valve(1), default_valve(2), default_valve(3)]})

dashboard_tank_selection = {"s1": False, "s2": False, "s3": False, "s4": False}
selection_source = "PHYSICAL"

command_sequence = 0
last_system_command = "STOP"
valve_command_sequence = 0
valve_commands = {
    1: {"command": "STOP", "sequence": 0},
    2: {"command": "STOP", "sequence": 0},
    3: {"command": "STOP", "sequence": 0},
    4: {"command": "STOP", "sequence": 0}
}

# Centralized Fault Registry (supports active tracking and resolved history)
fault_registry = {}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def current_time():
    return time.time()


def is_online(device_data):
    last_received = device_data.get("last_received", 0)
    if not last_received:
        return False
    return current_time() - last_received <= DEVICE_TIMEOUT


def normalize_device_name(value):
    value = str(value or "").strip().lower()
    aliases = {
        "master": "master", "master esp32": "master",
        "slave": "slave1", "slave1": "slave1", "slave 1": "slave1",
        "slave2": "slave2", "slave 2": "slave2"
    }
    return aliases.get(value)


def normalize_valves(valves, allowed_ids):
    normalized = {valve_id: default_valve(valve_id) for valve_id in allowed_ids}
    if not isinstance(valves, list):
        return normalized
    for valve in valves:
        if not isinstance(valve, dict):
            continue
        try:
            valve_id = int(valve.get("id"))
        except (TypeError, ValueError):
            continue
        if valve_id not in normalized:
            continue
        normalized[valve_id].update(copy.deepcopy(valve))
        normalized[valve_id]["id"] = valve_id
    return normalized


def normalize_faults(device_name, payload):
    result = []
    incoming = payload.get("faults", [])
    if isinstance(incoming, list):
        for fault in incoming:
            if not isinstance(fault, dict):
                continue
            item = copy.deepcopy(fault)
            item["device"] = device_name
            item.setdefault("source", device_name)
            item.setdefault("code", "DEVICE_FAULT")
            item.setdefault("severity", "warning")
            item.setdefault("message", "Device reported a fault")
            item.setdefault("cause", "Issue reported by device hardware.")
            item.setdefault("steps", ["Inspect device power supply.", "Verify wiring.", "Check ESP32 Serial output."])
            item.setdefault("active", True)
            item.setdefault("first_seen", current_time())
            item["last_seen"] = current_time()
            result.append(item)
    return result


def device_summary(device_data):
    return {
        "online": is_online(device_data),
        "ip": device_data.get("ip", "--"),
        "lastUpdate": device_data.get("last_received", 0),
        "system": copy.deepcopy(device_data.get("system", {}))
    }


def get_all_faults():
    raw_faults = []
    devices = [("master", master_data), ("slave1", slave1_data), ("slave2", slave2_data)]

    for device_name, device_data in devices:
        if not is_online(device_data):
            raw_faults.append({
                "device": device_name, "source": "network", "code": "DEVICE_OFFLINE",
                "severity": "critical", "message": device_name.upper() + " is offline",
                "cause": "No recent telemetry received within the 10-second timeout window.",
                "steps": ["Verify device is powered on.", "Check Wi-Fi connection.", "Verify Flask IP address in firmware."],
                "active": True, "first_seen": device_data.get("last_received", 0), "last_seen": device_data.get("last_received", 0)
            })
        raw_faults.extend(normalize_faults(device_name, device_data))

    # Missing tank sensor readings
    for tank_number in range(1, 5):
        tank_key = "tank" + str(tank_number)
        if tank_number <= 3:
            reading = slave1_data.get(tank_key) if is_online(slave1_data) else {}
            owner = "slave1"
        else:
            t4_reading = master_data.get("tank4")
            if not t4_reading or not isinstance(t4_reading, dict) or not t4_reading.get("sensor"):
                t4_from_tanks = master_data.get("tanks", {}).get("tank4") if isinstance(master_data.get("tanks"), dict) else None
                if t4_from_tanks:
                    t4_reading = t4_from_tanks
            reading = t4_reading if is_online(master_data) else {}
            owner = "master"

        owner_data = slave1_data if owner == "slave1" else master_data
        if is_online(owner_data) and isinstance(reading, dict) and not reading.get("sensor", False):
            raw_faults.append({
                "device": owner,
                "source": tank_key,
                "code": "TANK_SENSOR_INVALID",
                "severity": "warning",
                "message": "Tank " + str(tank_number) + " sensor reading is invalid",
                "cause": "The ultrasonic sensor did not provide a valid echo pulse.",
                "steps": [
                    "Check sensor VCC (5V) and GND connections.",
                    "Verify TRIG and ECHO GPIO wiring.",
                    "Check voltage divider on ECHO (5V to 3.3V)."
                ],
                "active": True,
                "first_seen": owner_data.get("last_received", 0),
                "last_seen": owner_data.get("last_received", 0)
            })

    unique = {}
    for fault in raw_faults:
        key = (fault.get("device"), fault.get("code"), fault.get("source"))
        unique[key] = fault

    # Update centralized fault registry (Active vs Resolved Lifecycle)
    active_keys = set()
    now_ts = current_time()

    for key, f in unique.items():
        active_keys.add(key)
        if key not in fault_registry:
            entry = copy.deepcopy(f)
            entry["first_seen"] = now_ts
            entry["last_seen"] = now_ts
            entry["status"] = "ACTIVE"
            entry["occurrence_count"] = 1
            fault_registry[key] = entry
        else:
            fault_registry[key]["last_seen"] = now_ts
            fault_registry[key]["status"] = "ACTIVE"
            fault_registry[key]["active"] = True

    for key, entry in fault_registry.items():
        if key not in active_keys and entry.get("status") == "ACTIVE":
            entry["status"] = "RESOLVED"
            entry["active"] = False
            entry["resolved_at"] = now_ts

    return [f for f in fault_registry.values() if f.get("status") == "ACTIVE"]


def get_resolved_faults():
    return [f for f in fault_registry.values() if f.get("status") == "RESOLVED"]


# ============================================================
# ROUTES
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/master", methods=["POST"])
def receive_master():
    global master_data, dashboard_tank_selection, selection_source
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    with data_lock:
        incoming = copy.deepcopy(data)
        incoming["device"] = "master"
        incoming["last_received"] = current_time()
        incoming.setdefault("ip", "--")
        if not isinstance(incoming.get("system"), dict):
            incoming["system"] = {}
        incoming["system"]["flaskConnected"] = True

        if "tank4" in incoming and isinstance(incoming["tank4"], dict):
            master_data["tank4"] = copy.deepcopy(incoming["tank4"])
        elif "tanks" in incoming and isinstance(incoming["tanks"], dict) and "tank4" in incoming["tanks"]:
            master_data["tank4"] = copy.deepcopy(incoming["tanks"]["tank4"])

        master_data.update(incoming)
        master_data["masterOnline"] = True

        if data.get("physicalSelectionChanged") is True:
            reported = data.get("switches", {})
            if isinstance(reported, dict):
                dashboard_tank_selection = {
                    "s1": bool(reported.get("s1", False)),
                    "s2": bool(reported.get("s2", False)),
                    "s3": bool(reported.get("s3", False)),
                    "s4": bool(reported.get("s4", False))
                }
                selection_source = "PHYSICAL"

    return jsonify({"success": True, "message": "Master telemetry received"})


@app.route("/api/slave", methods=["POST"])
def receive_slave():
    global slave1_data, slave2_data
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON"}), 400

    device_name = normalize_device_name(data.get("device"))
    if device_name not in ("slave1", "slave2"):
        return jsonify({"success": False, "error": "Invalid device"}), 400

    with data_lock:
        incoming = copy.deepcopy(data)
        incoming["device"] = device_name
        incoming["last_received"] = current_time()
        if device_name == "slave1":
            slave1_data.update(incoming)
        elif device_name == "slave2":
            slave2_data.update(incoming)

    return jsonify({"success": True, "device": device_name})


@app.route("/api/dashboard", methods=["GET"])
def dashboard_data():
    with data_lock:
        master_online = is_online(master_data)
        slave1_online = is_online(slave1_data)
        slave2_online = is_online(slave2_data)

        tanks = {}
        for tank_number in range(1, 4):
            key = "tank" + str(tank_number)
            tanks[key] = copy.deepcopy(slave1_data[key]) if slave1_online and isinstance(slave1_data.get(key), dict) else default_tank()
        t4_data = master_data.get("tank4")
        if not t4_data or not isinstance(t4_data, dict) or not t4_data.get("sensor"):
            t4_from_tanks = master_data.get("tanks", {}).get("tank4") if isinstance(master_data.get("tanks"), dict) else None
            if t4_from_tanks and t4_from_tanks.get("sensor"):
                t4_data = t4_from_tanks
        tanks["tank4"] = copy.deepcopy(t4_data if (master_online and t4_data) else default_tank())

        slave2_valves = normalize_valves(slave2_data.get("valves", []), (1, 2, 3))
        master_valves = normalize_valves(master_data.get("valves", []), (1, 2, 3, 4))
        valves = []
        for valve_id in range(1, 5):
            if valve_id <= 3 and slave2_online:
                valves.append(copy.deepcopy(slave2_valves[valve_id]))
            else:
                valves.append(copy.deepcopy(master_valves[valve_id]))

        result = {
            "master": device_summary(master_data),
            "slave1": device_summary(slave1_data),
            "slave2": device_summary(slave2_data),
            "masterOnline": master_online,
            "controller": copy.deepcopy(master_data.get("controller", {"state": "OFFLINE", "cycleRunning": False, "activeTank": 0})),
            "pump": copy.deepcopy(master_data.get("pump", {"running": False, "state": "OFF"})),
            "system": {"flaskConnected": True, "masterOnline": master_online, "slave1Online": slave1_online, "slave2Online": slave2_online},
            "tank1": tanks["tank1"], "tank2": tanks["tank2"], "tank3": tanks["tank3"], "tank4": tanks["tank4"],
            "valves": valves,
            "switches": copy.deepcopy(dashboard_tank_selection),
            "physicalSwitches": copy.deepcopy(master_data.get("physicalSwitches", {})),
            "selectionSource": selection_source,
            "faults": get_all_faults(),
            "faultHistory": get_resolved_faults(),
            "timestamp": current_time()
        }
    return jsonify(result)


@app.route("/api/control", methods=["POST"])
def dashboard_control():
    global command_sequence, last_system_command, dashboard_tank_selection, selection_source
    data = request.get_json(silent=True) or {}
    with data_lock:
        if "tankSelection" in data:
            dashboard_tank_selection = {f"s{i}": bool(data["tankSelection"].get(f"s{i}", False)) for i in range(1, 5)}
            selection_source = "DASHBOARD"
        command = str(data.get("command", "")).upper().strip()
        if command in ("START", "STOP"):
            last_system_command = command
            command_sequence += 1

        return jsonify({
            "success": True,
            "sequence": command_sequence,
            "command": last_system_command,
            "start": last_system_command == "START",
            "stop": last_system_command == "STOP",
            "tankSelection": copy.deepcopy(dashboard_tank_selection),
            "selectionSource": selection_source
        })


@app.route("/api/commands", methods=["GET"])
def get_commands():
    with data_lock:
        device = str(request.args.get("device", "master")).lower()
        response = {
            "success": True,
            "sequence": command_sequence,
            "command": last_system_command,
            "tankSelection": copy.deepcopy(dashboard_tank_selection),
            "selectionSource": selection_source,
            "start": last_system_command == "START",
            "stop": last_system_command == "STOP"
        }
        if device == "slave2":
            response["valveCommands"] = {str(vid): copy.deepcopy(valve_commands[vid]) for vid in (1, 2, 3)}
        if device == "master":
            response["valve4Command"] = copy.deepcopy(valve_commands[4])
            response["slave1Online"] = is_online(slave1_data)
            response["slave2Online"] = is_online(slave2_data)
            response["slaveTanks"] = {f"tank{i}": copy.deepcopy(slave1_data.get(f"tank{i}", default_tank())) for i in (1, 2, 3)}
            slave2_valves = normalize_valves(slave2_data.get("valves", []), (1, 2, 3))
            response["slaveValves"] = [copy.deepcopy(slave2_valves[vid]) for vid in (1, 2, 3)]
        return jsonify(response)


@app.route("/api/valve-command", methods=["POST"])
def set_valve_command():
    global valve_command_sequence
    data = request.get_json(silent=True) or {}
    valve_id = int(data.get("valve", 0))
    command = str(data.get("command", "")).upper().strip()
    if valve_id not in (1, 2, 3, 4) or command not in ("OPEN", "CLOSE", "STOP"):
        return jsonify({"success": False, "error": "Invalid command or valve"}), 400

    with data_lock:
        valve_command_sequence += 1
        valve_commands[valve_id] = {"command": command, "sequence": valve_command_sequence}

    return jsonify({"success": True, "valve": valve_id, "command": command, "sequence": valve_command_sequence})


@app.route("/api/faults", methods=["GET"])
def api_faults():
    with data_lock:
        return jsonify({"success": True, "activeFaults": get_all_faults(), "timestamp": current_time()})


@app.route("/api/faults/history", methods=["GET"])
def api_fault_history():
    with data_lock:
        return jsonify({"success": True, "faultHistory": get_resolved_faults(), "timestamp": current_time()})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"success": True, "service": "Water Tank System V5", "timestamp": current_time()})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5555))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
