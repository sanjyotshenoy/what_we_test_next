# ------------------------------------------------------------
# Opentrons OT‑2 MIC assay – 2‑fold dilution, 4 antibiotics,
# 2 replicates each, 96‑well plate.
# Uses ONLY the 8‑channel P300 pipette (p300_multi_gen2).
# API version: 2.13 (or any recent 2.x)
# ------------------------------------------------------------

from opentrons import protocol_api

metadata = {
    'protocolName': 'MIC 2‑fold dilution – 4 antibiotics, 2 replicates (8‑channel only)',
    'author': 'Your Name <you@lab.edu>',
    'description': (
        'Prepares a 96‑well plate for MIC testing using a serial '
        '2‑fold dilution down each column. 4 antibiotics, each in '
        'duplicate, with bacteria added at the end.'
    ),
    'apiLevel': '2.13'   # keep in sync with the OT‑2 app version
}

def run(protocol: protocol_api.ProtocolContext):
    # ========================================================
    # === USER SETTINGS (edit these to match your experiment) ==
    # ========================================================

    # ----- Plate layout -----
    NUM_ANTIBIOTICS = 4          # how many different drugs
    REPLICATES = 2               # technical replicates per drug
    NUM_STEPS = 8                # number of 2‑fold dilution steps (rows A‑H)
    START_CONC_Ug_UL = 100.0     # concentration of stock solution (µg/mL) – adjust per drug
    FINAL_VOL_UL = 100           # final assay volume per well (µL)

    # ----- Liquid handling -----
    TIP_VOL_UL = 300             # max volume of the P300 multi (we never exceed this)
    MIX_VOL_UL = 50              # volume used for mixing during dilutions
    MIX_REPS = 3                 # how many mix cycles per transfer

    # ----- Bacteria -----
    BACTERIA_VOL_UL = 10         # volume of bacterial suspension to add per well
    MEDIUM_VOL_UL   = FINAL_VOL_UL - BACTERIA_VOL_UL   # medium to leave in well before bacteria

    # ----- Labware names (as they appear in the OT‑2 library) -----
    TIPRACK_NAME = 'opentrons_96_tiprack_300ul'
    RESERVOIR_NAME = 'usascientific_12_reservoir_22ml'   # 12‑well reservoir
    PLATE_NAME   = 'corning_96_wellplate_360ul_flat'    # standard flat‑bottom 96‑well

    # ----- Well mapping in the reservoir -----
    MEDIUM_WELL      = 'A1'   # growth medium (no drug)
    BACTERIA_WELL    = 'A2'   # bacterial suspension (pre‑diluted to desired OD)
    # We need 8 source wells for the antibiotic stocks (4 drugs × 2 replicates)
    # Place them in reservoir wells A3‑A10.
    ANTIBIOTIC_RESERVOIR_WELLS = [
        'A3', 'A4', 'A5', 'A6',   # Antibiotic 1 – rep0, rep1; Antibiotic 2 – rep0, rep1
        'A7', 'A8', 'A9', 'A10'   # Antibiotic 3 – rep0, rep1; Antibiotic 4 – rep0, rep1
    ]

    # ========================================================
    # === DO NOT EDIT BELOW THIS LINE (unless you know what you're doing) ===
    # ========================================================

    # ----- Load labware -----
    tiprack = protocol.load_labware(TIPRACK_NAME, '1')          # tip rack in slot 1
    reservoir = protocol.load_labware(RESERVOIR_NAME, '2')      # reservoir in slot 2
    plate = protocol.load_labware(PLATE_NAME, '3')              # 96‑well plate in slot 3

    # ----- Instruments -----
    left_pipette = protocol.load_instrument(
        'p300_multi_gen2',   # 8‑channel, 300 µL
        mount='left',
        tip_racks=[tiprack]
    )

    # Helper lists for rows and columns (0‑indexed)
    ROWS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
    COLS = list(range(1, 13))   # 1‑12 as strings for column addressing

    # ------------------------------------------------------------------
    # STEP 0 – Fill plate with growth medium (diluent)
    # ------------------------------------------------------------------
    protocol.comment('Step 0: filling plate with growth medium')
    # Process column by column (8 wells at a time)
    for col in COLS:
        column_wells = [plate.wells_by_name()[f'{r}{col}'] for r in ROWS]
        left_pipette.pick_up_tip()
        left_pipette.transfer(
            MEDIUM_VOL_UL,
            reservoir.wells_by_name()[MEDIUM_WELL],
            column_wells,
            new_tip='never'   # reuse tip for the whole column (medium is clean)
        )
        left_pipette.drop_tip()

    # ------------------------------------------------------------------
    # STEP 1 – Add antibiotic stock to the top well (row A) of each column
    # ------------------------------------------------------------------
    protocol.comment('Step 1: spiking highest concentration (C0) into plate')
    # We have 8 columns → 8 antibiotic stocks (4 drugs × 2 replicates)
    # Build lists of source and destination wells (length 8)
    src_wells = [reservoir.wells_by_name()[well] for well in ANTIBIOTIC_RESERVOIR_WELLS]
    dst_wells = [plate.wells_by_name()[f'A{col}'] for col in COLS[:8]]   # only first 8 columns used
    stock_vol = FINAL_VOL_UL   # because we want C0 = stock concentration (adjust if stock is more concentrated)

    left_pipette.pick_up_tip()
    left_pipette.transfer(
        stock_vol,
        src_wells,
        dst_wells,
        mix_after=(MIX_REPS, MIX_VOL_UL),
        new_tip='never'
    )
    left_pipette.drop_tip()

    # ------------------------------------------------------------------
    # STEP 2 – Perform 2‑fold serial dilution down each column (A→B→…→H)
    # ------------------------------------------------------------------
    protocol.comment('Step 2: 2‑fold serial dilution down each column')
    transfer_vol = FINAL_VOL_UL / 2.0   # half the well volume goes to the next row
    for step in range(NUM_STEPS - 1):   # 0‑6 (A→B, B→C, …, G→H)
        src_row = ROWS[step]
        dst_row = ROWS[step + 1]
        src_wells = [plate.wells_by_name()[f'{src_row}{col}'] for col in COLS[:8]]
        dst_wells = [plate.wells_by_name()[f'{dst_row}{col}'] for col in COLS[:8]]

        left_pipette.pick_up_tip()
        left_pipette.transfer(
            transfer_vol,
            src_wells,
            dst_wells,
            mix_after=(MIX_REPS, MIX_VOL_UL),
            new_tip='never'
        )
        left_pipette.drop_tip()

    # ------------------------------------------------------------------
    # STEP 3 – Add bacterial inoculum to bring each well to final volume
    # ------------------------------------------------------------------
    protocol.comment('Step 3: adding bacterial inoculum')
    # Add bacteria column‑by‑column (8 wells at a time)
    for col in COLS:
        column_wells = [plate.wells_by_name()[f'{r}{col}'] for r in ROWS]
        left_pipette.pick_up_tip()
        left_pipette.transfer(
            BACTERIA_VOL_UL,
            reservoir.wells_by_name()[BACTERIA_WELL],
            column_wells,
            mix_after=(MIX_REPS, MIX_VOL_UL),
            new_tip='never'
        )
        left_pipette.drop_tip()

    protocol.comment('Protocol finished. Plate is ready for incubation.')

