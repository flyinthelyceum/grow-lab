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

JtagSerial usb;

void setup() {
    usb.begin();
    delay(200);

    // Initialize PWM for LED control
    pwm_init(LED_PWM_PIN);

    // Initialize pump relay pin
    pinMode(PUMP_RELAY_PIN, OUTPUT);
    digitalWrite(PUMP_RELAY_PIN, LOW);

    usb.println("{\"event\":\"boot\",\"version\":\"0.2.0\"}");
}

void loop() {
    char line[128];
    int len = usb.readLine(line, sizeof(line), 50);
    if (len > 0) {
        String cmd(line);
        command_dispatch(cmd, usb);
    }
}
