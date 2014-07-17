
# Constructor (...)*********************************************************
# The parameters specified here are those for for which we can't set up
# reliable defaults, so we need to have the user set them.
#***************************************************************************

import time

class simplepid(object):

    def __init__(self, setpoint, measure, kp, ki, kd, forward = True):
        
        self.setpoint = setpoint
        self.measure = measure
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.forward = forward      # default to True in __init__, this is whether the pid is forward or reverse

        self.output_min = 0
        self.output_max = 100        
        self.sample_time = 1000    # //default Controller Sample Time is 1 seconds
    
        self.last_measure = None
    #    PID::SetControllerDirection(ControllerDirection);
        setTunings(self.kp, self.ki, self.kd)
    
        last_time = time.localtime() - sample_time;    # TODO: need to convert to millisec

 
 
# Compute() **********************************************************************
# This, as they say, is where the magic happens. this function should be called
# every time "void loop()" executes. the function will decide for itself whether a new
# pid Output needs to be computed. 
#**********************************************************************************

    def compute(self):

        output = None
        if (self.last_time == None | time.localtime() - self.last_time >= self.sample_time):     # first time thru if self.last_time == None.  
                                                                                        # otherwise more than sample_time has passed since last loop
            error = self.setpoint - self.measure        # Compute all the working error variables
            i_value = (self.ki * error);
            if (i_value > self.output_max):
                i_value = self.output_max
            elif (i_value < output_min):
                i_value = self.output_min
                 
            input_change = (self.measure - self.last_measure)
            
            # Compute PID Output
            output = self.kp * error + i_value - self.kd * input_change
          
            if output > self.output_max:
                output = self.output_max
            elif output < self.output_min:
                output = self.output_min
                
            self.last_measure = measure

        self.last_time = time.localtime()
        
        return output       # will have to check for None in calling procedure.  Dont know how pythony that is.
      


# SetTunings(...)*************************************************************
# This function allows the controller's dynamic performance to be adjusted.
# it's called automatically from the constructor, but tunings can also
# be adjusted on the fly during normal operation
# *****************************************************************************

    def setTunings(kp, ki, kd):
        if (kp < 0 || ki < 0 || kd < 0):
            return
   
        sample_time_in_sec = self.sample_time / 1000
        self.kp = kp
        self.ki = ki * sample_time_in_sec
        self.kd = kd / sample_time_in_sec
 
        if (self.forward == False):
            self.kp = (0 - self.kp)
            self.ki = (0 - self.ki)
            self.kd = (0 - self.kd)

  
# Setsample_time(...) *********************************************************
# sets the period, in Milliseconds, at which the calculation is performed
#******************************************************************************

    def setSampleTime(self, new_sample_time):
        if (new_sample_time > 0):
            ratio = new_sample_time / self.sample_time
            ki *= ratio
            kd /= ratio
            self.sample_time = new_sample_time

 
# SetOutputLimits(...)****************************************************
# This function will be used far more often than SetInputLimits. while
# the input to the controller will generally be in the 0-1023 range (which is
# the default already,) the output will be a little different. maybe they'll
# be doing a time window and will need 0-8000 or something. or maybe they'll
# want to clamp it from 0-125. who knows. at any rate, that can all be done
# here.
#**************************************************************************

def setOutputLimits(self, min = None, max = None):

    if min is not None:
        self.output_min = min
        if self.ki < min:
            self.ki = min
    if max is not None:
        self.output_max = max
        if self.ki > max:
            self.ki = max
            

# SetMode(...)****************************************************************
# Allows the controller Mode to be set to manual (0) or Automatic (non-zero)
# when the transition from manual to auto occurs, the controller is
# automatically initialized
# *****************************************************************************
void PID::SetMode(int Mode)
{
    bool newAuto = (Mode == AUTOMATIC);
    if(newAuto == !inAuto)
    { /*we just went from manual to auto*/
        PID::Initialize();
    }
    inAuto = newAuto;
}
 
/* Initialize()****************************************************************
* does all the things that need to happen to ensure a bumpless transfer
* from manual to automatic mode.
******************************************************************************/
void PID::Initialize()
{
   ITerm = *myOutput;
   lastInput = *myInput;
   if(ITerm > outMax) ITerm = outMax;
   else if(ITerm < outMin) ITerm = outMin;
}

/* SetControllerDirection(...)*************************************************
* The PID will either be connected to a DIRECT acting process (+Output leads
* to +Input) or a REVERSE acting process(+Output leads to -Input.) we need to
* know which one, because otherwise we may increase the output when we should
* be decreasing. This is called from the constructor.
******************************************************************************/
void PID::SetControllerDirection(int Direction)
{
   if(inAuto && Direction !=controllerDirection)
   {
kp = (0 - kp);
      ki = (0 - ki);
      kd = (0 - kd);
   }
   controllerDirection = Direction;
}

/* Status Funcions*************************************************************
* Just because you set the kp=-1 doesn't mean it actually happened. these
* functions query the internal state of the PID. they're here for display
* purposes. this are the functions the PID Front-end uses for example
******************************************************************************/
double PID::Getkp(){ return dispkp; }
double PID::GetKi(){ return dispKi;}
double PID::GetKd(){ return dispKd;}
int PID::GetMode(){ return inAuto ? AUTOMATIC : MANUAL;}
int PID::GetDirection(){ return controllerDirection;}

