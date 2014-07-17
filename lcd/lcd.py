
#!/usr/bin/python
    
from time import *
import lcddriver

lcd = lcddriver.lcd()

#while True:
#    lcd.lcd_display_string(str(time()), 1)

lcd.lcd_display_string("Hi Marley!", 1)
