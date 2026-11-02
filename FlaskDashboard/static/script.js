// ============================================================
// WATER LEVEL MANAGEMENT V4
// DASHBOARD CONTROL + MONITORING
// ============================================================
//
// Browser -> Flask
//
// GET  /api/dashboard
//      Read current system status
//
// POST /api/control
//      Send dashboard commands
//
// Dashboard does NOT communicate directly with ESP32.
// ============================================================


// ============================================================
// SETTINGS
// ============================================================

const DASHBOARD_API = "/api/dashboard";
const CONTROL_API = "/api/control";

const REFRESH_INTERVAL = 1000;


// ============================================================
// STATE
// ============================================================

let dashboardData = null;

let controlBusy = false;


// ============================================================
// BASIC HELPERS
// ============================================================

function getElement(id) {

    return document.getElementById(id);
}


function setText(id, value) {

    const element = getElement(id);

    if (element) {
        element.textContent = value;
    }
}


function setBadge(id, text, type) {

    const element = getElement(id);

    if (!element) {
        return;
    }

    element.textContent = text;

    element.className =
        "badge " + type;
}


// ============================================================
// FORMAT HELPERS
// ============================================================

function formatDistance(distance) {

    if (
        distance === undefined ||
        distance === null ||
        Number(distance) < 0
    ) {
        return "--";
    }

    return Number(distance).toFixed(1) + " cm";
}


function formatLevel(level) {

    if (
        level === undefined ||
        level === null
    ) {
        return "--";
    }

    return Number(level).toFixed(0) + "%";
}


function formatTime(timestamp) {

    if (
        timestamp === undefined ||
        timestamp === null ||
        Number(timestamp) <= 0
    ) {
        return "--";
    }

    const date = new Date(
        Number(timestamp) * 1000
    );

    return date.toLocaleTimeString();
}


// ============================================================
// SYSTEM STATUS
// ============================================================

function updateSystemStatus(data) {

    const master =
        data.master || {};

    const slave =
        data.slave || {};

    const controller =
        data.controller || {};


    const systemDot =
        getElement(
            "systemStatusDot"
        );

    const systemText =
        getElement(
            "systemStatusText"
        );


    if (
        master.online &&
        slave.online
    ) {

        if (systemDot) {

            systemDot.className =
                "status-dot online";
        }

        if (systemText) {

            systemText.textContent =
                "SYSTEM ONLINE";
        }

    } else {

        if (systemDot) {

            systemDot.className =
                "status-dot offline";
        }

        if (systemText) {

            systemText.textContent =
                "SYSTEM OFFLINE";
        }
    }


    // --------------------------------------------------------
    // Controller status
    // --------------------------------------------------------

    const controllerState =
        String(
            controller.state ||
            "IDLE"
        ).toUpperCase();


    let controllerClass = "idle";


    if (
        controllerState === "RUNNING" ||
        controllerState === "FILLING"
    ) {

        controllerClass =
            "running";

    } else if (
        controllerState === "WARNING"
    ) {

        controllerClass =
            "warning";

    } else if (
        controllerState === "STOPPED"
    ) {

        controllerClass =
            "stopped";

    } else if (
        controllerState === "COMPLETED"
    ) {

        controllerClass =
            "completed";
    }


    setBadge(
        "controllerStatus",
        controllerState,
        controllerClass
    );


    // --------------------------------------------------------
    // Active tank
    // --------------------------------------------------------

    const activeTank =
        Number(
            controller.activeTank || 0
        );


    if (activeTank > 0) {

        setText(
            "activeTank",
            "TANK " + activeTank
        );

    } else {

        setText(
            "activeTank",
            "NONE"
        );
    }


    // --------------------------------------------------------
    // Cycle
    // --------------------------------------------------------

    setText(
        "cycleStatus",
        controller.cycleRunning
            ? "RUNNING"
            : "STOPPED"
    );
}


// ============================================================
// DEVICE STATUS
// ============================================================

