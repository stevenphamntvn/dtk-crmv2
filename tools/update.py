"""Run only after closing V2. V1 is never stopped or modified."""
import argparse
from pathlib import Path
import socket
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from crm_v2.releases import apply

parser = argparse.ArgumentParser()
parser.add_argument('package', type=Path)
parser.add_argument('--sha256')
args = parser.parse_args()
with socket.socket() as probe:
    if probe.connect_ex(('127.0.0.1', 8506)) == 0:
        raise SystemExit('Hay dong CRM V2 (cong 8506) truoc khi cap nhat. Khong can dong V1.')
version, backup = apply(Path(__file__).resolve().parents[1], args.package, args.sha256)
print(f'Da cap nhat {version}. Ban sao ma nguon cu: {backup}')
print('Chay python -m pip install -r requirements.txt neu ban moi thay doi thu vien. Sau do mo run.bat.')
