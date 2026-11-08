We need to respond with protocol design instructions for Opentrons OT-2 using Python API v2 perhaps. Provide code that sets up labware, reagents, and performs serial dilutions across wells in rows/columns? Need 4 antibiotics, 2 replicates each => total of 8 conditions per strain? Actually they have bacterial strains (maybe multiple?), but we can assume one strain; they'd like replicate wells.

Goal: 2-fold dilution series from some starting concentration down to maybe no drug. Typically you set up columns: column 1 highest conc, then serially dilute across row or column. For 4 antibiotics, could allocate separate sections of plate: e.g., first two columns for ABX1 replicates, next two for ABX2 etc. Or use rows A-H for each antibiotic duplicate.

Simplify: Use 96-well plate, fill all wells with growth medium + bacteria at appropriate OD. Then add antibiotics via serial dilution.

Approach: Prepare stock solutions of each antibiotic in reservoirs. Perform 2-fold serial dilution directly in plate: start by adding high concentration to first well(s) of each condition, then transfer half volume to next well mixing.

Given limited time, provide generic script where user defines parameters: number of antibiotics =4, replicates=2, dilution factor=2, initial concentration, final volume per well (e.g., 100 µL). Steps:

1. Load labware: tiprack_300ul, reservoir (12-channel? actually single reservoir with compartments), 96well plate.
2. Define mapping: For i in range(num_antibiotics): assign block of wells: start_well = i*replicates*dilution_steps? But we don't know steps count. Could define number of dilution steps (e.g., 8 steps including control). Let's assume 8 concentrations (including zero). So each antibiotic gets 2 replicates * 8 concentrations = 16 wells. Four antibiotics -> 64 wells used.

Provide code loops.

Will also include optional step to add bacteria after antibiotic addition if pre-incubated.

Let's produce clear commented protocol.

Also mention calibration steps.

Now craft final answer.