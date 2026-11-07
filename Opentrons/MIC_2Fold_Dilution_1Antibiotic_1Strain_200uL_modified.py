"""
MIC 2-fold broth microdilution, CLSI 100 + 100 uL format.
1 antibiotic x 1 bacterial strain, one plate (P1), 200 uL final per well.

Simplified from MIC_2Fold_Dilution_A4B4M4Am3Bm3_200uL.py (CL_Bridges Lab_CMU).

Deck:
    Slot 2  : P1, Corning 96-well flat 360 uL (assay plate)
    Slot 3  : USA Scientific 12-well reservoir 22 mL
                A1 = broth, A2 = antibiotic (2x top concentration), A3 = bacteria (2x final inoculum)
    Slot 6  : 300 uL tip rack (second rack, last 2 columns used)
    Slot 9  : 300 uL tip rack (first rack, all 12 columns used)
    Slot 12 : fixed trash
Pipette: P300 multi-channel on the left mount (P20 not used).

Final plate (all 8 rows A-H are replicates):
    Col 1-10 : 2-fold antibiotic series + bacteria   (200 uL)
    Col 11   : growth control, broth + bacteria      (200 uL)
    Col 12   : sterility control, broth only         (200 uL)
"""

from opentrons import protocol_api

metadata = {
    "protocolName": "MIC_2Fold_Dilution_CLSI_1Antibiotic_1Strain_200uL",
    "author": "CL_Bridges Lab_CMU",
    "description": "CLSI-style broth microdilution: 100 uL antibiotic dilution + 100 uL "
                   "inoculum, one antibiotic, one strain, one plate (P1).",
}

requirements = {"robotType": "OT-2", "apiLevel": "2.28"}

# ---------------------------------------------------------------------------
# Settings (edit here)
# ---------------------------------------------------------------------------
BROTH_VOL = 100           # uL broth in columns 2-11
STERILITY_VOL = 200       # uL broth in column 12
ANTIBIOTIC_VOL = 200      # uL antibiotic (2x top concentration) in column 1
DILUTION_VOL = 100        # uL moved column to column
BACTERIA_VOL = 100        # uL inoculum (2x final density) added to columns 1-11
MIX_VOL = 150             # uL mix volume (wells hold 200 uL while mixing)
MIX_REPS = 3
PAUSE_BEFORE_BACTERIA = True   # pause so the inoculum can be loaded/resuspended fresh


def run(protocol: protocol_api.ProtocolContext) -> None:
    # -----------------------------------------------------------------------
    # Labware
    # -----------------------------------------------------------------------
    tips_300_a = protocol.load_labware("opentrons_96_tiprack_300ul", "9")
    tips_300_b = protocol.load_labware("opentrons_96_tiprack_300ul", "6")
    reservoir = protocol.load_labware("usascientific_12_reservoir_22ml", "3")
    plate = protocol.load_labware("corning_96_wellplate_360ul_flat", "2", label="P1")
    trash = protocol.fixed_trash

    # -----------------------------------------------------------------------
    # Pipette (8-channel: one command = one full column)
    # -----------------------------------------------------------------------
    p300 = protocol.load_instrument("p300_multi", "left",
                                    tip_racks=[tips_300_a, tips_300_b])
    p300.flow_rate.aspirate = 150
    p300.flow_rate.dispense = 300
    p300.well_bottom_clearance.aspirate = 1   # mm above well bottom
    p300.well_bottom_clearance.dispense = 1

    # -----------------------------------------------------------------------
    # Liquids (for the Opentrons App deck map)
    # -----------------------------------------------------------------------
    broth = protocol.define_liquid("Broth (CAMHB)", display_color="#ff9900")
    antibiotic = protocol.define_liquid("Antibiotic, 2x top concentration",
                                        display_color="#cf0d0d")
    bacteria = protocol.define_liquid("Bacteria, ~1e6 CFU/mL", display_color="#0517c2")

    reservoir["A1"].load_liquid(liquid=broth, volume=12000)
    reservoir["A2"].load_liquid(liquid=antibiotic, volume=4000)
    reservoir["A3"].load_liquid(liquid=bacteria, volume=12000)

    broth_src = reservoir["A1"]
    abx_src = reservoir["A2"]
    bact_src = reservoir["A3"]
    col = plate.rows_by_name()["A"]  # col[0] = column 1 ... col[11] = column 12

    # -----------------------------------------------------------------------
    # Step 1: 100 uL broth into columns 2-11 (one tip)
    # Step 2: 200 uL broth into column 12 (same tip)
    # -----------------------------------------------------------------------
    p300.pick_up_tip()
    for dest in col[1:11]:
        p300.aspirate(BROTH_VOL, broth_src)
        p300.dispense(BROTH_VOL, dest)
    p300.aspirate(STERILITY_VOL, broth_src)
    p300.dispense(STERILITY_VOL, col[11])
    p300.drop_tip()

    # -----------------------------------------------------------------------
    # Step 3: 200 uL antibiotic into column 1 (pre-wet tip first)
    # -----------------------------------------------------------------------
    p300.pick_up_tip()
    p300.mix(1, ANTIBIOTIC_VOL, abx_src)          # pre-wet
    p300.aspirate(ANTIBIOTIC_VOL, abx_src)
    p300.dispense(ANTIBIOTIC_VOL, col[0])
    p300.drop_tip()

    # -----------------------------------------------------------------------
    # Step 4: serial dilution, column 1 -> 10, then discard 100 uL from column 10
    # -----------------------------------------------------------------------
    p300.pick_up_tip()
    p300.mix(1, DILUTION_VOL, col[0])             # pre-wet in column 1
    for src, dest in zip(col[0:9], col[1:10]):
        p300.aspirate(DILUTION_VOL, src)
        p300.dispense(DILUTION_VOL, dest)
        p300.mix(MIX_REPS, MIX_VOL, dest)
    p300.aspirate(DILUTION_VOL, col[9])
    p300.dispense(DILUTION_VOL, trash)
    p300.drop_tip()

    # -----------------------------------------------------------------------
    # Optional pause: load / resuspend the inoculum in reservoir A3
    # -----------------------------------------------------------------------
    if PAUSE_BEFORE_BACTERIA:
        protocol.pause("Load or resuspend the bacterial inoculum (~1e6 CFU/mL) in "
                       "reservoir A3, then click Resume. Use it within 15 min of preparation.")

    # -----------------------------------------------------------------------
    # Step 5: 100 uL bacteria into columns 1-11, fresh tip each column
    # -----------------------------------------------------------------------
    for dest in col[0:11]:
        p300.pick_up_tip()
        p300.mix(1, BACTERIA_VOL, bact_src)       # pre-wet (also resuspends)
        p300.aspirate(BACTERIA_VOL, bact_src)
        p300.dispense(BACTERIA_VOL, dest)
        p300.mix(MIX_REPS, MIX_VOL, dest)
        p300.drop_tip()
