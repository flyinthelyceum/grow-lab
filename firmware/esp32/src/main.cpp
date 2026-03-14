/**
 * Living Light System — ESP32 Controller
 *
 * Receives newline-delimited commands over USB-Serial/JTAG from the Pi.
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
#include "jtag_serial.h"

#ifndef LED_PWM_PIN
#define LED_PWM_PIN 18
#endif

#ifndef PUMP_RELAY_PIN
#define PUMP_RELAY_PIN 17
#endif

// Freenove ESP32-S3 onboard RGB LED (WS2812) is on GPIO48.
// We use the built-in neopixelWrite() for a simple heartbeat.
static const uint8_t HEARTBEAT_PIN = 48;
static unsigned long last_heartbeat = 0;
static bool heartbeat_on = false;

JtagSerial usb;

void setup() {
    usb.begin();
    delay(200);

    // Initialize PWM for LED control
    pwm_init(LED_PWM_PIN);

    // Initialize pump relay pin
    pinMode(PUMP_RELAY_PIN, OUTPUT);
    digitalWrite(PUMP_RELAY_PIN, LOW);

    // Initial heartbeat pulse
    neopixelWrite(HEARTBEAT_PIN, 0, 4, 0);  // dim green

    usb.println("{\"event\":\"boot\",\"version\":\"0.2.1\"}");
}

void loop() {
    // Heartbeat: brief green blink every 2 seconds
    unsigned long now = millis();
    if (now - last_heartbeat >= 2000) {
        last_heartbeat = now;
        heartbeat_on = true;
        neopixelWrite(HEARTBEAT_PIN, 0, 4, 0);  // dim green
    } else if (heartbeat_on && now - last_heartbeat >= 100) {
        heartbeat_on = false;
        neopixelWrite(HEARTBEAT_PIN, 0, 0, 0);  // off
    }

    char line[128];
    int len = usb.readLine(line, sizeof(line), 50);
    if (len > 0) {
        String cmd(line);
        command_dispatch(cmd, usb);
    }
}
