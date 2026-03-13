#ifndef JTAG_SERIAL_H
#define JTAG_SERIAL_H

/**
 * Stream wrapper for the ESP32-S3 USB-Serial/JTAG controller.
 *
 * Uses the low-level hardware FIFO directly, bypassing the ESP-IDF
 * driver to avoid initialization conflicts. The ROM bootloader uses
 * the same FIFO, so this path is known to work on this board.
 */

#include <Arduino.h>
#include "hal/usb_serial_jtag_ll.h"

class JtagSerial : public Stream {
public:
    void begin() {
        // Nothing to initialize — the USB-Serial/JTAG hardware is
        // already set up by the ROM bootloader.
    }

    int available() override {
        return usb_serial_jtag_ll_rxfifo_data_available() ? 1 : 0;
    }

    int read() override {
        uint8_t c;
        if (usb_serial_jtag_ll_read_rxfifo(&c, 1) > 0) {
            return c;
        }
        return -1;
    }

    int peek() override { return -1; }

    size_t write(uint8_t c) override {
        return write(&c, 1);
    }

    size_t write(const uint8_t *buf, size_t size) override {
        size_t sent = 0;
        uint32_t attempts = 0;
        while (sent < size && attempts < 10000) {
            uint32_t n = usb_serial_jtag_ll_write_txfifo(buf + sent, size - sent);
            if (n > 0) {
                usb_serial_jtag_ll_txfifo_flush();
                sent += n;
                attempts = 0;
            } else {
                attempts++;
                delayMicroseconds(100);
            }
        }
        return sent;
    }

    // Read a full line (up to newline), with a timeout.
    int readLine(char *buf, size_t maxlen, uint32_t timeout_ms = 100) {
        size_t pos = 0;
        unsigned long deadline = millis() + timeout_ms;
        while (pos < maxlen - 1 && millis() < deadline) {
            if (usb_serial_jtag_ll_rxfifo_data_available()) {
                uint8_t c;
                if (usb_serial_jtag_ll_read_rxfifo(&c, 1) > 0) {
                    if (c == '\n') break;
                    if (c != '\r') buf[pos++] = c;
                }
            } else {
                delay(1);
            }
        }
        buf[pos] = '\0';
        return pos;
    }
};

#endif
