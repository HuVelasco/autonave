# AutoNave — AEC Structural Calculation Library

> **Python library for structural geometry, gravity/wind/seismic loads (CFE), and cold-formed steel design.**

**Author:** Hugo Velasco · [dualitum.com](https://dualitum.com)
**License:** MIT · Copyright © 2026 Hugo Velasco

---

## What This Is

AutoNave is a Python structural engineering library for AEC automation workflows. It provides:

- **Geometry engine** — structural frame geometry, node/member topology, coordinate transforms
- **Load generation** — gravity, wind (CFE), and seismic (CFE) load calculations per Mexican code
- **CFS design engine** — cold-formed steel stud and track design, section library, AISI S100
- **ETABS adapter** — export AutoNave models directly to ETABS for analysis

It is designed to be called from scripts, Jupyter notebooks, or AI agents (via the ETABS MCP).

---

## Modules

| Module | Description |
|---|---|
| `Geometry.py` | Structural frame geometry — nodes, members, bays, stories |
| `Model.py` | Building model assembly and topology |
| `constants.py` | Material and section constants |
| `Profiles.py` | Steel section library (W, HSS, angles, channels, CFS) |
| `Design.py` | Steel member design checks |
| `CFEWindLoads.py` | Wind load generation per CFE (Mexican building code) |
| `CFESeismicLoads.py` | Seismic load generation per CFE |
| `GravityLoads.py` | Dead and live load patterns |
| `cfs_design/` | Cold-formed steel design engine (studs, tracks, AISI S100) |

---

## Installation

```bash
pip install -r requirements.txt
```

Requires Python 3.10+. No external AEC software needed for calculation; ETABS adapter requires CSI ETABS running.

---

## Usage

```python
from Model import BuildingModel
from CFEWindLoads import WindLoadGenerator
from cfs_design import CFSDesignEngine

# Build a model
model = BuildingModel(bays_x=3, bays_y=2, stories=5)
model.set_bay_width(6.0)  # meters
model.set_story_height(3.5)

# Generate wind loads (CFE)
wind = WindLoadGenerator(model)
loads = wind.generate(exposure="B", base_wind_speed=130)  # km/h

# Design CFS studs
engine = CFSDesignEngine()
result = engine.design_stud("600S162-43", axial=12.5, moment=0.8)
```

---

## ETABS Integration

AutoNave models export directly to ETABS via the ETABS MCP:

```python
from cfs_design.etabs_adapter import ETABSAdapter

adapter = ETABSAdapter(model)
adapter.export_to_etabs()  # pushes geometry + loads to running ETABS instance
```

---

## Use Cases

- **Preliminary design** — AI generates AutoNave models from architectural input, exports to ETABS for final analysis
- **CFE load automation** — parametric wind/seismic load generation for Mexican projects
- **CFS wall design** — standalone stud design without launching RSG CFS GUI
- **UBIM pipeline seed** — AutoNave geometry feeds the ETABS → UBIM → Tekla pipeline

---

## Project Status

- ✅ Geometry engine — production ready
- ✅ CFE wind loads — production ready
- ✅ CFE seismic loads — production ready
- ✅ CFS design engine — production ready
- ✅ ETABS adapter — production ready
- 🔄 ASCE 7 load generation — planned
- 🔄 Direct UBIM export — planned

---

## Contributing & Support

Issues and PRs welcome. For structural automation consulting, contact [dualitum.com](https://dualitum.com).

---

*© 2026 Hugo Velasco. This library produces preliminary engineering calculations. All outputs must be reviewed by a licensed professional engineer.*
