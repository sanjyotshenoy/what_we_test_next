from opentrons import protocol_api

metadata = {
    "protocolName": "2-fold MIC - 4 antibiotics in duplicate",
    "author": "Opentrons",
    "description": (
        "Ten 2-fold antibiotic dilutions with growth and sterility controls. "
        "One bacterial strain, four antibiotics, two replicates each."
    ),
    "apiLevel": "2.15"
}


def run(protocol: protocol_api.ProtocolContext):

    # -----------------------------
    # Labware
    # -----------------------------
    plate = protocol.load_labware(
        "nest_96_wellplate_200ul_flat",
        1,
        "MIC assay plate"
    )

    reservoir = protocol.load_labware(
        "nest_12_reservoir_15ml",
        2,
        "Media, antibiotics, bacteria, and waste"
    )

    tips = protocol.load_labware(
        "opentrons_96_tiprack_300ul",
        3,
        "300 uL tips"
    )

    p300 = protocol.load_instrument(
        "p300_multi_gen2",
        "right",
        tip_racks=[tips]
    )

    # Reservoir locations
    media = reservoir["A1"]
    bacteria = reservoir["A6"]
    waste = reservoir["A12"]

    # Antibiotic reservoir positions, referenced in the pause instructions:
    # antibiotic_1 = reservoir["A2"]
    # antibiotic_2 = reservoir["A3"]
    # antibiotic_3 = reservoir["A4"]
    # antibiotic_4 = reservoir["A5"]

    # Optional gentler flow rates
    p300.flow_rate.aspirate = 50
    p300.flow_rate.dispense = 50

    # A1 on a 96-well plate represents the complete A-H column
    # when using the 8-channel pipette.

    # -----------------------------
    # 1. Add media to columns 2-12
    # -----------------------------
    protocol.comment("Adding 50 uL media to columns 2-12.")

    p300.pick_up_tip()

    for column in range(2, 13):
        p300.aspirate(50, media)
        p300.dispense(50, plate[f"A{column}"])

    p300.drop_tip()

    # -----------------------------
    # 2. Manually load antibiotics
    # -----------------------------
    protocol.pause(
        "Manually add 100 uL of the appropriate 2X antibiotic working "
        "solution to column 1:\n"
        "A1 and B1: Antibiotic 1\n"
        "C1 and D1: Antibiotic 2\n"
        "E1 and F1: Antibiotic 3\n"
        "G1 and H1: Antibiotic 4\n"
        "Do not add antibiotic to any other wells. Resume when finished."
    )

    # -----------------------------
    # 3. Perform 2-fold serial dilution
    # -----------------------------
    protocol.comment(
        "Serially transferring 50 uL from column 1 through column 10."
    )

    p300.pick_up_tip()

    for column in range(1, 10):
        source = plate[f"A{column}"]
        destination = plate[f"A{column + 1}"]

        p300.aspirate(50, source)
        p300.dispense(50, destination)

        # Destination contains 100 uL at this stage
        p300.mix(repetitions=5, volume=75, location=destination)

    # Column 10 still contains 100 uL. Remove 50 uL so that
    # columns 1-10 each contain 50 uL before inoculation.
    p300.aspirate(50, plate["A10"])
    p300.dispense(50, waste)
    p300.drop_tip()

    # -----------------------------
    # 4. Inoculate columns 1-11
    # -----------------------------
    protocol.comment(
        "Adding 50 uL bacterial suspension to columns 1-11. "
        "Column 11 is the growth control."
    )

    # Fresh tips for each group reduce carryover between destinations.
    inoculation_groups = [
        range(1, 5),    # Columns 1-4
        range(5, 9),    # Columns 5-8
        range(9, 12)    # Columns 9-11
    ]

    for group in inoculation_groups:
        p300.pick_up_tip()

        for column in group:
            p300.aspirate(50, bacteria)
            p300.dispense(50, plate[f"A{column}"])

        p300.drop_tip()

    # -----------------------------
    # 5. Complete sterility controls
    # -----------------------------
    protocol.comment("Adding 50 uL media to column 12 sterility controls.")

    p300.pick_up_tip()
    p300.aspirate(50, media)
    p300.dispense(50, plate["A12"])
    p300.drop_tip()

    protocol.comment(
        "MIC plate complete. Every well should contain 100 uL. "
        "Cover or seal the plate and incubate according to your validated SOP."
    )
