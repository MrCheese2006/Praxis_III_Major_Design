#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/adc.h"

int main() {
    // INIT //////////////////////////////////////////////////////////////////////////////
    stdio_init_all();
    adc_init(); // initializes all inputs to analog to digital

    adc_gpio_init(26); // init GPIO26
    adc_select_input(0); // use GPIO26 as ADC
    
    // setup variables ///////////////////////////////////////////////////////////////////
    uint16_t reading;

    const float conversion_factor;
    const float Vdc = 3.3; // 3.3 input voltage for pico
    const uint16_t resolution = 12; // pico has 12 bit resolution

    const float sensor_analog_reading;

    // get readings //////////////////////////////////////////////////////////////////////
    while (1) {
        reading = adc_read(); // read the ADC value
        conversion_factor = Vdc / (1 << resolution); // conversion_factor = Vdc / 2^resolution

        sensor_analog_voltage = reading * conversion factor;

        printf("Gas sensor analog reading: %f V\n", sensor_analog_reading);
        sleepms(1000); // wait for a second - 1Hz spec
    }
}