function updateDeviceStatus(data) {

    const master =
        data.master || {};

    const slave =
        data.slave || {};


    // --------------------------------------------------------
    // Master
    // --------------------------------------------------------

    if (master.online) {

        setBadge(
            "masterStatus",
            "ONLINE",
            "online"
        );

    } else {

        setBadge(
            "masterStatus",
            "OFFLINE",
            "offline"
        );
    }


    setText(
        "masterIP",
        master.ip || "--"
    );


    setText(
        "masterLastUpdate",
        formatTime(
            master.lastUpdate
        )
    );


    // --------------------------------------------------------
    // Slave
    // --------------------------------------------------------

    if (slave.online) {

        setBadge(
            "slaveStatus",
            "ONLINE",
            "online"
        );

    } else {

        setBadge(
            "slaveStatus",
            "OFFLINE",
            "offline"
        );
    }


    setText(
        "slaveIP",
        slave.ip || "--"
    );


    setText(
        "slaveLastUpdate",
        formatTime(
            slave.lastUpdate
        )
    );
}


// ============================================================
// PUMP
// ============================================================

function updatePump(data) {

    const pump =
        data.pump || {};


    if (pump.running) {

        setBadge(
            "pumpStatus",
            "ON",
            "running"
        );


        setText(
            "pumpLargeStatus",
            "PUMP RUNNING"
        );

    } else {

        setBadge(
            "pumpStatus",
            "OFF",
            "stopped"
        );


        setText(
            "pumpLargeStatus",
            "PUMP OFF"
        );
    }
}


// ============================================================
// TANK DISPLAY
// ============================================================

function updateTank(
    tankNumber,
    tank
) {

    if (!tank) {
        return;
    }


    const level =
        Number(
            tank.level ??
            tank.percentage ??
            0
        );


    const sensor =
        Boolean(
            tank.sensor
        );


    // --------------------------------------------------------
    // Level
    // --------------------------------------------------------

    setText(
        "tank" +
        tankNumber +
        "Level",
        formatLevel(level)
    );


    setText(
        "tank" +
        tankNumber +
        "Percent",
        formatLevel(level)
    );


    // --------------------------------------------------------
    // Distance
    // --------------------------------------------------------

    setText(
        "tank" +
        tankNumber +
        "Distance",
        formatDistance(
            tank.distance
        )
    );


    // --------------------------------------------------------
    // Tank fill graphic
    // --------------------------------------------------------

    const fill =
        getElement(
            "tank" +
            tankNumber +
            "Fill"
        );


    if (fill) {

        const percentage =
            Math.max(
                0,
                Math.min(
                    100,
                    level
                )
            );


        fill.style.height =
            percentage + "%";
    }


    // --------------------------------------------------------
    // Sensor status
    // --------------------------------------------------------

    if (sensor) {

        setBadge(
            "tank" +
            tankNumber +
            "Sensor",
            "ONLINE",
            "online"
        );

    } else {

        setBadge(
            "tank" +
            tankNumber +
            "Sensor",
            "OFFLINE",
            "offline"
        );
    }
}


// ============================================================
// ALL TANKS
// ============================================================

function updateTanks(data) {

    updateTank(
        1,
        data.tank1
    );

    updateTank(
        2,
        data.tank2
    );

    updateTank(
        3,
        data.tank3
    );

    updateTank(
        4,
        data.tank4
    );
}


// ============================================================
// TANK SELECTION DISPLAY
// ============================================================
//
// IMPORTANT:
//
// The dashboard switch is a CONTROL.
//
// The value shown here is the latest state reported by Master.
//
// This prevents the dashboard from assuming that a command
// was successfully applied before Master reports it.
// ============================================================

