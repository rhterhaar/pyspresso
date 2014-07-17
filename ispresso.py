#!/usr/bin/python

# Copyright (c) 2013 Chris Synan & Dataworlds LLC
# Portions copyright (c) 2012 Stephen P. Smith
#
# Permission is hereby granted, free of charge, to any person obtaining 
# a copy of this software and associated documentation files 
# (the "Software"), to deal in the Software without restriction, 
# including without limitation the rights to use, copy, modify, 
# merge, publish, distribute, sublicense, and/or sell copies of the Software, 
# and to permit persons to whom the Software is furnished to do so, 
# subject to the following conditions:

# The software is free for non-commercial uses.  Commercial uses of this software 
# or any derivative must obtain a license from Dataworlds LLC (Austin TX)

# In addition, the above copyright notice and this permission notice shall 
# be included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS 
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, 
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR 
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import sys, os, time, logging, logging.handlers, traceback
import threading, subprocess, urllib2
from multiprocessing import Process, Pipe, Queue, current_process
from subprocess import Popen, PIPE, call, signal
from datetime import datetime
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import web, random, json, atexit
from pid import pidpy as PIDController
import RPi.GPIO as GPIO 
from lcd import lcddriver
import glob

#logging.basicConfig()
logger = logging.getLogger('ispresso')


# REMOTE DEBUG -- TODO:  Remove this before going to production
#import rpdb2 
#rpdb2.start_embedded_debugger('funkymonkey', fAllowRemote = True)

