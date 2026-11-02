package com.nubeera.watertankv5.data.model

import com.google.gson.annotations.SerializedName

data class DashboardResponse(
    @SerializedName("master") val master: DeviceSummary? = null,
    @SerializedName("slave1") val slave1: DeviceSummary? = null,
    @SerializedName("slave2") val slave2: DeviceSummary? = null,
    @SerializedName("masterOnline") val masterOnline: Boolean = false,
    @SerializedName("controller") val controller: ControllerState? = null,
    @SerializedName("pump") val pump: PumpState? = null,
    @SerializedName("tank1") val tank1: TankReading? = null,
    @SerializedName("tank2") val tank2: TankReading? = null,
    @SerializedName("tank3") val tank3: TankReading? = null,
    @SerializedName("tank4") val tank4: TankReading? = null,
    @SerializedName("valves") val valves: List<ValveItem> = emptyList(),
    @SerializedName("switches") val switches: SwitchesMap? = null,
    @SerializedName("physicalSwitches") val physicalSwitches: SwitchesMap? = null,
    @SerializedName("selectionSource") val selectionSource: String = "PHYSICAL",
    @SerializedName("faults") val faults: List<FaultRecord> = emptyList(),
    @SerializedName("timestamp") val timestamp: Double = 0.0
)

data class DeviceSummary(
    @SerializedName("online") val online: Boolean = false,
    @SerializedName("ip") val ip: String = "--",
    @SerializedName("lastUpdate") val lastUpdate: Double = 0.0
)

data class ControllerState(
    @SerializedName("state") val state: String = "OFFLINE",
    @SerializedName("cycleRunning") val cycleRunning: Boolean = false,
    @SerializedName("activeTank") val activeTank: Int = 0
)

data class PumpState(
    @SerializedName("running") val running: Boolean = false,
    @SerializedName("state") val state: String = "OFF"
)

data class TankReading(
    @SerializedName("distance") val distance: Double = -1.0,
    @SerializedName("level") val level: Int = 0,
    @SerializedName("sensor") val sensor: Boolean = false
)

data class ValveItem(
    @SerializedName("id") val id: Int = 0,
    @SerializedName("state") val state: String = "CLOSED",
    @SerializedName("selected") val selected: Boolean = false,
    @SerializedName("error") val error: Boolean = false
) {
    /**
     * Exact requested V5 status text: Opening, Open, Closing, Close
     */
    val displayStatusText: String
        get() = when (state.uppercase()) {
            "OPENING" -> "Opening"
            "OPEN" -> "Open"
            "CLOSING" -> "Closing"
            "CLOSED", "CLOSE" -> "Close"
            "STOPPED" -> "Stopped"
            else -> if (error) "Error" else state
        }
}

data class SwitchesMap(
    @SerializedName("s1") val s1: Boolean = false,
    @SerializedName("s2") val s2: Boolean = false,
    @SerializedName("s3") val s3: Boolean = false,
    @SerializedName("s4") val s4: Boolean = false
)

data class FaultRecord(
    @SerializedName("code") val code: String = "",
    @SerializedName("device") val device: String = "",
    @SerializedName("source") val source: String = "",
    @SerializedName("severity") val severity: String = "warning",
    @SerializedName("message") val message: String = "",
    @SerializedName("cause") val cause: String = "",
    @SerializedName("steps") val steps: List<String> = emptyList(),
    @SerializedName("active") val active: Boolean = true,
    @SerializedName("first_seen") val firstSeen: Double = 0.0,
    @SerializedName("last_seen") val lastSeen: Double = 0.0
)

data class ControlRequest(
    @SerializedName("command") val command: String? = null,
    @SerializedName("tankSelection") val tankSelection: SwitchesMap? = null
)

data class ControlResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("command") val command: String? = null,
    @SerializedName("sequence") val sequence: Int = 0,
    @SerializedName("error") val error: String? = null
)

data class HealthResponse(
    @SerializedName("success") val success: Boolean = false,
    @SerializedName("service") val service: String = "",
    @SerializedName("timestamp") val timestamp: Double = 0.0
)