function updateSelection(
    tankNumber,
    selected
) {

    const card =
        getElement(
            "selection" +
            tankNumber
        );


    const checkbox =
        getElement(
            "tankSwitch" +
            tankNumber
        );


    const state =
        getElement(
            "selection" +
            tankNumber +
            "State"
        );


    if (checkbox) {

        checkbox.checked =
            Boolean(selected);
    }


    if (card) {

        if (selected) {

            card.classList.add(
                "selected"
            );

        } else {

            card.classList.remove(
                "selected"
            );
        }
    }


    if (state) {

        state.textContent =
            selected
                ? "SELECTED"
                : "NOT SELECTED";
    }
}


function updateTankSelection(data) {

    const switches =
        data.switches || {};


    updateSelection(
        1,
        Boolean(
            switches.s1
        )
    );


    updateSelection(
        2,
        Boolean(
            switches.s2
        )
    );


    updateSelection(
        3,
        Boolean(
            switches.s3
        )
    );


    updateSelection(
        4,
        Boolean(
            switches.s4
        )
    );
}


// ============================================================
// VALVES
// ============================================================

function updateValve(valve) {

    if (!valve) {
        return;
    }


    const id =
        Number(
            valve.id
        );


    if (
        id < 1 ||
        id > 4
    ) {
        return;
    }


    const card =
        getElement(
            "valve" + id
        );


    const stateElement =
        getElement(
            "valve" +
            id +
            "State"
        );


    if (
        !card ||
        !stateElement
    ) {
        return;
    }


    const state =
        String(
            valve.state ||
            "CLOSED"
        ).toUpperCase();


    stateElement.textContent =
        state;


    card.classList.remove(
        "open",
        "closed",
        "opening",
        "closing",
        "error"
    );


    if (state === "OPEN") {

        card.classList.add(
            "open"
        );

    } else if (
        state === "OPENING"
    ) {

        card.classList.add(
            "opening"
        );

    } else if (
        state === "CLOSING"
    ) {

        card.classList.add(
            "closing"
        );

    } else if (
        state === "CLOSED"
    ) {

        card.classList.add(
            "closed"
        );

    } else {

        card.classList.add(
            "error"
        );
    }


    if (valve.error) {

        card.classList.add(
            "error"
        );
    }
}


function updateValves(data) {

    const valves =
        data.valves || [];


    valves.forEach(
        function(valve) {

            updateValve(
                valve
            );
        }
    );
}


// ============================================================
// PHYSICAL BUTTON STATUS
// ============================================================

function updatePhysicalButtons(data) {

    const buttons =
        data.buttons || {};


    setText(
        "physicalStartButton",
        buttons.start
            ? "PRESSED"
            : "RELEASED"
    );


    setText(
        "physicalStopButton",
        buttons.stop
            ? "PRESSED"
            : "RELEASED"
    );
}


// ============================================================
// CONTROL MESSAGE
// ============================================================

function showControlMessage(
    message,
    type = "info"
) {

    const element =
        getElement(
            "controlMessage"
        );


    if (!element) {
        return;
    }


    element.textContent =
        message;


    element.className =
        "control-message " +
        type;


    setTimeout(
        function() {

            element.textContent =
                "";

            element.className =
                "control-message";

        },
        3000
    );
}


// ============================================================
// TANK SELECTION COMMAND
// ============================================================

async function tankSelectionChanged(
    changedTank
) {

    if (controlBusy) {
        return;
    }


    const selection = {

        s1: Boolean(
            getElement(
                "tankSwitch1"
            ).checked
        ),

        s2: Boolean(
            getElement(
                "tankSwitch2"
            ).checked
        ),

        s3: Boolean(
            getElement(
                "tankSwitch3"
            ).checked
        ),

        s4: Boolean(
            getElement(
                "tankSwitch4"
            ).checked
        )
    };


    controlBusy = true;


    try {

        const response =
            await fetch(
                CONTROL_API,
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        tankSelection:
                            selection

                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(
                result.error ||
                "Tank selection failed"
            );
        }


        showControlMessage(
            "Tank selection command sent.",
            "success"
        );


    } catch (error) {

        console.error(
            "Tank selection error:",
            error
        );


        showControlMessage(
            "Unable to send tank selection.",
            "error"
        );


        // Re-read actual Master state.

        await fetchDashboardData();

    } finally {

        controlBusy = false;
    }
}