gpio_heat = 24
gpio_pump = 23
gpio_btn_heat_led = 8
gpio_btn_heat_sig = 7
gpio_btn_pump_led = 10
gpio_btn_pump_sig = 9

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) 
GPIO.setup(gpio_btn_heat_sig, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
GPIO.setup(gpio_btn_pump_sig, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
GPIO.setup(gpio_heat, GPIO.OUT) 
GPIO.setup(gpio_pump, GPIO.OUT) 
GPIO.setup(gpio_btn_heat_led, GPIO.OUT)
GPIO.setup(gpio_btn_pump_led, GPIO.OUT)

def logger_init():

    logger.setLevel(logging.DEBUG)
    log_file_size = 1024 * 1024 * 1 # 1 MB
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(process)d - %(name)s : %(message)s')
    fh = logging.handlers.RotatingFileHandler('/var/log/ispresso.log', maxBytes=log_file_size, backupCount=5)
    fh.setFormatter(formatter)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.info('Starting up...')

def initialize():

    settings.load()

    if setup.check_connected() == False:            # this needs to happen after lcd pipe is set up
        logger.warn("WiFi can't connect to internet.  Entering Smart Connect mode.  Connect to iSPRESSO wireless network.")
        mem.lcd_connection.send(["iSPRESSO WiFi", "Access Point", 0])
        setup.smart_connect()
    else:
        logger.info("WiFi connection looks ok")
        mem.lcd_connection.send(["iSPRESSO", "WiFi OK", 3])
        mem.lcd_connection.send(["iSPRESSO", "", 0])

class mem:          # global class  
    cache_day = None
    cache_start_time = None
    cache_end_time = None
    heat_connection = Pipe()
    lcd_connection = Pipe()
    brew_connection = Pipe()
    flag_pump_on = False
    sched_flag_on = False
    sched_flag_off = False
    time_heat_button_pressed = time.time()
    scheduler_enabled = True
    presoak_time = 3
    wait_time = 2
    brew_time = 25
    one_wire = None

class param:
    mode = "off"
    cycle_time = 2.0
    duty_cycle = 0.0
    set_point = 211
    k_param = 6     # was 6
    i_param = 60   # was 120
    d_param = 15     # was 5

def add_global_hook(parent_conn, statusQ):

#    mem.heat_connection = parent_conn    
    g = web.storage({"parent_conn" : parent_conn, "statusQ" : statusQ})
    def _wrapper(handler):
        web.ctx.globals = g
        return handler()
    return _wrapper

class advanced: 
    def __init__(self):
                
        self.mode = param.mode
        self.cycle_time = param.cycle_time
        self.duty_cycle = param.duty_cycle
        self.set_point = param.set_point
        self.k_param = param.k_param
        self.i_param = param.i_param
        self.d_param = param.d_param
        
    def GET(self):
       
        return render.advanced(self.mode, self.set_point, self.duty_cycle, self.cycle_time, self.k_param, self.i_param, self.d_param)
        
    def POST(self):
        data = web.data()
        datalist = data.split("&")
        for item in datalist:
            datalistkey = item.split("=")
            if datalistkey[0] == "mode":
                self.mode = datalistkey[1]
            if datalistkey[0] == "setpoint":
                self.set_point = float(datalistkey[1])
            if datalistkey[0] == "dutycycle":
                self.duty_cycle = float(datalistkey[1])
            if datalistkey[0] == "cycletime":
                self.cycle_time = float(datalistkey[1])
            if datalistkey[0] == "k":
                self.k_param = float(datalistkey[1])
            if datalistkey[0] == "i":
                self.i_param = float(datalistkey[1])
            if datalistkey[0] == "d":
                self.d_param = float(datalistkey[1])

        param.mode = self.mode 
        param.cycle_time = self.cycle_time
        param.duty_cycle = self.duty_cycle 
        param.set_point = self.set_point
        param.k_param = self.k_param
        param.i_param = self.i_param 
        param.d_param = self.d_param
        settings.save()

        web.ctx.globals.parent_conn.send([self.mode, self.cycle_time, self.duty_cycle, self.set_point, self.k_param, self.i_param, self.d_param, False])  

def gettempProc(conn):
    p = current_process()
    logger = logging.getLogger('ispresso').getChild("getTempProc")
    logger.info('Starting:' + p.name + ":" + str(p.pid))
    try:
        while (True):
            t = time.time()
            time.sleep(0.5) #.1+~.83 = ~1.33 seconds
            num = tempdata()
            elapsed = "%.2f" % (time.time() - t)
            conn.send([num, elapsed])
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


def getonofftime(cycle_time, duty_cycle):
    duty = duty_cycle / 100.0
    on_time = cycle_time * (duty)
    off_time = cycle_time * (1.0 - duty)   
    return [on_time, off_time]

def tellHeatProc(heat_mode = None, flush_cache = None):

    if flush_cache is None:
        flush_cache = False
    
    if heat_mode is not None:
        param.mode = heat_mode

    mem.heat_connection.send([param.mode, param.cycle_time, param.duty_cycle, param.set_point, param.k_param, param.i_param, param.d_param, flush_cache])
        
def heatProc(cycle_time, duty_cycle, conn):
    p = current_process()
    logger = logging.getLogger('ispresso').getChild("heatProc")
    logger.info('Starting:' + p.name + ":" + str(p.pid))

    try:    
        while (True):
            while (conn.poll()): #get last
                cycle_time, duty_cycle = conn.recv()
            conn.send([cycle_time, duty_cycle])  
            if duty_cycle == 0:
                GPIO.output(gpio_heat, GPIO.LOW)
                time.sleep(cycle_time)
            elif duty_cycle == 100:
                GPIO.output(gpio_heat, GPIO.HIGH)
                time.sleep(cycle_time)
            else:
                on_time, off_time = getonofftime(cycle_time, duty_cycle)
                GPIO.output(gpio_heat, GPIO.HIGH)
                time.sleep(on_time)
                GPIO.output(gpio_heat, GPIO.LOW)
                time.sleep(off_time)
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


def lcdControlProc(lcd_child_conn):
    p = current_process()
    logger = logging.getLogger("ispresso").getChild("lcdControlProc")
    logger.info('Starting:' + p.name + ":" + str(p.pid))

    lcd = lcddriver.lcd()
    while (True):
        time.sleep(0.25)
        while lcd_child_conn.poll():
            try:
                line1, line2, duration = lcd_child_conn.recv()
                if line1 is not None:
                    lcd.lcd_display_string(line1.ljust(16), 1)
                    time.sleep(duration)
                if line2 is not None:
                    lcd.lcd_display_string(line2.ljust(16), 2)
                    time.sleep(duration)

            except:
                lcd.lcd_clear()
                exc_type, exc_value, exc_traceback = sys.exc_info()
                logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


def brewControlProc(brew_child_conn):
    p = current_process()
    logger = logging.getLogger("ispresso").getChild("brewControlProc")
    logger.info('Starting:' + p.name + ":" + str(p.pid))

    try:
        mem.flag_pump_on = False
        button_bounce_threshold_secs = 1
        
        while(True):
            time_button_pushed, brew_plan = brew_child_conn.recv()     # BLOCKS until something shows up
            mem.flag_pump_on = True
    
            for listitem in brew_plan:
                if mem.flag_pump_on == False:
                    while brew_child_conn.poll():               # clear out anything other button presses in the queue
                        brew_child_conn.recv()                              
                    break
                
                action = listitem[0]
                duration = listitem[1]
                counter = 0
                start_time = time.time()
                
                if action.upper() in ("PRESOAK", "BREW"):
                    GPIO.output(gpio_btn_pump_led, GPIO.HIGH)
                    GPIO.output(gpio_pump, GPIO.HIGH)
            
                while ((counter < duration) & mem.flag_pump_on) :       # might not need the check for flag_pump_on here, as its above
                    time.sleep(0.1)
                    if brew_child_conn.poll():                  # mem.brew_connection.poll() returns TRUE or FALSE immediately and does NOT block
                        time_button_pushed_again, throwaway_brew_plan = brew_child_conn.recv()                            # get item off the list, check how long since time_button_pushed, against button_bounce_threshold_secs.  If too short, clean up and exit this loop
                        if time_button_pushed_again - time_button_pushed > button_bounce_threshold_secs:
                            GPIO.output(gpio_pump, GPIO.LOW)
                            GPIO.output(gpio_btn_pump_led, GPIO.LOW)
                            mem.flag_pump_on = False
                            mem.lcd_connection.send([None, "", 0])
                            break
    
                    if (time.time() - start_time) >= counter:
                        counter = counter + 1
                        message = action + 'ing ' + str(duration - counter) + 's'
                        mem.lcd_connection.send([None, message, 0])
                        logger.debug(message)
            
                GPIO.output(gpio_pump, GPIO.LOW)
                GPIO.output(gpio_btn_pump_led, GPIO.LOW)
                mem.lcd_connection.send([None, '', 0])
    
            while brew_child_conn.poll():               # clear out anything other button presses in the queue
                brew_child_conn.recv()    

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


def tempControlProc(mode, cycle_time, duty_cycle, set_point, k_param, i_param, d_param, statusQ, conn):  
    p = current_process()
    logger = logging.getLogger('ispresso').getChild("tempControlProc")
    logger.info('Starting:' + p.name + ":" + str(p.pid))

    try:
        parent_conn_temp, child_conn_temp = Pipe()            
        ptemp = Process(name = "gettempProc", target=gettempProc, args=(child_conn_temp,))
        ptemp.daemon = True
        ptemp.start()   
        parent_conn_heat, child_conn_heat = Pipe()           
        pheat = Process(name = "heatProc", target=heatProc, args=(cycle_time, duty_cycle, child_conn_heat))
        pheat.daemon = True
        pheat.start() 

        pid = PIDController.pidpy(cycle_time, k_param, i_param, d_param) #init pid
        flush_cache = False
        last_temp_C = 0
        
        while (True):
            time.sleep(0.1)

            readytemp = False
            while parent_conn_temp.poll():
                temp_C, elapsed = parent_conn_temp.recv() #non blocking receive    
                    
                mode = scheduled_mode(mode)      # check to see if scheduler should fire on or off -- MOVING THIS as the OFF doesnt seem to fire..
                if temp_C > 0:              #  the 1-wire sensor sometimes comes back with 0 -- need to fix that by holding on to last value.  
                    last_temp_C = temp_C
                else:
                    temp_C = last_temp_C    
                
                temp_F = (9.0/5.0)*temp_C + 32
                temp_C_str = "%3.2f" % temp_C
                temp_F_str = "%3.2f" % temp_F
                temp_F_pretty = "%3.0f" % temp_F
                mem.lcd_connection.send(['iSPRESSO ' + str(temp_F_pretty) + ' F', None, 0])

                readytemp = True
            if readytemp == True:
                if mode == "auto":
                    duty_cycle = pid.calcPID_reg4(temp_F, set_point, True)
                    parent_conn_heat.send([cycle_time, duty_cycle])
                    GPIO.output(gpio_btn_heat_led, GPIO.HIGH) 
                elif mode == "off":
                    duty_cycle = 0
                    parent_conn_heat.send([cycle_time, duty_cycle])
                    GPIO.output(gpio_btn_heat_led, GPIO.LOW)
                if (not statusQ.full()):    
                    statusQ.put([temp_F_str, elapsed, mode, cycle_time, duty_cycle, set_point, k_param, i_param, d_param]) #GET request
                readytemp == False   
                
            while parent_conn_heat.poll(): #non blocking receive
                cycle_time, duty_cycle = parent_conn_heat.recv()
                     
            while conn.poll(): #POST settings
                mode, cycle_time, duty_cycle_temp, set_point, k_param, i_param, d_param, flush_cache = conn.recv()
            
            if flush_cache:
                mem.cache_day = None    # this should force cache flush   
                flush_cache = False 

            mode = scheduled_mode(mode)      # check to see if scheduler should fire on or off

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


class getstatus:

    def __init__(self):
        pass

    def GET(self):       #blocking receive

        if (statusQ.full()): #remove old data
            for i in range(statusQ.qsize()):
                temp, elapsed, mode, cycle_time, duty_cycle, set_point, k_param, i_param, d_param = web.ctx.globals.statusQ.get() 
        temp, elapsed, mode, cycle_time, duty_cycle, set_point, k_param, i_param, d_param = web.ctx.globals.statusQ.get() 

        out = json.dumps({"temp" : temp, "elapsed" : elapsed, "mode" : mode, "cycle_time" : cycle_time, "duty_cycle" : duty_cycle,
                     "set_point" : set_point, "k_param" : k_param, "i_param" : i_param, "d_param" : d_param, "pump" : mem.flag_pump_on})  
        return out

    def POST(self):
        pass

class settings:
    def GET(self):
        with open("settings.json") as f:
            filecontents = json.load(f)
            return render.settings(json.dumps(filecontents))    # a JSON object (string) at this point
    
    def POST(self):
        data = web.data()      #web.input gives back a Storage < > thing
        mydata = json.loads(data)
        for datalistkey in mydata:
            logger.debug("datalistkey = " + str(datalistkey))
            if datalistkey == "temp":
                param.set_point = int(mydata[datalistkey])  
                logger.debug("temp changed to " + str( mydata[datalistkey]   ))
            if datalistkey == "brewSecs":
                mem.brew_time = int(mydata[datalistkey])
                logger.debug("brew secs changed")
            if datalistkey == "soakSecs":
                mem.presoak_time = int(mydata[datalistkey])
                logger.debug("soak secs changed")
            if datalistkey == "waitSecs":
                mem.wait_time = int(mydata[datalistkey])
                logger.debug("wait secs changed")
        logger.debug("Settings updated:  " + str(mydata))
        settings.save()

    @staticmethod 
    def load():
        with open("settings.json") as loadFile:
            my_settings = json.load(loadFile)      
            mem.brew_time = my_settings["brewSecs"]
            mem.presoak_time = my_settings["soakSecs"]
            mem.wait_time = my_settings["waitSecs"]
            param.set_point = my_settings["temp"]
            param.k_param = my_settings["p_value"]
            param.i_param = my_settings["i_value"]
            param.d_param = my_settings["d_value"]            
    
    @staticmethod
    def save():
        with open("settings.json") as saveFile:
            my_settings = json.load(saveFile)
            my_settings['brewSecs'] = mem.brew_time
            my_settings['soakSecs'] = mem.presoak_time
            my_settings['waitSecs'] = mem.wait_time
            my_settings['temp'] = param.set_point
            my_settings['p_value'] = param.k_param
            my_settings['i_value'] = param.i_param
            my_settings['d_value'] = param.d_param
        logger.debug("About to save settings = " + str(my_settings))
        with open("settings.json", "wb") as output_file:
            json.dump(my_settings, output_file)


class ispresso:

    def GET(self):
        return render.ispresso()

    def POST(self):
        op = ""
        flag = ""
        data = web.data()
        datalist = data.split("&")
        for item in datalist:
            datalistkey = item.split("=")
            if datalistkey[0] == "operation":
                op = datalistkey[1]
            if datalistkey[0] == "flag":
                flag = datalistkey[1]

        if str(op).upper() == "HEAT":
            if flag == "on":
                tellHeatProc("auto")
            else:
                tellHeatProc("off")
        elif str(op).upper() == "PUMP":
            time_stamp = time.time()
            brew_plan = [['Presoak', mem.presoak_time], ['Wait', mem.wait_time], ['Brew', mem.brew_time]]
            logger.debug("Caught POST, Pump button.  brewing ... " + str(brew_plan))
            mem.brew_connection.send([time_stamp, brew_plan])

def scheduled_mode(old_mode):

    try:
        now = datetime.now()
        today = datetime.isoweekday(datetime.now())
        if today == 7:
            today = 0
        if mem.cache_day is None or mem.cache_day != today:   # refresh cache, reset flags, turn off heat
            logger.debug("scheduled_mode:  cache flush or new day.  resetting flags, turning off heat.")
            mem.cache_day = today
            mem.sched_flag_off = False
            mem.sched_flag_on = False
            with open("schedule.json") as f:
                my_schedule = json.load(f)      # t= time.strptime("00:05:42.244", "%H:%M:%S")
                mem.cache_start_time = my_schedule['days'][today]['time']['startTime']
                mem.cache_start_time = now.replace(hour = int(mem.cache_start_time.split(":")[0]), minute = int(mem.cache_start_time.split(":")[1]) )
                mem.cache_end_time = my_schedule['days'][today]['time']['endTime']
                mem.cache_end_time = now.replace(hour = int(mem.cache_end_time.split(":")[0]), minute = int(mem.cache_end_time.split(":")[1]) )
            return "off"
    
        if now < mem.cache_start_time:
            return old_mode
    
        if now > mem.cache_start_time and now < mem.cache_end_time:
            if mem.sched_flag_on:
                return old_mode
            else:               # start flag NOT set
                mem.sched_flag_on = True    # set flag
                logger.debug("scheduled_mode:  going AUTO")
                return "auto"
    
        if now > mem.cache_end_time:
            if mem.sched_flag_off:
                return old_mode
            else:                   # end flag NOT set
                mem.sched_flag_off = True   # set end flag
                logger.debug("scheduled_mode:  going OFF")
                return "off"

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


class setup:
    def GET(self):
        
        try:
            iwlist_cmd = "iwlist wlan0 scanning | grep ESSID"
            proc = subprocess.Popen(iwlist_cmd, shell=True, stdout=subprocess.PIPE)
            myNwList = []
            while True:
                line = proc.stdout.readline()
                if line != '':
                    line = line[line.find('"') + 1 : len(line) - 2]
                    myNwList.append(line)
                    #the real code does filtering here
                    logger.debug( "ESSID :" + line.rstrip())
                else:
                    break
                
            return render.setup(myNwList)

        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))

    
    def POST(self):        # catch the inputs, put them into a config file, then call a shell script

        try:
            ssid = ""
            passwd = ""
            data = web.data()
            datalist = data.split("&")
            for item in datalist:
                datalistkey = item.split("=")
                if datalistkey[0] == "ssid":
                    ssid = datalistkey[1]
                if datalistkey[0] == "passwd":
                    passwd = datalistkey[1]
    
            with open('/var/www/setup/interfaces_default', 'r') as file:
                lines  = file.readlines()
            
            for idx, line in enumerate(lines):
                if line.find("wpa-ssid") > -1:
                    lines[idx] = '  wpa-ssid "' + ssid + '"\n'
                if line.find("wpa-psk") > -1:
                    lines[idx] = '  wpa-psk "' + passwd + '"\n'
            
            with open('/var/www/setup/interfaces_default', 'w') as file:
                file.writelines( lines )
    
            subprocess.call("/var/www/setup/default.sh 2>&1 >> /var/log/smartconnect.log", shell=True)      #, Shell=True
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


    @staticmethod
    def check_connected():
        try:
            response = urllib2.urlopen('http://74.125.228.100', timeout=10)
            return True
        except urllib2.URLError as err: pass
        return False

    @staticmethod
    def smart_connect():
        logger.debug("Calling SmartConnect setup.sh")
        subprocess.call("/var/www/setup/setup.sh 2>&1 >> /var/log/smartconnect.log", shell=True)


