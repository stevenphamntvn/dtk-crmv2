"""Local customer creation; Google Sheets upload remains an explicit action."""

import os
import re
import tempfile
from pathlib import Path
from threading import RLock

import pandas as pd


CUSTOMER_COLUMNS = ['KID', 'PLK', 'thongtin_KID', 'ghi_chu', 'bo_loc_KID', 'ngay_tuong_tac']
_customer_lock = RLock()


def read_customers(path):
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=CUSTOMER_COLUMNS)
    try:
        customers = pd.read_csv(path, dtype=str, encoding='utf-8-sig').fillna('')
        customers.columns = customers.columns.str.strip()
        return customers
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=CUSTOMER_COLUMNS)


def next_customer_id(customers):
    ids = customers.get('KID', pd.Series(dtype=str)).astype(str).str.strip()
    numbers = [int(m.group(1)) for value in ids if (m := re.fullmatch(r'KID_(\d+)', value, re.I))]
    return f"KID_{max(numbers, default=0) + 1:03d}"


def append_customer(path, record):
    """Re-read the latest CSV, reject duplicate IDs, and replace it atomically."""
    if not str(record.get('thongtin_KID', '')).strip():
        raise ValueError('Vui lòng nhập tên khách hàng.')
    if not str(record.get('KID', '')).strip():
        raise ValueError('Thiếu mã khách hàng.')
    with _customer_lock:
        customers = read_customers(path)
        if record['KID'] in set(customers.get('KID', pd.Series(dtype=str)).astype(str).str.strip()):
            raise ValueError('Mã khách đã được sử dụng. Hãy quay lại và xem báo cáo để lấy mã mới.')
        columns = list(dict.fromkeys([*customers.columns, *CUSTOMER_COLUMNS]))
        row = {column: str(record.get(column, '')) for column in columns}
        updated = pd.concat([customers.reindex(columns=columns), pd.DataFrame([row])], ignore_index=True).fillna('')
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as stream:
                temporary = stream.name
            updated.to_csv(temporary, index=False, encoding='utf-8-sig')
            os.replace(temporary, path)
        finally:
            if temporary and os.path.exists(temporary):
                os.remove(temporary)
    return updated
