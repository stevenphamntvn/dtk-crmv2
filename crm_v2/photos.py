"""Browser photo adapter. File handles and image bytes never enter Python."""
from pathlib import Path
import streamlit as st

ASSETS = Path(__file__).parent / "photo_assets"
_VIEWER = st.components.v2.component(
    "dtk_crm_v2_photos",
    html='<section id="photos"></section>\n',
    js=(ASSETS / "viewer.js").read_text(encoding="utf-8"),
    css=(ASSETS / "viewer.css").read_text(encoding="utf-8"),
)


def browser_photos_enabled(is_cloud):
    return is_cloud or st.session_state.get("v2_photo_mode") == "Ảnh trên thiết bị (trình duyệt)"


def request_photos(row, *, district, street, number, uid, drive):
    import time
    st.session_state["v2_photo_request"] = {
        "nonce": time.time_ns(), "district": str(row.get(district, "")),
        "street": str(row.get(street, "")), "number": str(row.get(number, "")),
        "uid": str(row.get(uid, "")), "drive_url": str(row.get(drive, "")),
    }


def render_photo_viewer():
    # Mounted inside the main UI fragment so grid events update the gallery.
    _VIEWER(key="v2_device_photos", data={"request": st.session_state.get("v2_photo_request")},
            height="content")
