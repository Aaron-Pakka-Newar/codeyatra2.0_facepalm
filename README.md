# Directional Tactile Navigation Device Simulation

A multi-platform simulation of a 3×3 tactile grid navigation system designed to assist visually impaired users in detecting and navigating around obstacles. This project includes both a Python-based pygame simulation and a Unity 3D visualization.

## Features

### Python Simulation
- **3×3 Tactile Grid**: Displays distance (immediate/near/far) and direction (left/center/right) zones
- **Elevation Detection**: Identifies ground-level, steps, mid-height, head-level obstacles, and potholes
- **First-Person View**: Real-time visualization of the detection field
- **Moving Obstacles**: Dynamic obstacle simulation with vibration feedback indication
- **Adaptive Resolution**: Automatically scales to fit your monitor

### Unity 3D Visualization
- **Grid Generator**: Creates and manages the tactile grid visualization in 3D space
- **Servo Linear Actuator**: Simulates the physical servo-driven pin actuators
- **Camera Orbit Controller**: Allows interactive viewing of the device from all angles
- **Grid Movement**: Handles the dynamic movement and animation of grid elements

## Project Structure

```
├── tactile_device.py          # Python simulation
├── requirement.txt            # Python dependencies
├── Assets/                    # Unity assets
│   ├── Scripts/              # C# scripts for Unity
│   │   ├── CameraOrbitController.cs
│   │   ├── GridGenerator.cs
│   │   ├── GridMovement.cs
│   │   └── ServoLinearActuator.cs
│   ├── Scenes/               # Unity scenes
│   ├── Settings/             # Render pipeline settings
│   └── sg90_servo__11_scale.glb  # 3D servo model
├── Packages/                  # Unity package dependencies
└── ProjectSettings/           # Unity project configuration
```

## Requirements

### Python Simulation
- Python 3.10+
- pygame
- numpy

### Unity Visualization
- Unity 2022.3 LTS or newer (with Universal Render Pipeline)

## Installation

### Python Simulation

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

### Unity Visualization

1. Open Unity Hub
2. Click "Open" and select the project folder
3. Open the scene from `Assets/Scenes/SampleScene.unity`

## Usage

### Python Simulation

```bash
python tactile_device.py
```

#### Controls

| Key | Action |
|-----|--------|
| W / ↑ | Move forward |
| S / ↓ | Move backward |
| A / ← | Rotate left |
| D / → | Rotate right |
| Space bar /  | Jump |
| R | Reset obstacles |
| ESC | Quit |

### Unity Visualization

1. Open the SampleScene in Unity
2. Press Play to start the visualization
3. Use mouse to orbit camera around the device

## Tactile Encoding

| Color | Meaning |
|-------|---------|
| Green | Step (can step over) |
| Yellow | Mid-height obstacle (deflect/redirect) |
| Red | Top/Head level (avoid) |
| Purple | Pothole (drop below surface) |
| Vibration | Moving obstacle detected |
