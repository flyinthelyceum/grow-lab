#include "pwm_control.h"

static uint8_t current_duty = 0;
static uint8_t pwm_pin = 0;

void pwm_init(uint8_t pin) {
    pwm_pin = pin;
    ledcAttach(pin, PWM_FREQ, PWM_RESOLUTION);
    ledcWrite(pin, 0);
    current_duty = 0;
}

void pwm_set_duty(uint8_t duty) {
    current_duty = duty;
    ledcWrite(pwm_pin, duty);
}

uint8_t pwm_get_duty() {
    return current_duty;
}
