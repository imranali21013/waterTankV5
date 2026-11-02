package com.nubeera.watertankv5.ui

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.viewModelScope
import com.nubeera.watertankv5.data.PreferencesManager
import com.nubeera.watertankv5.data.api.ApiClient
import com.nubeera.watertankv5.data.model.ControlRequest
import com.nubeera.watertankv5.data.model.DashboardResponse
import com.nubeera.watertankv5.data.model.SwitchesMap
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = PreferencesManager(application)

    private val _dashboardData = MutableLiveData<DashboardResponse?>()
    val dashboardData: LiveData<DashboardResponse?> = _dashboardData

    private val _isConnected = MutableLiveData<Boolean>(false)
    val isConnected: LiveData<Boolean> = _isConnected

    private val _isBusy = MutableLiveData<Boolean>(false)
    val isBusy: LiveData<Boolean> = _isBusy

    private val _statusMessage = MutableLiveData<String?>()
    val statusMessage: LiveData<String?> = _statusMessage

    private var pollingJob: Job? = null

    init {
        startPolling()
    }

    fun startPolling() {
        pollingJob?.cancel()
        pollingJob = viewModelScope.launch {
            while (isActive) {
                fetchDashboard()
                delay(prefs.pollIntervalMs)
            }
        }
    }

    fun stopPolling() {
        pollingJob?.cancel()
    }

    fun refreshManually() {
        viewModelScope.launch {
            fetchDashboard()
        }
    }

    private suspend fun fetchDashboard() {
        try {
            val api = ApiClient.getService(prefs.serverUrl)
            val response = api.getDashboardData()
            if (response.isSuccessful && response.body() != null) {
                _dashboardData.postValue(response.body())
                _isConnected.postValue(true)
            } else {
                _isConnected.postValue(false)
            }
        } catch (e: Exception) {
            _isConnected.postValue(false)
        }
    }

    fun sendStartCommand() {
        sendCommand("START")
    }

    fun sendStopCommand() {
        sendCommand("STOP")
    }

    private fun sendCommand(command: String) {
        viewModelScope.launch {
            _isBusy.value = true
            try {
                val api = ApiClient.getService(prefs.serverUrl)
                val response = api.sendControlCommand(ControlRequest(command = command))
                if (response.isSuccessful && response.body()?.success == true) {
                    _statusMessage.postValue("$command command sent to system")
                    fetchDashboard()
                } else {
                    _statusMessage.postValue("Command $command failed")
                }
            } catch (e: Exception) {
                _statusMessage.postValue("Error: ${e.localizedMessage}")
            } finally {
                _isBusy.value = false
            }
        }
    }

    fun setTankSelection(s1: Boolean, s2: Boolean, s3: Boolean, s4: Boolean) {
        viewModelScope.launch {
            try {
                val api = ApiClient.getService(prefs.serverUrl)
                val selection = SwitchesMap(s1 = s1, s2 = s2, s3 = s3, s4 = s4)
                val response = api.sendControlCommand(ControlRequest(tankSelection = selection))
                if (response.isSuccessful && response.body()?.success == true) {
                    fetchDashboard()
                }
            } catch (e: Exception) {
                _statusMessage.postValue("Selection update failed: ${e.localizedMessage}")
            }
        }
    }

    fun clearStatusMessage() {
        _statusMessage.value = null
    }

    override fun onCleared() {
        super.onCleared()
        stopPolling()
    }
}

