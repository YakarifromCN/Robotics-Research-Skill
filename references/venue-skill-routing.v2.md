# Venue workflow redirection v2

Canonical entry point: `scripts/route_robotics_submanifold.py`.

It reads `corpus/venue-catalog.v2.json` (114 venues, no rating fields),
`corpus/robotics-submanifold.v1.json` (eight semantic axes), and the balanced
paper calibration report. The external workflow skills named by the user are
capability sources, not runtime dependencies or separate venue hierarchies.

| Capability source | Axes | Local redirect |
|---|---|---|
| CS/AI conference workflow | L/P/D/S | Idea contribution family → Experiment evidence shape → Review sibling/fallback |
| Engineering-technology journal workflow | E/P/C/L/S | Idea contribution center → Writing archival framing → Review checklist |
| Science Robotics | E/P/A/H/S | Experiment physical repeatability → Writing broad significance → Review hardware/video |
| IJRR | E/P/C/L/D | Idea conceptual frame → Experiment cross-condition mechanism → Writing long-form depth |
| T-RO | E/P/C/L/S | Experiment complete validation → Writing quantitative evidence → Review reproducibility |
| HRI | H/P/A | Experiment human/IRB protocol → Writing interaction claim → Review participant evidence |
| CoRL | L/P/C/S | Idea learning contribution → Experiment seeds/splits/real-robot spot-check → Review artifact/rebuttal |
| RSS | E/P/C/D/S | Experiment mechanism/failure campaign → Writing concise contribution → Review hardware/anonymization |
| IROS | E/P/C/A/S | Experiment integrated system → Writing paper/video package → Review no-traditional-rebuttal constraints |
| ICRA | E/P/C/L/S | Idea broad robotics relevance → Experiment logged hardware campaign → Writing/fallback package |

Every route returns factor-fit ranking or fixed-venue fit, evidence pressure,
and official-scope refresh status. It never returns a calibrated acceptance
probability. Use `corpus/venue-skill-capabilities.v2.json` for the machine-
readable redirect map.
