# Pump PWM/FG Startup Guard

A small, testable reference for one easy-to-miss embedded-fluidics failure:
the host MCU can still be in reset/high impedance while a pump control input
interprets a floating PWM line as a run command.

The repository accompanies the engineering article **“The code has not run,
but the pump is already at full speed.”** It provides:

- a deterministic startup/FG timeout guard in `pump_guard.py`;
- seven `unittest` checks in `test_pump_guard.py`;
- two reproducible synthetic timing figures;
- an explicit boundary between rotor feedback and proof of liquid flow.

## Public interface facts used in the example

The public
[FOREACH DPL30H selection and interface guide](https://www.foreachtek.com/en/resources/technical-articles/dpl30h-high-pressure-liquid-diaphragm-pump-selection-guide/)
states for the five-wire brushless example:

- PWM at 0–0.25 V stops the pump;
- floating PWM or 4.5–5 V commands full speed;
- FG outputs three square-wave pulses per rotor revolution.

Combining that interface behavior with a controller pin that is high impedance
during reset creates a **system-level risk hypothesis**. It is not a claim that
every controller board will exhibit the fault. The selected MCU, pin, pull
network, power sequence, formal pump interface specification, and bench
measurement must all be checked.

## Run

```bash
python pump_guard.py
python -m unittest -v test_pump_guard.py
```

Expected test summary:

```text
Ran 7 tests
OK
```

## FG conversion

With three FG pulses per revolution:

```text
RPM = 60 × f_FG / 3 = 20 × f_FG
RPM = 20 / T_FG
```

FG is rotor feedback. It does not, by itself, prove that liquid moved, flow was
correct, or the fluid path was unobstructed.

## Engineering boundaries

The public pages do not define a universal pull-down resistance, recommended
PWM frequency, 3.3 V logic compatibility, FG output topology, startup grace
period, or release threshold. Values in this repository are architecture and
fault-injection examples—not product release parameters.

## License

MIT. See `LICENSE`.
