# autonave

> **Python structural engineering library — parametric geometry, CFE wind/seismic loads, cold-formed steel design, and ETABS export.**

**By [Hugo Velasco](https://github.com/HuVelasco)** · [dualitum.com](https://dualitum.com)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Code](https://img.shields.io/badge/Code-CFE%20%7C%20AISI%20S100-orange)](https://dualitum.com)

---

## What It Does

AutoNave is a standalone Python library for AEC automation workflows. It handles the calculation layer between an AI-generated building concept and a structural analysis model — geometry, loads, and preliminary design — so that Claude (or any Python script) can go from architectural intent to a ready-to-run ETABS model without touching a GUI.

```
Architectural input (bays, stories, heights)
        │
        ▼  AutoNave
Parametric geometry + CFE loads + CFS preliminary design
        │
        ▼  ETABS adapter
CSI ETABS model ready for analysis
```

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
| `CFESeismicLoads.py` | Seismic load generation per CFE / NTC-CDMX |
| `GravityLoads.py` | Dead and live load patterns |
| `cfs_design/` | Cold-formed steel design engine (studs, tracks, AISI S100) |

---

## Installation

```bash
git clone https://github.com/HuVelasco/autonave.git
cd autonave
pip install -r requirements.txt
```

Python 3.10+. No AEC software needed for the calculation layer; ETABS adapter requires CSI ETABS running.

---

## Usage

```python
from Model import BuildingModel
from CFEWindLoads import WindLoadGenerator
from cfs_design import CFSDesignEngine

# Build a model
model = BuildingModel(bays_x=3, bays_y=2, stories=5)
model.set_bay_width(6.0)       # meters
model.set_story_height(3.5)

# Generate wind loads per CFE
wind = WindLoadGenerator(model)
loads = wind.generate(exposure="B", base_wind_speed=130)   # km/h

# Preliminary CFS stud design
engine = CFSDesignEngine()
result = engine.design_stud("600S162-43", axial=12.5, moment=0.8)
print(result.dcr, result.passes)
```

### Export to ETABS

```python
from cfs_design.etabs_adapter import ETABSAdapter

adapter = ETABSAdapter(model)
adapter.export_to_etabs()   # pushes geometry + loads to running ETABS instance
```

---

## Use Cases

- **AI-driven preliminary design** — Claude generates AutoNave models from architectural input, exports to ETABS for final FEA
- **CFE load automation** — parametric wind/seismic load generation for Mexican projects
- **CFS wall design** — stud design without launching RSG CFS GUI
- **UBIM pipeline seed** — AutoNave geometry feeds the ETABS → UBIM → Tekla pipeline

---

## Design Code Coverage

- **CFE** (Comisión Federal de Electricidad) — wind and seismic loads, Mexico
- **NTC-CDMX** — seismic spectrum, Mexico City
- **AISI S100** — cold-formed steel design

---

## Project Status

| Module | Status |
|---|---|
| Geometry engine | ✅ Production |
| CFE wind loads | ✅ Production |
| CFE seismic loads | ✅ Production |
| CFS design engine | ✅ Production |
| ETABS adapter | ✅ Production |
| ASCE 7 loads | 🔄 Planned |
| Direct UBIM export | 🔄 Planned |

---

## License

MIT © 2026 Hugo Velasco. See [LICENSE](LICENSE).

All structural outputs must be reviewed by a licensed professional engineer.

---

*Part of the [Hugo Velasco](https://github.com/HuVelasco) AEC automation suite · [dualitum.com](https://dualitum.com)*
