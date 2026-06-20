# Enclosure Files

Put slicer-ready `.3mf` files in `hardware/enclosure/3mf/`.

## MVP enclosure concept

The first enclosure should hold:

- Raspberry Pi Zero 2 W
- DHT22 temperature/humidity sensor
- BH1750 light sensor
- USB power cable
- small standoffs or screw bosses for the Pi

Design goals:

- keep the Pi in a protected electronics bay
- place the DHT22 in a vented sensor bay away from Pi heat
- place the BH1750 where it can see ambient greenhouse light
- leave room for wiring strain relief
- make the lid removable for service

## Suggested print notes

- Material: PETG for greenhouse heat/humidity resistance
- Layer height: 0.20 mm
- Walls: 3 perimeters
- Infill: 15-25%
- Avoid supports in sensor vents if possible

## Revision log

- `v0`: placeholder folder for early concept models

