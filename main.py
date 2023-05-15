import time
from dfplayermini import Player
from machine import Pin
import utime
import random
import micropython
from primitives import Switch
import uasyncio as asyncio

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import List, Tuple, Optional
    from enum import IntEnum
else:
    IntEnum = object

micropython.alloc_emergency_exception_buf(100)


class State(IntEnum):
    STANDBY = 0
    CALLBACK = 1
    DIAL_TONE = 2
    INCOMING_CALL = 3


class RetroPhone:
    def __init__(self):
        self.alive = True
        self.state = State.STANDBY
        self.audioPlayer = Player(pin_TX=13, pin_RX=12)
        self.bellAH = Pin(21, Pin.OUT)
        self.offHookAH = Pin(27, Pin.IN, Pin.PULL_DOWN)
        self.rotaryPulseAL = Pin(23, Pin.IN, Pin.PULL_DOWN)
        self.rotaryActionAH = Pin(18, Pin.IN, Pin.PULL_DOWN)
        self.switches: [Switch] = []

        red_button_sw = Switch(Pin(14, Pin.IN, Pin.PULL_UP))
        red_button_sw.close_func(self.red_button_cb, ())
        self.switches.append(red_button_sw)

    def deinit(self):
        self.alive = False
        self.set_ringer(False)
        for sw in self.switches:
            await sw.deinit()
        self.switches = []

    def is_alive(self) -> bool:
        return self.alive

    def change_state(self, state_change_list: List[Tuple[State, State]]) -> bool:
        for (expected_current_state, to_state) in state_change_list:
            if not self.state == expected_current_state:
                continue
            elif to_state == self.state:
                return False
            else:
                print('changing state, from:', self.state, "to:", to_state)
                self.state = to_state
                return True
        return False

    def red_button_cb(self):
        print('red_button_cb')
        self.change_state([(State.CALLBACK, State.STANDBY),
                           (State.STANDBY, State.CALLBACK)])

    def set_ringer(self, value: bool):
        self.bellAH.value(1 if value else 0)

    def is_ringer_on(self):
        return True if self.bellAH.value() else False

    async def bell_ringer(self):
        is_active = False
        counter = 0
        try:
            while self.alive:
                if self.state == State.CALLBACK:
                    if not is_active:
                        is_active = True
                        counter = 1
                    sleep_time = 0
                    if not self.is_ringer_on():
                        self.set_ringer(True)
                        counter += 1
                        sleep_time = 2000
                    else:
                        self.set_ringer(False)
                        sleep_time = 3000

                    task = asyncio.sleep_ms(sleep_time)
                    await task

                    if counter > 5:
                        self.change_state([(State.CALLBACK, State.STANDBY)])
                else:
                    self.set_ringer(False)
                    is_active = False
                    counter = 0
                await asyncio.sleep_ms(50)

        finally:
            self.set_ringer(False)

    def perform_incoming_call(self):
        self.bellAH.value(1)
        start_time = utime.ticks_ms()
        counter = 0
        wait_time = 2000

        try:
            print("perform incoming call", self.state)
            while self.state == State.CALLBACK:
                current_time = utime.ticks_ms()
                elapsed_time = utime.ticks_diff(current_time, start_time)
                if elapsed_time >= wait_time:
                    counter = counter + 1
                    start_time = utime.ticks_ms()
                    if self.is_ringer_on():
                        self.set_ringer(False)
                        wait_time = 3000
                    else:
                        self.set_ringer(True)
                        wait_time = 2000

                # await asyncio.sleep_ms(50)
                time.sleep_ms(50)
                # if self.offHookAH.value() == 1:
                #     handle_state_change(STATE_INCOMING_CALL)
                #     return
                if counter > 10:
                    self.change_state([(State.CALLBACK, State.STANDBY)])
            return
        finally:
            self.set_ringer(False)


offHookCallbackTime = utime.ticks_ms()
rotaryActionCallbackTime = utime.ticks_ms()
rotaryPulseCallbackTime = utime.ticks_ms()
rotaryPulsePulseCount = 0
numberDialed = ""


