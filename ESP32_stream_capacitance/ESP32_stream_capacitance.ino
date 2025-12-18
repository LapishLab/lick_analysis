// List of ESP32 touch-capable pins
const int touchPins[] = {1,2,3,4,5,6,7,8,9}; //GPIO pin numbers, not TOUCH numbers
const int reading_delay = 10; //ms delay between readings  ## Values only seem to update every 10ms ##

void setup() {
  Serial.begin(250000);
  // touchSetCycles(TOUCH_PAD_MEASURE_CYCLE_DEFAULT, TOUCH_PAD_SLEEP_CYCLE_DEFAULT); //uint16_t measure, uint16_t sleep; defaults (clock cycles) 500,15 = update every ~5ms
  touchSetCycles(1000, 30); //uint16_t measure, uint16_t sleep; defaults (clock cycles) 500,15 = update every ~5ms

  delay(1000); // Give time for Serial to initialize
}


const int numTouchPins = sizeof(touchPins) / sizeof(touchPins[0]);
void loop() {
  for (int i=0; i<numTouchPins; i++){
    int c = Serial.print(touchRead(touchPins[i]));
    if (i < numTouchPins - 1) { 
      Serial.printf("%i,", c); // print comma if not last element
    } else {
      Serial.printf("%i\n", c); // print newline if last element
    }
  }
  delay(reading_delay);
}