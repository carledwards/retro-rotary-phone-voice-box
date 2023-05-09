import time

from dfplayermini import Player
from machine import Pin
import utime
import random

STATE_STANDBY = 0
STATE_EXPECT_CALLBACK = 1
STATE_DIAL_TONE = 2
STATE_INCOMING_CALL = 3

state = STATE_STANDBY

audioPlayer = Player(pin_TX=13, pin_RX=12)

redButtonAH = Pin(14, Pin.IN, Pin.PULL_DOWN)
bellAH = Pin(21, Pin.OUT)
offHookAH = Pin(27, Pin.IN, Pin.PULL_DOWN)
rotaryPulseAL = Pin(23, Pin.IN, Pin.PULL_DOWN)
rotaryActionAH = Pin(18, Pin.IN, Pin.PULL_DOWN)

redButtonCallbackTime = utime.ticks_ms()
offHookCallbackTime = utime.ticks_ms()
rotaryActionCallbackTime = utime.ticks_ms()
rotaryPulseCallbackTime = utime.ticks_ms()
rotaryPulsePulseCount = 0
numberDialed = ""

def perform_incoming_call():
    global state
    bellAH.value(1)
    start_time = utime.ticks_ms()
    counter = 0
    wait_time = 2000
    bell_on = True

    try:
        while state == STATE_EXPECT_CALLBACK:
            current_time = utime.ticks_ms()
            elapsed_time = utime.ticks_diff(current_time, start_time)
            if elapsed_time >= wait_time:
                counter = counter + 1
                start_time = utime.ticks_ms()
                if bell_on:
                    bellAH.value(0)
                    bell_on = False
                    wait_time = 3000
                else:
                    bellAH.value(1)
                    bell_on = True
                    wait_time = 2000

            utime.sleep_ms(50)
            if offHookAH.value() == 1:
                state = STATE_INCOMING_CALL
                return
            if counter > 10:
                state = STATE_STANDBY
                return
        state = STATE_STANDBY
        return
    finally:
        bellAH.value(0)


def red_button_cb(p):
    global state, redButtonCallbackTime
    print("red_button_cb", utime.ticks_ms(), p.value())

    if utime.ticks_diff(utime.ticks_ms(), redButtonCallbackTime) < 500:
        print("red_button_cb ignoring noise")
        return
    redButtonCallbackTime = utime.ticks_ms()

    if state == STATE_EXPECT_CALLBACK:
        state = STATE_STANDBY
    elif state == STATE_STANDBY:
        state = STATE_EXPECT_CALLBACK


def rotary_pulse_cb(p):
    global rotaryPulseCallbackTime, rotaryPulsePulseCount

    if not state == STATE_DIAL_TONE:
        return

    time_now = utime.ticks_ms()
    pin_value = p.value()
    time_diff = utime.ticks_diff(time_now, rotaryPulseCallbackTime)
    print("pulse", time_diff, pin_value)

    if time_diff < 50:
        print("pulse ignoring noise")
        return
    if time_diff > 600:
        print("pulse resetting")
        rotaryPulsePulseCount = -1
    if pin_value == 1:
        return

    rotaryPulseCallbackTime = time_now
    rotaryPulsePulseCount = rotaryPulsePulseCount + 1
    print('pulse count:', rotaryPulsePulseCount + 1)


def rotary_action_cb(p):
    global rotaryActionCallbackTime, rotaryPulsePulseCount, numberDialed

    if not state == STATE_DIAL_TONE:
        return

    pin_value = p.value()
    time_now = utime.ticks_ms()
#    print("rotary action", utime.ticks_ms(), pin_value)

    if utime.ticks_diff(time_now, rotaryActionCallbackTime) < 300:
        #print("rotary action ignoring noise")
        return

    if utime.ticks_diff(time_now, rotaryPulseCallbackTime) > 600:
        return

    rotaryActionCallbackTime = time_now

    print("rotary action", pin_value)
    if pin_value == 1:
        rotaryPulsePulseCount = -1
    else:
        if rotaryPulsePulseCount > -1:
            number = rotaryPulsePulseCount + 1
            if number > 9:
                number = 0
            numberDialed = numberDialed + str(number)
            rotaryPulsePulseCount = -1
            # print("number dialed:", numberDialed + "\n\n")

def off_hook_cb(p):
    global state, numberDialed
    pin_value = p.value()
    print("off_hook_cb", utime.ticks_ms(), pin_value)
    # hanging up the phone should stop any audio
    if pin_value == 0:
        print("hanging up, going to standby")
        audioPlayer.stop()
        state = STATE_STANDBY
    elif state == STATE_STANDBY and pin_value == 1:
        print("handset lifted, moving to dial tone")
        numberDialed = ""
        state = STATE_DIAL_TONE


def init():
    redButtonAH.irq(lambda p: red_button_cb(p), trigger=Pin.IRQ_RISING)
    rotaryPulseAL.irq(lambda p: rotary_pulse_cb(p), trigger=Pin.IRQ_FALLING)
    rotaryActionAH.irq(lambda p: rotary_action_cb(p))
    offHookAH.irq(lambda p: off_hook_cb(p))


def deinit():
    redButtonAH.irq(handler=None)
    rotaryPulseAL.irq(handler=None)
    rotaryActionAH.irq(handler=None)
    offHookAH.irq(handler=None)

def callNumber(number):
    global state
    print('calling', number)
    audioPlayer.volume(7)
    file_number = int(number[0])
    audioPlayer.play(file_number)
    # state = STATE_STANDBY

def main():
    global state, numberDialed
    init()
    try:
        while True:
            if state == STATE_EXPECT_CALLBACK:
                perform_incoming_call()
                if state == STATE_INCOMING_CALL:
                    audioPlayer.volume(7)
                    time.sleep_ms(2000)
                    audioPlayer.play(random.randint(1, 6))
            elif state == STATE_DIAL_TONE:
                if len(numberDialed) >= 3:
                    callNumber(numberDialed)
                    numberDialed = ""
            time.sleep_ms(100)
        pass
    except KeyboardInterrupt:
        pass
    finally:
        deinit()


if __name__ == '__main__':
    main()
