import unittest

from pump_guard import GuardConfig, PumpGuard, State


class PumpGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = PumpGuard(
            GuardConfig(startup_grace_s=0.30, fg_timeout_s=0.16)
        )

    def test_run_is_blocked_before_safe_level_confirmation(self):
        with self.assertRaises(RuntimeError):
            self.guard.command_run(duty=0.5, now_s=0.0)

    def test_unconfirmed_3v3_is_not_treated_as_safe(self):
        with self.assertRaises(ValueError):
            self.guard.confirm_hardware_safe_level(3.3)

    def test_fg_edges_move_guard_to_run(self):
        self.guard.confirm_hardware_safe_level(0.10)
        self.guard.command_run(duty=0.5, now_s=0.0)
        for edge in [0.20, 0.206667, 0.213334]:
            self.guard.on_fg_edge(edge)
        self.assertEqual(self.guard.tick(0.31), State.RUN)

    def test_fg_period_converts_to_rpm(self):
        self.guard.on_fg_edge(1.000000)
        self.guard.on_fg_edge(1.006667)
        self.assertAlmostEqual(self.guard.rpm, 3000, delta=1)

    def test_fg_timeout_forces_zero_command(self):
        self.guard.confirm_hardware_safe_level(0.10)
        self.guard.command_run(duty=0.6, now_s=0.0)
        self.guard.on_fg_edge(0.20)
        self.assertEqual(self.guard.tick(0.40), State.FAULT_FG_TIMEOUT)
        self.assertEqual(self.guard.commanded_duty, 0.0)
        self.assertIsNone(self.guard.rpm)

    def test_watchdog_reset_returns_to_boot_hiz(self):
        self.guard.confirm_hardware_safe_level(0.10)
        self.guard.command_run(duty=0.5, now_s=0.0)
        self.guard.reset()
        self.assertEqual(self.guard.state, State.BOOT_HIZ)
        self.assertEqual(self.guard.commanded_duty, 0.0)

    def test_precommand_fg_is_not_reused_after_new_start(self):
        self.guard.on_fg_edge(0.900000)
        self.guard.on_fg_edge(0.906667)
        self.assertGreater(self.guard.rpm, 0)

        self.guard.confirm_hardware_safe_level(0.10)
        self.guard.command_run(duty=0.5, now_s=1.0)

        self.assertIsNone(self.guard.rpm)
        self.assertEqual(self.guard.tick(1.31), State.FAULT_FG_TIMEOUT)

    def test_fg_does_not_prove_liquid_flow(self):
        self.guard.on_fg_edge(1.000000)
        self.guard.on_fg_edge(1.006667)
        self.assertGreater(self.guard.rpm, 0)
        self.assertFalse(self.guard.flow_confirmed)


if __name__ == "__main__":
    unittest.main()
