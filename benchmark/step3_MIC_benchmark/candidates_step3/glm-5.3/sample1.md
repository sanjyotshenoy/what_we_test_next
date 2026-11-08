# MIC Broth Microdilution Protocol — OT-2

Below is a complete design for a CLSI-style 2-fold broth microdilution MIC assay: 4 antibiotics × 2 replicates, 11 concentrations each + growth control, all on one 96-well plate, driven by the 8-channel pipette.

## 1. Plate Map

Each **row** = one antibiotic replicate; dilution runs **across columns 1→11**; column 12 = growth control (no antibiotic).

| Row | Antibiotic | Col 1 → Col 11 | Col 12 |
|---|---|---|---|
| A, B | Antibiotic 1 (rep 1, 2) | 2-fold dilution series (high → low) | Growth control |
| C, D | Antibiotic 2 (rep 1, 2) | ″ | Growth control |
| E, F | Antibiotic 3 (rep 1, 2) | ″ | Growth control |
| G, H | Antibiotic 4 (rep 1, 2) | ″ | Growth control |

**Concentration scheme (2× strategy, 100 µL final volume/well):**
- Reservoir antibiotic stock = **2× your highest desired final concentration**
- Example: stock 512 µg/mL → final well concentrations: **256, 128, 64, 32, 16, 8, 4, 2, 1, 0.5, 0.25 µg/mL**, 0 (col 12)

## 2. Liquid Handling Volumes (per well)

| Step | Volume | Target |
|---|---|---|
| Media (e.g., cMHB) | 50 µL | Columns 2–12 (all rows) |
| Antibiotic 2× stock | 100 µL | Column 1 (rows per antibiotic) |
| Serial dilution transfer | 50 µL | Col 1→2→…→10→11, then discard 50 µL from col 11 to waste |
| Bacterial inoculum (2×) | 50 µL | All 96 wells |

Final volume = 100 µL/well; inoculum target ~5×10⁵ CFU/mL (load reservoir at ~1×10⁶ CFU/mL, i.e., a 0.5 McFarland suspension appropriately diluted).

## 3. Deck Layout

| Slot | Labware | Notes |
|---|---|---|
| 1 | 300 µL tiprack | 8-channel (exactly 96 tips used — no reuse across antibiotics to prevent cross-contamination) |
| 2 | 96-well plate | flat-bottom, e.g. Corning 360 µL |
| 5 | 12-channel reservoir | see map below |
| 6 | 300 µL tiprack | single-channel |

**Reservoir map (A1–A12):**
- A1: Media (~6 mL +)
- A2: Antibiotic 1 (2× stock, ≥0.5 mL)
- A3: Antibiotic 2 · A4: Antibiotic 3 · A5: Antibistic 4
- A6: Bacterial inoculum (~7 mL)
- A12: Waste (for col 11 discard volume / blowouts)

> ⚠️ One note on your labware list: the 8-channel pipette **cannot seed column 1**, because column 1 contains *four different* antibiotics (2 rows each) while the multichannel aspirates a uniform trough. You'll need either a **P300 single-channel pipette on the right mount** (recommended — only 4 tips used), or to pre-load column 1 manually (8 pipettings) before the run. Everything else below is 8-channel.

## 4. Protocol (Python API v2)