// ============================================================
// START COMMAND
// ============================================================

async function sendStartCommand() {

    if (controlBusy) {
        return;
    }


    const button =
        getElement(
            "startButtonControl"
        );


    controlBusy = true;


    if (button) {

        button.disabled = true;

        button.textContent =
            "STARTING...";
    }


    try {

        const response =
            await fetch(
                CONTROL_API,
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        command: "START"

                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(
                result.error ||
                "START command failed"
            );
        }


        showControlMessage(
            "START command sent to Master.",
            "success"
        );


        // Immediately refresh status.

        await fetchDashboardData();


    } catch (error) {

        console.error(
            "START error:",
            error
        );


        showControlMessage(
            "Unable to send START command.",
            "error"
        );

    } finally {

        controlBusy = false;


        if (button) {

            button.disabled = false;

            button.textContent =
                "START FILLING";
        }
    }
}


// ============================================================
// STOP COMMAND
// ============================================================

async function sendStopCommand() {

    if (controlBusy) {
        return;
    }


    const button =
        getElement(
            "stopButtonControl"
        );


    controlBusy = true;


    if (button) {

        button.disabled = true;

        button.textContent =
            "STOPPING...";
    }


    try {

        const response =
            await fetch(
                CONTROL_API,
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        command: "STOP"

                    })
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }


        const result =
            await response.json();


        if (!result.success) {

            throw new Error(
                result.error ||
                "STOP command failed"
            );
        }


        showControlMessage(
            "STOP command sent to Master.",
            "success"
        );


        // Immediately refresh status.

        await fetchDashboardData();


    } catch (error) {

        console.error(
            "STOP error:",
            error
        );


        showControlMessage(
            "Unable to send STOP command.",
            "error"
        );

    } finally {

        controlBusy = false;


        if (button) {

            button.disabled = false;

            button.textContent =
                "STOP ALL";
        }
    }
}


// ============================================================
// GET DASHBOARD DATA
// ============================================================
//
// Browser -> Flask
//
// This remains GET only for reading data.
// ============================================================

async function fetchDashboardData() {

    try {

        const response =
            await fetch(
                DASHBOARD_API,
                {

                    method: "GET",

                    cache: "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );
        }


        const data =
            await response.json();


        dashboardData =
            data;


        updateDashboard(
            data
        );


    } catch (error) {

        console.error(
            "Dashboard API error:",
            error
        );


        setBadge(
            "masterStatus",
            "NO DATA",
            "offline"
        );


        setBadge(
            "slaveStatus",
            "NO DATA",
            "offline"
        );


        const dot =
            getElement(
                "systemStatusDot"
            );


        const text =
            getElement(
                "systemStatusText"
            );


        if (dot) {

            dot.className =
                "status-dot offline";
        }


        if (text) {

            text.textContent =
                "SERVER UNAVAILABLE";
        }
    }
}


// ============================================================
// COMPLETE DASHBOARD UPDATE
// ============================================================

function updateDashboard(data) {

    if (!data) {
        return;
    }


    updateDeviceStatus(
        data
    );


    updateSystemStatus(
        data
    );


    updatePump(
        data
    );


    updateTanks(
        data
    );


    updateTankSelection(
        data
    );


    updateValves(
        data
    );


    updatePhysicalButtons(
        data
    );


    setText(
        "dashboardLastUpdate",
        new Date().toLocaleTimeString()
    );
}


// ============================================================
// START DASHBOARD
// ============================================================

function startDashboard() {

    fetchDashboardData();


    setInterval(
        fetchDashboardData,
        REFRESH_INTERVAL
    );
}


// ============================================================
// PAGE LOAD
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        startDashboard();

    }
);