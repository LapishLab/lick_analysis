// List of ESP32 touch-capable pins
const int touchPins[] = {1,6}; //GPIO pin numbers, not TOUCH numbers
const int reading_delay = 10; //ms delay between readings  ## Values only seem to update every 10ms ##
const int norm_val = 100;

void setup() {
  Serial.begin(250000);
  // touchSetCycles(TOUCH_PAD_MEASURE_CYCLE_DEFAULT, TOUCH_PAD_SLEEP_CYCLE_DEFAULT); //uint16_t measure, uint16_t sleep; defaults (clock cycles) 500,15 = update every ~5ms
  touchSetCycles(1000, 30); //uint16_t measure, uint16_t sleep; defaults (clock cycles) 500,15 = update every ~5ms

  delay(1000); // Give time for Serial to initialize
}


const int numTouchPins = sizeof(touchPins) / sizeof(touchPins[0]);
void loop() {
  for (int i=0; i<numTouchPins; i++){
    unsigned long c = touchRead(touchPins[i]) / norm_val;
    if (i < numTouchPins - 1) { 
      Serial.printf("%lu,", c); // print comma if not last element
    } else {
      Serial.printf("%lu\n", c); // print newline if last element
    }
  }
  delay(reading_delay);
}