class schedule:
    def GET(self):
        with open("schedule.json") as f:
            filecontents = json.load(f)
            return render.schedule(json.dumps(filecontents), str(datetime.now()))    # a JSON object (string) at this point

    def POST(self):
        data = web.data()      #web.input gives back a Storage < > thing
        mydata = json.loads(data)
        with open("schedule.json") as f:
            my_schedule = json.load(f)
            week = {'Sunday':0, 'Monday':1, 'Tuesday':2, 'Wednesday':3, 'Thursday':4, 'Friday':5, 'Saturday':6}
            my_schedule['days'][week[mydata['day']]]['time']['startTime'] = mydata['time']['startTime']
            my_schedule['days'][week[mydata['day']]]['time']['endTime'] = mydata['time']['endTime']
            tellHeatProc(None, True) # FLUSH the cache so that the other process picks up the changes
        with open("schedule.json", "wb") as output_file:
            json.dump(my_schedule, output_file)

        return json.dumps("OK")

def tempdata():

    try:
        one_wire = mem.one_wire  # gets set below, on init      "/sys/bus/w1/devices/28-000004e0badb/w1_slave"
        pipe = Popen(["cat", one_wire], stdout=PIPE)
        result = pipe.communicate()[0]
        result_list = result.split("=")    
        try:
            temp_C = float(result_list[-1])/1000 # temp in Celcius
        except ValueError:                      # probably means we can't read the 1-wire sensor
            #logger.warn('Could not get a value from 1-wire connector.  Using ' + one_wire )
            temp_C = 0
        return temp_C

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))

