package com.nubeera.watertankv5.ui

import android.graphics.Color
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.android.material.appbar.MaterialToolbar
import com.nubeera.watertankv5.R
import com.nubeera.watertankv5.data.PreferencesManager
import com.nubeera.watertankv5.data.api.ApiClient
import com.nubeera.watertankv5.databinding.ActivitySettingsBinding
import kotlinx.coroutines.launch

class SettingsActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySettingsBinding
    private lateinit var prefs: PreferencesManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivitySettingsBinding.inflate(layoutInflater)
        setContentView(binding.root)

        prefs = PreferencesManager(this)

        val toolbar = findViewById<MaterialToolbar>(R.id.toolbarSettings)
        toolbar.setNavigationOnClickListener { finish() }

        binding.etServerUrl.setText(prefs.serverUrl)

        binding.btnTestConnection.setOnClickListener {
            testConnection()
        }

        binding.btnSaveSettings.setOnClickListener {
            saveSettings()
        }
    }

    private fun testConnection() {
        val inputUrl = binding.etServerUrl.text.toString().trim()
        if (inputUrl.isEmpty()) {
            binding.tvTestResult.text = "Please enter a valid URL"
            binding.tvTestResult.setTextColor(Color.RED)
            return
        }

        binding.tvTestResult.text = "Connecting..."
        binding.tvTestResult.setTextColor(Color.DKGRAY)

        lifecycleScope.launch {
            try {
                val api = ApiClient.getService(inputUrl)
                val response = api.checkHealth()
                if (response.isSuccessful && response.body()?.success == true) {
                    binding.tvTestResult.text = "Success! Server is reachable (${response.body()?.service})"
                    binding.tvTestResult.setTextColor(Color.parseColor("#16A34A"))
                } else {
                    binding.tvTestResult.text = "HTTP Error: ${response.code()}"
                    binding.tvTestResult.setTextColor(Color.RED)
                }
            } catch (e: Exception) {
                binding.tvTestResult.text = "Connection Failed: ${e.localizedMessage}"
                binding.tvTestResult.setTextColor(Color.RED)
            }
        }
    }

    private fun saveSettings() {
        val inputUrl = binding.etServerUrl.text.toString().trim()
        if (inputUrl.isNotEmpty()) {
            prefs.serverUrl = inputUrl
            Toast.makeText(this, "Server URL saved", Toast.LENGTH_SHORT).show()
            finish()
        }
    }
}

