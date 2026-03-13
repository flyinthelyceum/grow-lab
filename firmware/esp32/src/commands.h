#ifndef COMMANDS_H
#define COMMANDS_H

#include <Arduino.h>

// Parse and dispatch a serial command line.
// Supported commands:
//   LIGHT <0..255>   Set LED PWM duty cycle
//   PUMP <0|1>       Set pump relay state
//   STATUS           Request current state (JSON response)
void command_dispatch(const String& line, Print& out);

#endif
