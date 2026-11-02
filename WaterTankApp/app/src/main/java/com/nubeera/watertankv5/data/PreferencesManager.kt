package com.nubeera.watertankv5.data

import android.content.Context
import android.content.SharedPreferences

class PreferencesManager(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("water_tank_v5_prefs", Context.MODE_PRIVATE)

    companion object {
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_POLL_INTERVAL = "poll_interval_ms"
        const val DEFAULT_SERVER_URL = "http://water.nubeera.com"
        const val DEFAULT_POLL_INTERVAL = 1000L
    }

    var serverUrl: String
        get() {
            val url = prefs.getString(KEY_SERVER_URL, DEFAULT_SERVER_URL) ?: DEFAULT_SERVER_URL
            return if (url.endsWith("/")) url else "$url/"
        }
        set(value) {
            val formatted = value.trim()
            val finalUrl = if (formatted.startsWith("http://") || formatted.startsWith("https://")) {
                formatted
            } else {
                "http://$formatted"
            }
            prefs.edit().putString(KEY_SERVER_URL, finalUrl).apply()
        }

    var pollIntervalMs: Long
        get() = prefs.getLong(KEY_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        set(value) = prefs.edit().putLong(KEY_POLL_INTERVAL, value).apply()
}

