"""Verify reports against the actual push/pull direction, without real sync."""

import ast
from pathlib import Path
import sys
import unittest

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Data'))
from sync_report import build_sync_report, style_sync_report


class SyncReportTests(unittest.TestCase):
    def test_online_customer_is_green_when_pulling_and_red_when_pushing(self):
        local = pd.DataFrame([{'KID': 'KID_001', 'thongtin_KID': 'Khách A'}])
        online = pd.DataFrame([{'KID': 'KID_001', 'thongtin_KID': 'Khách A'},
                               {'KID': 'KID_003', 'thongtin_KID': 'Khách C'}])
        pull = build_sync_report(local, online, ['KID'], 'pull')
        push = build_sync_report(local, online, ['KID'], 'push')
        self.assertEqual((pull['added'], pull['removed'], pull['updated']), (1, 0, 0))
        self.assertEqual((push['added'], push['removed'], push['updated']), (0, 1, 0))
        row = pull['rows'].query("`Thông tin` == 'Tên / thông tin khách'").iloc[0]
        self.assertEqual((row['Local'], row['Online']), ('—', '+ Khách C'))
        row = push['rows'].query("`Thông tin` == 'Tên / thông tin khách'").iloc[0]
        self.assertEqual((row['Local'], row['Online']), ('—', '− Khách C'))
        pull_styles = style_sync_report(pull)._compute().ctx
        push_styles = style_sync_report(push)._compute().ctx
        online_col = pull['rows'].columns.get_loc('Online')
        self.assertIn(('color', '#15803d'), pull_styles[(0, online_col)])
        self.assertIn(('color', '#b91c1c'), push_styles[(0, online_col)])

    def test_edits_show_only_changed_fields_with_before_and_after(self):
        local = pd.DataFrame([{'KID': 'KID_001', 'thongtin_KID': 'Minh', 'PLK': 'B', 'ghi_chu': 'Gọi chiều'}])
        online = pd.DataFrame([{'KID': 'KID_001', 'thongtin_KID': 'Minh', 'PLK': 'A', 'ghi_chu': 'Gọi sáng'}])
        for direction in ['push', 'pull']:
            with self.subTest(direction=direction):
                report = build_sync_report(local, online, ['KID'], direction)
                self.assertEqual(report['updated'], 1)
                self.assertEqual(len(report['rows']), 2)
                notes = report['rows'].query("`Thông tin` == 'Ghi chú'").iloc[0]
                expected = ('+ Gọi chiều', '− Gọi sáng') if direction == 'push' else ('− Gọi chiều', '+ Gọi sáng')
                self.assertEqual((notes['Local'], notes['Online']), expected)

    def test_log_identity_includes_customer_and_house(self):
        local = pd.DataFrame([{'KID': 'K1', 'UID': '0012', 'trang_thai': 'đã gửi', 'phan_hoi': 'Thích'}])
        online = pd.DataFrame([{'KID': 'K1', 'UID': '0012', 'trang_thai': 'chưa gửi', 'phan_hoi': ''}])
        report = build_sync_report(local, online, ['KID', 'UID'], 'push', {'K1': 'Anh Minh'})
        self.assertEqual(report['updated'], 1)
        self.assertEqual(set(report['rows']['UID']), {'0012'})
        self.assertEqual(set(report['rows']['Khách hàng']), {'Anh Minh'})
        self.assertIn('− (trống)', set(report['rows']['Online']))
        self.assertIn('+ Thích', set(report['rows']['Local']))

    def test_empty_online_pull_preserves_local_just_like_current_writer(self):
        local = pd.DataFrame([{'KID': 'K1', 'thongtin_KID': 'Minh'}])
        report = build_sync_report(local, pd.DataFrame(), ['KID'], 'pull')
        self.assertTrue(report['skipped_empty_pull'])
        self.assertEqual(report['removed'], 0)
        self.assertTrue(report['rows'].empty)

    def test_empty_local_push_reports_every_online_record_to_remove(self):
        online = pd.DataFrame([{'KID': 'K1', 'thongtin_KID': 'Minh'}])
        report = build_sync_report(pd.DataFrame(), online, ['KID'], 'push')
        self.assertEqual(report['removed'], 1)
        self.assertEqual(set(report['rows']['Local']), {'—'})
        self.assertIn('− Minh', set(report['rows']['Online']))

    def test_schema_changes_and_blank_values_are_visible(self):
        local = pd.DataFrame([{'KID': 'K1', 'ghi_chu': ''}])
        online = pd.DataFrame([{'KID': 'K1', 'ghi_chu': 'Ghi chú cũ', 'custom': ''}])
        report = build_sync_report(local, online, ['KID'], 'push')
        self.assertEqual(report['updated'], 1)
        self.assertIn('+ (trống)', set(report['rows']['Local']))
        self.assertIn('+ (không có cột)', set(report['rows']['Local']))

    def test_unchanged_rows_are_omitted_and_input_frames_stay_intact(self):
        local = pd.DataFrame([{'KID': ' K1 ', 'ghi_chu': 'Gọi chiều  '}])
        original = local.copy(deep=True)
        online = pd.DataFrame([{'KID': 'K1', 'ghi_chu': 'Gọi chiều'}])
        report = build_sync_report(local, online, ['KID'], 'push')
        self.assertTrue(report['rows'].empty)
        pd.testing.assert_frame_equal(local, original)

    def test_one_note_change_is_the_only_row_despite_all_customer_dates_changing(self):
        online = pd.DataFrame([
            {'KID': f'KID_{i:03d}', 'thongtin_KID': f'Khách {i}', 'ghi_chu': 'Ghi chú cũ',
             'PLK': 'A', 'ngay_tuong_tac': '2026-10-20', 'updated_at': '2026-10-20 10:00:00'}
            for i in range(1, 42)
        ])
        local = online.copy(deep=True)
        local['ngay_tuong_tac'] = '2026-10-22'
        local['updated_at'] = '2026-10-22 09:00:00'
        local['ngay_tuong_tac_new'] = '2026-10-22'
        local.loc[20, 'ghi_chu'] = 'Gọi sau 17h'
        for direction in ['push', 'pull']:
            with self.subTest(direction=direction):
                report = build_sync_report(local, online, ['KID'], direction)
                self.assertEqual((report['added'], report['removed'], report['updated']), (0, 0, 1))
                self.assertEqual(len(report['rows']), 1)
                row = report['rows'].iloc[0]
                self.assertEqual((row['KID'], row['Thông tin']), ('KID_021', 'Ghi chú'))
                self.assertIn('Gọi sau 17h', row['Local'])
                self.assertIn('Ghi chú cũ', row['Online'])

    def test_only_automatic_timestamp_changes_produce_no_report_rows_or_updates(self):
        local = pd.DataFrame([{'KID': 'K1', 'UID': '0012', 'trang_thai': 'đã gửi',
                               'timestamp': '2026-10-22 17:00:00', 'modified_at': '2026-10-22'}])
        online = local.copy(deep=True)
        online['timestamp'] = '2026-10-20 09:00:00'
        online['modified_at'] = '2026-10-20'
        for direction in ['push', 'pull']:
            report = build_sync_report(local, online, ['KID', 'UID'], direction)
            self.assertEqual(report['updated'], 0)
            self.assertTrue(report['rows'].empty)

    def test_scheduled_send_date_changes_remain_visible(self):
        local = pd.DataFrame([{'KID': 'K1', 'UID': '0012', 'ngay_gui': '2026-10-23',
                               'timestamp': '2026-10-22 17:00:00'}])
        online = pd.DataFrame([{'KID': 'K1', 'UID': '0012', 'ngay_gui': '2026-10-24',
                                'timestamp': '2026-10-20 09:00:00'}])
        report = build_sync_report(local, online, ['KID', 'UID'], 'push')
        self.assertEqual(report['updated'], 1)
        self.assertEqual(report['rows']['Thông tin'].tolist(), ['Ngày hẹn / gửi nhà'])

    def test_added_and_removed_customers_still_appear_without_date_fields(self):
        local = pd.DataFrame([{'KID': 'K1', 'thongtin_KID': 'Khách A', 'ngay_tuong_tac_new': '2026-10-22'}])
        online = pd.DataFrame([{'KID': 'K2', 'thongtin_KID': 'Khách B', 'ngay_tuong_tac': '2026-10-20'}])
        report = build_sync_report(local, online, ['KID'], 'push')
        self.assertEqual((report['added'], report['removed'], report['updated']), (1, 1, 0))
        self.assertEqual(set(report['rows']['KID']), {'K1', 'K2'})
        self.assertEqual(set(report['rows']['Thông tin']), {'Mã khách', 'Tên / thông tin khách'})

    def test_ambiguous_keys_are_reported_as_errors(self):
        for rows in [[{'KID': ''}], [{'KID': 'K1'}, {'KID': 'K1'}], [{'name': 'Minh'}]]:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    build_sync_report(pd.DataFrame(rows), pd.DataFrame(), ['KID'], 'push')

    def test_real_dialog_renders_details_without_writing_or_connecting(self):
        tree = ast.parse((ROOT / 'Data' / 'crm_app.py').read_text(encoding='utf-8'))
        definitions = '\n\n'.join(ast.unparse(node) for node in tree.body
                                  if isinstance(node, ast.FunctionDef)
                                  and node.name in ['render_sync_report', 'dialog_kiem_duyet_khoi_khach'])
        script = f'''
import sys
sys.path.insert(0, {str(ROOT / 'Data')!r})
import streamlit as st
import pandas as pd
from sync_report import build_sync_report, style_sync_report
{definitions}
local = pd.DataFrame([{{'KID': 'K1', 'thongtin_KID': 'Khách A'}}])
online = pd.DataFrame([{{'KID': 'K1', 'thongtin_KID': 'Khách A'}},
                       {{'KID': 'K3', 'thongtin_KID': 'Khách C'}}])
dialog_kiem_duyet_khoi_khach(online, local, pd.DataFrame(), pd.DataFrame(), 'pull')
'''
        app = AppTest.from_string(script, default_timeout=10).run()
        self.assertFalse(app.exception)
        self.assertIn('+ Khách C', set(app.dataframe[0].value['Online']))
        self.assertTrue(any(button.label == '📥 XÁC NHẬN OK - TẢI VỀ MÁY' for button in app.button))


if __name__ == '__main__':
    unittest.main()
