#ifndef JTAG_SERIAL_H
#define JTAG_SERIAL_H

/**
 * Stream wrapper for the ESP32-S3 USB-Serial/JTAG controller.
 *
 * The Freenove ESP32-S3 WROOM board routes USB through the built-in
 * USB-Serial/JTAG peripheral (not USB-OTG). Arduino's Serial class
 * cannot target this peripheral, so we use the ESP-IDF driver directly.
 */

#include <Arduino.h>
#include "driver/usb_serial_jtag.h"

class JtagSerial : public Stream {
public:
    bool begin(unsigned long = 0) {
        usb_serial_jtag_driver_config_t cfg = {
            .tx_buffer_size = 512,
            .rx_buffer_size = 512,
        };
        return usb_serial_jtag_driver_install(&cfg) == ESP_OK;
    }

    int available() override {
        // No direct "bytes available" API; try a zero-wait read.
        return 0; // We use readBytes with a timeout instead.
    }

    int read() override {
        uint8_t c;
        int n = usb_serial_jtag_read_bytes(&c, 1, 0);
        return n > 0 ? c : -1;
    }

    int peek() override { return -1; }

    size_t write(uint8_t c) override {
        return usb_serial_jtag_write_bytes(&c, 1, pdMS_TO_TICKS(100));
    }

    size_t write(const uint8_t *buf, size_t size) override {
        return usb_serial_jtag_write_bytes(buf, size, pdMS_TO_TICKS(100));
    }

    // Read a full line (up to newline), with a timeout.
    // Returns number of bytes read.
    int readLine(char *buf, size_t maxlen, uint32_t timeout_ms = 100) {
        size_t pos = 0;
        TickType_t deadline = xTaskGetTickCount() + pdMS_TO_TICKS(timeout_ms);
        while (pos < maxlen - 1) {
            uint8_t c;
            TickType_t remaining = deadline - xTaskGetTickCount();
            if ((int32_t)remaining <= 0) break;
            int n = usb_serial_jtag_read_bytes(&c, 1, remaining);
            if (n <= 0) break;
            if (c == '\n') { break; }
            if (c != '\r') { buf[pos++] = c; }
        }
        buf[pos] = '\0';
        return pos;
    }
};

#endif
