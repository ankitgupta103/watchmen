"""

using sensor.sleep() + machine.idle() for power saving mode and state change

Power Saving
1. sensor.sleep() - Puts camera sensor to sleep (saves ~20-30mA)
2. machine.idle() - Halts CPU while keeping peripherals active (saves ~50-80mA)
3. Combined: ~50-80mA total power consumption (vs ~130mA active)
4. RAM is maintained (unlike deep sleep which resets)

"""

import time
import machine
import sensor



PIR_PIN = 'P13'
ACTIVE_DELAY_SEC = 5  # Stay active for 5 seconds after motion stops
IDLE_CHECK_INTERVAL_MS = 100  # Check PIR every 100ms when in idle mode

pir = machine.Pin(PIR_PIN, machine.Pin.IN, machine.Pin.PULL_DOWN)    # init P13 as input

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
print("Camera sensor initialized")

def main():

    print("PIR Low Power Mode Started")
    print(f"PIR Pin: {PIR_PIN}")
    print(f"Active delay: {ACTIVE_DELAY_SEC} seconds after motion stops")
    print("=" * 60)

    while True:
        # Check PIR sensor state
        pir_value = pir.value()

        if pir_value == 1:


            while pir.value() == 1:     # Stay active while motion is detected
                img = sensor.snapshot()     # sensor.snapshot() automatically wakeup the camera sensor
                print(f"Frame captured")
                time.sleep_ms(100)  # Small delay to avoid busy loop


            print(f"Motion stopped. Active for {ACTIVE_DELAY_SEC} more seconds...")
            time.sleep(ACTIVE_DELAY_SEC)               # Wait 5 seconds before going to low-power mode

            # Put camera sensor to sleep to save power
            sensor.sleep(True)
            print("Camera sensor sleeping")


            # Re-check PIR after delay - if still 0, will enter idle mode
            continue  # Go back to top of loop to check PIR again

        # PIR = 0 (no motion) - use idle mode for low power
        # machine.idle() halts CPU but keeps peripherals active
        # Combine idle() with sleep() for better power savings
        print("No motion - Entering idle mode...")

        idle_start = time.ticks_ms()
        idle_count = 0

        while pir.value() == 0:
            # ============================================================
            # WHY CALL machine.idle() MULTIPLE TIMES (50 times)?
            # ============================================================
            # machine.idle() halts the CPU until an interrupt occurs.
            # However, on RT1062, idle() may return immediately if:
            # 1. There are pending interrupts (system timers, etc.)
            # 2. The idle implementation has overhead
            # 3. The CPU wakes up quickly from idle state
            #
            # By calling idle() 50 times in a loop, we ensure:
            # - CPU stays in idle state longer (better power savings)
            # - We handle cases where idle() returns quickly
            # - More time spent in low-power CPU halt state
            #
            # Reference: RT1062 doesn't support lightsleep(), so idle()
            # is the closest we can get to light sleep while maintaining state.
            # ============================================================
            for _ in range(50):  # Call idle multiple times
                machine.idle()

            # ============================================================
            # WHY USE time.sleep_ms(50) AFTER idle() CALLS?
            # ============================================================
            # time.sleep_ms() provides additional power savings by:
            # 1. Reducing CPU wake-up frequency - Without sleep, we'd wake
            #    up immediately after idle() returns, causing frequent CPU
            #    wake-ups and higher power consumption
            #
            # 2. Allowing peripherals to enter lower power states - The
            #    sleep delay gives time for other components to reduce power
            #
            # 3. Balancing responsiveness vs power - 50ms is short enough
            #    to respond quickly to PIR changes, but long enough to save
            #    significant power compared to continuous polling
            #
            # 4. Combined effect: idle() + sleep() = Better power savings
            #    than either alone. idle() halts CPU, sleep() reduces
            #    wake-up frequency. Together: ~50-80mA vs ~130mA active.
            #
            # Reference: Forum discussion mentioned using sensor.sleep(True),
            # machine.idle(), then time.sleep(n) for best power savings.
            # ============================================================
            time.sleep_ms(50)

            idle_count += 1

            # Periodically check PIR state (wake from idle to check)
            # Check every IDLE_CHECK_INTERVAL_MS (100ms) to balance
            # power savings with motion detection responsiveness
            elapsed = time.ticks_diff(time.ticks_ms(), idle_start)
            if elapsed >= IDLE_CHECK_INTERVAL_MS:
                # Break to check PIR state in main loop
                print(f"Idle check: PIR still 0 (idle cycles: {idle_count})")
                break

        if pir.value() == 1:
            print("Motion detected while in idle mode")



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        raise

