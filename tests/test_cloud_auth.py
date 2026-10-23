import ast
from pathlib import Path
import unittest
from unittest.mock import Mock


class CloudAuthTests(unittest.TestCase):
    def auth(self, cloud):
        source = (Path(__file__).resolve().parents[1] / 'Data/crm_app.py').read_text(encoding='utf-8')
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'check_authentication')
        st = Mock()
        st.session_state = {}
        st.secrets = {}
        st.stop.side_effect = RuntimeError('streamlit stopped')
        ns = {'st': st, 'IS_CLOUD': cloud}
        exec(ast.get_source_segment(source, node), ns)
        return ns['check_authentication'], st

    def test_cloud_without_configured_users_stops_before_loading_customer_data(self):
        auth, st = self.auth(True)
        with self.assertRaisesRegex(RuntimeError, 'streamlit stopped'):
            auth()
        st.error.assert_called_once()
        st.stop.assert_called_once()

    def test_windows_local_keeps_existing_login_behavior(self):
        auth, st = self.auth(False)
        self.assertTrue(auth())
        st.stop.assert_not_called()
        st.error.assert_not_called()
