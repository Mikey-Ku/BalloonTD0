# Balloon Tower Defense

A simple version of the popular **Bloons TD** game by Ninja Kiwi, built from scratch in Python using Pygame.

## Overview

In this tower defense game, you must defend your territory against waves of colorful balloons by placing and upgrading towers along a predefined path. Features include multiple tower types, tiered balloon enemies, customizable rounds, and a looping soundtrack for immersion.

## Features

- **Multiple Tower Types**

  - **Dart Tower** (fast, low damage)
  - **Sniper Tower** (high damage, long range)
  - **Tac Tower** (fast, short radius)
  - **Super Tower** (rapid-fire, extreme range)  
    _(Defined in `towers.py`)_

- **Varied Balloon Enemies**

  - Red, Blue, Green, Yellow, Pink balloons with increasing health and speed
  - **MOAB** boss that splits into smaller balloons upon destruction  
    _(Implemented in `balloon.py`)_

- **Wave-Based Gameplay**

  - 20 configurable rounds with spawn delays and mixed balloon types
  - Bonus income awarded at the end of each round  
    _(Configured in `rounds.py`)_

- **Dynamic Path & Map**

  - Waypoints loaded from `equidistant_points.csv` for easy map customization
  - Valid tower placements determined at runtime  
    _(Logic in `track.py`)_

- **Interactive UI**

  - Click buttons or press **SPACE** to start rounds
  - Toggle game speed between 1× and 2×
  - Place, upgrade, or sell towers via on-screen controls  
    _(See `user_interface.py`)_

- **Visuals & Audio**

  - Sprite assets in:
    - `balloon_images/`
    - `monkey_images/`
    - `background_images/`
  - Looping main theme in `soundtrack/SpotiDownloader.com - Main Theme - Tim Haywood.mp3`

- **Website & Documentation**
  - Static site source (for GitHub Pages) in `docs/`

## Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/olincollege/BalloonTD0.git
   cd BalloonTD0
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Assets**
   Ensure the following asset directories and files are present:
   - `equidistant_points.csv`
   - `background_images/Background.webp`
   - `balloon_images/*.png`
   - `monkey_images/*.png`
   - `soundtrack/SpotiDownloader.com - Main Theme - Tim Haywood.mp3`

## Usage

Run the game:

```bash
python main.py
```

### Controls

- **Start Round**: Click the **Play** button or press **SPACE**
- **Toggle Speed**: Click **Play** during a round (switches between 1× and 2×)
- **Place Tower**: Click a tower button, then click a valid map location
- **Upgrade/Sell Tower**: Click an existing tower, then click **Upgrade** or **Sell**
- **Restart/Quit**: After game over, press **R** to restart or **Q** to quit

## Code Style

- **Formatting**: [Black](https://github.com/psf/black) (100-character line width)
- **Linting**: [Pylint](https://pylint.org/) with Pygame false-positive suppression

## License & Acknowledgements

- Built with [Pygame](https://www.pygame.org/)
- Original concept and map by Ninja Kiwi (Bloons TD)
- Main theme by Tim Haywood

Enjoy defending against the balloon onslaught!
