# Understanding RSSI and Noise Floor in LoRa (SX1262)

## What is RSSI?

**RSSI** (Received Signal Strength Indicator) is a measure of how strong a received signal is. It is usually represented in **dBm (decibels relative to 1 milliwatt)**.

- **Closer to 0 dBm** → Stronger signal
- **More negative** (e.g., -120 dBm) → Weaker signal

---

## Types of RSSI in SX1262 Output

Example Output:

- the packet rssi value: -12dBm  
- the current noise rssi value: -93dBm



### 1. **Packet RSSI**
- Represents the strength of the **received packet**.
- Example: `-12 dBm` → Very strong signal.

### 2. **Noise RSSI** (a.k.a Channel RSSI)
- Indicates the **ambient RF noise floor** on the channel.
- Example: `-93 dBm` → Low background noise.

---

## Typical RSSI Ranges for LoRa (868 MHz)

| RSSI (dBm)    | Signal Strength | Description                          |
|--------------|------------------|--------------------------------------|
| 0 to -30     | Excellent         | Device is very close                 |
| -30 to -60   | Good              | Strong, reliable signal              |
| -60 to -80   | Moderate          | Usable but with range limitations    |
| -80 to -100  | Weak              | May experience packet loss           |
| < -100       | Very Weak         | Likely unreliable or dropped packets |

---

## Understanding Noise Floor (Channel RSSI)

- Represents interference or idle noise on the frequency.
- Ideal range for **LoRa Noise Floor**: `-120 dBm to -90 dBm`
- If Noise RSSI > `-90 dBm`, there may be **interference**.

> The **greater the difference between packet RSSI and noise RSSI**, the better your link quality.

---

## SNR vs RSSI (Basic Concept)

> **SNR** (Signal-to-Noise Ratio) ≈ `Packet RSSI - Noise RSSI`

**Example:**
```text
SNR = -12 dBm (packet) - (-93 dBm noise) = 81 dB
```

## Simplified SNR Interpretation

> This is a **simplified interpretation**; actual **SNR** (Signal-to-Noise Ratio) is calculated differently at the **physical layer**.  
> However, this rough estimate gives good intuition for evaluating signal quality.

---

## What Are Good RSSI/Noise Values?

| **Metric**         | **Ideal Value**        |
|--------------------|------------------------|
| Packet RSSI        | > -80 dBm              |
| Noise RSSI         | < -90 dBm              |
| SNR                | > 10 dB                |
| Packet Delivery    | > 99% success rate     |

---

## Use Cases for RSSI and Noise Monitoring

### 1. Link Quality Monitoring
- Continuously log RSSI to monitor signal strength.
- Identify weak or failing links in the system.

### 2. Adaptive Power Control
- If RSSI is very strong (e.g., `-20 dBm`), reduce transmission power.
- Helps conserve power in battery-powered devices.

### 3. Channel Scanning
- Measure noise floor (Noise RSSI) across channels.
- Choose channels with **lowest interference** for optimal communication.

---

## Summary

| **Term**        | **Meaning**                                 | **Example**     |
|------------------|----------------------------------------------|------------------|
| Packet RSSI      | Signal strength of received packet           | `-12 dBm`        |
| Noise RSSI       | Ambient channel noise floor                  | `-93 dBm`        |
| Ideal Packet     | Greater than `-80 dBm`                       | `-30 to -60`     |
| Ideal Noise      | Less than `-90 dBm`                          | `-110 dBm`       |
| SNR              | Difference between Packet and Noise RSSI     | `> 10 dB`        |

---
