#include "commands.h"
#include "pwm_control.h"

#ifndef PUMP_RELAY_PIN
#define PUMP_RELAY_PIN 17
#endif

static bool pump_state = false;

static void cmd_light(const String& arg) {
    int value = arg.toInt();
    if (value < 0 || value > 255) {
        Serial.println("{\"error\":\"LIGHT value must be 0-255\"}");
        return;
    }
    pwm_set_duty((uint8_t)value);
    Serial.print("{\"ok\":true,\"pwm\":");
    Serial.print(value);
    Serial.println("}");
}

static void cmd_pump(const String& arg) {
    int value = arg.toInt();
    if (value != 0 && value != 1) {
        Serial.println("{\"error\":\"PUMP value must be 0 or 1\"}");
        return;
    }
    pump_state = (value == 1);
    digitalWrite(PUMP_RELAY_PIN, pump_state ? HIGH : LOW);
    Serial.print("{\"ok\":true,\"pump\":");
    Serial.print(pump_state ? "true" : "false");
    Serial.println("}");
}

static void cmd_status() {
    Serial.print("{\"pwm\":");
    Serial.print(pwm_get_duty());
    Serial.print(",\"pump\":");
    Serial.print(pump_state ? "true" : "false");
    Serial.print(",\"uptime\":");
    Serial.print(millis() / 1000);
    Serial.println("}");
}

void command_dispatch(const String& line) {
    String trimmed = line;
    trimmed.trim();

    if (trimmed.startsWith("LIGHT ")) {
        cmd_light(trimmed.substring(6));
    } else if (trimmed.startsWith("PUMP ")) {
        cmd_pump(trimmed.substring(5));
    } else if (trimmed == "STATUS") {
        cmd_status();
    } else {
        Serial.print("{\"error\":\"unknown command: ");
        Serial.print(trimmed);
        Serial.println("\"}");
    }
}
