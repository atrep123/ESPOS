#pragma once

#define INPUT 0
#define INPUT_PULLUP 2
#define LOW 0
#define HIGH 1

void pinMode(int pin, int mode);
int analogRead(int pin);
int digitalRead(int pin);
