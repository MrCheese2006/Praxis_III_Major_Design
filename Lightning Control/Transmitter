#include <RH_ASK.h>
#include <SPI.h>

const int BUTTON_PIN = 15;

// RH_ASK(speed, rxPin, txPin, pttPin, pttInverted)
// transmitter only, so rxPin is unused here
RH_ASK driver(2000, 255, 16, 255, false);

void setup() {
  // driver.init();
  Serial.begin(9600);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  if (!driver.init()) {
    Serial.println("RF init failed");
  } else {
    Serial.println("Transmitter ready");
  }
}

void loop() {
  static bool lastButtonState = HIGH;
  bool buttonState = digitalRead(BUTTON_PIN);

  // Send once when button is pressed
  if (lastButtonState == HIGH && buttonState == LOW) {
    const char *msg = "Fire";

    for (int i = 0; i < 5; i++) {
      driver.send((uint8_t *)msg, strlen(msg) + 1);
      driver.waitPacketSent();
      delay(50);
    }

    Serial.println("Sent: Fire");
    delay(200); // debounce
  }

  lastButtonState = buttonState;
}