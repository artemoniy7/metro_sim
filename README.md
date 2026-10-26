# Metro Sim

A small Python/Pygame metro simulator scaffold. Configuration, train definitions, line layouts and signal rules live in JSON files under `data/`; game logic is split between `core/` and `systems/`.

## Run
```bash
python -m pip install -r requirements.txt
python main.py
```

## Controls
- **W / Up** — increase traction
- **S / Down** — brake
- **Space** — emergency brake
- **Esc** — quit

The initial scene is a simple test route intended to be extended with station stops, signal aspects, ALS-ARS speed limits and train sprites.
