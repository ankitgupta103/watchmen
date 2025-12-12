// ESP32 Arduino sketch
// - Pull GPIO21 and GPIO22 LOW
// - Use UART on GPIO16 (RX) and GPIO17 (TX) at 115200 baud
// - Set Serial2 timeout = 2000 ms
// - Blink LED when data goes IN or OUT of UART

const int PIN_D21 = 21; // D21 -> GPIO21
const int PIN_D22 = 22; // D22 -> GPIO22

// UART pins for Serial2
const int UART2_RX_PIN = 16; // external device TX -> ESP32 RX (GPIO16)
const int UART2_TX_PIN = 17; // external device RX <- ESP32 TX (GPIO17)

const int LED_PIN = 2;     // On-board LED on most ESP32 dev boards
const int LED_BLINK_TIME = 10;  // ms LED stays ON per activity

unsigned long ledOffTime = 0;   // timestamp for turning LED off

void blinkLED() {
  digitalWrite(LED_PIN, HIGH);
  ledOffTime = millis() + LED_BLINK_TIME;
}

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  pinMode(PIN_D21, OUTPUT);
  pinMode(PIN_D22, OUTPUT);
  digitalWrite(PIN_D21, LOW);
  digitalWrite(PIN_D22, LOW);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println();
  Serial.println("ESP32 UART (Serial2) example with LED blink activity");

  Serial2.begin(115200, SERIAL_8N1, UART2_RX_PIN, UART2_TX_PIN);
  Serial2.setTimeout(2000);

  Serial.println("Serial2 started @115200, timeout=2000 ms");
}

void loop() {
  // Turn LED OFF when timeout expires
  if (millis() > ledOffTime) {
    digitalWrite(LED_PIN, LOW);
  }

  // UART → USB
  if (Serial2.available()) {
    String inFromUART = Serial2.readString();
    Serial.print("[UART -> USB] ");
    Serial.println(inFromUART);

    blinkLED();   // blink LED on RX activity
  }

  // USB → UART
  if (Serial.available()) {
    String outToUART = Serial.readStringUntil('\n');

    Serial2.print(outToUART);
    Serial2.print('\n');

    Serial.print("[USB -> UART] ");
    Serial.println(outToUART);

    blinkLED();   // blink LED on TX activity
  }

  delay(10);
}