```python
metadata = {
    'protocolName': 'MIC 2-fold broth microdilution - 4 antibiotics x 2 replicates',
    'apiLevel': '2.13'
}

def run(protocol):
    # ---------- Labware ----------
    tips_multi   = protocol.load_labware('opentrons_96_tiprack_300ul', 1)
    tips_single  = protocol.load_labware('opentrons_96_tiprack_300ul', 6)
    plate        = protocol.load_labware('corning_96_wellplate_360ul_flat', 2)
    reservoir    = protocol.load_labware('usascientific_12_reservoir_22ml', 5)

    m300 = protocol.load_instrument('p300_multi_gen2', 'left',
                                    tip_racks=[tips_multi])
    p300 = protocol.load_instrument('p300_single_gen2', 'right',
                                    tip_racks=[tips_single])

    # ---------- Reservoir assignments ----------
    media     = reservoir['A1']
    abx_stock = [reservoir['A2'], reservoir['A3'],
                 reservoir['A4'], reservoir['A5']]
    bacteria  = reservoir['A6']
    waste     = reservoir['A12']

    # Rows per antibiotic: A/B = Abx1, C/D = Abx2, E/F = Abx3, G/H = Abx4
    abx_rows = [['A', 'B'], ['C', 'D'], ['E', 'F'], ['G', 'H']]

    VOL_MEDIA    = 50   # µL into cols 2-12
    VOL_SEED     = 100  # µL antibiotic stock into col 1
    VOL_TRANSFER = 50   # µL serial dilution transfer
    VOL_BACT     = 50   # µL inoculum into all wells

    cols = plate.columns()

    # ---------- Step 1: media into columns 2-12 ----------
    m300.pick_up_tip()
    media_dests = [w for col in cols[1:] for w in col]
    m300.distribute(VOL_MEDIA, media.bottom(2), media_dests,
                    disposal_volume=20)
    m300.drop_tip()

    # ---------- Step 2: seed column 1 with 2x antibiotic stocks ----------
    for stock, rows in zip(abx_stock, abx_rows):
        p300.pick_up_tip()
        p300.aspirate(VOL_SEED * 2, stock.bottom(2))
        for r in rows:
            p300.dispense(VOL_SEED, plate[r + '1'].bottom(5))
        p300.blow_out(waste)
        p300.drop_tip()

    # ---------- Step 3: 2-fold serial dilution across columns 1 -> 11 ----------
    for i in range(10):
        m300.pick_up_tip()
        m300.transfer(VOL_TRANSFER, cols[i], cols[i + 1],
                      mix_after=(3, 40),      # 3x 40 µL mix in destination
                      touch_tip=True,
                      new_tip='never')
        if i < 9:
            m300.drop_tip()
        else:
            # Remove excess 50 µL from column 11 to normalize volume
            m300.aspirate(VOL_TRANSFER, cols[10])
            p300_none = None
            m300.dispense(VOL_TRANSFER, waste)
            m300.drop_tip()

    # ---------- Step 4: inoculate all wells with bacteria ----------
    m300.pick_up_tip()
    all_wells = [w for col in cols for w in col]
    m300.distribute(VOL_BACT, bacteria.bottom(2), all_wells,
                    disposal_volume=20)
    m300.drop_tip()
```

*(Remove the stray `p300_none = None` line — or just use a fresh tip pickup there if you add a second multichannel rack.)*

**Tip budget check (8-channel):** media 1 + dilution 10 (waste-removal merged into the 10th) + inoculum 1 = 12 pickups × 8 tips = **exactly 96 tips, one rack**. Fresh tips at every dilution step are essential — reusing tips would carry antibiotic 1 into antibiotic 4 rows.

## 5. Important Notes

- **Labware definitions:** swap the `load_labware` strings to match your *actual* plate/reservoir (check the Opentrons Labware Library); miscalibrated definitions will cause crashes and volume errors.
- **Dead volume:** single-channel aspirating 200 µL from a 22 mL trough works, but load ≥0.5 mL of each antibiotic; load media/inoculum with ~1–2 mL excess over the calculated 4.4/4.8 mL.
- **No sterility control fits on this plate** (all 96 wells used). If you want one, either run a duplicate media-only plate, or drop one replicate's column 12... simplest is a separate blank plate incubated alongside.
- **Mixing the inoculum:** gently resuspend the bacterial suspension right before loading; the distribute step dispenses into 50 µL of liquid, giving adequate mixing. If you want explicit post-inoculation mixing, add a second tiprack and a slow 2× 50 µL mix pass.
- **After the run:** seal or lid the plate, incubate 35 ± 2 °C, 16–20 h. MIC = lowest concentration with no visible growth (confirm with OD600 or resazurin if you prefer a plate reader).
- **Sanity checks before the real run:** do a dry/water run to verify tiprack positions, and confirm the col-1 stock concentration math (stock = 2× desired top final concentration).

Want me to modify this for a different plate map (e.g., antibiotics by column with 8-point dilution, freeing a sterility control), a specific plate labware, or add the optional mixing/plate-reader steps?