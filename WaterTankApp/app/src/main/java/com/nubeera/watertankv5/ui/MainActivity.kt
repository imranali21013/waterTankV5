package com.nubeera.watertankv5.ui

import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import android.widget.Toast
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.nubeera.watertankv5.R
import com.nubeera.watertankv5.data.model.DashboardResponse
import com.nubeera.watertankv5.data.model.ValveItem
import com.nubeera.watertankv5.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val viewModel: MainViewModel by viewModels()

    private var isUpdatingSwitches = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setupListeners()
        observeViewModel()
    }

    override fun onResume() {
        super.onResume()
        viewModel.startPolling()
    }

    override fun onPause() {
        super.onPause()
        viewModel.stopPolling()
    }

    private fun setupListeners() {
        binding.swipeRefresh.setOnRefreshListener {
            viewModel.refreshManually()
            binding.swipeRefresh.isRefreshing = false
        }

        binding.btnSettings.setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class.java))
        }

        binding.cardFaults.setOnClickListener {
            startActivity(Intent(this, FaultsActivity::class.java))
        }

        binding.btnStartFilling.setOnClickListener {
            viewModel.sendStartCommand()
        }

        binding.btnStopAll.setOnClickListener {
            viewModel.sendStopCommand()
        }

        // Selection switches
        val onSwitchChanged = {
            if (!isUpdatingSwitches) {
                viewModel.setTankSelection(
                    s1 = binding.switchTank1.isChecked,
                    s2 = binding.switchTank2.isChecked,
                    s3 = binding.switchTank3.isChecked,
                    s4 = binding.switchTank4.isChecked
                )
            }
        }

        binding.switchTank1.setOnCheckedChangeListener { _, _ -> onSwitchChanged() }
        binding.switchTank2.setOnCheckedChangeListener { _, _ -> onSwitchChanged() }
        binding.switchTank3.setOnCheckedChangeListener { _, _ -> onSwitchChanged() }
        binding.switchTank4.setOnCheckedChangeListener { _, _ -> onSwitchChanged() }
    }

    private fun observeViewModel() {
        viewModel.isConnected.observe(this) { connected ->
            if (connected) {
                binding.tvConnectionStatus.text = "ONLINE"
                binding.tvConnectionStatus.setBackgroundResource(R.drawable.bg_badge_open)
                binding.tvConnectionStatus.setTextColor(ContextCompat.getColor(this, R.color.status_online))
                binding.tvFlaskServerState.text = "CONNECTED"
                binding.tvFlaskServerState.setTextColor(ContextCompat.getColor(this, R.color.status_online))
            } else {
                binding.tvConnectionStatus.text = "OFFLINE"
                binding.tvConnectionStatus.setBackgroundResource(R.drawable.bg_badge_error)
                binding.tvConnectionStatus.setTextColor(ContextCompat.getColor(this, R.color.status_offline))
                binding.tvFlaskServerState.text = "DISCONNECTED"
                binding.tvFlaskServerState.setTextColor(ContextCompat.getColor(this, R.color.status_offline))
            }
        }

        viewModel.dashboardData.observe(this) { data ->
            data?.let { renderDashboard(it) }
        }

        viewModel.statusMessage.observe(this) { msg ->
            msg?.let {
                Toast.makeText(this, it, Toast.LENGTH_SHORT).show()
                viewModel.clearStatusMessage()
            }
        }
    }

    private fun renderDashboard(data: DashboardResponse) {
        // System Status
        binding.tvSystemState.text = data.controller?.state ?: "OFFLINE"
        val pumpRunning = data.pump?.running == true
        binding.tvPumpState.text = if (pumpRunning) "ON" else "OFF"
        binding.tvPumpState.setTextColor(
            ContextCompat.getColor(this, if (pumpRunning) R.color.status_online else R.color.text_secondary)
        )

        val active = data.controller?.activeTank ?: 0
        binding.tvActiveTank.text = if (active > 0) "Tank $active" else "-"

        // ESP32 Devices
        binding.tvMasterIp.text = data.master?.ip ?: "--"
        binding.tvMasterBadge.text = if (data.master?.online == true) "ONLINE" else "OFFLINE"
        binding.tvMasterBadge.setTextColor(
            ContextCompat.getColor(this, if (data.master?.online == true) R.color.status_online else R.color.status_offline)
        )

        binding.tvSlave1Ip.text = data.slave1?.ip ?: "--"
        binding.tvSlave1Badge.text = if (data.slave1?.online == true) "ONLINE" else "OFFLINE"
        binding.tvSlave1Badge.setTextColor(
            ContextCompat.getColor(this, if (data.slave1?.online == true) R.color.status_online else R.color.status_offline)
        )

        binding.tvSlave2Ip.text = data.slave2?.ip ?: "--"
        binding.tvSlave2Badge.text = if (data.slave2?.online == true) "ONLINE" else "OFFLINE"
        binding.tvSlave2Badge.setTextColor(
            ContextCompat.getColor(this, if (data.slave2?.online == true) R.color.status_online else R.color.status_offline)
        )

        // Tank Levels
        data.tank1?.let {
            binding.progressTank1.progress = it.level.coerceIn(0, 100)
            binding.tvTank1Percent.text = "${it.level}%"
            val dist = if (it.distance >= 0) "${it.distance} cm" else "-- cm"
            binding.tvTank1Distance.text = "Distance: $dist | Sensor: ${if (it.sensor) "OK" else "ERROR"}"
        }

        data.tank2?.let {
            binding.progressTank2.progress = it.level.coerceIn(0, 100)
            binding.tvTank2Percent.text = "${it.level}%"
            val dist = if (it.distance >= 0) "${it.distance} cm" else "-- cm"
            binding.tvTank2Distance.text = "Distance: $dist | Sensor: ${if (it.sensor) "OK" else "ERROR"}"
        }

        data.tank3?.let {
            binding.progressTank3.progress = it.level.coerceIn(0, 100)
            binding.tvTank3Percent.text = "${it.level}%"
            val dist = if (it.distance >= 0) "${it.distance} cm" else "-- cm"
            binding.tvTank3Distance.text = "Distance: $dist | Sensor: ${if (it.sensor) "OK" else "ERROR"}"
        }

        data.tank4?.let {
            binding.progressTank4.progress = it.level.coerceIn(0, 100)
            binding.tvTank4Percent.text = "${it.level}%"
            val dist = if (it.distance >= 0) "${it.distance} cm" else "-- cm"
            binding.tvTank4Distance.text = "Distance: $dist | Sensor: ${if (it.sensor) "OK" else "ERROR"}"
        }

        // Valve Statuses (Text: Opening, Open, Closing, Close)
        val valvesMap = data.valves.associateBy { it.id }
        updateValveBadge(binding.badgeValve1, valvesMap[1])
        updateValveBadge(binding.badgeValve2, valvesMap[2])
        updateValveBadge(binding.badgeValve3, valvesMap[3])
        updateValveBadge(binding.badgeValve4, valvesMap[4])

        // Tank Selection
        binding.tvSelectionSource.text = "Source: ${data.selectionSource}"
        data.switches?.let {
            isUpdatingSwitches = true
            binding.switchTank1.isChecked = it.s1
            binding.switchTank2.isChecked = it.s2
            binding.switchTank3.isChecked = it.s3
            binding.switchTank4.isChecked = it.s4
            isUpdatingSwitches = false
        }

        // Faults summary
        val faultCount = data.faults.count { it.active }
        binding.tvFaultSummary.text = if (faultCount > 0) {
            "$faultCount Active Fault(s) Detected - Tap to review"
        } else {
            "0 Active Faults (All Systems Operational)"
        }
    }

    private fun updateValveBadge(textView: TextView, valve: ValveItem?) {
        val stateText = valve?.displayStatusText ?: "Close"
        textView.text = stateText

        val (bgRes, textColorRes) = when (stateText) {
            "Open" -> Pair(R.drawable.bg_badge_open, R.color.valve_open_text)
            "Opening" -> Pair(R.drawable.bg_badge_opening, R.color.valve_opening_text)
            "Closing" -> Pair(R.drawable.bg_badge_closing, R.color.valve_closing_text)
            "Close" -> Pair(R.drawable.bg_badge_close, R.color.valve_close_text)
            else -> Pair(R.drawable.bg_badge_error, R.color.valve_error_text)
        }

        textView.setBackgroundResource(bgRes)
        textView.setTextColor(ContextCompat.getColor(this, textColorRes))
    }
}

