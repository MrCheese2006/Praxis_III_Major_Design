#include <stdio.h>
#include "pico/time.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"
const uint TEMP_SENSOR = 12;



void init()
{
    gpio_set_function(TEMP_SENSOR,GPIO_FUNC_SIO);
    gpio_pull_up(TEMP_SENSOR);

}

float get_data()
{
    uint8_t data[5];
    float RH;
    int16_t raw_temp;
    float temp;
    while(true){
        gpio_set_dir(TEMP_SENSOR, GPIO_OUT);
        gpio_put(TEMP_SENSOR, 0);
        sleep_ms(1);
        gpio_put(TEMP_SENSOR, 1);
        sleep_us(30);
        uint32_t start = 0;
        uint32_t end = 0;
        gpio_set_dir(TEMP_SENSOR, GPIO_IN);

        for(int i = 0; i < 5; i++){
            data[i] = 0;
            for(int j = 0; j <8;j++){
                while(gpio_get(TEMP_SENSOR)==0){}
                start = to_us_since_boot(get_absolute_time());
                while(gpio_get(TEMP_SENSOR)!=0){}
                end = to_us_since_boot(get_absolute_time());

                int bit = 0;
                uint32_t time = end-start;
                if (time > 50){
                    bit = 1;
                }
                else{
                    bit=0;
                }
                data[i] = data[i] | bit<< 1;
            }
        }

        RH = (data[0]<<8|data[1])/10
        raw_temp = (data[1]<<8)
        if (raw_temp & 0x8000){
            raw_temp =raw_temp & 0x7FFF;
            temp = - ((float)raw_temp)/10.0;
        }else{
            temp = ((float)raw_temp)/10.0;
        }

        printf("Relative Humidity: %f \n Temperature (C): %f \n", RH, Temp);
    }
}


