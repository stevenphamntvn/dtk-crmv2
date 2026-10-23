"""Read-only, direction-aware details for the existing overwrite sync."""

import pandas as pd


FIELD_LABELS = {
    'KID': 'Mã khách', 'UID': 'Mã nhà', 'PLK': 'Phân loại',
    'thongtin_KID': 'Tên / thông tin khách', 'ghi_chu': 'Ghi chú',
    'bo_loc_KID': 'Nhu cầu (BLK)', 'ngay_tuong_tac': 'Ngày tương tác cuối',
    'ngay_gui': 'Ngày hẹn / gửi nhà', 'trang_thai': 'Trạng thái gửi',
    'phan_hoi': 'Phản hồi', 'timestamp': 'Thời điểm tương tác',
}
REPORT_COLUMNS = ['Thao tác', 'Khách hàng', 'KID', 'UID', 'Thông tin', 'Local', 'Online']
ADD_STYLE = 'color: #15803d; background-color: #dcfce7; font-weight: bold'
REMOVE_STYLE = 'color: #b91c1c; background-color: #fee2e2; font-weight: bold'
# These values are recalculated or stamped during normal editing/sync. They
# still sync normally; they just don't make a customer/log appear in review.
AUTO_UPDATE_FIELDS = frozenset({
    'ngay_tuong_tac', 'ngay_tuong_tac_new', 'timestamp',
    'update', 'updated_at', 'modified_at',
})


def build_sync_report(df_local, df_cloud, primary_keys, direction, customer_names=None):
    if direction not in ('push', 'pull'):
        raise ValueError('Chiều đồng bộ không hợp lệ.')
    source_side, target_side = ('Local', 'Online') if direction == 'push' else ('Online', 'Local')
    frames = {}
    for side, frame in [('Local', df_local), ('Online', df_cloud)]:
        frame = frame.copy().fillna('')
        frame.columns = frame.columns.astype(str).str.strip()
        if frame.columns.duplicated().any():
            raise ValueError(f'{side} có tên cột trùng; cần kiểm tra trước khi đồng bộ.')
        if not frame.empty:
            if any(key not in frame.columns for key in primary_keys):
                raise ValueError(f'{side} thiếu cột khóa {", ".join(primary_keys)}.')
            for column in frame.columns:
                frame[column] = frame[column].astype(str).str.strip()
            if frame[primary_keys].eq('').any().any() or frame.duplicated(primary_keys).any():
                raise ValueError(f'{side} có mã trống hoặc trùng ({", ".join(primary_keys)}); cần kiểm tra trước khi đồng bộ.')
        frames[side] = frame

    report = {'added': 0, 'removed': 0, 'updated': 0, 'source': source_side, 'target': target_side,
              'rows': pd.DataFrame(columns=REPORT_COLUMNS), 'skipped_empty_pull': False}
    # The existing pull skips writing empty source tables; report the real action.
    if direction == 'pull' and frames[source_side].empty:
        report['skipped_empty_pull'] = True
        return report

    def by_key(frame):
        return {tuple(row[key] for key in primary_keys): row for row in frame.to_dict('records')}

    local, cloud = by_key(frames['Local']), by_key(frames['Online'])
    source, target = (local, cloud) if direction == 'push' else (cloud, local)
    fields = [field for field in dict.fromkeys([*frames[target_side].columns, *frames[source_side].columns])
              if field.lower() not in AUTO_UPDATE_FIELDS]
    rows = []
    for key in sorted(set(source) | set(target)):
        new, old = source.get(key), target.get(key)
        if old is None:
            kind, action = 'added', f'Thêm vào {target_side}'
        elif new is None:
            kind, action = 'removed', f'Bỏ khỏi {target_side}'
        else:
            kind, action = 'updated', f'Sửa trên {target_side}: bỏ cũ / thêm mới'
        changed_fields = [field for field in fields
                          if old is None or new is None or old.get(field, '') != new.get(field, '')
                          or (field in old) != (field in new)]
        if not changed_fields:
            continue
        report[kind] += 1
        identity = new if new is not None else old
        kid = identity.get('KID', '')
        name = identity.get('thongtin_KID', '') or (customer_names or {}).get(kid, '') or kid
        for field in changed_fields:
            values = {}
            for side, record in [('Local', local.get(key)), ('Online', cloud.get(key))]:
                if record is None:
                    values[side] = '—'
                else:
                    prefix = '+ ' if side == source_side else '− '
                    value = record.get(field, '(không có cột)') or '(trống)'
                    values[side] = prefix + value
            rows.append({'Thao tác': action, 'Khách hàng': name, 'KID': kid,
                         'UID': identity.get('UID', ''), 'Thông tin': FIELD_LABELS.get(field, field), **values})
    report['rows'] = pd.DataFrame(rows, columns=REPORT_COLUMNS)
    return report


def style_sync_report(report):
    frame = report['rows']
    styles = pd.DataFrame('', index=frame.index, columns=frame.columns)
    for side in ['Local', 'Online']:
        styles.loc[frame[side] != '—', side] = ADD_STYLE if side == report['source'] else REMOVE_STYLE
    return frame.style.apply(lambda _: styles, axis=None)
