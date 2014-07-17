#!/usr/bin/env python

import time

from lcd import lcddriver

from i2clibraries import i2c_lcd_smbus

lcd1 = lcddriver.lcd()

lcd2 = i2c_lcd_smbus.i2c_lcd(0x3f,1, 2, 1, 0, 4, 5, 6, 7, 3)
lcd2.command(lcd2.CMD_Display_Control | lcd2.OPT_Enable_Display)
lcd2.backLightOn()


def writeLcd1(message):

    lcd1.lcd_display_string(str(message), (message % 2) + 1)


def writeLcd2(message):
    
    lcd2.setPosition((message % 2) + 1 , 0)
    lcd2.writeString(str(message))
    

if __name__=='__main__':
    for count in [10**2, 10**3]:
        _start = time.time()

        for ii in xrange(0, count):
            writeLcd1(ii)

        print "Sending %s numbers to LCD1 took %s seconds" % (count, (time.time() - _start))

    for count in [10**2, 10**3]:
        _start = time.time()

        for ii in xrange(0, count):
            writeLcd2(ii)

        print "Sending %s numbers to LCD2 took %s seconds" % (count, (time.time() - _start))

