# Metro Sim

A small Python/Pygame metro driving simulator. The playable train is the 81-760 «Ока», using the sprites in `assets/trains/81-760/`.

## Run
```bash
python -m pip install -r requirements.txt
python main.py
```

## Controls
- **W / Up** — traction
- **S / Down** — service brake
- **Space** — emergency brake
- **Esc** — quit

## Scale and route
- World distances are in metres.
- Stations on the test route are spaced 1,000 m apart.
- The leading 81-760 cab is 20 m long; each following car is 19 m.
- The camera uses 50% zoom (twice as far out as the previous view) and follows the leading cab.
- Train textures are loaded from `assets/trains/81-760/81-760-loco.png` and `assets/trains/81-760/81-760-car.png`.
