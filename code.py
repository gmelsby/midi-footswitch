import asyncio
import json
import board
import usb_midi
import adafruit_midi
import simpleio
import digitalio
from adafruit_debouncer import Debouncer
from analogio import AnalogIn
from adafruit_midi.control_change import ControlChange

# enables specifying pins from a json string
PIN_DICT = {
    'GP0': board.GP0,
    'GP1': board.GP1,
    'GP2': board.GP2,
    'GP3': board.GP3,
    'GP4': board.GP4,
    'GP5': board.GP5,
    'GP6': board.GP6,
    'GP7': board.GP7,
    'GP8': board.GP8,
    'GP9': board.GP9,
    'GP10': board.GP10,
    'GP11': board.GP11,
    'GP12': board.GP12,
    'GP13': board.GP13,
    'GP14': board.GP14,
    'GP15': board.GP15,
    'GP16': board.GP16,
    'GP17': board.GP17,
    'GP18': board.GP18,
    'GP19': board.GP19,
    'GP20': board.GP20,
    'GP21': board.GP21,
    'GP22': board.GP22,
    'GP23': board.GP23,
    'GP24': board.GP24,
    'GP25': board.GP25,
    'GP26': board.GP26,
    'GP27': board.GP27,
    'GP28': board.GP28,
    'A0': board.A0,
    'A1': board.A1,
    'A2': board.A2
}


class FootSwitch:
    """
    Encapsulation for foot switches
    Keeps track of foot switch state and mode
    """

    def __init__(self, midi_out, pin, cc_parameter, update_rate=0, momentary=False):
        # switch setup
        pin_in = digitalio.DigitalInOut(pin)
        pin_in.direction = digitalio.Direction.INPUT
        pin_in.pull = digitalio.Pull.UP
        self.switch = Debouncer(pin_in)

        self.pressed = False
        self.midi_out = midi_out
        self.cc_parameter = cc_parameter
        self.update_rate = update_rate
        self.momentary = momentary


    async def monitor(self):
        """
        Loops while monitoring switch state
        Sends changes to midi_out on cc_parameter
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
            cc_message = ControlChange(self.cc_parameter, int(self.pressed) * 127)
            print(f'{cc_message} pedal status: {"on" if self.pressed else "off"}')
            self.midi_out.send(cc_message)

    async def momentary_poll(self):
        """
        Behavior for momentary-type footswitch
        When the switch is pressed sends 127, when released sends 0
        """
        self.switch.update()
        if self.switch.fell:
            cc_message = ControlChange(self.cc_parameter, 127)
            print(f'{cc_message} pedal status: {"pressed"}')
            self.midi_out.send(cc_message)

        if self.switch.rose:
            cc_message = ControlChange(self.cc_parameter, 0)
            print(f'{cc_message} pedal status: {"rose"}')
            self.midi_out.send(cc_message)


class ModeChangeFootSwitch(FootSwitch):
    """
    FootSwitch that can be changed from momentary to toggle with a flip of another switch
    """

    def __init__(self, midi_out, pin, flip_pin, cc_parameter, update_rate=0, flip_update_rate=0.025, momentary=False):
        super().__init__(midi_out, pin, cc_parameter, update_rate, momentary)
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


class ExpressionPedal:
    """
    Encapsulation for expression pedal
    """

    def __init__(self, midi_out, pin, cc_parameter=11, update_rate=0.025, sensitivity=2, pot_min=400, pot_max=65535):
        self.mod_pot = AnalogIn(pin)
        self.midi_out = midi_out
        self.cc_parameter = cc_parameter
        self.last_value = 0
        self.update_rate = update_rate
        self.sensitivity = sensitivity
        self.pot_min = pot_min
        self.pot_max = pot_max

    async def monitor(self):
        """
        Polls the poteniometer at the rate specified by update_rate
        Sends MIDI CC messages if change exceeds sensitivty
        """
        while True:
            await asyncio.sleep(self.update_rate)

            # maps range of potentiometer input to midi values
            current_value = round(simpleio.map_range(self.mod_pot.value, self.pot_min, self.pot_max, 0, 127))

            # if change in value is larger than sensitivity or value is at the ends of the range
            if abs(current_value - self.last_value) >= self.sensitivity or (current_value != self.last_value and current_value in (0, 127)):
                self.last_value = current_value
                # create CC message
                modWheel = ControlChange(self.cc_parameter, current_value)
                # send CC message
                print(modWheel)
                self.midi_out.send(modWheel)


async def main():
    config_file = open('config.json', mode='r')
    config = json.load(config_file)

    #  midi setup
    # use 'midi_out_channel' from config.json, if exists, else default to 1
    midi = adafruit_midi.MIDI(
        midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1], 
        out_channel=config['midi_out_channel'] if 'midi_out_channel' in config else 1 
    )
    print(f"MIDI channel: {midi.out_channel}")

    tasks = []
    # add specified expression pedals to tasks
    if 'expression_pedals' in config:
        for pedal in config['expression_pedals']:
            pedal['pin'] = PIN_DICT[pedal['pin']]
            exp_pedal = ExpressionPedal(midi, **pedal)
            tasks.append(asyncio.create_task(exp_pedal.monitor()))

    # add specified switches to tasks
    if 'switches' in config:
        for switch in config ['switches']:
            switch['pin'] = PIN_DICT[switch['pin']]
            # default to standard foot switch, change to mode switch if flip_pin specified
            switch_class = FootSwitch 
            if 'flip_pin' in switch:
                switch['flip_pin'] = PIN_DICT[switch['flip_pin']]
                switch_class = ModeChangeFootSwitch
            foot_switch = switch_class(midi, **switch)
            tasks.append(asyncio.create_task(foot_switch.monitor()))

    await asyncio.gather(*tasks)

asyncio.run(main())
