# Example using PIO to drive a set of WS2812 LEDs.

import array, time
from machine import Pin
import rp2

# Configure the number of WS2812 LEDs.
NUM_LEDS = 45
PIN_NUM = 22
brightness = 0.1

# Configure the physical button
BTN_PIN = 20
button = Pin(BTN_PIN, Pin.IN, Pin.PULL_UP)

# What state is the dino starting in? [sleep, wake, night, day]
startstate = "sleep"
currentstate = startstate
states = ["sleep", "wake", "night", "day"]  # Order of rotation

# Assign each layer a specific set of LEDs
layer_1 = range(0, 9)    # LEDs 1-9
layer_2 = range(9, 18)   # LEDs 10-18
layer_3 = range(18, 27)  # LEDs 19-27
layer_4 = range(27, 36)  # LEDs 28-36
layer_5 = range(36, 45)  # LEDs 37-45

# List of layers for easy iteration
layers = [layer_1, layer_2, layer_3, layer_4, layer_5]

# ws2812 Stuff
@rp2.asm_pio(sideset_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True, pull_thresh=24)
def ws2812():
    T1 = 2
    T2 = 5
    T3 = 3
    wrap_target()
    label("bitloop")
    out(x, 1)               .side(0)    [T3 - 1]
    jmp(not_x, "do_zero")   .side(1)    [T1 - 1]
    jmp("bitloop")          .side(1)    [T2 - 1]
    label("do_zero")
    nop()                   .side(0)    [T2 - 1]
    wrap()

# Create the StateMachine with the ws2812 program, outputting on pin
sm = rp2.StateMachine(0, ws2812, freq=8_000_000, sideset_base=Pin(PIN_NUM))

# Start the StateMachine, it will wait for data on its FIFO.
sm.active(1)

# Display a pattern on the LEDs via an array of LED RGB values.
ar = array.array("I", [0 for _ in range(NUM_LEDS)])


#### Functions

def pixels_show():
    dimmer_ar = array.array("I", [0 for _ in range(NUM_LEDS)])
    for i,c in enumerate(ar):
        r = int(((c >> 8) & 0xFF) * brightness)
        g = int(((c >> 16) & 0xFF) * brightness)
        b = int((c & 0xFF) * brightness)
        dimmer_ar[i] = (g<<16) + (r<<8) + b
    sm.put(dimmer_ar, 8)
    time.sleep_ms(10)

def pixels_set(i, color):
    ar[i] = (color[1]<<16) + (color[0]<<8) + color[2]

def pixels_fill(color):
    for i in range(len(ar)):
        pixels_set(i, color)
    pixels_show()

def wheel(pos):
    # For the rainbow effect

    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

# Dino Lamp States
def dino_state(state):
    print(f"Dino is now in {state} mode")

    if currentstate == "sleep":
        # Make all pixels black
        pixels_fill((0, 0, 0))

    elif currentstate == "wake":
        # Start-up Animation
        for j in range(255):
            for i in range(NUM_LEDS):
                rc_index = (i * 256 // NUM_LEDS) + j
                pixels_set(i, wheel(rc_index & 255))
            pixels_show()

        # Turn Lamp on to Night Mode
        dino_state("night")

    elif currentstate == "night":
        layer_colors = [
            (255, 0, 0),  # Red for Layer 1
            (0, 128, 0),  # Dark Green for Layer 2
            (0, 0, 255),  # Blue for Layer 3
            (255, 0, 255),  # Purple for Layer 4
            (255, 255, 255)  # Purple for layer 5
        ]
        for layer_index, layer in enumerate(layers):
            for led in layer:
                pixels_set(led, layer_colors[layer_index])
        pixels_show()

    elif currentstate == "day":
        layer_colors = [
            (255, 128, 0),  # Yellow for layer 1
            (0, 255, 0),  # Green for layer 2
            (0, 153, 0),  # Blue/Green for layer 3
            (102, 255, 255),  # Light Blue for layer 4
            (255, 0, 0)  # Purple for layer 5
        ]
        for layer_index, layer in enumerate(layers):
            for led in layer:
                pixels_set(led, layer_colors[layer_index])
        pixels_show()


    else:
        print("Unknown state")
        dino_state("wake")


# Button Handling
def check_button(currentstate):
    if button.value() == 0:  # Button is pressed (active-low)
        time.sleep(0.2)  # Debounce delay
        if button.value() == 0:  # Confirm it's still pressed
            print("Button was pressed, switching state")
            current_index = states.index(currentstate)
            print("current_index is: ", current_index)
            next_index = (current_index + 1) % len(states)
            currentstate = states[next_index]
            print("Switching to ", currentstate)
            dino_state(currentstate)
            while button.value() == 0:
                time.sleep(0.1)  # Wait for release

#### End Functions

print("It's dino time!")

# Set initial state
dino_state(currentstate)  # Set initial state

while True:
    # TODO: Make it change mode based on if the room is dark/light using a flux sensor
    # TODO: Make a button to cycle between sleep/wake/day/night states

    check_button(currentstate)  # Check if button is pressed to change state
    time.sleep(0.1)  # Small delay to avoid CPU overuse
