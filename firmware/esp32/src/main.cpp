/**
 * Living Light System — ESP32 Controller
 *
 * Receives newline-delimited commands over serial from the Pi.
 * Controls LED PWM dimming and pump relay.
 *
 * Commands:
 *   LIGHT <0..255>   Set LED brightness
 *   PUMP <0|1>       Toggle pump relay
 *   STATUS           Report current state as JSON
 */

#include <Arduino.h>
#include "commands.h"
#include "pwm_control.h"

#ifndef LED_PWM_PIN
#define LED_PWM_PIN 18
#endif

#ifndef PUMP_RELAY_PIN
#define PUMP_RELAY_PIN 17
#endif

static String input_buffer = "";

void setup() {
    Serial.begin(115200);
    while (!Serial) { delay(10); }

    // Initialize PWM for LED control
    pwm_init(LED_PWM_PIN);

    // Initialize pump relay pin
    pinMode(PUMP_RELAY_PIN, OUTPUT);
    digitalWrite(PUMP_RELAY_PIN, LOW);

    Serial.println("{\"event\":\"boot\",\"version\":\"0.1.0\"}");
}

void loop() {
    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n') {
            if (input_buffer.length() > 0) {
                command_dispatch(input_buffer);
                input_buffer = "";
            }
        } else if (c != '\r') {
            input_buffer += c;
            // Prevent buffer overflow
            if (input_buffer.length() > 64) {
                Serial.println("{\"error\":\"command too long\"}");
                input_buffer = "";
            }
        }
    }
}
