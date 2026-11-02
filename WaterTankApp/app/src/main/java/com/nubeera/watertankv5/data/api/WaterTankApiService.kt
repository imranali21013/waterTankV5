package com.nubeera.watertankv5.data.api

import com.nubeera.watertankv5.data.model.ControlRequest
import com.nubeera.watertankv5.data.model.ControlResponse
import com.nubeera.watertankv5.data.model.DashboardResponse
import com.nubeera.watertankv5.data.model.HealthResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface WaterTankApiService {

    @GET("api/dashboard")
    suspend fun getDashboardData(): Response<DashboardResponse>

    @POST("api/control")
    suspend fun sendControlCommand(
        @Body request: ControlRequest
    ): Response<ControlResponse>

    @GET("api/health")
    suspend fun checkHealth(): Response<HealthResponse>
}

