# GALAXIAN - Space Defender

A polished Pygame recreation of the classic arcade game "Galaxian".

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Controls](#controls)
- [Gameplay](#gameplay)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [License](#license)

## Overview

GALAXIAN - Space Defender is a modern reimagining of the classic 1980s arcade game Galaxian. This enhanced version features improved graphics, sound effects, and gameplay mechanics while maintaining the nostalgic charm of the original.

The game is built using Python and Pygame, making it easy to run on multiple platforms with minimal setup.

## Features

- Classic Galaxian gameplay with modern enhancements
- Smooth animations and visual effects
- Dynamic sound system with multiple sound effects
- Multiple enemy types with different behaviors
- Power-up system with shield, dual fire, and rapid fire options
- Starfield and nebula background effects
- Score tracking and high score system
- Pause functionality
- Responsive controls

## Installation

### Prerequisites
- Python 3.6 or higher
- Pygame library

### Setup Instructions
1. Clone or download this repository
2. Install the required dependencies:
   ```bash
   pip install pygame
   ```
3. Run the game:
   ```bash
   python galaxian.py
   ```

## Controls

### Player Ship Controls:
- **Arrow Keys** or **A/D** - Move ship left/right
- **Arrow Keys** or **W/S** - Move ship up/down
- **SPACE** - Fire weapon
- **P** - Pause game
- **ESC** - Return to title screen or quit game

## Gameplay

### Objective
Defend Earth from waves of alien invaders by destroying all enemies before they reach the bottom of the screen.

### Enemies:
- **Basic Enemies** (Green) - Worth 30 points
- **Diver Enemies** (Blue) - Worth 50 points, dive down to attack
- **Commander Enemies** (Red) - Worth 70 points, more aggressive
- **Flagship Enemies** (Gold) - Worth 100 points, largest and most powerful

### Power-ups:
- **Shield** (White) - Temporary protection
- **Dual Fire** (Cyan) - Shoot two bullets simultaneously
- **Rapid Fire** (Yellow) - Faster shooting rate

### Scoring:
- Basic enemies: 30 points
- Diver enemies: 50 points
- Commander enemies: 70 points
- Flagship enemies: 100 points
- Bonus points for combo kills

## Project Structure

```
Galaxian_Game/
├── galaxian.py          # Main game implementation
├── README.md            # This file
└── .gitignore           # Git ignore rules
├── requirements.txt     # Python dependencies
└── .venv/               # Virtual environment directory
```

## Requirements

The project requires the following Python packages:
- `pygame==2.6.1` 

To install all dependencies:
```bash
pip install -r requirements.txt
```

## License

This project is created for educational purposes and is inspired by the classic Galaxian arcade game. The original game was developed by Namco and is copyrighted by them.

The code provided here is a fan-made recreation.


## Contributing

This project is primarily for educational purposes. However, contributions are welcome in the form of:
- Bug fixes
- Feature enhancements
- Performance improvements
- Documentation improvements

## Credits

- Original Galaxian game by Namco
- Pygame library by pygame.org
- This enhanced version by Amatya Chattaraj.
