# ESP32-C3 firmware reliability and functional validation

Based on upstream v2.1.0, commit abc0adc. This is a development branch, not a released firmware.

The scope is ordinary embedded firmware quality assurance on the maintainer's own ESP32-C3 test hardware: diagnose software panics and resets, improve resource management and verify normal operation under repeated workloads. Upstream issue #69 is a reference for similar symptoms on a different ESP32 variant, not proof of a common root cause.

- Save the configuration JSON and record the current device counter before flashing. Do not erase NVS or restore an older counter as part of diagnosis.
- Use the existing valid C3 wiring. GPIO 11–19 and nonexistent GPIOs are rejected for the radio on the C3; fix the configuration before enabling the radio. The fork does not guess replacement pins. Board profile migration needs a build and board-specific verification.
- Retained MQTT commands are ignored on replay; retained Home Assistant availability remains supported.
- C3 memory diagnostics appear over USB serial every 30 seconds while no positioning or OTA operation is active. Values are bytes; loopStackMin is the task high-water mark.
- The firmware still identifies itself as v2.1.0 until a separate release is approved. GitHub OTA is restricted to this fork.

## Local verification

```sh
pio run -e esp32c3
python3 tests/run_tests.py
pio device monitor -e esp32c3 --port /dev/ttyACM0
```

Use the actual serial device. Keep .pio/build/esp32c3/firmware.elf and firmware.map alongside the matching OTA image for panic decoding; never use an ELF from a different build. Test local MQTT broker disconnect/reconnect, normal broker delivery of stored messages at subscription time, full log refresh, radio reception under normal noise conditions and prolonged idle separately. Do not connect motors to an unverified build for initial smoke testing.

The firmware build and full host suite have not yet been executed for this branch. An issue #69 crash cannot be assigned to a source line without the matching ELF. The rolling-counter write ordering and SPI lifecycle need additional dedicated analysis and hardware tests; they are not modified here.
