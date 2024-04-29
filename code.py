import asyncio
import board
import usb_midi
import adafruit_midi
import simpleio
import digitalio
from adafruit_debouncer import Debouncer
from analogio import AnalogIn
from adafruit_midi.control_change import ControlChange

# change in modulation value necessary to trigger midi change
EXP_SENSITIVITY = 2

# board wiring info
POTENTIONMETER_PIN = board.A0
SWITCH_PIN = board.GP13
FLIPSWITCH_PIN = board.GP15


class FootSwitch:
    """
    Encapsulation for foot switches
    Keeps track of foot switch state and mode
    """

    def __init__(self, pin, midi_out, cc_channel, update_rate, momentary=False):
        # switch setup
        pin_in = digitalio.DigitalInOut(pin)
        pin_in.direction = digitalio.Direction.INPUT
        pin_in.pull = digitalio.Pull.UP
        self.switch = Debouncer(pin_in)
        
        self.pressed = False
        self.midi_out = midi_out
        self.cc_channel = cc_channel
        self.update_rate = update_rate
        self.momentary = momentary
      
      
    async def monitor(self):
        """
        Loops while monitoring switch state
        Sends changes to midi_out on cc_channel
        """
        while True:
            await asyncio.sleep(self.update_rate)
            if not self.momentary:
                await self.toggle_poll()
            else:
                await self.momentary_poll()
       
       
    async def toggle_poll(self):
        """
        Behavior for toggle-type footswitch
        Pressing the switch toggles the footswitch state between on and off
        """
        self.switch.update()
        if self.switch.fell:
            self.pressed = not self.pressed
            # create CC message
            print(f'pedal status: {"on" if self.pressed else "off"}')
            self.midi_out.send(ControlChange(self.cc_channel, int(self.pressed) * 127))
            
    async def momentary_poll(self):
        """
        Behavior for momentary-type footswitch
        When the switch is pressed sends 127, when released sends 0
        """
        self.switch.update()
        if self.switch.fell:
            print(f'pedal status: {"pressed"}')
            self.midi_out.send(ControlChange(self.cc_channel, 127))
            
        if self.switch.rose:
            print(f'pedal status: {"rose"}')
            self.midi_out.send(ControlChange(self.cc_channel, 0))
            

class ModeChangeFootSwitch(FootSwitch):
    """
    FootSwitch that can be changed from momentary to toggle with a flip of another switch
    """
    
    def __init__(self, pin, flip_pin, midi_out, cc_channel, update_rate, flip_update_rate=0.025, momentary=False):
        super().__init__(pin, midi_out, cc_channel, update_rate, momentary)
        self.flip_pin = digitalio.DigitalInOut(flip_pin)
        self.flip_pin.direction = digitalio.Direction.INPUT
        self.flip_pin.pull = digitalio.Pull.UP
        self.flip_update_rate = flip_update_rate
        
    async def monitor(self):
        """
        Overrides parent method, includes monitoring of flip switch
        """
        footswitch_monitor_task = super().monitor()
        flipswitch_monitor_task = self.monitorFlipSwitch()
        
        await asyncio.gather(footswitch_monitor_task, flipswitch_monitor_task)
        
    async def monitorFlipSwitch(self):
        """
        Polls the flippable switch for changes
        If a change is detected, changes the mode of the footswitch
        """
        while True:
            await asyncio.sleep(self.flip_update_rate)
            if self.flip_pin.value != self.momentary:
                print(f'switch flipped: {"momentary" if self.flip_pin.value else "toggle"}')
                self.momentary = self.flip_pin.value
            
        


async def monitorExpressionPedal(midi_out, mod_pot):
    # last read value
    last_value = 0
    while True:
        # Prints out the min/max values from potentiometer to the serial monitor and plotter
        # print((mod_pot.value,))
        await asyncio.sleep(0.0025)

        #  map range of potentiometer input to midi values - update the min/max values below
        current_value = round(simpleio.map_range(mod_pot.value, 400, 65535, 0, 127))

        # if change in value is larger than sensitivity or value is at the ends of the range
        if abs(current_value - last_value) >= EXP_SENSITIVITY or (current_value != last_value and current_value in [0, 127]):
            #  update mod_val2
            last_value = current_value
            #  create integer
            modulation = int(last_value)
            #  create CC message
            modWheel = ControlChange(11, modulation)
            #  send CC message
            print(modWheel)
            midi_out.send(modWheel)


async def main():
    #  midi setup
    midi = adafruit_midi.MIDI(
        midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], out_channel=1
    )
    
    exp_task = asyncio.create_task(monitorExpressionPedal(midi, AnalogIn(POTENTIONMETER_PIN)))
    
    foot_switch = ModeChangeFootSwitch(SWITCH_PIN, FLIPSWITCH_PIN, midi, 80, 0, momentary=True)
    switch_task = asyncio.create_task(foot_switch.monitor())
    
    await asyncio.gather(exp_task, switch_task)

asyncio.run(main())
