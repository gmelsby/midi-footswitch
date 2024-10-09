# Pi Pico CircuitPython USB MIDI Pedal Controller
MIDI controller platform for RP2040 that handles tappable switches and expression pedals with easy configuration through a JSON file

For use with [CircuitPython 9.0.5](https://github.com/adafruit/circuitpython/releases/tag/9.0.5)

![pedal](/images/pedal.jpeg)
![expression pedal gif](/images/gifs/Expression%20Pedal.gif)


## Setup
### Hardware
The two main input devices supported by this software are expression pedals and tappable switches. Optionally, an additional flippable switch can be added which enables the tappable switches to change modes between 'toggle' and 'momentary'. 

#### Expression Pedal
To use an expression pedal, connect the pins of a 1/4" TRS jack socket to the board. Using the [Pico Pinout Diagram](https://learn.adafruit.com/assets/99339) as reference, connect the 'tip' pin of the jack to `3V3(OUT)` the 'ring' pin of the jack to `ADC0` and the 'sleeve' pin of the jack to ground (`GND`).

#### Tappable Switches
This software is meant for use with **momentary switches** that are normally open. In other words, use switches that complete a circuit only when pressed down, not switches that latch and need to be pressed again in order to break the circuit. 

Software enables these momentary switches to behave, for the purposes of MIDI output, as latching switches if desired. The reverse behavior would not be possible, as behavior like long presses or short consecutive taps would not be registered on a latching switch.

| ![Momentary example](/images/gifs/Momentary.gif) |
|:--:| 
| *Momentary Switch Behavior* |

| ![Toggle example](/images/gifs/Toggle.gif) |
|:--:| 
| *Toogle/Latching Switch Behavior* |



To connect these switches to the microcontroller, wire one pin to ground (`GND`) and the other to any pin labelled `GPx` (where x is an integer) on the [Pico Pinout Diagram](https://learn.adafruit.com/assets/99339). The `config.json` file provides some reasonable defaults for a four-footswitch setup (`GP10`, `GP11`, `GP12`, and `GP13`), but it can be modified to suit other hardware states.

#### Optional Toggle Switch for Mode Change
If desired, a toggle switch can be added that enables users to change the behavior of individual tappable switches while the toggle switch is in the 'ON' position. While the toggle switch circuit is complete, single-tapping a footswitch will place it in 'latching' or 'toggle' mode, and double-tapping a footswitch will place it in 'momentary' mode. These changes persist after the toggle switch is switched back to 'OFF'.

| ![Mode change to momentary example](/images/gifs/Switch%20Modes%20To%20Momentary.gif) |
|:--:| 
| *Example of changing a footswitch to momentary mode by double tapping* |


To connect a toggle switch to the microcontroller, wire one pin to ground and the other to to any pin labelled `GPx` (where x is an integer) on the [Pico Pinout Diagram](https://learn.adafruit.com/assets/99339). The default `config.json` pin for the toggle switch is `GP15`.

### Software
Install [CircuitPython 9.0.5](https://github.com/adafruit/circuitpython/releases/tag/9.0.5) on the Raspberry Pi Pico.  

Upon successful install, the Pi Pico should show up as an external drive named CIRCUITPY on the computer it is linked to with a USB cable.  
Copy the contents of the CIRCUITPY folder in this repo to the root of the CIRCUITPY external drive.  
The microcontroller will then execute the Pedal Controller code found in `code.py` in accordance with the specifications laid out in `config.json` any time it is powered on.

The behavior of the pedal can be modified by directly editing the `code.py` or `config.json` files on the CIRCUITPY drive. Once a change is saved to the CIRCUITPY drive, the device will begin running the new code. The [Mu Editor](https://codewith.mu/) contains many useful tools, such as a serial monitor, that make it easier to debug CircuitPython programs running on the Pi Pico until the desired behavior is achieved.

### Configuration
The majority of configuration is done by modifying the JSON object in `config.json`.  

#### Midi Out Channel
`midi_out_channel` determines the channel that MIDI messages are broadcast on.  

#### Expression Pedals
`expression_pedals` is a list of objects of the form
```
{
  "pin": "A0",        # Pin the 'ring' part of the jack is connected to
  "cc_parameter": 11, # Control Change parameter on which readings will be sent
  "sensitivity": 2    # Minimum change between two readings necessary for update
}
```
If there are no expression pedals, an empty list will suffice.  

#### Footswitches
`switches` is a list of objects of the form
```
{
  "pin": "GP10",      # Pin the footswitch is connected to
  "cc_parameter": 80, # Control Change parameter on which readings will be sent
  "momentary": true   # Determines whether switch behaves latching or momentary
},
```
If there are no footswitches, an empty list will suffice.

#### Toggle Switch For Mode Change
`mode_change_switch` is an object of the form
```
{
  "pin": "GP15" # Pin the flippable toggle switch is connected to
}
```
If no mode-changing flippable toggle switch is being used, omit the object from `config.json`.
 
#### Serial Debugging
To enable/disable debugging print statements sent over serial, change the value of `DEBUG` at the top of `code.py` to the appropriate boolean.


### Enclosures
The holes on the enclosures found in the 'cases' folder accomodate four 1/2" bushing diameter foot switches, one panel mount 1/4" TRS socket with a 1/2" bushing diameter, and one 1/4" bushing diameter flippable toggle switch. The cutout for the Micro USB port is designed to accomodate [this panel mount extender](https://www.adafruit.com/product/3258).

The laser-cuttable wooden enclosure is a [ClosedBox](https://boxes.hackerspace-bamberg.de/ClosedBox?language=en) from Boxes.py modified in Inkscape to add cutouts for hardware. It has been tested with 1/8" thickness Baltic Birch Plywood using a Universal Laser Systems VLS3.50.

![laser cut wood](/images/laser_cut.jpeg)
![pedal body](/images/body.jpeg)
![pedal with hardware installed](/images/hardware.jpeg)
![wired pedal](/images/wired.jpeg)

The 3d-printable enclosure is a [Basic Box model](https://lightningboxes.com/product/basic-box/) from Lightning Boxes modified in TinkerCAD to add cutouts for hardware. It has not been tested.

