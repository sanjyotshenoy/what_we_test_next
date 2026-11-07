"""Constants for building the knowledge graphs."""
CHEMBL_RELEASE = "ChEMBL 37"
CUTOFF_YEAR = 2024            # default hold-out: nothing from documents published in this year or later
CAP_PER_TARGET = 2000         # max IC50 activities (INHIBITS edges) per target in the seed biology graph
PROTEIN_KINASE_CLASS = 1100   # ChEMBL protein_class_id "Protein Kinase" (parent 6 "Kinase")
