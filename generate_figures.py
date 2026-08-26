from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


OUT = Path(__file__).resolve().parent


# Figure 1: system-level inference from two published facts.
t = np.linspace(0, 1.8, 1000)
mcu_reset = (t < 0.42).astype(float)
pwm_pin_voltage = np.piecewise(
    t,
    [t < 0.42, (t >= 0.42) & (t < 0.75), t >= 0.75],
    [np.nan, 0.0, 2.0],
)
pump_command = np.piecewise(
    t,
    [t < 0.42, (t >= 0.42) & (t < 0.75), t >= 0.75],
    [100.0, 0.0, 40.0],
)

fig, axes = plt.subplots(3, 1, figsize=(11, 7.2), sharex=True,
                         gridspec_kw={"height_ratios": [1, 1, 1.2]})
axes[0].fill_between(t, 0, mcu_reset, step="pre", color="#B8C0FF")
axes[0].set_yticks([0, 1], ["firmware", "reset / Hi-Z"])
axes[0].set_ylim(-0.1, 1.1)
axes[0].set_title("Unsafe startup inference: floating PWM can become a full-speed command",
                  fontsize=14, pad=10)

axes[1].plot(t, pwm_pin_voltage, color="#005F73", linewidth=2.5)
axes[1].axhspan(0, 0.25, color="#94D2BD", alpha=0.35, label="published stop band: 0–0.25 V")
axes[1].axhspan(4.5, 5.0, color="#EE9B00", alpha=0.25, label="published full-speed band: 4.5–5 V")
axes[1].text(0.12, 2.8, "floating / undefined voltage\n(external circuit decides)",
             ha="center", fontsize=9, color="#7F1D1D")
axes[1].set_ylabel("PWM pin (V)")
axes[1].set_ylim(-0.2, 5.2)
axes[1].legend(loc="upper right", fontsize=9)

axes[2].step(t, pump_command, where="pre", color="#9B2226", linewidth=2.6)
axes[2].set_ylabel("interpreted\ncommand (%)")
axes[2].set_xlabel("Time after power is applied (s)")
axes[2].set_ylim(-5, 105)
axes[2].annotate("uncommanded full speed", xy=(0.20, 100), xytext=(0.48, 78),
                 arrowprops={"arrowstyle": "->", "color": "#9B2226"},
                 color="#9B2226", fontsize=10)
axes[2].annotate("firmware finally drives stop", xy=(0.48, 0), xytext=(0.80, 20),
                 arrowprops={"arrowstyle": "->", "color": "#005F73"},
                 color="#005F73", fontsize=10)
axes[2].annotate("controlled run", xy=(1.15, 40), xytext=(1.35, 62),
                 arrowprops={"arrowstyle": "->", "color": "#0A9396"},
                 color="#0A9396", fontsize=10)

for ax in axes:
    ax.grid(True, alpha=0.22)

fig.text(0.01, 0.01,
         "Illustrative timing diagram. Confirm the selected MCU reset state and the selected pump's formal interface specification.",
         fontsize=8.8, color="#555555")
plt.tight_layout(rect=(0, 0.035, 1, 1))
plt.savefig(OUT / "figure-1-hiz-full-speed-startup.png", dpi=180, bbox_inches="tight")
plt.close(fig)


# Figure 2: FG feedback, derived RPM and timeout fault injection.
dt = 0.002
t = np.arange(0.0, 3.6, dt)
duty = np.zeros_like(t)
duty[(t >= 0.55) & (t < 3.1)] = 50.0

rpm_true = np.zeros_like(t)
run = (t >= 0.72) & (t < 2.40)
rpm_true[run] = 3000.0

# Three FG pulses per revolution -> f_FG = RPM / 20.
fg_hz = rpm_true / 20.0
phase = np.cumsum(fg_hz * dt)
fg_edges = np.where(np.diff(np.floor(phase), prepend=np.floor(phase[0])) > 0)[0]

estimated_rpm = np.full_like(t, np.nan)
validated_rpm = np.full_like(t, np.nan)
last_edge_time = None
last_period = None
edge_iter = iter(fg_edges)
next_edge = next(edge_iter, None)
fault = np.zeros_like(t, dtype=bool)
startup_grace_s = 0.30
timeout_s = 0.16
run_command_time = 0.55

for i, now in enumerate(t):
    if next_edge is not None and i == next_edge:
        if last_edge_time is not None:
            last_period = now - last_edge_time
        last_edge_time = now
        next_edge = next(edge_iter, None)
    if last_period:
        estimated_rpm[i] = 20.0 / last_period
        if last_edge_time is not None and now - last_edge_time <= timeout_s:
            validated_rpm[i] = estimated_rpm[i]
    if duty[i] > 0 and now > run_command_time + startup_grace_s:
        no_recent_edge = last_edge_time is None or now - last_edge_time > timeout_s
        fault[i] = no_recent_edge

fig, axes = plt.subplots(3, 1, figsize=(11, 7.4), sharex=True,
                         gridspec_kw={"height_ratios": [1, 1.25, 1]})
axes[0].step(t, duty, where="post", linewidth=2.3, color="#005F73")
axes[0].axvspan(run_command_time, run_command_time + startup_grace_s,
                color="#E9D8A6", alpha=0.6, label="startup grace")
axes[0].set_ylabel("PWM duty (%)")
axes[0].set_ylim(-5, 105)
axes[0].legend(loc="upper right")

axes[1].plot(t, rpm_true, linewidth=2.2, color="#0A9396", label="simulated rotor RPM")
axes[1].plot(t, estimated_rpm, linestyle="--", linewidth=1.35, color="#EE9B00", alpha=0.85,
             label="naive last-period estimate (becomes stale)")
axes[1].plot(t, validated_rpm, linewidth=2.0, color="#7B2CBF",
             label="estimate invalidated after FG timeout")
axes[1].vlines(t[fg_edges], 0, 320, color="#3D405B", alpha=0.18, linewidth=0.6,
               label="FG edges")
axes[1].set_ylabel("RPM")
axes[1].set_ylim(-100, 3500)
axes[1].legend(loc="upper right", fontsize=9)

axes[2].fill_between(t, 0, fault.astype(int), step="post", color="#BB3E03", alpha=0.7)
axes[2].set_yticks([0, 1], ["monitoring", "FG timeout"])
axes[2].set_ylim(-0.1, 1.1)
axes[2].set_xlabel("Time (s)")
axes[2].annotate("motor/FG fault candidate", xy=(2.58, 1), xytext=(2.80, 0.45),
                 arrowprops={"arrowstyle": "->", "color": "#9B2226"},
                 color="#9B2226", fontsize=10)

axes[0].set_title("Fault injection: run command remains high after FG pulses disappear",
                  fontsize=14, pad=10)
for ax in axes:
    ax.grid(True, alpha=0.22)

fig.text(0.01, 0.01,
         "Synthetic trace. FG timeout indicates a motor/feedback fault candidate; it does not by itself prove a blocked liquid path.",
         fontsize=8.8, color="#555555")
plt.tight_layout(rect=(0, 0.035, 1, 1))
plt.savefig(OUT / "figure-2-fg-timeout-fault-injection.png", dpi=180, bbox_inches="tight")
plt.close(fig)


print("wrote figure-1-hiz-full-speed-startup.png")
print("wrote figure-2-fg-timeout-fault-injection.png")
