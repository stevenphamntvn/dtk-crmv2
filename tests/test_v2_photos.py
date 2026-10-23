"""Photo request metadata integration, without connecting to Sheets."""
import ast
from pathlib import Path
import unittest
import pandas as pd


class PhotoMetadataTests(unittest.TestCase):
    def test_zalo_photo_metadata_keeps_the_drive_link_for_the_correct_house(self):
        source = (Path(__file__).resolve().parents[1] / 'Data/crm_app.py').read_text(encoding='utf-8')
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'prepare_tab3_data')
        ns = {'pd': pd, 'CONFIG_GSK_CM': {'UID':'uid','SONHA':'sonha','TENDUONG':'tenduong',
              'GIA':'gia','PL':'PL','CUS':'cus','QUAN':'quan'},
              'COL_LINK_URL':'URL_Quy_Hoach', 'COL_LINK_GGD':'URL_GGD'}
        exec(ast.get_source_segment(source, node), ns)
        houses = pd.DataFrame([{'uid':'home-1','sonha':'123','tenduong':'Đặng Văn Ngữ',
            'gia':'12','PL':'A','cus':'test','quan':'Phú Nhuận',
            'URL_GGD':'https://drive.google.com/drive/folders/home-1'}])
        logs = pd.DataFrame([['customer-1','home-1','Test','','đã gửi','','2026-10-23'],
                             ['customer-1','missing','Test','','đã gửi','','2026-10-22']],
                            columns=['KID','UID','thongtin_KID','ngay_gui','trang_thai','phan_hoi','timestamp'])
        result = ns['prepare_tab3_data'](logs, houses).set_index('_uid_key')
        self.assertEqual(result.loc['home-1','_link_drive'], 'https://drive.google.com/drive/folders/home-1')
        self.assertEqual(result.loc['home-1','_sonha'], '123')
        self.assertEqual(result.loc['missing','_link_drive'], '')
