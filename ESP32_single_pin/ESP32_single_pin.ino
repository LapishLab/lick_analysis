const int touchPin = 1;
const int reading_delay = 10; //ms delay between readings  ## Values only seem to update every 10ms ##

void setup() {
  Serial.begin(250000);
  touchSetCycles(1000, 30); //uint16_t measure, uint16_t sleep; defaults (clock cycles) 500,15 = update every ~5ms
  delay(1000); // Give time for Serial to initialize
}

void loop() {
  Serial.println(touchRead(touchPin));
  delay(reading_delay);
}