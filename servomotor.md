# Servo Motors for 3×3 Tactile Navigation Device

## What is a Servo Motor?

A servo motor is a small actuator that rotates to a specific angle (0°–180°) with high precision using PWM (Pulse Width Modulation). Unlike DC motors, servos can hold their position, making them ideal for tactile feedback systems.

## Why Servo Motors in This Project?

| Step | Action |
|------|--------|
| 1 | Depth camera detects obstacles |
| 2 | Depth data mapped to 3×3 grid |
| 3 | Each grid cell controls one servo |
| 4 | Servo lifts/lowers a tactile pin |

This allows visually impaired users to **physically feel** obstacle direction and distance.

## System Layout (9 Servos)

```
[ L-Far ]   [ C-Far ]   [ R-Far ]
[ L-Near ]  [ C-Near ]  [ R-Near ]
[ L-Imm ]   [ C-Imm ]   [ R-Imm ]
```

- **Row** → Distance (Immediate / Near / Far)
- **Column** → Direction (Left / Center / Right)

## Servo Elevation Mapping

| Distance | Servo Angle | Pin Height |
|----------|-------------|------------|
| 0–1m | 150°–180° | High |
| 1–2m | 90°–120° | Medium |
| 2–3m | 30°–60° | Low |
| >3m | 0° | Flat |

**Closer obstacle = Higher elevation**

## Typical Servo Specs (SG90)

| Parameter | Value |
|-----------|-------|
| Voltage | 4.8V–6V |
| Torque | ~1.8 kg·cm |
| Rotation | 0°–180° |
| Weight | ~9g |

## Wiring

| Wire Color | Connection |
|------------|------------|
| Brown/Black | GND |
| Red | +5V |
| Yellow/Orange | PWM Signal |

**PWM Control:**
- 1ms pulse → 0°
- 1.5ms pulse → 90°
- 2ms pulse → 180°

## Software Mapping

```python
angle = int((height_value / 3.0) * 180)
```

## Safety Notes

- Use **external 5V power supply** for 9 servos (not microcontroller 5V)
- Ensure **common ground**
- Use smooth transitions (avoid sudden 180° jumps)

## Advantages

- Precise control
- Compact & affordable
- Easy microcontroller integration
- Real-time tactile feedback

## Conclusion

The 9-servo array converts depth data into tactile elevation, enabling spatial awareness for visually impaired users through touch-based feedback.
