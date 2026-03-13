#ifndef PWM_CONTROL_H
#define PWM_CONTROL_H

#include <Arduino.h>

// LEDC PWM configuration
static const uint8_t PWM_CHANNEL = 0;
static const uint32_t PWM_FREQ = 1000;   // 1 kHz
static const uint8_t PWM_RESOLUTION = 8; // 0-255

void pwm_init(uint8_t pin);
void pwm_set_duty(uint8_t duty);
uint8_t pwm_get_duty();

#endif
