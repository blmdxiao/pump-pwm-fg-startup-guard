from dataclasses import dataclass
from enum import Enum, auto


class State(Enum):
    BOOT_HIZ = auto()
    SAFE_LEVEL_CONFIRMED = auto()
    STARTUP_GRACE = auto()
    RUN = auto()
    FAULT_FG_TIMEOUT = auto()


@dataclass(frozen=True)
class GuardConfig:
    pulses_per_revolution: int = 3
    startup_grace_s: float = 0.30
    fg_timeout_s: float = 0.16
    published_stop_max_v: float = 0.25


class PumpGuard:
    """Architecture demo; thresholds are examples, not product release limits."""

    def __init__(self, config: GuardConfig = GuardConfig()):
        self.config = config
        self.reset()

    def reset(self):
        self.state = State.BOOT_HIZ
        self.commanded_duty = 0.0
        self.command_time_s = None
        self.last_fg_edge_s = None
        self.last_fg_period_s = None
        self._flow_confirmed = False

    def confirm_hardware_safe_level(self, measured_pwm_v: float):
        if not 0.0 <= measured_pwm_v <= self.config.published_stop_max_v:
            raise ValueError("PWM input has not been proven inside the published stop band.")
        self.state = State.SAFE_LEVEL_CONFIRMED

    def command_run(self, duty: float, now_s: float):
        if self.state is not State.SAFE_LEVEL_CONFIRMED:
            raise RuntimeError("Run is blocked until the hardware-safe PWM level is confirmed.")
        if not 0.0 < duty <= 1.0:
            raise ValueError("Duty must be in (0, 1].")
        # A new run command starts a new evidence window.  Edges captured before
        # this command must never authorize the new run or produce a fresh RPM.
        self.last_fg_edge_s = None
        self.last_fg_period_s = None
        self.commanded_duty = duty
        self.command_time_s = now_s
        self.state = State.STARTUP_GRACE

    def on_fg_edge(self, now_s: float):
        if self.last_fg_edge_s is not None:
            period = now_s - self.last_fg_edge_s
            if period <= 0:
                raise ValueError("FG timestamps must be strictly increasing.")
            self.last_fg_period_s = period
        self.last_fg_edge_s = now_s

    def tick(self, now_s: float):
        if self.state not in {State.STARTUP_GRACE, State.RUN}:
            return self.state

        age_from_command = now_s - self.command_time_s
        if self.state is State.STARTUP_GRACE and age_from_command <= self.config.startup_grace_s:
            return self.state

        fg_age = float("inf") if self.last_fg_edge_s is None else now_s - self.last_fg_edge_s
        if fg_age > self.config.fg_timeout_s:
            self.commanded_duty = 0.0
            self.last_fg_period_s = None
            self.state = State.FAULT_FG_TIMEOUT
        else:
            self.state = State.RUN
        return self.state

    @property
    def rpm(self):
        if self.last_fg_period_s is None or self.last_fg_edge_s is None:
            return None
        return 60.0 / (self.config.pulses_per_revolution * self.last_fg_period_s)

    @property
    def flow_confirmed(self):
        # FG is rotor feedback. No flow sensor/evidence exists in this demo.
        return self._flow_confirmed


if __name__ == "__main__":
    guard = PumpGuard()
    guard.confirm_hardware_safe_level(0.10)
    guard.command_run(duty=0.50, now_s=0.0)
    for edge in [0.10, 0.106667, 0.113334]:
        guard.on_fg_edge(edge)
    print("state:", guard.tick(0.20).name)
    print("estimated RPM:", round(guard.rpm))
    print("flow confirmed:", guard.flow_confirmed)
    print("after injected FG loss:", guard.tick(0.50).name)
