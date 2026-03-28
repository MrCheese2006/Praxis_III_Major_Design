#include <stdio.h>
#include "pico/time.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"

const uint TEMP_SENSOR = 12;

void init() {
    gpio_init(TEMP_SENSOR);
    gpio_pull_up(TEMP_SENSOR);
}

bool read_dht22(float *temp, float *rh) {
    uint8_t data[5] = {0};

    // --- Start signal ---
    gpio_set_dir(TEMP_SENSOR, GPIO_OUT);
    gpio_put(TEMP_SENSOR, 0);
    sleep_ms(1);
    gpio_put(TEMP_SENSOR, 1);
    sleep_us(30);

    gpio_set_dir(TEMP_SENSOR, GPIO_IN);

    // --- Sensor response ---
    while (gpio_get(TEMP_SENSOR) == 1);
    while (gpio_get(TEMP_SENSOR) == 0);
    while (gpio_get(TEMP_SENSOR) == 1);

    // --- Read 40 bits ---
    for (int i = 0; i < 5; i++) {
        for (int j = 0; j < 8; j++) {

            while (gpio_get(TEMP_SENSOR) == 0);

            uint32_t start = to_us_since_boot(get_absolute_time());

            while (gpio_get(TEMP_SENSOR) == 1);

            uint32_t end = to_us_since_boot(get_absolute_time());

            uint32_t duration = end - start;

            data[i] <<= 1;

            if (duration > 50) {
                data[i] |= 1;
            }
        }
    }

    // --- Checksum ---
    if (((data[0] + data[1] + data[2] + data[3]) & 0xFF) != data[4]) {
        return false;
    }

    // --- Convert ---
    uint16_t raw_humidity = (data[0] << 8) | data[1];
    int16_t raw_temp = (data[2] << 8) | data[3];

    *rh = raw_humidity / 10.0;

    if (raw_temp & 0x8000) {
        raw_temp &= 0x7FFF;
        *temp = -raw_temp / 10.0;
    } else {
        *temp = raw_temp / 10.0;
    }

    return true;
}