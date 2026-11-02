package com.nubeera.watertankv5.ui.adapter

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.nubeera.watertankv5.R
import com.nubeera.watertankv5.data.model.FaultRecord

class FaultAdapter(private val faults: List<FaultRecord>) :
    RecyclerView.Adapter<FaultAdapter.FaultViewHolder>() {

    class FaultViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvTitle: TextView = view.findViewById(R.id.tvFaultTitle)
        val tvSeverity: TextView = view.findViewById(R.id.tvFaultSeverity)
        val tvMeta: TextView = view.findViewById(R.id.tvFaultMeta)
        val tvCause: TextView = view.findViewById(R.id.tvFaultCause)
        val tvSteps: TextView = view.findViewById(R.id.tvFaultSteps)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): FaultViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_fault_card, parent, false)
        return FaultViewHolder(view)
    }

    override fun onBindViewHolder(holder: FaultViewHolder, position: Int) {
        val fault = faults[position]
        holder.tvTitle.text = fault.message.ifBlank { fault.code }
        holder.tvSeverity.text = fault.severity.uppercase()
        holder.tvMeta.text = "Device: ${fault.device.uppercase()} | Code: ${fault.code}"
        holder.tvCause.text = "Possible Cause: ${fault.cause}"

        if (fault.steps.isNotEmpty()) {
            val stepsText = fault.steps.mapIndexed { index, step -> "${index + 1}. $step" }
                .joinToString("\n")
            holder.tvSteps.text = "Troubleshooting Steps:\n$stepsText"
            holder.tvSteps.visibility = View.VISIBLE
        } else {
            holder.tvSteps.visibility = View.GONE
        }
    }

    override fun getItemCount(): Int = faults.size
}