#
# if not to_state == state:
#     print("state change, from: ", state, " to: ", to_state)
#     state = to_state
#     if to_state == STATE_EXPECT_CALLBACK:
#         print("calling perform incoming call")
#         print(perform_incoming_call())
#     elif to_state == STATE_INCOMING_CALL:
#         audioPlayer.volume(7)
#         time.sleep_ms(2000)
#         audioPlayer.play(random.randint(1, 6))


# def rotary_pulse_cb(p):
#     global rotaryPulseCallbackTime, rotaryPulsePulseCount
#
#     if not state == STATE_DIAL_TONE:
#         return
#
#     time_now = utime.ticks_ms()
#     pin_value = p.value()
#     time_diff = utime.ticks_diff(time_now, rotaryPulseCallbackTime)
#     print("pulse", time_diff, pin_value)
#
#     if time_diff < 50:
#         print("pulse ignoring noise")
#         return
#     if time_diff > 600:
#         print("pulse resetting")
#         rotaryPulsePulseCount = -1
#     if pin_value == 1:
#         return
#
#     rotaryPulseCallbackTime = time_now
#     rotaryPulsePulseCount = rotaryPulsePulseCount + 1
#     print('pulse count:', rotaryPulsePulseCount + 1)
#
#
# def rotary_action_cb(p):
#     global rotaryActionCallbackTime, rotaryPulsePulseCount, numberDialed
#
#     if not state == STATE_DIAL_TONE:
#         return
#
#     pin_value = p.value()
#     time_now = utime.ticks_ms()
#     #    print("rotary action", utime.ticks_ms(), pin_value)
#
#     if utime.ticks_diff(time_now, rotaryActionCallbackTime) < 300:
#         # print("rotary action ignoring noise")
#         return
#
#     if utime.ticks_diff(time_now, rotaryPulseCallbackTime) > 600:
#         return
#
#     rotaryActionCallbackTime = time_now
#
#     print("rotary action", pin_value)
#     if pin_value == 1:
#         rotaryPulsePulseCount = -1
#     else:
#         if rotaryPulsePulseCount > -1:
#             number = rotaryPulsePulseCount + 1
#             if number > 9:
#                 number = 0
#             numberDialed = numberDialed + str(number)
#             rotaryPulsePulseCount = -1
#             # print("number dialed:", numberDialed + "\n\n")


# def off_hook_cb(p):
#     global numberDialed
#     pin_value = p.value()
#     print("off_hook_cb", utime.ticks_ms(), pin_value)
#     # hanging up the phone should stop any audio
#     if pin_value == 0:
#         print("hanging up, going to standby")
#         audioPlayer.stop()
#         handle_state_change(STATE_STANDBY)
#     elif state == STATE_STANDBY and pin_value == 1:
#         print("handset lifted, moving to dial tone")
#         numberDialed = ""
#         handle_state_change(STATE_DIAL_TONE)


# def init():
#     red_button_sw = Switch(Pin(14, Pin.IN, Pin.PULL_UP))
#     red_button_sw.close_func(red_button_cb, ())
#     switches.append(red_button_sw)
#
#     rotaryPulseAL.irq(lambda p: rotary_pulse_cb(p), trigger=Pin.IRQ_FALLING)
#     rotaryActionAH.irq(lambda p: rotary_action_cb(p))
#     offHookAH.irq(lambda p: off_hook_cb(p))


# async def deinit():
#     global switches
#     for sw in switches:
#         await sw.deinit()
#
#     rotaryPulseAL.irq(handler=None)
#     rotaryActionAH.irq(handler=None)
#     offHookAH.irq(handler=None)
#     switches = []
    # await asyncio.sleep_ms(10)


# def callNumber(number):
#     print('calling', number)
#     audioPlayer.volume(7)
#     file_number = int(number[0])
#     audioPlayer.play(file_number)
#     # state = STATE_STANDBY


async def my_app(retro: RetroPhone):
    # global numberDialed
    while retro.is_alive():
        # if state == STATE_DIAL_TONE:
        #     if len(numberDialed) >= 3:
        #         callNumber(numberDialed)
        #         numberDialed = ""
        # await asyncio.sleep_ms(100)
        await retro.bell_ringer()


def main():
    retro = RetroPhone()
    try:
        asyncio.run(my_app(retro))
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(retro.deinit())


if __name__ == '__main__':
    main()
