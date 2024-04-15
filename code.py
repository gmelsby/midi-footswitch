import asyncio
import board
import usb_midi
import adafruit_midi
import simpleio
import digitalio
from adafruit_debouncer import Debouncer
from analogio import AnalogIn
from adafruit_midi.control_change import ControlChange

# board wiring info
potentiometer_pin = board.A0
switch_pin = board.GP13

# change in modulation value necessary to trigger midi change
EXP_SENSITIVITY = 2

#  midi setup
midi = adafruit_midi.MIDI(
    midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=1
)
# swtich setup
pin1 = digitalio.DigitalInOut(switch_pin)
pin1.direction = digitalio.Direction.INPUT
pin1.pull = digitalio.Pull.UP
switch1 = Debouncer(pin1)



async def monitorExpressionPedal(midi_out, mod_pot):
    # last read value
    last_value = 0
    while True:
        # Prints out the min/max values from potentiometer to the serial monitor and plotter
        # print((mod_pot.value,))
        await asyncio.sleep(0.025)

        #  map range of potentiometer input to midi values - update the min/max values below
        current_value = round(simpleio.map_range(mod_pot.value, 400, 65535, 0, 127))

        #  if modulation value is updated...
        if abs(current_value - last_value) >= EXP_SENSITIVITY:
            #  update mod_val2
            last_value = current_value
            #  create integer
            modulation = int(last_value)
            #  create CC message
            modWheel = ControlChange(11, modulation)
            #  send CC message
            print(modWheel)
            midi_out.send(modWheel)
            
async def monitorSwitch(midi_out, cc_channel, switch):
    pressed = False
    while True:
        await asyncio.sleep(0.025)
        switch.update()
        if switch.fell:
            pressed = not pressed
            # create CC message
            print(f'pedal status: {"on" if pressed else "off"}')
            midi_out.send(ControlChange(cc_channel, int(pressed) * 127))

async def main():
    exp_task = asyncio.create_task(monitorExpressionPedal(midi, AnalogIn(potentiometer_pin)))
    switch_task = asyncio.create_task(monitorSwitch(midi, 80, switch1))
    await asyncio.gather(exp_task, switch_task)
    
asyncio.run(main())
