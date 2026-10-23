from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crm_v2 import VERSION
from crm_v2.releases import build

root = Path(__file__).resolve().parents[1]
destination = root / 'releases' / f'DTK_CRM_{VERSION}.zip'
print(destination)
print('SHA256:', build(root, destination, VERSION))
