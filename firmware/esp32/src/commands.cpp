#include "commands.h"
#include "pwm_control.h"

#ifndef PUMP_RELAY_PIN
#define PUMP_RELAY_PIN 17
#endif

static bool pump_state = false;

static void cmd_light(const String& arg, Print& out) {
    int value = arg.toInt();
    if (value < 0 || value > 255) {
        out.println("{\"error\":\"LIGHT value must be 0-255\"}");
        return;
    }
    pwm_set_duty((uint8_t)value);
    out.print("{\"ok\":true,\"pwm\":");
    out.print(value);
    out.println("}");
}

static void cmd_pump(const String& arg, Print& out) {
    int value = arg.toInt();
    if (value != 0 && value != 1) {
        out.println("{\"error\":\"PUMP value must be 0 or 1\"}");
        return;
    }
    pump_state = (value == 1);
    digitalWrite(PUMP_RELAY_PIN, pump_state ? HIGH : LOW);
    out.print("{\"ok\":true,\"pump\":");
    out.print(pump_state ? "true" : "false");
    out.println("}");
}

static void cmd_status(Print& out) {
    out.print("{\"pwm\":");
    out.print(pwm_get_duty());
    out.print(",\"pump\":");
    out.print(pump_state ? "true" : "false");
    out.print(",\"uptime\":");
    out.print(millis() / 1000);
    out.println("}");
}

void command_dispatch(const String& line, Print& out) {
    String trimmed = line;
    trimmed.trim();

    if (trimmed.startsWith("LIGHT ")) {
        cmd_light(trimmed.substring(6), out);
    } else if (trimmed.startsWith("PUMP ")) {
        cmd_pump(trimmed.substring(5), out);
    } else if (trimmed == "STATUS") {
        cmd_status(out);
    } else {
        out.print("{\"error\":\"unknown command: ");
        out.print(trimmed);
        out.println("\"}");
    }
}
