#!/usr/bin/python
# need to do this in external file so it can be called from init scripts :)


#from lcd.CharLCD import CharLCD
import RPi.GPIO as GPIO 

print '\nshutdown.py:  cleaning up resources.\n'

#lcd = CharLCD()

gpio_heat = 24
gpio_pump = 23

gpio_btn_heat_led = 8
gpio_btn_pump_led = 10

GPIO.setwarnings(False) 

GPIO.setmode(GPIO.BCM)

GPIO.setup(gpio_heat, GPIO.OUT) 
GPIO.setup(gpio_pump, GPIO.OUT) 
GPIO.setup(gpio_btn_heat_led, GPIO.OUT) 
GPIO.setup(gpio_btn_pump_led, GPIO.OUT) 

GPIO.output(gpio_heat, GPIO.LOW)
GPIO.output(gpio_pump, GPIO.LOW)
GPIO.output(gpio_btn_heat_led, GPIO.LOW)
GPIO.output(gpio_btn_pump_led, GPIO.LOW)

#lcd.clear()
#lcd.message('iSpresso\nDeactivated')

GPIO.cleanup()      