def catchButton(btn):    # GPIO

    try:
        time.sleep(0.05)        
        if GPIO.input(btn) != GPIO.HIGH:        # check to see if the input button is still high, protect against EMI false positive
            return
    
        if (GPIO.input(gpio_btn_heat_sig) == GPIO.HIGH & GPIO.input(gpio_btn_pump_sig) == GPIO.HIGH):  # both buttons pressed
            mem.lcd_connection.send(["Live long", "and prosper!", 1])       #easter egg
            mem.lcd_connection.send(["iSPRESSO", "", 0])       #easter egg
            logger.info("You found an easter egg!")
            return

        if btn == gpio_btn_heat_sig:
            
            now = time.time()
            if now - mem.time_heat_button_pressed < 1:
                mem.time_heat_button_pressed = now
                return
            mem.time_heat_button_pressed = now    
    
            if param.mode == "off":
                GPIO.output(gpio_btn_heat_led, GPIO.HIGH)       # this is a bit of a hack because the temp control also regulates the LED but putting it here gives better user experience.
                logger.debug("catchButton:  telling Heat Proc AUTO (ON) ")
                tellHeatProc("auto")
            else:
                GPIO.output(gpio_btn_heat_led, GPIO.LOW) 
                logger.debug("catchButton:  telling Heat Proc OFF")
                tellHeatProc("off")
    
        elif btn == gpio_btn_pump_sig:
            logger.debug("catchButton:  telling Brew Proc (toggle)")
            time_stamp = time.time()
            brew_plan = [['Presoak', mem.presoak_time], ['Wait', mem.wait_time], ['Brew', mem.brew_time]]
            mem.brew_connection.send([time_stamp, brew_plan])

    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))


