# Estimating Distance from RSSI in LoRa

RSSI (Received Signal Strength Indicator) can be used to estimate distance between two LoRa modules, but the result is **approximate** due to many environmental factors.

---

## Formula: Log-Distance Path Loss Model

```
RSSI = -10 * n * log10(d) + A
```

Where:

- **RSSI**: Measured signal strength in dBm
- **n**: Path-loss exponent (depends on environment)
  - Free space: 2
  - Urban: 2.7–3.5
  - Indoor: 3–5
- **d**: Distance in meters
- **A**: RSSI at 1 meter distance (must be calibrated)

---

## Rearranged Formula (Distance from RSSI):

```
d = 10^((A - RSSI) / (10 * n))
```

---

## Example Calculation

Given:

- RSSI = -80 dBm
- n = 2.7
- A = -40 dBm

\[
d = 10^{( -40 - (-80) ) / (10 * 2.7)} = 10^{40 / 27} ≈ 49 meters
\]

---

## Python Example

```python
import math

def estimate_distance(rssi, A=-40, n=2.7):
    return 10 ** ((A - rssi) / (10 * n))

# Example
print("Estimated distance:", estimate_distance(-80), "meters")
```

---

## How to Measure A (RSSI at 1 Meter)

1. Place transmitter and receiver 1 meter apart in open space.
2. Send test packet and log RSSI.
3. Use this value as `A`.

---

## Limitations

| Factor             | Effect on Accuracy |
|--------------------|--------------------|
| Multipath fading   | Reflections distort signal |
| Obstacles          | Walls, people, trees impact signal |
| Device variability | Different hardware and antennas affect RSSI |
| Environment        | Weather, humidity, terrain impact signal |
| Non-linearity      | RSSI doesn’t drop linearly with distance |

---

## Better Alternatives

- **ToF (Time of Flight)** or **TDoA (Time Difference of Arrival)** if your hardware supports it
- Use **averaged RSSI** over multiple packets for better results

---

_Use this method for **coarse estimation only** — not for precise localization._
```
RSSI = -10 * n * log10(d) + A
```

Where:

- **RSSI**: Measured signal strength in dBm
- **n**: Path-loss exponent (depends on environment)
  - Free space: 2
  - Urban: 2.7–3.5
  - Indoor: 3–5
- **d**: Distance in meters
- **A**: RSSI at 1 meter distance (must be calibrated)

---

## Rearranged Formula (Distance from RSSI):

```
d = 10^((A - RSSI) / (10 * n))
```

---

## Example Calculation

Given:

- RSSI = -80 dBm
- n = 2.7
- A = -40 dBm

\[
d = 10^{( -40 - (-80) ) / (10 * 2.7)} = 10^{40 / 27} ≈ 49 meters
\]

---

## Python Example

```python
import math

def estimate_distance(rssi, A=-40, n=2.7):
    return 10 ** ((A - rssi) / (10 * n))

# Example
print("Estimated distance:", estimate_distance(-80), "meters")
```

---

## How to Measure A (RSSI at 1 Meter)

1. Place transmitter and receiver 1 meter apart in open space.
2. Send test packet and log RSSI.
3. Use this value as `A`.

---

## Limitations

| Factor             | Effect on Accuracy |
|--------------------|--------------------|
| Multipath fading   | Reflections distort signal |
| Obstacles          | Walls, people, trees impact signal |
| Device variability | Different hardware and antennas affect RSSI |
| Environment        | Weather, humidity, terrain impact signal |
| Non-linearity      | RSSI doesn’t drop linearly with distance |

---

## Better Alternatives

- **ToF (Time of Flight)** or **TDoA (Time Difference of Arrival)** if your hardware supports it
- Use **averaged RSSI** over multiple packets for better results

---

_Use this method for **coarse estimation only** — not for precise localization._