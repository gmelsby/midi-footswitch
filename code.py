import asyncio
import json
import board # type: ignore
import usb_midi
import adafruit_midi
import simpleio
import digitalio
from adafruit_debouncer import Button
from analogio import AnalogIn
from adafruit_midi.control_change import ControlChange

# easy switch for console output only in debug mode
DEBUG = True

# replaces print so DEBUG toggles console output
def log(s):
    if DEBUG:
        print(s)

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
        self.switch = Button(pin_in)

        self.pin = pin
        self.pressed = False
        self.midi_out = midi_out
        self.cc_parameter = cc_parameter
        self.update_rate = update_rate
        self.momentary = momentary
        self.mode_change = False


    async def monitor(self):
        """
        Loops while monitoring switch state
        Sends changes to midi_out on cc_parameter
        """
        while True:
            await asyncio.sleep(self.update_rate)
            if self.mode_change:
                await self.mode_change_poll()
                continue

            if not self.momentary:
                await self.toggle_poll()
            else:
                await self.momentary_poll()


    async def mode_change_poll(self):
        """
        Behavior for changing mode on the foot_switch
        """
        self.switch.update()
        if self.switch.short_count == 0:
            return
        # single tap changes to toggle
        elif self.switch.short_count == 1:
            self.momentary = False
        # double tap (or more) changes to momentary
        else:
            self.momentary = True

        log(f'Pedal {self.pin} switched to  {"momentary" if self.momentary else "toggle"} mode')

    async def toggle_poll(self):
        """
        Behavior for toggle-type foot_switch
        Pressing the switch toggles the foot_switch state between on and off
        """
        self.switch.update()
        if self.switch.pressed:
            self.pressed = not self.pressed
            # create CC message
            cc_message = ControlChange(self.cc_parameter, int(self.pressed) * 127)
            log(f'{cc_message} pedal status: {"on" if self.pressed else "off"}')
            self.midi_out.send(cc_message)

    async def momentary_poll(self):
        """
        Behavior for momentary-type foot_switch
        When the switch is pressed sends 127, when released sends 0
        """
        self.switch.update()
        if self.switch.pressed:
            cc_message = ControlChange(self.cc_parameter, 127)
            log(f'{cc_message} pedal status: {"pressed"}')
            self.midi_out.send(cc_message)

        if self.switch.released:
            cc_message = ControlChange(self.cc_parameter, 0)
            log(f'{cc_message} pedal status: {"released"}')
            self.midi_out.send(cc_message)

    def __str__(self):
        """
        Represents the Foot Switch as a string
        """
        return '\n\t'.join([
            f'{self.__class__.__name__}:',
            f'pin: {self.pin}',
            f'cc_parameter: {self.cc_parameter}',
            f'update_rate: {self.update_rate}',
            f'momentary: {self.momentary}'])



class ModeChangeSwitch():
    """
    Flip switch that enables changing input mode on foot switches
    """
    def __init__(self, foot_switches, pin, update_rate=0.1):
        self.foot_switches = foot_switches
        self.pin_board_info = pin
        self.pin = digitalio.DigitalInOut(pin)
        self.pin.direction = digitalio.Direction.INPUT
        self.pin.pull = digitalio.Pull.UP
        self.update_rate = update_rate
        self.is_on = False

    async def monitor(self):
        """
        Polls the flippable switch for changes
        If a change is detected, enables/disables changing input mode on foot switches
        """
        while True:
            await asyncio.sleep(self.update_rate)
            if self.pin.value != self.is_on:
                self.is_on = self.pin.value
                log(f'toggle switch flipped: {"on" if self.is_on else "off"}')

                for foot_switch in self.foot_switches:
                    foot_switch.mode_change = self.is_on

    def __str__(self):
        """
        Represents the toggle switch as a string
        """
        return '\n\t'.join([
            f'{self.__class__.__name__}:',
            f'pin: {self.pin_board_info}',
            f'update_rate: {self.update_rate}',
            f'FootSwitches: {", ".join(str(foot_switch.pin) for foot_switch in self.foot_switches)}'
        ])


class ExpressionPedal:
    """
    Encapsulation for expression pedal
    """

    def __init__(self, midi_out, pin, cc_parameter=11, update_rate=0.025, sensitivity=2, pot_min=400, pot_max=65535):
        self.pin = pin
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
        Polls the potentiometer at the rate specified by update_rate
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
                log(modWheel)
                self.midi_out.send(modWheel)

    def __str__(self):
        """
        Represents the Expression Pedal as a string
        """
        return '\n\t'.join([
            f'{self.__class__.__name__}:',
            f'pin: {self.pin}',
            f'cc_parameter: {self.cc_parameter}',
            f'update_rate: {self.update_rate}',
            f'sensitivity: {self.sensitivity}',
            f'pot_min: {self.pot_min}',
            f'pot_max: {self.pot_max}'])

async def main():
    config_file = open('config.json', mode='r')
    config = json.load(config_file)

    # midi setup
    # use 'midi_out_channel' from config.json, if exists, else default to 1
    midi = adafruit_midi.MIDI(
        midi_in=usb_midi.ports[0], in_channel=0, midi_out=usb_midi.ports[1],
        out_channel=config['midi_out_channel'] if 'midi_out_channel' in config else 1
    )
    log(f"MIDI channel: {midi.out_channel}\n")

    tasks = []
    # add specified expression pedals to tasks
    if 'expression_pedals' in config:
        for pedal in config['expression_pedals']:
            pedal['pin'] = PIN_DICT[pedal['pin']]
            exp_pedal = ExpressionPedal(midi, **pedal)
            log(f'{exp_pedal}\n')
            tasks.append(asyncio.create_task(exp_pedal.monitor()))

    # store FootSwitches in list to be passed into ModeChangeSwitch
    foot_switches = []
    # add specified switches to tasks
    if 'switches' in config:
        for switch in config ['switches']:
            switch['pin'] = PIN_DICT[switch['pin']]
            # default to standard foot switch, change to mode switch if flip_pin specified
            foot_switch = FootSwitch(midi, **switch)
            log(f'{foot_switch}\n')
            foot_switches.append(foot_switch)
            tasks.append(asyncio.create_task(foot_switch.monitor()))

    if 'mode_change_switch' in config:
        mode_change_args = config['mode_change_switch']
        mode_change_args['pin'] = PIN_DICT[mode_change_args['pin']]
        mode_change_switch = ModeChangeSwitch(foot_switches, **mode_change_args)
        log(f'{mode_change_switch}\n')
        tasks.append(asyncio.create_task(mode_change_switch.monitor()))

    await asyncio.gather(*tasks)

asyncio.run(main())