class logdisplay:
    def GET(self):
        fp=open('/var/log/ispresso.log','rU')             #reading file from file path
        text=fp.read()                      #no problem found till this line.
        fp.close()            
        return render.logdisplay(text) #calling file_display.html 

def cleanUp():
    logger.info("Shutting down...")
    mem.lcd_connection.send(["iSPRESSO", "Shutting down", 0])
    execfile ('shutdown.py')

if __name__ == '__main__':
    
    try:

	logger_init()

        os.chdir("/var/www")
    
        call(["modprobe", "w1-gpio"])
        call(["modprobe", "w1-therm"])
        call(["modprobe", "i2c-dev"])
        
        base_dir = '/sys/bus/w1/devices/'
        
	try:
	    base_dir = glob.glob(base_dir + '28*')[0]
	except:
	    logger.error("EPIC FAIL!  1-Wire Temp sensor not found in " + base_dir)

        mem.one_wire = base_dir + '/w1_slave'
        
        urls = ("/", "ispresso", "/settings", "settings", "/schedule", "schedule", "/advanced", "advanced", "/getstatus", "getstatus", "/logdisplay", "logdisplay", "/setup", "setup")
    
        render = web.template.render("/var/www/templates/")
    
        app = web.application(urls, globals()) 
    
        atexit.register(cleanUp)
    
        statusQ = Queue(2)       
        parent_conn, child_conn = Pipe()
    
        lcd_parent_conn, lcd_child_conn = Pipe()
        mem.lcd_connection = lcd_parent_conn

        initialize()

        brew_parent_conn, brew_child_conn = Pipe()
        mem.brew_connection = brew_parent_conn
        
        GPIO.add_event_detect(gpio_btn_heat_sig, GPIO.RISING, callback=catchButton, bouncetime=250)  
        GPIO.add_event_detect(gpio_btn_pump_sig, GPIO.RISING, callback=catchButton, bouncetime=250)       # was RISING, at one point HIGH. who knows

        mem.heat_connection = parent_conn
        lcdproc = Process(name = "lcdControlProc", target=lcdControlProc, args=(lcd_child_conn,))
        lcdproc.start()
        
        brewproc = Process(name = "brewControlProc", target=brewControlProc, args=(brew_child_conn,))
        brewproc.start()

        p = Process(name = "tempControlProc", target=tempControlProc, args=(param.mode, param.cycle_time, param.duty_cycle, \
                                            param.set_point, param.k_param, param.i_param, param.d_param, statusQ, child_conn))
        p.start()

        app.add_processor(add_global_hook(parent_conn, statusQ))
        app.run()

    except KeyboardInterrupt:
        cleanUp()
        sys.exit()
        
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logger.error(''.join('!! ' + line for line in traceback.format_exception(exc_type, exc_value, exc_traceback)))

        cleanUp()
        sys.exit()

    if mem.scheduler_enabled:           # if program is just been started, set the mode according to the schedule, assuming schedule is ON
        tellHeatProc("auto") 



