"""Exercise customer creation with temporary CSVs and no Google Sheets access."""

import ast
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, Mock

import pandas as pd
from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Data'))
from customer_data import append_customer, next_customer_id, read_customers
from sync_report import build_sync_report


# The legacy entry point runs authentication/UI on import. Extract only the
# relevant functions so tests never initialize the real app or its credentials.
TREE = ast.parse((ROOT / 'Data' / 'crm_app.py').read_text(encoding='utf-8'))


def definitions(*names):
    return '\n\n'.join(ast.unparse(node) for node in TREE.body
                        if isinstance(node, ast.FunctionDef) and node.name in names)


class CustomerCreationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'customers.csv'

    def test_append_preserves_existing_rows_columns_and_leading_zeroes(self):
        original = pd.DataFrame([{'KID': 'KID_009', 'PLK': 'C', 'custom': '0012', 'ghi_chu': 'Cũ'}])
        original.to_csv(self.path, index=False, encoding='utf-8-sig')
        kid = next_customer_id(read_customers(self.path))
        self.assertEqual(kid, 'KID_010')
        append_customer(self.path, {'KID': kid, 'PLK': 'B', 'thongtin_KID': 'Khách mới', 'ghi_chu': 'Có nhu cầu'})
        saved = read_customers(self.path)
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved.iloc[0]['custom'], '0012')
        self.assertEqual(saved.iloc[1]['thongtin_KID'], 'Khách mới')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            append_customer(self.path, {'KID': kid, 'thongtin_KID': 'Trùng'})
        self.assertEqual(self.path.read_bytes(), before)

    def test_blank_name_never_writes(self):
        with self.assertRaises(ValueError):
            append_customer(self.path, {'KID': 'KID_001', 'thongtin_KID': '  '})
        self.assertFalse(self.path.exists())

    def test_protocol_preserves_fractional_filters(self):
        namespace = {'re': re, 'pd': pd}
        exec(definitions('parse_blk', 'build_blk'), namespace)
        protocol = namespace['build_blk']('Khách mới', 6.5, 9.5, {'QBT': ['1']}, 3.7, 2, 3, 45.5, ['MAT', 'KLP'])
        parsed = namespace['parse_blk'](protocol)
        self.assertEqual((parsed['min_gia'], parsed['max_gia'], parsed['min_ngang'], parsed['min_dt']), (6.5, 9.5, 3.7, 45.5))
        self.assertEqual(parsed['quan_phuong'], {'QBT': ['1']})
        self.assertEqual(parsed['tags'], ['MAT', 'KLP'])

    def test_empty_log_does_not_pull_over_local_customers(self):
        pd.DataFrame([{'KID': 'KID_001', 'thongtin_KID': 'Chưa upload'}]).to_csv(self.path, index=False)
        houses = Path(self.directory.name) / 'houses.csv'
        pd.DataFrame([{'uid': '001'}]).to_csv(houses, index=False)
        pull = Mock(return_value=(pd.DataFrame(), pd.DataFrame()))
        namespace = {'pd': pd, 'os': os, 'FILE_KID': str(self.path), 'FILE_GSK': str(houses),
                     'FILE_LOG': str(Path(self.directory.name) / 'log.csv'),
                     'pull_khoi_khach_va_log': pull, 'st': Mock()}
        exec(definitions('load_local_data'), namespace)
        _, customers, _ = namespace['load_local_data']()
        pull.assert_called_once_with(pull_kids=False, pull_logs=True)
        self.assertEqual(customers.iloc[0]['thongtin_KID'], 'Chưa upload')

    def test_existing_push_uploads_the_new_local_customer(self):
        record = {'KID': 'KID_001', 'PLK': 'A', 'thongtin_KID': 'Khách mới',
                  'ghi_chu': 'Gọi chiều', 'bo_loc_KID': 'Khách mới.G6-9T.QBT', 'ngay_tuong_tac': ''}
        append_customer(self.path, record)
        local = read_customers(self.path)
        st = MagicMock()
        st.dialog.return_value = lambda function: function
        st.session_state = {}
        st.button.return_value = True
        sheet = Mock()
        kid_sheet, log_sheet = Mock(), Mock()
        sheet.worksheet.side_effect = {'MyKID': kid_sheet, 'KID_log': log_sheet}.__getitem__
        client = Mock()
        client.open_by_key.return_value = sheet
        namespace = {'pd': pd, 'st': st, 'SHEET_ID': 'test-only', 'get_gspread_client': lambda: client,
                     'build_sync_report': build_sync_report, 'render_sync_report': Mock()}
        exec(definitions('compare_dataframes', 'dialog_kiem_duyet_khoi_khach'), namespace)
        namespace['dialog_kiem_duyet_khoi_khach'](pd.DataFrame(), local, pd.DataFrame(), pd.DataFrame(), 'push')
        kid_sheet.update.assert_called_once_with([local.columns.tolist()] + local.values.tolist())
        self.assertEqual(st.session_state['sync_success'], 'push')

    def test_saved_customer_replaces_stale_selection_and_classification_filter(self):
        namespace = {'st': Mock()}
        exec(definitions('apply_created_customer_selection'), namespace)
        for classification in ['A', 'B', 'D']:
            with self.subTest(classification=classification):
                state = {'customer_to_select': 'KID_010', 'app_mode': 'TIM_KHACH',
                         'local_plk_filter': 'Khách C', 'cloud_plk_filter': 'Khách C',
                         'kid_selectbox_Khách C': 'Khách cũ', 'active_kid': 'KID_009', 'active_blk': 'Cũ'}
                namespace['st'].session_state = state
                customers = pd.DataFrame([{'KID': 'KID_010', 'PLK': classification, 'thongtin_KID': 'Khách mới'}])
                namespace['apply_created_customer_selection'](customers)
                selected_filter = 'Khách D (Đã bỏ)' if classification == 'D' else f'Khách {classification}'
                self.assertEqual(state['local_plk_filter'], selected_filter)
                self.assertEqual(state['cloud_plk_filter'], selected_filter)
                self.assertEqual(state[f'kid_selectbox_{selected_filter}'], f'KID_010({classification}). Khách mới')
                self.assertNotIn('kid_selectbox_Khách C', state)
                self.assertNotIn('customer_to_select', state)
                self.assertNotIn('active_kid', state)
                self.assertEqual(state['app_mode'], 'GUI_KHACH')

    def make_app(self):
        source = f"""
import sys
sys.path.insert(0, {str(ROOT / 'Data')!r})
import streamlit as st
import pandas as pd
from customer_data import append_customer, next_customer_id, read_customers
FILE_KID = {str(self.path)!r}
MAP_QUAN = {{'Bình Thạnh': 'QBT', 'Phú Nhuận': 'QPN'}}
REV_MAP_QUAN = {{v: k for k, v in MAP_QUAN.items()}}
CONFIG_GSK_CM = {{'QUAN': 'quan', 'PHUONG': 'phuong'}}
{definitions('build_blk', 'current_customer_needs', 'show_customer_needs', 'dialog_add_customer', 'render_add_customer_button', 'apply_created_customer_selection')}
st.session_state.setdefault('active_kid', 'KID_009')
st.session_state.setdefault('mg_KID_009', 6.5)
st.session_state.setdefault('xg_KID_009', 9.5)
st.session_state.setdefault('mn_KID_009', 3.7)
st.session_state.setdefault('q_KID_009', ['Bình Thạnh', 'Phú Nhuận'])
st.session_state.setdefault('p_KID_009', ['1', '2'])
st.session_state.setdefault('mat_KID_009', True)
houses = pd.DataFrame([{{'quan': 'Bình Thạnh', 'phuong': '1'}}, {{'quan': 'Phú Nhuận', 'phuong': '2'}}])
customers = read_customers(FILE_KID)
apply_created_customer_selection(customers)
if not customers.empty:
    st.dataframe(customers)
    selected_filter = st.session_state.get('local_plk_filter', 'Khách A')
    options = [f"{{row.KID}}({{row.PLK}}). {{row.thongtin_KID}}" for row in customers.itertuples()]
    st.selectbox('Đang chăm sóc:', options, key=f'kid_selectbox_{{selected_filter}}')
if 'customer_created_message' in st.session_state:
    st.success(st.session_state.pop('customer_created_message'))
    st.session_state['test_dialog_open'] = False
if st.button('➕ Thêm khách hàng'):
    st.session_state['test_dialog_open'] = True
if st.session_state.get('test_dialog_open'):
    dialog_add_customer(current_customer_needs(houses), ['A', 'B', 'C', 'D'])
"""
        return AppTest.from_string(source, default_timeout=10).run()

    def button(self, app, label):
        return next(button for button in app.button if button.label == label)

    def test_review_edit_confirm_local_only(self):
        app = self.make_app()
        self.button(app, '➕ Thêm khách hàng').click().run()
        self.assertFalse(app.exception)
        app.text_input[0].set_value('Anh Minh')
        app.selectbox[0].set_value('B')
        app.text_area[0].set_value('Liên hệ buổi chiều')
        self.button(app, 'Xem báo cáo trước khi lưu').click().run()
        self.assertFalse(app.exception)
        self.assertFalse(self.path.exists(), 'Review must not save data')
        self.assertEqual(app.session_state['new_customer_review']['bo_loc_KID'],
                         'Anh Minh.G6.5-9.5T.QBT(1)+QPN(2).N3.7M.MAT')
        reviewed_protocol = app.code[0].value
        self.assertEqual(reviewed_protocol, app.session_state['new_customer_review']['bo_loc_KID'])
        self.button(app, 'Quay lại chỉnh sửa').click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.text_input[0].value, 'Anh Minh')
        app.text_area[0].set_value('Gọi sau 17h')
        self.button(app, 'Xem báo cáo trước khi lưu').click().run()
        self.button(app, 'Xác nhận lưu khách hàng').click().run()
        self.assertFalse(app.exception)
        saved = read_customers(self.path)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved.iloc[0]['PLK'], 'B')
        self.assertEqual(saved.iloc[0]['ghi_chu'], 'Gọi sau 17h')
        self.assertEqual(saved.iloc[0]['thongtin_KID'], 'Anh Minh')
        self.assertEqual(saved.iloc[0]['bo_loc_KID'], reviewed_protocol)
        self.assertIn('UP KK LÊN', app.success[0].value)
        self.assertEqual(app.dataframe[0].value.iloc[0]['thongtin_KID'], 'Anh Minh')
        self.assertEqual(app.selectbox[0].value, 'KID_001(B). Anh Minh')

    def test_budget_8_to_15_review_and_save_use_the_exact_protocol(self):
        app = self.make_app()
        app.session_state['mg_KID_009'] = 8.0
        app.session_state['xg_KID_009'] = 15.0
        app.session_state['mn_KID_009'] = 4.0
        app.session_state['mpn_KID_009'] = 3
        app.session_state['mtg_KID_009'] = 4
        app.session_state['mdt_KID_009'] = 60.0
        app.session_state['p_KID_009'] = ['1']
        app.session_state['hxh_KID_009'] = True
        app.session_state['tma_KID_009'] = True
        app.session_state['klp_KID_009'] = True
        self.button(app, '➕ Thêm khách hàng').click().run()
        app.text_input[0].set_value('Anh Minh')
        self.button(app, 'Xem báo cáo trước khi lưu').click().run()
        self.assertFalse(app.exception)
        expected = 'Anh Minh.G8-15T.QBT(1)+QPN.N4M.PN3.TG4.DT60.MAT.HXH.TMA.KLP'
        self.assertEqual(app.code[0].value, expected)
        self.assertFalse(self.path.exists())
        self.button(app, 'Xác nhận lưu khách hàng').click().run()
        self.assertFalse(app.exception)
        saved = read_customers(self.path).iloc[0]
        self.assertEqual(saved['thongtin_KID'], 'Anh Minh')
        self.assertEqual(saved['bo_loc_KID'], expected)

    def test_empty_name_and_invalid_price_cannot_reach_confirmation(self):
        app = self.make_app()
        self.button(app, '➕ Thêm khách hàng').click().run()
        self.button(app, 'Xem báo cáo trước khi lưu').click().run()
        self.assertTrue(app.error)
        self.assertFalse(self.path.exists())
        app = self.make_app()
        app.session_state['mg_KID_009'] = 20.0
        self.button(app, '➕ Thêm khách hàng').click().run()
        app.text_input[0].set_value('Khách')
        self.button(app, 'Xem báo cáo trước khi lưu').click().run()
        self.assertTrue(app.error)
        self.assertFalse(self.path.exists())


if __name__ == '__main__':
    unittest.main()
