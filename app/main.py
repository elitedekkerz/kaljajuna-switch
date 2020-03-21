import utime
import machine

mqtt = None

class servo:
    def __init__(self, pin):
        servo_pin = machine.Pin(pin)
        self.pwm = machine.PWM(servo_pin, freq = 50)
        self.mind = 40
        self.maxd = 115

    def set_limits(self, min_duty, max_duty):
        self.mind = min_duty
        self.maxd = max_duty

    def set_angle(self, angle):
        if angle < 0:
            d = 0
        else:
            angle = max(0, min(180, angle))
            d = self.mind + (self.maxd - self.mind) * angle // 180 

        print("duty {}->{}".format(angle, d))
        self.pwm.duty(d)

    def set_duty(self, d):
        self.pwm.duty(d)
        print("duty {}".format(d))

        
s = servo(2)
pin_up_time = 0
pin_down = False

def pin_callback(p):
    global mqtt
    global pin_down
    global pin_up_time

    if p.value() == 0:
        if pin_down == False:
            mqtt.pub("status", "occupied")
            pin_down = True

        pin_up_time = 0
    else:
        pin_up_time = utime.ticks_ms()

def callback_angle(message):
    d = int(message)
    s.set_angle(d)

def callback_duty(message):
    d = int(message)
    s.set_duty(d)

def callback_route(message):
    if message == "b":
        s.set_angle(150)
    elif message == "c":
        s.set_angle(60)

def run(mqtt_obj, parameters):
    #Make mqtt object global, so it can be called from interrupts
    global mqtt 
    mqtt = mqtt_obj
    
    #Set project name as prefix so we can easily filter topics
    #Final topic will be in form:
    #UID/prefix/user_topic
    mqtt.set_prefix("switch")

    s.set_limits(20, 120)
    s.set_angle(90)

    #Subscribe
    mqtt.sub("angle", callback_angle)
    mqtt.sub("duty", callback_duty)
    mqtt.sub("route", callback_route)

    #Setup callback for pin 
    p0 = machine.Pin(0, machine.Pin.IN)
    p0.irq(trigger=machine.Pin.IRQ_FALLING | machine.Pin.IRQ_RISING, handler=pin_callback)

    #Main loop
    while True:
        #Call periodicaly to check if we have recived new messages. 
        mqtt.check_msg()

        utime.sleep(0.1)

        global pin_down
        global pin_up_time
        if pin_down == True and pin_up_time > 0:
            dt = utime.ticks_diff(utime.ticks_ms(), pin_up_time)
            if dt > 1000:
                mqtt.pub("status", "free")
                pin_down = False