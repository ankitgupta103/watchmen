# 10KB Data Transfer Test (Without ACK)

This test sends 10KB of data without per-packet ACK protocol. Uses retransmission based on missing packet list.

## How It Works

1. **TX**: Sends all packets sequentially without waiting for ACK
2. **RX**: Receives packets and tracks which sequence numbers are missing/corrupted
3. **RX**: Sends back list of missing packet sequence numbers
4. **TX**: Retransmits only the missing packets
5. **RX**: Receives retransmitted packets

## Configuration

- Spreading Factor: 5
- Bandwidth: 500 kHz
- Coding Rate: 5 (4/5)
- Preamble Length: 8
- Frequency: 868.0 MHz
- CRC: Enabled

## Usage

1. Start receiver: `import rx_10kb_test`
2. Start transmitter: `import tx_10kb_test`

## Output

- TX: Shows transmission time and retransmission time
- RX: Shows received packets count and missing packets count

