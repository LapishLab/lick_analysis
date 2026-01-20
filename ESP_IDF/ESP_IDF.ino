#include "driver/touch_pad.h"

// Define the GPIO/Touch Pad (Example: GPIO 1 is Touch Pad 1)
#define TOUCH_PAD_NUM TOUCH_PAD_NUM1 

void setup() {
  Serial.begin(115200);

  // 1. Initialize the Touch Peripheral
  touch_pad_init();

  // 2. Configure the FSM (Finite State Machine) for timing
  // Set sleep cycles to 0 for maximum speed (continuous mode)
  // Set measure cycles to ~0.5ms (assuming 17.5MHz clock, 0x2000 is ~0.46ms)
  touch_pad_set_fsm_mode(TOUCH_FSM_MODE_SW); // Software trigger for manual polling
  touch_pad_set_voltage(TOUCH_PAD_HIGH_VOLTAGE_THRESHOLD, TOUCH_PAD_LOW_VOLTAGE_THRESHOLD, TOUCH_PAD_ATTEN_1V5);
  
  // 3. Configure the specific pad
  touch_pad_config(TOUCH_PAD_NUM);

  // 4. Start the measurement
  touch_pad_fsm_start();
}

void loop() {
  uint32_t touch_value;

  // 5. Read the raw data (on S3, higher value = more capacitance/touch)
  // The 'v2' API uses touch_pad_read_raw_data
  touch_pad_read_raw_data(TOUCH_PAD_NUM, &touch_value);

  Serial.printf("Raw Touch Value: %lu\n", touch_value);
  
  delay(10); // Small delay to prevent serial flooding
}
