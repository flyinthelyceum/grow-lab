#include "pwm_control.h"

static uint8_t current_duty = 0;

void pwm_init(uint8_t pin) {
    ledcSetup(PWM_CHANNEL, PWM_FREQ, PWM_RESOLUTION);
    ledcAttachPin(pin, PWM_CHANNEL);
    ledcWrite(PWM_CHANNEL, 0);
    current_duty = 0;
}

void pwm_set_duty(uint8_t duty) {
    current_duty = duty;
    ledcWrite(PWM_CHANNEL, duty);
}

uint8_t pwm_get_duty() {
    return current_duty;
}
