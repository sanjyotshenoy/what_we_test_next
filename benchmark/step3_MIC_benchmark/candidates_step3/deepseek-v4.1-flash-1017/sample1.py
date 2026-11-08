from opentrons import protocol_api

metadata = {
    'protocolName': 'MIC 2-fold dilution assay - 4 antibiotics x 2 replicates',
    'author': 'Opentrons prototype',
    'apiLevel': '2.14'
}

def run(protocol: protocol_api.ProtocolContext):
    # ------------------- Labware -------------------
    tiprack = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    assay_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    source_plate = protocol.load_labware('nest_96_wellplate_2ml_deep', 3)  # row-specific 2x antibiotic master mixes
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', 4)

    # ------------------- Pipette -------------------
    pipette = protocol.load_instrument('p300_multi_gen2', 'right', tip_racks=[tiprack])

    # ------------------- Reagents -------------------
    media = reservoir.wells()[0]      # A1
    bacteria = reservoir.wells()[1]   # A2
    waste = reservoir.wells()[11]     # A12

    # ------------------- Parameters -------------------
    media_vol = 100
    drug_vol = 200
    transfer_vol = 100
    inoculum_vol = 100
    mix_reps = 3
    mix_vol = 100
    num_concentrations = 10  # columns 1-10; columns 11-12 for controls

    # ------------------- 1. Fill media into columns 2-12 -------------------
    pipette.pick_up_tip()
    for col in range(1, 12):  # 0-indexed: columns 2 to 12
        pipette.aspirate(media_vol, media)
        pipette.dispense(media_vol, assay_plate.columns()[col])
        pipette.blow_out(media)
    pipette.drop_tip()

    # ------------------- 2. Add 2x antibiotic master mix to column 1 -------------------
    pipette.pick_up_tip()
    pipette.aspirate(drug_vol, source_plate.columns()[0])
    pipette.dispense(drug_vol, assay_plate.columns()[0])
    pipette.blow_out()
    pipette.drop_tip()

    # ------------------- 3. Serial dilution: col1 -> col2 ... -> col10 -------------------
    pipette.pick_up_tip()
    for i in range(num_concentrations - 1):
        source_col = assay_plate.columns()[i]
        dest_col = assay_plate.columns()[i + 1]
        pipette.aspirate(transfer_vol, source_col)
        pipette.dispense(transfer_vol, dest_col)
        pipette.mix(mix_reps, mix_vol, dest_col)
    # Discard 100 µL from the last concentration column to leave 100 µL
    last_col = assay_plate.columns()[num_concentrations - 1]
    pipette.aspirate(transfer_vol, last_col)
    pipette.dispense(transfer_vol, waste)
    pipette.blow_out(waste)
    pipette.drop_tip()

    # ------------------- 4. Add bacteria to columns 1-11 (growth control in col 11) -------------------
    pipette.pick_up_tip()
    pipette.mix(5, 200, bacteria)  # resuspend bacteria
    for col in range(11):  # 0-10: columns 1-11
        pipette.aspirate(inoculum_vol, bacteria)
        pipette.dispense(inoculum_vol, assay_plate.columns()[col])
        pipette.blow_out()
    pipette.drop_tip()

    # ------------------- 5. Add media to column 12 (sterility control) -------------------
    pipette.pick_up_tip()
    pipette.aspirate(media_vol, media)
    pipette.dispense(media_vol, assay_plate.columns()[11])
    pipette.blow_out(media)
    pipette.drop_tip()
