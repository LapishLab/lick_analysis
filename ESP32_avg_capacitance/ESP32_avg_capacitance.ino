// List of ESP32 touch-capable pins
const int touchPin= 2; //GPIO pin numbers, not TOUCH numbers
const int num_avg = 1000;
const int reading_delay = 10; //us delay between readings

void setup() {
  Serial.begin(250000);
  // touchSetCycles(4096, 4096); 
  delay(1000);
}

uint64_t c;
void loop() {
  c = 0;
  for (int i=0; i<num_avg; i++){
    delayMicroseconds(reading_delay);
    c += touchRead(touchPin);
  }
  Serial.println(c / num_avg/10);
}