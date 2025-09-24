// List of ESP32 touch-capable pins
const int touchPins[] = {1,4};
const int reading_delay = 10; //ms delay between readings  ## Values only seem to update every 10ms ##

void setup() {
  Serial.begin(250000);
  // touchSetCycles(TOUCH_PAD_MEASURE_CYCLE_DEFAULT, TOUCH_PAD_SLEEP_CYCLE_DEFAULT); //uint16_t measure, uint16_t sleep; defaults (clock cycles) 500,15 = update every ~5ms
  touchSetCycles(1000, 30); //uint16_t measure, uint16_t sleep; defaults (clock cycles) 500,15 = update every ~5ms

  delay(1000); // Give time for Serial to initialize
}

void loop() {
  uint32_t c1 = touchRead(touchPins[0]);
  uint32_t c2 = touchRead(touchPins[1]);
  Serial.printf("%i,%i\n", c1, c2);
  delay(reading_delay);
}

// const int numTouchPins = sizeof(touchPins) / sizeof(touchPins[0]);
// void loop() {
  // for (int i=0; i<numTouchPins; i++){
  //   // unsigned long int time = millis();
  //   int pin = touchPins[i];
  //   int c = touchRead(pin);
  //   // Serial.printf("GPIO%i:%i \n",  pin, c);
  //   Serial.print(c);
  // }
  // delay(reading_delay);
  // Serial.printf("Ymin:%i\n", 50000);
  // Serial.printf("Ymax:%i\n", 130000);
// }