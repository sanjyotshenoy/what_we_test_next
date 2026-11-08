# Why it failed

The previous version needed a **single-channel pipette** to seed column 1 (because that column contains 4 different antibiotics — 2 rows each — and an 8-channel aspirates one uniform liquid across all 8 rows). With only the 8-channel attached, the protocol can't mount.

# The underlying problem — and the fix

An 8-channel pipette can only aspirate **one liquid at a time** across its 8 nozzles. So it can never seed a column that holds 4 different antibiotics directly from the trough reservoir.

**Solution: an antibiotic "stock plate."** Pre-array the four 2× antibiotic stocks in a spare 96-well plate exactly matching the layout of assay-plate column 1. Then one 8-channel move aspirates 8 *different* liquids (one per channel/nozzle) and dispenses them into column 1 in a single step. This is a standard trick for multichannel-only MIC protocols, and it uses only basic API commands that simulate reliably.

The stocks are loaded into the stock plate by hand (8 wells × ~200 µL) — the same manual effort as filling the reservoir troughs, using any handheld pipette. Everything downstream is fully automated.

## New deck layout

| Slot | Labware | Contents |
|---|---|---|
| 1 | 300 µL tiprack (96 tips) | Multichannel — consumed **exactly** |
| 2 | 96-well assay plate | As before |
| 5 | 12-channel reservoir | A1 = media (~6 mL), A6 = bacteria (~6 mL), A12 = waste (A2–A5 now unused) |
| 6 | **Stock plate** (96-well) | Column 1: A1,B1 = Abx 1 · C1,D1 = Abx 2 · E1,F1 = Abx 3 · G1,H1 = Abx 4 — each well ≥ 200 µL of 2× stock |

# Complete corrected protocol

```python
metadata = {
    'protocolName': 'MIC 2-fold broth microdilution - 4 antibiotics x 2 replicates (8-channel only)',
    'apiLevel': '2.13'
}

def run(protocol):
    # ---------------- Labware ----------------
    tips_multi  = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    plate       = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    reservoir   = protocol.load_labware('usascientific_12_reservoir_22ml', 5)
    stock_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', 6)

    m300 = protocol.load_instrument('p300_multi_gen2', 'left',
                                    tip_racks=[tips_multi])

    # ---------------- Reservoir / stock plate assignments ----------------
    media    = reservoir['A1']     # cation-adjusted MHB, load >= 6 mL
    bacteria = reservoir['A6']      # 2x inoculum (~1e6 CFU/mL), load >= 6 mL
    waste    = reservoir['A12']

    # Stock plate column 1 mirrors assay plate column 1:
    #   A1,B1 = Antibiotic 1 | C1,D1 = Antibiotic 2
    #   E1,F1 = Antibiotic 3 | G1,H1 = Antibiotic 4
    # Each well loaded with >= 200 uL of 2x stock.
    abx_stock_col = stock_plate['A1']   # one well -> multichannel acts on A1..H1

    VOL_MEDIA    = 50   # uL media into cols 2-12
    VOL_SEED     = 100  # uL antibiotic stock into col 1
    VOL_TRANSFER = 50   # uL serial dilution transfer
    VOL_BACT     = 50   # uL inoculum into all wells

    cols = plate.columns()

    # ---------------- STEP 1: media into columns 2-12 ----------------
    m300.pick_up_tip()
    media_cols = cols[1:]                              # columns 2..12
    for i in range(0, len(media_cols), 4):
        batch = media_cols[i:i + 4]
        m300.aspirate(VOL_MEDIA * len(batch), media.bottom(2))
        for col in batch:
            m300.dispense(VOL_MEDIA, col[0])           # well A -> whole column
    m300.blow_out(media.top())
    m300.drop_tip()

    # ---------------- STEP 2: seed column 1 from the stock plate ----------------
    # Each channel aspirates its OWN antibiotic from its own stock well,
    # then dispenses into the matching assay-plate row.
    m300.pick_up_tip()
    m300.aspirate(VOL_SEED, abx_stock_col.bottom(3))
    m300.dispense(VOL_SEED, plate['A1'].bottom(5))
    # Tips are NOT dropped here: each channel's tip has only ever touched
    # its own antibiotic, so they are reused for the first dilution
    # transfer (this keeps total tip usage at exactly 96).

    # ---------------- STEP 3: 2-fold serial dilution, columns 1 -> 11 ----------------
    for i in range(10):
        if i > 0:
            m300.pick_up_tip()                          # fresh tips per transfer
        src = cols[i][0]
        dst = cols[i + 1][0]

        m300.aspirate(VOL_TRANSFER, src)
        m300.dispense(VOL_TRANSFER, dst)

        # mix destination column 3 x 50 uL
        for _ in range(3):
            m300.aspirate(VOL_TRANSFER, dst)
            m300.dispense(VOL_TRANSFER, dst)

        if i == 9:
            # remove excess 50 uL from column 11 to normalize volume
            m300.aspirate(VOL_TRANSFER, dst)
            m300.dispense(VOL_TRANSFER, waste)

        m300.drop_tip()

    # ---------------- STEP 4: inoculate all 96 wells ----------------
    m300.pick_up_tip()

    # gently resuspend inoculum in the trough before dispensing
    for _ in range(3):
        m300.aspirate(100, bacteria.bottom(5))
        m300.dispense(100, bacteria.bottom(5))

    for i in range(0, 12, 4):
        batch = cols[i:i + 4]
        m300.aspirate(VOL_BACT * len(batch), bacteria.bottom(2))
        for col in batch:
            m300.dispense(VOL_BACT, col[0])

    m300.drop_tip()
```

# Key points

- **Tip budget = exactly 96 tips (one rack):** media 1 column + seeding 1 column (reused for dilution transfer 1) + 9 fresh columns for transfers 2→3 through 10→11 + inoculum 1 column = 12 columns. There is zero margin — if you add any extra step (e.g., post-inoculation well mixing), you must add a second tiprack to `tip_racks`.
- **Why reusing the seeding tips for transfer 1 is safe:** nozzle/channel 0 only ever touches row A (Antibiotic 1), channel 2 only row C (Antibiotic 2), etc. Channels map 1:1 to rows, so cross-antibiotic contamination is geometrically impossible. Fresh tips are still used for every subsequent transfer, per best practice.
- **Stock plate loading:** 8 manual dispenses of ~200 µL (≥ 150 µL required per well). Antibiotic stocks must be at **2× your highest desired final concentration** (e.g., 512 µg/mL → 256 µg/mL top final in column 1). Any spare 96-well plate works; a deep-well plate (e.g., `nest_96_wellplate_2ml_deep`) is also fine — just change the load string.
- **Pipette name:** I assumed a **GEN2** 8-channel (`p300_multi_gen2`, the standard OT-2 config with a 300 µL tip box). If yours is a first-generation pipette, change it to `p300_multi`.
- **Alternative if you don't want a stock plate:** seed column 1 manually with a handheld pipette (8 dispenses of 100 µL), delete Step 2, and change the Step 3 loop to always `pick_up_tip()` (add `if i >= 0:` or just call it unconditionally at loop top) — but the stock-plate approach keeps the run fully automated after loading.
- Reservoir wells A2–A5 are now free; you could optionally use them for sterile water/touch-tip rinse, or leave empty.

Run it in the simulator — it uses only `pick_up_tip`/`aspirate`/`dispense`/`drop_tip`/`blow_out` with fully explicit tip state, all of which already validated on your setup. Let me know if anything else comes up.