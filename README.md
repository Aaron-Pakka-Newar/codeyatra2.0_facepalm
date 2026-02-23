# Directional Tactile Navigation Device Simulation

A pygame-based simulation of a 3×3 tactile grid navigation system designed to assist visually impaired users in detecting and navigating around obstacles.

## Features

- **3×3 Tactile Grid**: Displays distance (immediate/near/far) and direction (left/center/right) zones
- **Elevation Detection**: Identifies ground-level, steps, mid-height, head-level obstacles, and potholes
- **First-Person View**: Real-time visualization of the detection field
- **Moving Obstacles**: Dynamic obstacle simulation with vibration feedback indication
- **Adaptive Resolution**: Automatically scales to fit your monitor

## Requirements

- Python 3.10+
- pygame
- numpy

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/Braille.git
   cd Braille
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # Linux/macOS
   source .venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirement.txt
   ```

## Usage

```bash
python tactile_device.py
```

### Controls

| Key | Action |
|-----|--------|
| W / ↑ | Move forward |
| S / ↓ | Move backward |
| A / ← | Rotate left |
| D / → | Rotate right |
| Space bar / → | Jump |
| R | Reset obstacles |
| ESC | Quit |

## Tactile Encoding

| Color | Meaning |
|-------|---------|
| Green | Step (can step over) |
| Yellow | Mid-height obstacle (deflect/redirect) |
| Red | Top/Head level (avoid) |
| Purple | Pothole (drop below surface) |
| Vibration | Moving obstacle detected |

## License

MIT
