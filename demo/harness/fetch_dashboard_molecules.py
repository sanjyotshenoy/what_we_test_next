"""Cache ChEMBL 2D structures for the saved dashboard, with source provenance.

Run from the repo root: python -m demo.harness.fetch_dashboard_molecules
"""
from datetime import datetime, timezone
import hashlib
import json
from urllib.request import urlopen
from xml.etree import ElementTree
from demo.harness.paths import DEMO

IDS = ('CHEMBL8', 'CHEMBL454950')
DEST = DEMO / 'harness/stage/static/data/molecules'


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    provenance = {}
    for identity in IDS:
        source = f'https://www.ebi.ac.uk/chembl/api/data/image/{identity}.svg'
        with urlopen(source, timeout=45) as response:
            image = response.read(2_000_000)
        if ElementTree.fromstring(image).tag.split('}')[-1] != 'svg':
            raise ValueError('ChEMBL did not return an SVG')
        molecule_url = f'https://www.ebi.ac.uk/chembl/api/data/molecule/{identity}.json'
        with urlopen(molecule_url, timeout=45) as response:
            molecule = json.load(response)
        if molecule['molecule_chembl_id'] != identity:
            raise ValueError('Molecule identity mismatch')
        structures = molecule['molecule_structures']
        (DEST / f'{identity}.svg').write_bytes(image)
        (DEST / f'{identity}.mol').write_text(structures['molfile'])
        provenance[identity] = {'image_url': source, 'molecule_url': molecule_url,
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'image_sha256': hashlib.sha256(image).hexdigest(),
            'canonical_smiles': structures['canonical_smiles'],
            'note': 'ChEMBL 2D depiction, not a measured 3D conformation.'}
    (DEST / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    print(f'Cached {len(provenance)} ChEMBL structures.')


if __name__ == '__main__':
    main()
