package com.nubeera.watertankv5.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.google.android.material.appbar.MaterialToolbar
import com.nubeera.watertankv5.R
import com.nubeera.watertankv5.data.PreferencesManager
import com.nubeera.watertankv5.data.api.ApiClient
import com.nubeera.watertankv5.databinding.ActivityFaultsBinding
import com.nubeera.watertankv5.ui.adapter.FaultAdapter
import kotlinx.coroutines.launch

class FaultsActivity : AppCompatActivity() {

    private lateinit var binding: ActivityFaultsBinding
    private lateinit var prefs: PreferencesManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityFaultsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = PreferencesManager(this)

        val toolbar = findViewById<MaterialToolbar>(R.id.toolbarFaults)
        toolbar.setNavigationOnClickListener { finish() }

        binding.rvFaults.layoutManager = LinearLayoutManager(this)

        loadFaults()
    }

    private fun loadFaults() {
        lifecycleScope.launch {
            try {
                val api = ApiClient.getService(prefs.serverUrl)
                val response = api.getDashboardData()
                if (response.isSuccessful) {
                    val faults = response.body()?.faults ?: emptyList()
                    binding.rvFaults.adapter = FaultAdapter(faults)
                }
            } catch (ignored: Exception) {
            }
        }
    }
}

