# run-002: fixture-compound-A / fixture-species-B

Separate physical run. Replace/load the labeled source liquids and consumables before this run.

Requested replicate rows: AB; surplus technical rows: CDEFGH.

Source identities:
- A1: cation-adjusted Mueller-Hinton broth
- A2: fixture-compound-A
- A3: fixture-species-B

# Run sheet - 1 species, 10-point 2-fold series

Generated beside the OT-2 protocol. The robot does the liquid handling; these steps are yours.

## Before the robot

- **compound** - 3.6 mL into reservoir channel 2 (includes the 2 mL the tips cannot reach)
- **inoculum** - 10.8 mL into reservoir channel 3 (includes the 2 mL the tips cannot reach)
- **medium** - 11.6 mL into reservoir channel 1 (includes the 2 mL the tips cannot reach)
- the compound goes in at **100 uM**, twice the top assay concentration, because the inoculum doubles the volume and halves it
- Grow the strain to log phase and dilute it in broth to the inoculum density (2x final).

## Plate map

```
plate 1 of 1  (2-fold, 10 points, final concentrations in uM)
             1        2        3        4        5        6        7        8        9       10       11       12
  A         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  B         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  C         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  D         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  E         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  F         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  G         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  H         50       25     12.5     6.25     3.12     1.56    0.781    0.391    0.195   0.0977       GC       SC   fixture-species-B
  GC = growth control (no compound)   SC = sterility control (medium only)
```

## After the robot

- **incubate** - Incubate about 18 h at 37 C.
- **read** - Read turbidity (OD590 / OD530) or score visible growth; MIC = lowest concentration with no growth.
- **analysis** - MIC = the lowest concentration whose signal falls below the no-growth cutoff (mean + 3 SD of the inhibited controls), or by CLSI visual reading.
- **atmosphere** - incubate **aerobic**; this lab has aerobic, anaerobic

## Check before trusting a result

- **assumed** incubation_atmosphere: anaerobic incubation (jars, sachets or an anaerobic incubator) assumed because the project is phenotyping anaerobic microbiome bacteria; confirm the lab has one before reporting a result
- **unconfirmed** pipette p20_single_gen2 on the right mount may not be installed
- **unconfirmed** capability 'shaking' is unconfirmed
- **warning** lab.yaml declares apiLevel 2.28, but the highest an OT-2-capable opentrons simulates is 2.27; generated at 2.27 so the protocol can be checked before it runs. Confirm the level from the robot itself

## Proposal conditions (authoritative for this design)

Medium: cation-adjusted Mueller-Hinton broth; incubation: 37.0 C / 18.0 h / aerobic; readout: absorbance (OD590).
Template descriptions are precedents, not additional executed operations. The template reference-antibiotic control is not implemented by this two-control compiler.
