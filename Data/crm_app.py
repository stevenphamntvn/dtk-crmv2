import streamlit as st
from crm_v2 import VERSION
from crm_v2.filter_ui import render_cloud_features
from crm_v2.photos import browser_photos_enabled, request_photos, render_photo_viewer
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
from pathlib import Path
import csv
import json
import re
import subprocess
import tempfile
import platform
import hashlib
from customer_data import append_customer, next_customer_id, read_customers
from sync_report import build_sync_report, style_sync_report

from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from st_aggrid.shared import GridUpdateMode, DataReturnMode

import unicodedata

# ==========================================
# 0. CẤU HÌNH TRANG STREAMLIT & GIAO DIỆN CHUẨN (BẮT BUỘC ĐẦU TIÊN)
# ==========================================
st.set_page_config(
    page_title="CRM V2",
    page_icon=str(Path(__file__).resolve().parents[1] / "assets" / "icons" / "crm.png"),
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# Thiết lập theme màu tối đồng nhất cho cả Local và Cloud (Tối ưu Full-Width tràn viền cho Tablet)
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background-color: #0f0f0f;
        color: #e0e0e0;
    }
    
    /* Container backgrounds */
    .main {
        background-color: #0f0f0f;
    }
    
    /* Tối ưu tràn viền Full-Width 100% cho màn hình Tablet & Cloud */
    .block-container, [data-testid="stAppViewBlockContainer"] {
        background-color: #0f0f0f;
        max-width: 100% !important;
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #1a1a1a;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    
    /* Text elements */
    p, span, div, label {
        color: #e0e0e0 !important;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #2d2d2d;
        color: #ffffff;
        border: 1px solid #404040;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #3d3d3d;
        border-color: #505050;
    }
    
    /* Input elements */
    .stSelectbox>div>div>select, 
    .stTextInput>div>div>input, 
    .stNumberInput>div>div>input {
        background-color: #1a1a1a;
        color: #ffffff;
        border: 1px solid #404040;
    }
    
    /* Text areas */
    .stTextArea>div>div>textarea {
        background-color: #1a1a1a;
        color: #ffffff;
        border: 1px solid #404040;
    }
    
    /* Checkboxes */
    .stCheckbox>label {
        color: #e0e0e0;
    }
    
    /* Info boxes */
    .stAlert {
        background-color: #1a1a1a;
        border: 1px solid #404040;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: #1a2e1a;
        border: 1px solid #2d4a2d;
    }
    
    /* Warning messages */
    .stWarning {
        background-color: #2e2a1a;
        border: 1px solid #4a4a2d;
    }
    
    /* Error messages */
    .stError {
        background-color: #2e1a1a;
        border: 1px solid #4a2d2d;
    }
    
    /* Dividers */
    hr {
        border-color: #404040;
    }
    
    /* Columns */
    [data-testid="column"] {
        background-color: #0f0f0f;
    }
    
    /* Cards and containers */
    .stContainer {
        background-color: #0f0f0f;
    }
    
    /* Data tables */
    .stDataFrame {
        background-color: #1a1a1a;
        color: #e0e0e0;
    }
    
    /* Metrics */
    .stMetric {
        background-color: #1a1a1a;
        color: #ffffff;
    }
    
    /* Tabs */
    [data-testid="stTabs"] {
        background-color: #0f0f0f;
    }
    
    /* Tab content */
    [data-testid="stTabContent"] {
        background-color: #0f0f0f;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CẤU HÌNH NHẬN DIỆN MÔI TRƯỜNG & HÀM HỖ TRỢ BẢN ĐỊA
# ==========================================
# Nhận diện tự động: Streamlit Cloud (Linux/Container) vs Local PC (Windows)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_JSON = os.path.join(BASE_DIR, "credentials.json")

def detect_is_cloud():
    """Nhận diện tự động môi trường Cloud mà không gây lỗi khi thiếu secrets.toml ở Local"""
    if os.environ.get('STREAMLIT_SERVER', '') != '' or os.environ.get('STREAMLIT_SHARING_MODE', '') != '':
        return True
    if platform.system() != 'Windows':
        return True
    # Kiểm tra an toàn secrets
    try:
        if hasattr(st, 'secrets') and "GOOGLE_CREDENTIALS" in st.secrets and not os.path.exists(CREDS_JSON):
            return True
    except Exception:
        pass
    return False

IS_CLOUD = detect_is_cloud()

# ==========================================
# PWA INTEGRATION (Chỉ kích hoạt ở Local nếu cần)
# ==========================================
def inject_pwa_scripts():
    """Inject PWA scripts into Streamlit app"""
    if IS_CLOUD:
        return
        
    pwa_html = """
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#FF4B4B">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <script src="/indexeddb-manager.js"></script>
    <script src="/pwa-integration.js"></script>
    """
    st.markdown(pwa_html, unsafe_allow_html=True)

if not IS_CLOUD:
    pass  # V2 replaces the legacy PWA stub with a browser photo adapter.

if IS_CLOUD:
    ROOT_DIR = ""  # Cloud environment không có truy cập file local Windows
else:
    path_pc = r"D:\GGD\My Drive\Real estate\QH-SH-MAP\SH\SH Total"
    path_laptop = r"G:\My Drive\Real estate\QH-SH-MAP\SH\SH Total"

    if os.path.exists(path_pc):
        ROOT_DIR = path_pc
    elif os.path.exists(path_laptop):
        ROOT_DIR = path_laptop
    else:
        ROOT_DIR = "" # Fallback an toàn nếu không tìm thấy thư mục

def remove_vietnamese_accent(s):
    """Gọt sạch dấu tiếng Việt để đối chiếu với cấu trúc Folder Windows"""
    if not isinstance(s, str): s = str(s)
    if not s: return ""
    s = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', s)
    s = re.sub(r'[ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴ]', 'A', s)
    s = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', s)
    s = re.sub(r'[ÈÉẸẺẼÊỀẾỆỂỄ]', 'E', s)
    s = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', s)
    s = re.sub(r'[ÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠ]', 'O', s)
    s = re.sub(r'[ìíịỉĩ]', 'i', s)
    s = re.sub(r'[ÌÍỊỈĨ]', 'I', s)
    s = re.sub(r'[ùúụủũưừứựửữ]', 'u', s)
    s = re.sub(r'[ÙÚỤỦŨƯỪỨỰỬỮ]', 'U', s)
    s = re.sub(r'[ỳýỵỷỹ]', 'y', s)
    s = re.sub(r'[ỲÝỴỶỸ]', 'Y', s)
    s = re.sub(r'[đ]', 'd', s)
    s = re.sub(r'[Đ]', 'D', s)
    s = unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8')
    return s.strip()

# ==========================================
# 1. CẤU HÌNH HỆ THỐNG & COLUMN MAP
# ==========================================

# Tự động nhận diện thư mục đang chứa file crm_app.py (chính là thư mục 'data')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDS_JSON = os.path.join(BASE_DIR, "credentials.json")

SHEET_ID = "1a0roK3rSRQYlFMYIyC_5iMLNr0t7wUz5IRi0OdckPKA"
GSK_SHEET_NAME = "BT-PN.PK-6.0-10000"
# --- Cấu hình bổ sung ---
LINK_SHEET_NAME = "linkcolfuid"
COL_LINK_URL = "URL_Quy_Hoach" # Tên cột trong sheet link
COL_LINK_GGD = "URL_GGD" # <--- THÊM DÒNG NÀY
CONFIG_GSK_CM = {
    "STT": "stt", "STATUS": "status", "NGAY": "ngay", "PL": "PL", 
    "QUAN": "quan", "SONHA": "sonha", "TENDUONG": "tenduong",
    "PHUONG": "phuong", "NGANG": "ngang", "DAI": "dai",
    "GIA": "gia", "PM2": "p/m2", "DIENTICH": "dientich",
    "KETCAU": "ketcau", "UID": "uid", "MOTACHITIET": "motachitiet",
    "UPDATE": "update",
    "HEM": "hem",
    "CUS": "cus",
    "DINHGIA_Q": "dinhgia"
}
# --- CẤU HÌNH TRẠM OFFLINE CACHE ---
CACHE_DIR = os.path.join(BASE_DIR, "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

FILE_GSK = os.path.join(CACHE_DIR, "gsk_cache.csv")
FILE_KID = os.path.join(CACHE_DIR, "mykid_cache.csv")
FILE_LOG = os.path.join(CACHE_DIR, "kid_log_cache.csv")
FILE_PENDING = os.path.join(CACHE_DIR, "pending_logs.csv")
FILE_PREFS = os.path.join(CACHE_DIR, "filter_prefs.json") # File não bộ CRM
FILE_LAST_KID = os.path.join(CACHE_DIR, "last_kid_cache.txt") # <--- THÊM DÒNG NÀY VÀO ĐÂY
# --- TỪ ĐIỂN ĐỒNG BỘ NGÔN NGỮ (GSK <-> BLK) NGUYÊN KHỐI ---
MAP_QUAN = {
    "Bình Thạnh": "QBT", "Phú Nhuận": "QPN", "Gò Vấp": "QGV",
    "Tân Bình": "QTB", "Tân Phú": "QTP", "Bình Tân": "QBTA",
    "Quận 1": "Q1", "Quận 3": "Q3", "Quận 10": "Q10", "Quận 11": "Q11",
    "Quận 2": "Q2", "Quận 4": "Q4", "Quận 5": "Q5", "Quận 6": "Q6",
    "Quận 7": "Q7", "Quận 8": "Q8", "Quận 9": "Q9", "Quận 12": "Q12"
}

# ==========================================
# CẤU HÌNH ĐỘ RỘNG CỘT GIAO DIỆN (AGGRID WIDTH)
# ==========================================
UI_WIDTH = {
    # --- TAB 1: BẢNG CHỌN NHÀ ---
    "t1_trangthai": 35,
    "t1_pl": 42,
    "t1_quan": 60,
    "t1_phuong": 42,
    "t1_sonha": 90, # Cột số nhà tùy chỉnh theo ý muốn
    "t1_ggd": 25,   # Cột Link ảnh Google Drive (Chỉ để 25px)
    "t1_tenduong": 120,
    "t1_ngang": 40,
    "t1_dai": 40,
    "t1_dientich": 55,
    "t1_gia": 55,
    "t1_dinhgia": 55,
    "t1_ketcau": 50,
    "t1_dacdiem": 250, # Cột đặc điểm tăng thêm 50px (200 -> 250px)
    "t1_update": 90,
    "t1_uid": 50,
    "t1_cus": 120,
    "t1_note": 650, # Cột Ghi chú riêng N(...) nằm ở cuối cùng bảng

    # --- TAB 2: MYKID ---
    "t2_kid": 120,
    "t2_plk": 80,
    "t2_thongtin": 250,
    "t2_ghichu": 300,
    "t2_boloc": 250,
    "t2_ngaytt": 120,

    # --- TAB 3: NHẬT KÝ ZALO ---
    "t3_kid": 120,
    "t3_thongtin": 180,
    "t3_nhagui": 350,
    "t3_qh": 70,
    "t3_anh": 70,
    "t3_ngaygui": 110,
    "t3_ngaylog": 110,
    "t3_trangthai": 110,
    "t3_phanhoi": 200,

    # --- DIALOG CHỌN KHÁCH ---
    "dl_trangthai": 80,
    "dl_kid": 70,
    "dl_khachhang": 360,
    "dl_ngayhen": 130,
    "dl_dagui": 80
}

# Từ điển dịch ngược để UI hiểu (VD: QBT -> Bình Thạnh)
REV_MAP_QUAN = {v: k for k, v in MAP_QUAN.items()}

# ==========================================
# 2. CÁC HÀM XỬ LÝ LÕI (CORE FUNCTIONS)
# ==========================================

def clean_numeric(series):
    """Xử lý triệt để dấu phẩy Việt Nam: 3,7 -> 3.7 (float)"""
    if series is None: return 0.0
    # Chuyển về chuỗi, xóa khoảng trắng
    s = series.astype(str).str.strip()
    # Thay dấu phẩy thành dấu chấm
    s = s.str.replace(',', '.', regex=False)
    # Chuyển về số, giá trị lỗi biến thành 0.0
    return pd.to_numeric(s, errors='coerce').fillna(0.0)

@st.cache_resource
def get_gspread_client():
    """Hàm sống còn: Kết nối Google API (Hỗ trợ linh hoạt Streamlit Cloud Secrets và credentials.json)"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 1. Thử lấy credentials từ Streamlit Secrets (dành cho Streamlit Cloud)
    try:
        if hasattr(st, "secrets") and "GOOGLE_CREDENTIALS" in st.secrets:
            creds_data = st.secrets["GOOGLE_CREDENTIALS"]
            if isinstance(creds_data, str):
                creds_dict = json.loads(creds_data)
            else:
                creds_dict = dict(creds_data)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            return gspread.authorize(creds)
    except Exception:
        pass
            
    # 2. Fallback sang file credentials.json (dành cho Local)
    if os.path.exists(CREDS_JSON):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_JSON, scope)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"Lỗi khởi tạo Google Service Account từ credentials.json: {e}")
            
    raise RuntimeError("Không tìm thấy Google Credentials! Vui lòng cấu hình st.secrets['GOOGLE_CREDENTIALS'] trên Cloud hoặc file Data/credentials.json ở Local.")

def pull_khoi_nha():
    """Tải riêng Khối Nhà (KN) và Bảng Link về Cache - Tích hợp chốt chặn Header"""
    gc = get_gspread_client()
    with st.spinner("⬇️ Đang tải Khối Nhà & Link từ Google Sheets..."):
        try:
            sh = gc.open_by_key(SHEET_ID)
            ws_houses = sh.worksheet(GSK_SHEET_NAME)
            
            data_h = ws_houses.get_all_values()
            df_h = pd.DataFrame(data_h[1:], columns=data_h[0]) if data_h else pd.DataFrame()
            
            # --- 🛡️ CHỐT CHẶN BẢO VỆ DỮ LIỆU LOCAL (FAIL-FAST) ---
            if not df_h.empty:
                df_h.columns = df_h.columns.astype(str).str.strip() # Gọt khoảng trắng header
                
                # Định nghĩa các cột sống còn tuyệt đối không được phép mất
                critical_cols = [
                    CONFIG_GSK_CM["UID"], 
                    CONFIG_GSK_CM["SONHA"], 
                    CONFIG_GSK_CM["QUAN"]
                ]
                
                missing_cols = [col for col in critical_cols if col not in df_h.columns]
                
                if missing_cols:
                    st.error(f"🚨 LỖI NGHIÊM TRỌNG: Khối Nhà trên Google Sheets đang bị mất cột Header: **{', '.join(missing_cols)}**.")
                    st.warning("🛑 Hệ thống đã ngắt lệnh đồng bộ để bảo vệ dữ liệu hiện tại. Vui lòng khôi phục lại Header trên Cloud và thử lại!")
                    return pd.DataFrame()
            # ---------------------------------------------------------
            
            try:
                ws_links = sh.worksheet(LINK_SHEET_NAME)
                data_l = ws_links.get_all_values()
                df_l = pd.DataFrame(data_l[1:], columns=data_l[0]) if data_l else pd.DataFrame()
            except: df_l = pd.DataFrame()
            
            if not df_h.empty and not df_l.empty:
                df_h[CONFIG_GSK_CM["UID"]] = df_h[CONFIG_GSK_CM["UID"]].astype(str).str.strip()
                df_l["UID"] = df_l["UID"].astype(str).str.strip()
                
                cols_to_merge = ["UID", COL_LINK_URL]
                if COL_LINK_GGD in df_l.columns:
                    cols_to_merge.append(COL_LINK_GGD)
                    
                df_h = pd.merge(df_h, df_l[cols_to_merge], 
                                left_on=CONFIG_GSK_CM["UID"], right_on="UID", 
                                how="left").drop(columns=["UID_y"], errors='ignore').rename(columns={"UID_x": CONFIG_GSK_CM["UID"]})

            if CONFIG_GSK_CM["SONHA"] in df_h.columns:
                # Xử lý nhanh cờ Mặt tiền (isMAT) bằng Vectorized
                df_h['isMAT'] = ~df_h[CONFIG_GSK_CM["SONHA"]].astype(str).str.contains(r'\.', na=False)

            # Khóa dữ liệu chuẩn chuỗi trước khi lưu chống mất số 0
            df_h.astype(str).to_csv(FILE_GSK, index=False, encoding='utf-8-sig')
            st.toast("✅ Kho nhà và Link đã được đồng bộ thành công!")
            return df_h
        except Exception as e:
            st.error(f"Lỗi tải Khối Nhà: {e}")
            return pd.DataFrame()

def pull_khoi_khach_va_log(pull_kids=True, pull_logs=True):
    """Tải Khối Khách (MyKID) và Nhật Ký (KID_log) từ Google Sheets về Cache"""
    gc = get_gspread_client()
    with st.spinner("⬇️ Đang tải Khối Khách & Nhật Ký từ Google Sheets..."):
        try:
            sh = gc.open_by_key(SHEET_ID)
            
            # 1. Tải MyKID
            data_k = sh.worksheet("MyKID").get_all_values() if pull_kids else []
            df_k = pd.DataFrame(data_k[1:], columns=data_k[0]) if data_k else pd.DataFrame()
            if not df_k.empty:
                df_k.columns = df_k.columns.astype(str).str.strip()
                df_k.astype(str).to_csv(FILE_KID, index=False, encoding='utf-8-sig')
                
            # 2. Tải KID_log
            data_l = sh.worksheet("KID_log").get_all_values() if pull_logs else []
            df_l = pd.DataFrame(data_l[1:], columns=data_l[0]) if data_l else pd.DataFrame()
            if not df_l.empty:
                df_l.columns = df_l.columns.astype(str).str.strip()
                df_l.astype(str).to_csv(FILE_LOG, index=False, encoding='utf-8-sig')
                
            st.toast("✅ Khối Khách và Nhật Ký đã được đồng bộ thành công!")
            return df_k, df_l
        except Exception as e:
            st.error(f"Lỗi tải Khối Khách & Nhật Ký: {e}")
            return pd.DataFrame(), pd.DataFrame()

def pull_all_data():
    """Tải toàn bộ dữ liệu (Khối Nhà, Khối Khách, Nhật Ký) từ Google Sheets"""
    pull_khoi_nha()
    pull_khoi_khach_va_log()

def compare_dataframes(df_local, df_cloud, primary_keys):
    """Thuật toán so sánh Dataframe chuẩn xác bằng Pandas (Lọc Khóa + Deep Compare)"""
    if df_local.empty and df_cloud.empty: return 0, 0, 0
    if df_local.empty: return 0, len(df_cloud), 0
    if df_cloud.empty: return len(df_local), 0, 0

    df_l = df_local.copy()
    df_c = df_cloud.copy()
    
    # 1. Gọt sạch khoảng trắng tên cột
    df_l.columns = df_l.columns.str.strip()
    df_c.columns = df_c.columns.str.strip()
    
    # Gom danh sách các cột chung để chuẩn bị so sánh sâu
    common_cols = list(set(df_l.columns) & set(df_c.columns))
    
    # Đảm bảo các cột khóa chính luôn có mặt
    for col in primary_keys:
        if col not in common_cols:
            if col not in df_l.columns: df_l[col] = ""
            if col not in df_c.columns: df_c[col] = ""
            common_cols.append(col)
            
    # 2. Chuẩn hóa triệt để kiểu chuỗi và khoảng trắng cho toàn bộ lưới dữ liệu
    for col in common_cols:
        df_l[col] = df_l[col].fillna("").astype(str).str.strip()
        df_c[col] = df_c[col].fillna("").astype(str).str.strip()

    # 3. Chạy giao cắt tập hợp để đếm Thêm mới / Bị xóa
    merged_keys = pd.merge(df_l[primary_keys], df_c[primary_keys], on=primary_keys, how='outer', indicator=True)
    
    only_local = len(merged_keys[merged_keys['_merge'] == 'left_only'])
    only_cloud = len(merged_keys[merged_keys['_merge'] == 'right_only'])
    
    # 4. Deep Compare (So sánh sâu nội dung) cho nhóm Both
    both_keys = merged_keys[merged_keys['_merge'] == 'both'][primary_keys]
    actual_updates = 0
    
    if not both_keys.empty:
        # Lọc ra các dòng cùng khóa chính ở cả 2 bảng
        df_l_both = pd.merge(both_keys, df_l[common_cols], on=primary_keys, how='inner')
        df_c_both = pd.merge(both_keys, df_c[common_cols], on=primary_keys, how='inner')
        
        # Căn chỉnh thứ tự dòng để so sánh Vectorized trực tiếp
        df_l_both = df_l_both.sort_values(by=primary_keys).reset_index(drop=True)
        df_c_both = df_c_both.sort_values(by=primary_keys).reset_index(drop=True)
        
        # Chỉ so sánh nội dung (loại trừ cột khóa)
        compare_cols = [c for c in common_cols if c not in primary_keys]
        
        if compare_cols:
            # Đảm bảo cả hai DataFrames có cùng cấu trúc cột trước khi so sánh
            # Chỉ lấy các cột thực sự có trong cả hai DataFrames
            final_compare_cols = [c for c in compare_cols if c in df_l_both.columns and c in df_c_both.columns]
            
            if final_compare_cols:
                # So sánh từng cột riêng biệt để tránh lỗi cấu trúc khác nhau
                diff_rows = []
                for idx in range(len(df_l_both)):
                    row_diff = False
                    for col in final_compare_cols:
                        try:
                            if df_l_both.iloc[idx][col] != df_c_both.iloc[idx][col]:
                                row_diff = True
                                break
                        except:
                            row_diff = True
                            break
                    diff_rows.append(row_diff)
                
                actual_updates = sum(diff_rows)
            
    return only_local, only_cloud, actual_updates

def render_sync_report(report):
    if report['skipped_empty_pull']:
        st.info('Online đang trống. Theo cơ chế tải về hiện tại, bảng Local này được giữ nguyên.')
        return
    st.write(f"Thay đổi nội dung dự kiến trên **{report['target']}**: "
             f"thêm **{report['added']}**, bỏ **{report['removed']}**, sửa **{report['updated']}** bản ghi.")
    if report['rows'].empty:
        st.caption('Không có thay đổi nội dung cần xem. Bỏ qua các mốc thời gian tự cập nhật.')
        return
    st.caption('Mỗi dòng là một trường dữ liệu. Dấu + màu xanh: thêm; dấu − màu đỏ: bỏ. '
               'Sửa gồm bỏ giá trị cũ và thêm giá trị mới. Chỉ hiện trường có thay đổi nội dung; '
               'ẩn ngày tương tác và mốc thời gian tự cập nhật, vẫn hiện thay đổi ngày hẹn / gửi nhà.')
    st.dataframe(style_sync_report(report), hide_index=True,
                 column_config={'Local': st.column_config.TextColumn('Local', width='large'),
                                'Online': st.column_config.TextColumn('Online', width='large')})


@st.dialog("⚠️ KIỂM DUYỆT ĐỒNG BỘ KHỐI KHÁCH (KK)", width="large")
def dialog_kiem_duyet_khoi_khach(df_kid_cloud, df_kid_local, df_log_cloud, df_log_local, direction):
    """Giao diện Popup so sánh và báo cáo thay đổi dựa trên thuật toán Khóa Chính"""
    is_push = (direction == "push")
    
    st.info(f"💡 Chế độ: **{'📤 UP LÊN CLOUD (Nguồn Local sẽ đè lên Cloud)' if is_push else '📥 TẢI VỀ MÁY (Nguồn Cloud sẽ đè xuống Local)'}**")
    
    try:
        customer_names = {}
        for frame in [df_kid_local, df_kid_cloud]:
            if 'KID' in frame.columns and 'thongtin_KID' in frame.columns:
                customer_names.update(dict(zip(frame['KID'].fillna('').astype(str).str.strip(),
                                               frame['thongtin_KID'].fillna('').astype(str))))
        kid_report = build_sync_report(df_kid_local, df_kid_cloud, ['KID'], direction)
        log_report = build_sync_report(df_log_local, df_log_cloud, ['KID', 'UID'], direction, customer_names)
    except ValueError as exc:
        st.error(f'Chưa thể lập báo cáo đồng bộ: {exc}')
        return

    st.subheader('👥 Báo cáo Khách Hàng (MyKID)')
    render_sync_report(kid_report)
    st.divider()
    st.subheader('📝 Báo cáo Nhật Ký Zalo (KID_log)')
    render_sync_report(log_report)
    st.divider()

    # --- CƠ CHẾ CHỐT CHẶN BẢO VỆ DỮ LIỆU ---
    if is_push:
        if st.button("🚀 XÁC NHẬN OK - ĐẨY LÊN CLOUD", type="primary", width="stretch"):
            with st.spinner("Đang thực thi lệnh Batch Update tốc độ cao lên Google Sheets..."):
                try:
                    gc = get_gspread_client()
                    sh = gc.open_by_key(SHEET_ID)
                    
                    ws_kids = sh.worksheet("MyKID")
                    ws_kids.clear()
                    if not df_kid_local.empty:
                        ws_kids.update([df_kid_local.columns.tolist()] + df_kid_local.values.tolist())
                    
                    ws_logs = sh.worksheet("KID_log")
                    ws_logs.clear()
                    if not df_log_local.empty:
                        ws_logs.update([df_log_local.columns.tolist()] + df_log_local.values.tolist())
                    
                    st.session_state['sync_success'] = "push"
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi ghi đè Cloud: {e}")
    else:
        # Bật cảnh báo nút Đỏ nếu Tải về mà có nguy cơ mất dữ liệu Local
        nguy_co_mat_data = (kid_report['removed'] > 0 or log_report['removed'] > 0)
        
        if st.button("📥 XÁC NHẬN OK - TẢI VỀ MÁY", type="secondary" if nguy_co_mat_data else "primary", width="stretch"):
            with st.spinner("Đang ghi đè dữ liệu xuống ổ cứng..."):
                try:
                    if not df_kid_cloud.empty:
                        df_kid_cloud.astype(str).to_csv(FILE_KID, index=False, encoding='utf-8-sig')
                    if not df_log_cloud.empty:
                        df_log_cloud.astype(str).to_csv(FILE_LOG, index=False, encoding='utf-8-sig')
                    
                    st.session_state['sync_success'] = "pull"
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi lưu Local: {e}")

def trigger_sync_khoi_khach(direction="push"):
    """Hàm Pre-fetch âm thầm kéo Cloud về đối chiếu In-Memory với Local"""
    if 'sync_success' in st.session_state and st.session_state['sync_success']:
        if st.session_state['sync_success'] == "push":
            st.toast("✅ Đã đồng bộ Khối Khách lên Cloud thành công!")
        else:
            st.toast("✅ Đã tải Khối Khách về máy thành công!")
            st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
        
        st.session_state['sync_success'] = False
        return

    success_fetch = False
    
    with st.spinner("🔄 Đang tải nháp và phân tích dữ liệu đối chiếu..."):
        try:
            # 1. Đọc dữ liệu Local (OD)
            df_kid_local = pd.read_csv(FILE_KID, dtype=str).fillna("") if os.path.exists(FILE_KID) else pd.DataFrame()
            df_log_local = pd.read_csv(FILE_LOG, dtype=str).fillna("") if os.path.exists(FILE_LOG) else pd.DataFrame()
            
            # Cập nhật lại ngày tương tác tại Local bằng thuật toán trước khi phân tích (Chỉ làm In-memory)
            if direction == "push" and not df_log_local.empty and not df_kid_local.empty:
                df_l_valid = df_log_local[df_log_local['timestamp'].astype(str).str.strip() != ""].copy()
                if not df_l_valid.empty:
                    df_l_valid['KID_clean'] = df_l_valid['KID'].astype(str).str.strip()
                    df_l_valid['dt'] = pd.to_datetime(df_l_valid['timestamp'], errors='coerce')
                    
                    # Đồng bộ định dạng %Y-%m-%d để khớp tuyệt đối với Tab 2
                    last_inter = df_l_valid.groupby('KID_clean')['dt'].max().dt.strftime('%Y-%m-%d').to_dict()
                    df_kid_local['ngay_tuong_tac'] = df_kid_local['KID'].map(lambda k: last_inter.get(str(k).strip(), ""))
                    
                    # [BẢN VÁ]: Đã XÓA dòng to_csv ở đây để chống lỗi Rerun sập Dialog!

            # 2. Tải nháp dữ liệu Cloud
            gc = get_gspread_client()
            sh = gc.open_by_key(SHEET_ID)
            
            ws_kids = sh.worksheet("MyKID")
            data_k = ws_kids.get_all_values()
            df_kid_cloud = pd.DataFrame(data_k[1:], columns=data_k[0]) if data_k else pd.DataFrame()
            
            ws_logs = sh.worksheet("KID_log")
            data_l = ws_logs.get_all_values()
            df_log_cloud = pd.DataFrame(data_l[1:], columns=data_l[0]) if data_l else pd.DataFrame()
            
            success_fetch = True
            
        except Exception as e:
            st.error(f"Lỗi phân tích đồng bộ: {e}")

    # 3. Kích hoạt Trạm kiểm duyệt (ĐÃ KÉO RA NGOÀI SPINNER ĐỂ BẢO VỆ DIALOG)
    if success_fetch:
        dialog_kiem_duyet_khoi_khach(df_kid_cloud, df_kid_local, df_log_cloud, df_log_local, direction)

def render_tab2_mykid(df_kids, df_log):
    """Bảng Tab 2: Quản lý khách hàng chuyên sâu - Tích hợp Max Date (Manual + Auto) và Fix Loop Tuyệt Đối"""
    if df_kids.empty:
        st.info("Chưa có dữ liệu khách hàng từ MyKID.")
        return

    # 1. TỰ ĐỘNG TÍNH NGÀY TƯƠNG TÁC CUỐI TỪ TAB 3 (Auto)
    last_interaction = {}
    if not df_log.empty:
        try:
            df_log_valid = df_log[df_log['timestamp'].astype(str).str.strip() != ""].copy()
            if not df_log_valid.empty:
                df_log_valid['KID_clean'] = df_log_valid['KID'].astype(str).str.strip()
                df_log_valid['dt'] = pd.to_datetime(df_log_valid['timestamp'], errors='coerce')
                last_interaction = df_log_valid.groupby('KID_clean')['dt'].max()
        except Exception: pass

    # 2. THUẬT TOÁN ĐỒNG BỘ MAX DATE (Lấy ngày lớn nhất giữa Manual và Auto)
    if 'ngay_tuong_tac' not in df_kids.columns:
        df_kids['ngay_tuong_tac'] = ""
        
    def get_max_date(kid, current_date_str):
        log_dt = last_interaction.get(str(kid).strip(), pd.NaT)
        curr_dt = pd.to_datetime(current_date_str, errors='coerce')
        
        if pd.isna(log_dt) and pd.isna(curr_dt): return ""
        if pd.isna(log_dt): return curr_dt.strftime("%Y-%m-%d")
        if pd.isna(curr_dt): return log_dt.strftime("%Y-%m-%d")
        return max(log_dt, curr_dt).strftime("%Y-%m-%d")

    df_kids['ngay_tuong_tac_new'] = df_kids.apply(lambda row: get_max_date(row['KID'], row['ngay_tuong_tac']), axis=1)
    
    mask_diff = df_kids['ngay_tuong_tac'].fillna("").astype(str).str.strip() != df_kids['ngay_tuong_tac_new'].fillna("").astype(str).str.strip()
    if mask_diff.any():
        df_kids['ngay_tuong_tac'] = df_kids['ngay_tuong_tac_new']
        df_kids.to_csv(FILE_KID, index=False, encoding='utf-8-sig')
    
    df_kids = df_kids.drop(columns=['ngay_tuong_tac_new'])

    # 3. CHUẨN HÓA CỘT RENDER UI
    df_display = df_kids.copy()
    for col in ['KID', 'PLK', 'thongtin_KID', 'ghi_chu', 'bo_loc_KID', 'ngay_tuong_tac']:
        if col not in df_display.columns:
            df_display[col] = ""
        df_display[col] = df_display[col].fillna("").astype(str).str.strip().replace(r'(?i)^(nan|none|null|<na>)$', '', regex=True)

    df_display['PLK'] = df_display['PLK'].str.upper()

    # 4. MÃ JAVASCRIPT GIAO DIỆN & DATE PICKER
    plk_style_js = JsCode("""
    function(params) {
        if (params.value === 'A') { return {'backgroundColor': '#28a745', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}; } 
        if (params.value === 'B') { return {'backgroundColor': '#0d6efd', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}; } 
        if (params.value === 'C') { return {'backgroundColor': '#ffc107', 'color': 'black', 'fontWeight': 'bold', 'textAlign': 'center'}; } 
        if (params.value === 'D') { return {'backgroundColor': '#dc3545', 'color': 'white', 'fontWeight': 'bold', 'textAlign': 'center'}; } 
        return {'textAlign': 'center'};
    }
    """)

    row_style_js = JsCode("""
    function(params) {
        if (params.data && params.data.PLK === 'D') {
            return { 'backgroundColor': '#f8f9fa', 'color': '#adb5bd', 'fontStyle': 'italic' };
        }
        return null;
    }
    """)
    
    date_editor_js = JsCode("""
    class DatePickerEditor {
        init(params) {
            this.eInput = document.createElement('input');
            this.eInput.type = 'date';
            this.eInput.style.width = '100%';
            this.eInput.style.height = '100%';
            this.eInput.style.border = 'none';
            this.eInput.style.outline = 'none';
            this.eInput.style.backgroundColor = 'transparent';
            this.eInput.style.color = 'inherit';
            this.eInput.value = params.value; 
        }
        getGui() { return this.eInput; }
        afterGuiAttached() { 
            this.eInput.focus(); 
            if(this.eInput.showPicker) { this.eInput.showPicker(); } 
        }
        getValue() { return this.eInput.value; }
        isPopup() { return false; }
    }
    """)

    # 5. CẤU HÌNH AGGRID
    gb = GridOptionsBuilder.from_dataframe(df_display[['KID', 'PLK', 'thongtin_KID', 'ghi_chu', 'bo_loc_KID', 'ngay_tuong_tac']])
    gb.configure_default_column(sortable=True, filter=True, resizable=True, suppressSizeToFit=True)
    
    gb.configure_column('KID', width=UI_WIDTH["t2_kid"], minWidth=UI_WIDTH["t2_kid"], maxWidth=UI_WIDTH["t2_kid"])
    gb.configure_column('PLK', header_name="Loại", width=UI_WIDTH["t2_plk"], minWidth=UI_WIDTH["t2_plk"], maxWidth=UI_WIDTH["t2_plk"], 
                        editable=True, cellEditor='agSelectCellEditor', cellEditorParams={'values': ['A', 'B', 'C', 'D']},
                        cellStyle=plk_style_js)
    gb.configure_column('thongtin_KID', header_name="Khách Hàng & Nhu cầu", width=UI_WIDTH["t2_thongtin"], minWidth=UI_WIDTH["t2_thongtin"])
    gb.configure_column('ghi_chu', header_name="Ghi chú / Lịch sử xem", width=UI_WIDTH["t2_ghichu"], minWidth=UI_WIDTH["t2_ghichu"], editable=True, 
                        cellStyle={'color': '#007bff'})
    gb.configure_column('bo_loc_KID', header_name="Chuỗi Protocol (BLK)", width=UI_WIDTH["t2_boloc"], minWidth=UI_WIDTH["t2_boloc"])
    gb.configure_column('ngay_tuong_tac', header_name="Tương tác cuối", width=UI_WIDTH["t2_ngaytt"], minWidth=UI_WIDTH["t2_ngaytt"], maxWidth=UI_WIDTH["t2_ngaytt"],
                        editable=True, cellEditor=date_editor_js,
                        cellStyle={'color': '#198754', 'fontWeight': 'bold', 'textAlign': 'center', 'cursor': 'pointer'})
    
    gb.configure_grid_options(getRowStyle=row_style_js)
    
    refresh_count = st.session_state.get('refresh_counter', 0)
    
    ag_response = AgGrid(
        df_display, 
        gridOptions=gb.build(), 
        allow_unsafe_jscode=True, 
        update_mode=GridUpdateMode.VALUE_CHANGED, 
        data_return_mode=DataReturnMode.AS_INPUT, 
        fit_columns_on_grid_load=False, 
        theme='streamlit', 
        height=600,
        # [BẢN VÁ]: Thêm refresh_count vào key để bắt lưới Reset khi có tác vụ Gửi khách
        key=f"mykid_dashboard_grid_{len(df_display)}_{refresh_count}" 
    )
    
    # 6. LOGIC LƯU NGẦM TỰ ĐỘNG (BẢO VỆ CHỐNG LOOP TUYỆT ĐỐI BẰNG PANDAS EQUALS)
    if ag_response['data'] is not None:
        updated_df = pd.DataFrame(ag_response['data'])
        if not updated_df.empty:
            
            def strict_clean(val):
                """Lọc sạch mọi ký tự ẩn (\r), dấu xuống dòng và rác hệ thống HTML/JS"""
                if pd.isna(val): return ""
                # Ép kiểu chuỗi, gọt đầu đuôi và chuẩn hóa toàn bộ \r\n thành \n
                s = str(val).strip().replace('\r\n', '\n').replace('\r', '\n')
                return "" if s.lower() in ['nan', 'none', 'null', '<na>', 'nat', ''] else s
                
            cols_check = ['KID', 'PLK', 'ghi_chu', 'ngay_tuong_tac']
            
            # Trích xuất 2 bản sao để kiểm tra
            df_old = df_display[cols_check].copy()
            df_new = updated_df[cols_check].copy()
            
            # Áp dụng bộ lọc siêu sạch
            for c in cols_check:
                df_old[c] = df_old[c].apply(strict_clean)
                df_new[c] = df_new[c].apply(strict_clean)
                
            # Đảm bảo PLK luôn là chữ in hoa để tránh phân biệt HOA/thường
            df_old['PLK'] = df_old['PLK'].str.upper()
            df_new['PLK'] = df_new['PLK'].str.upper()
            
            # Căn chỉnh lại Index để khớp 1-1
            df_old = df_old.reset_index(drop=True)
            df_new = df_new.reset_index(drop=True)
            
            # CHỈ KÍCH HOẠT LƯU KHI VÀ CHỈ KHI 2 BẢNG THỰC SỰ KHÁC NHAU VỀ NỘI DUNG
            if not df_old.equals(df_new):
                
                # Tạo Map Dictionary nhanh từ DataFrame Mới
                real_plk_map = dict(zip(df_new['KID'], df_new['PLK']))
                real_gc_map = dict(zip(df_new['KID'], df_new['ghi_chu']))
                real_ntt_map = dict(zip(df_new['KID'], df_new['ngay_tuong_tac']))
                
                df_kids['KID_clean'] = df_kids['KID'].fillna("").astype(str).str.strip()
                
                # Cập nhật Vectorized siêu tốc
                mask = df_kids['KID_clean'].isin(real_plk_map.keys())
                if mask.any():
                    df_kids.loc[mask, 'PLK'] = df_kids.loc[mask, 'KID_clean'].map(real_plk_map)
                    df_kids.loc[mask, 'ghi_chu'] = df_kids.loc[mask, 'KID_clean'].map(real_gc_map)
                    df_kids.loc[mask, 'ngay_tuong_tac'] = df_kids.loc[mask, 'KID_clean'].map(real_ntt_map)
                
                df_kids = df_kids.drop(columns=['KID_clean'])
                
                df_kids.to_csv(FILE_KID, index=False, encoding='utf-8-sig') 
                st.toast("💾 Đã lưu thay đổi khách hàng! (Bao gồm Ngày tương tác)", icon="✅")
                st.rerun()

def pull_latest_houses_only():
    """Tải riêng nhà và link để cập nhật nhanh F5 - Tích hợp chốt chặn Header"""
    gc = get_gspread_client()
    with st.spinner("⬇️ Đang kéo nhà & link mới nhất..."):
        try:
            sh = gc.open_by_key(SHEET_ID)
            ws_houses = sh.worksheet(GSK_SHEET_NAME)
            
            data_h = ws_houses.get_all_values()
            df_h = pd.DataFrame(data_h[1:], columns=data_h[0]) if data_h else pd.DataFrame()
            
            # --- 🛡️ CHỐT CHẶN BẢO VỆ DỮ LIỆU LOCAL (FAIL-FAST) ---
            if not df_h.empty:
                df_h.columns = df_h.columns.astype(str).str.strip()
                
                critical_cols = [
                    CONFIG_GSK_CM["UID"], 
                    CONFIG_GSK_CM["SONHA"], 
                    CONFIG_GSK_CM["QUAN"]
                ]
                
                missing_cols = [col for col in critical_cols if col not in df_h.columns]
                
                if missing_cols:
                    st.error(f"🚨 LỖI NGHIÊM TRỌNG: Khối Nhà trên Google Sheets đang bị mất cột Header: **{', '.join(missing_cols)}**.")
                    st.warning("🛑 Lệnh làm mới (F5) đã bị hủy để bảo vệ dữ liệu gốc. Vui lòng khôi phục Header!")
                    return
            # ---------------------------------------------------------
            
            try:
                ws_links = sh.worksheet(LINK_SHEET_NAME)
                data_l = ws_links.get_all_values()
                df_l = pd.DataFrame(data_l[1:], columns=data_l[0]) if data_l else pd.DataFrame()
            except: df_l = pd.DataFrame()
            
            if not df_h.empty and not df_l.empty:
                df_h[CONFIG_GSK_CM["UID"]] = df_h[CONFIG_GSK_CM["UID"]].astype(str).str.strip()
                df_l["UID"] = df_l["UID"].astype(str).str.strip()
                
                cols_to_merge = ["UID", COL_LINK_URL]
                if COL_LINK_GGD in df_l.columns:
                    cols_to_merge.append(COL_LINK_GGD)
                    
                df_h = pd.merge(df_h, df_l[cols_to_merge], 
                                left_on=CONFIG_GSK_CM["UID"], right_on="UID", 
                                how="left").drop(columns=["UID_y"], errors='ignore').rename(columns={"UID_x": CONFIG_GSK_CM["UID"]})

            if CONFIG_GSK_CM["SONHA"] in df_h.columns:
                df_h['isMAT'] = ~df_h[CONFIG_GSK_CM["SONHA"]].astype(str).str.contains(r'\.', na=False)

            df_h.astype(str).to_csv(FILE_GSK, index=False, encoding='utf-8-sig')
            st.toast("✅ Kho nhà đã được cập nhật link mới nhất!")
        except Exception as e:
            st.error(f"Lỗi: {e}")

def parse_blk(blk_string):
    from crm_v2.protocol import parse_blk as shared
    return shared(blk_string)

def build_blk(ten_khach, min_gia, max_gia, dict_qp_codes, min_ngang, min_pn, min_tang, min_dt, tags):
    from crm_v2.protocol import build_blk as shared
    return shared(ten_khach, min_gia, max_gia, dict_qp_codes, min_ngang, min_pn, min_tang, min_dt, tags)

def current_customer_needs(df_houses):
    """Snapshot the active filter widgets, including unsaved filter changes."""
    suffix = 'tim' if st.session_state.get('app_mode') == 'TIM_KHACH' else str(st.session_state.get('active_kid', ''))
    state = st.session_state
    districts = list(state.get(f'q_{suffix}', state.get('f_quan', [])))
    wards = [str(p) for p in state.get(f'p_{suffix}', state.get('f_phuong', []))]
    district_wards = {}
    for district in districts:
        code = MAP_QUAN.get(district, f"Q{district.replace('Quận ', '').replace(' ', '').upper()}")
        selected_wards = wards
        if wards and not df_houses.empty:
            district_rows = df_houses[df_houses[CONFIG_GSK_CM['QUAN']].astype(str).str.strip().str.title() == district]
            valid_wards = set(district_rows[CONFIG_GSK_CM['PHUONG']].astype(str).str.replace(r'\.0$', '', regex=True))
            selected_wards = [p for p in wards if p in valid_wards]
        district_wards[code] = selected_wards
    tags = [tag for tag in ['MAT', 'HXT', 'HXH', 'HBG', 'TMA', 'NTC', 'KLP', 'TTT', 'DTT', '2MT', 'CGO']
            if state.get(f'{tag.lower()}_{suffix}', tag in state.get('f_tags', []))]
    return {
        'min_gia': float(state.get(f'mg_{suffix}', state.get('f_min_gia', 0.0))),
        'max_gia': float(state.get(f'xg_{suffix}', state.get('f_max_gia', 100.0))),
        'dict_qp_codes': district_wards,
        'min_ngang': float(state.get(f'mn_{suffix}', state.get('f_ngang', 0.0))),
        'min_pn': int(state.get(f'mpn_{suffix}', state.get('f_min_pn', 0))),
        'min_tang': int(state.get(f'mtg_{suffix}', state.get('f_min_tang', 0))),
        'min_dt': float(state.get(f'mdt_{suffix}', state.get('f_min_dt', 0.0))),
        'tags': tags,
    }


def show_customer_needs(needs):
    areas = []
    for code, wards in needs['dict_qp_codes'].items():
        label = REV_MAP_QUAN.get(code, code)
        areas.append(f"{label} (phường {', '.join(wards)})" if wards else label)
    st.write(f"**Phân khúc:** {needs['min_gia']:g} – {needs['max_gia']:g} tỷ")
    st.write('**Khu vực:** ' + ('; '.join(areas) or 'Tất cả khu vực'))
    st.write(f"**Nhu cầu tối thiểu:** ngang {needs['min_ngang']:g} m; {needs['min_pn']} phòng ngủ; "
             f"{needs['min_tang']} tầng; diện tích {needs['min_dt']:g} m²")
    tag_labels = {'MAT': 'Mặt tiền', 'HXT': 'Hẻm xe tải', 'HXH': 'Hẻm xe hơi', 'HBG': 'Hẻm ba gác',
                  'TMA': 'Thang máy', 'NTC': 'Nội thất cao cấp', 'KLP': 'Không lỗi phong thủy',
                  'TTT': 'Tây Tứ Trạch', 'DTT': 'Đông Tứ Trạch', '2MT': 'Hai mặt tiền', 'CGO': 'Căn góc'}
    st.write('**Đặc điểm:** ' + (', '.join(tag_labels.get(tag, tag) for tag in needs['tags']) or 'Không giới hạn'))


@st.dialog('Thêm khách hàng', width='large')
def dialog_add_customer(needs, classifications):
    def prepare_review():
        name = st.session_state['new_customer_name'].strip()
        classification = st.session_state['new_customer_classification']
        notes = st.session_state['new_customer_notes'].strip()
        st.session_state['new_customer_fields'] = {'name': name, 'classification': classification, 'notes': notes}
        st.session_state.pop('new_customer_error', None)
        if not name:
            st.session_state['new_customer_error'] = 'Vui lòng nhập tên khách hàng.'
            return
        if needs['min_gia'] < 0 or needs['max_gia'] < needs['min_gia']:
            st.session_state['new_customer_error'] = 'Khoảng giá không hợp lệ. Hãy chỉnh lại bộ lọc nhu cầu.'
            return
        try:
            kid = next_customer_id(read_customers(FILE_KID))
        except Exception as exc:
            st.session_state['new_customer_error'] = f'Không đọc được danh sách khách local: {exc}'
            return
        st.session_state['new_customer_review'] = {
            'KID': kid, 'PLK': classification, 'thongtin_KID': name,
            'ghi_chu': notes, 'bo_loc_KID': build_blk(name, **needs), 'ngay_tuong_tac': '',
        }

    draft = st.session_state.get('new_customer_review')
    if draft is None:
        st.caption('Phân khúc và khu vực được lấy từ bộ lọc hiện tại. Đóng cửa sổ để chỉnh lại bộ lọc nếu cần.')
        show_customer_needs(needs)
        fields = st.session_state.get('new_customer_fields', {})
        with st.form('new_customer_form'):
            st.text_input('Tên khách hàng', value=fields.get('name', ''), max_chars=200, key='new_customer_name')
            st.selectbox('Phân loại', classifications, key='new_customer_classification',
                         index=classifications.index(fields.get('classification', 'A')))
            st.text_area('Ghi chú', value=fields.get('notes', ''), key='new_customer_notes')
            st.form_submit_button('Xem báo cáo trước khi lưu', type='primary', on_click=prepare_review)
        if st.session_state.get('new_customer_error'):
            st.error(st.session_state['new_customer_error'])
        return

    st.subheader('Kiểm tra thông tin khách hàng')
    st.write('**Mã khách:**', draft['KID'])
    st.write('**Tên khách:**', draft['thongtin_KID'])
    st.write('**Phân loại:**', draft['PLK'])
    st.write('**Ghi chú:**', draft['ghi_chu'] or 'Chưa có')
    show_customer_needs(needs)
    st.write('**Chuỗi nhu cầu sẽ lưu:**')
    st.code(draft['bo_loc_KID'], language=None)
    st.info('Xác nhận sẽ lưu vào danh sách local. Nhấn 📤 UP KK LÊN khi muốn đưa dữ liệu lên Google Sheets.')
    edit_col, save_col = st.columns(2)
    edit_col.button('Quay lại chỉnh sửa', on_click=lambda: st.session_state.pop('new_customer_review', None))
    if save_col.button('Xác nhận lưu khách hàng', type='primary'):
        try:
            append_customer(FILE_KID, draft)
        except Exception as exc:
            st.error(f'Chưa lưu khách hàng: {exc}')
            return
        st.session_state['customer_created_message'] = f"Đã lưu khách {draft['KID']} — {draft['thongtin_KID']} vào local. Nhấn 📤 UP KK LÊN để đồng bộ lên Google Sheets."
        st.session_state.pop('new_customer_review', None)
        st.session_state.pop('new_customer_fields', None)
        st.session_state['customer_to_select'] = draft['KID']
        st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
        st.rerun(scope='app')


def apply_created_customer_selection(df_kids):
    """Select the saved customer before rendering the parent fragment's widgets."""
    kid = st.session_state.get('customer_to_select')
    if not kid or 'KID' not in df_kids.columns:
        return
    rows = df_kids[df_kids['KID'].astype(str).str.strip() == str(kid)]
    if rows.empty:
        return
    row = rows.iloc[0]
    classification = str(row.get('PLK', '')).strip().upper()
    selected_filter = 'Khách D (Đã bỏ)' if classification == 'D' else f'Khách {classification}'
    for key in list(st.session_state):
        if key.startswith('kid_selectbox_'):
            del st.session_state[key]
    st.session_state['cloud_plk_filter'] = selected_filter
    st.session_state['local_plk_filter'] = selected_filter
    st.session_state[f'kid_selectbox_{selected_filter}'] = f"{kid}({classification}). {str(row.get('thongtin_KID', '')).strip()}"
    st.session_state['app_mode'] = 'GUI_KHACH'
    st.session_state.pop('active_kid', None)
    st.session_state.pop('active_blk', None)
    st.session_state.pop('customer_to_select', None)


def render_add_customer_button(df_houses, df_kids, key):
    if st.button('➕ Thêm khách hàng', key=key):
        for field in ['new_customer_review', 'new_customer_fields', 'new_customer_error',
                      'new_customer_name', 'new_customer_classification', 'new_customer_notes']:
            st.session_state.pop(field, None)
        classifications = ['A', 'B', 'C', 'D']
        existing = df_kids.get('PLK', pd.Series(dtype=str)).fillna('').astype(str).str.strip().str.upper()
        classifications += sorted(set(existing) - set(classifications) - {''})
        dialog_add_customer(current_customer_needs(df_houses), classifications)


def update_filters_from_kid():
    selected_str = st.session_state.selected_kid_ui
    kid_id = selected_str.split(" - ")[0]
    
    # [VÁ LỖI TỪ APP 2]: Sửa lỗi biến kid_info chưa khai báo
    kid_row = df_kids[df_kids['KID'].astype(str) == kid_id].iloc[0]
    blk_str = str(kid_row.get('bo_loc_KID', kid_row.get('thongtin_KID', ""))).strip()
    prefs = parse_blk(blk_str)
    
    st.session_state.f_min_gia = float(prefs['min_gia'])
    st.session_state.f_max_gia = float(prefs['max_gia'])
    st.session_state.f_ngang = float(prefs['min_ngang'])
    st.session_state.f_pn = float(prefs.get('min_pn', 0)) 
    st.session_state.f_tang = float(prefs.get('min_tang', 0)) # Nâng cấp thêm số tầng
    st.session_state.f_quan = list(prefs['quan_phuong'].keys())
    
    for tag in ["MAT", "HXT", "HXH", "HBG", "TMA", "KLP", "NTC"]:
        st.session_state[f"f_tag_{tag}"] = tag in prefs['tags']

def get_kid_prefs(kid_id, default_tc, kid_tags_str):
    """Trích xuất thói quen lọc của khách hàng từ ổ cứng"""
    default_prefs = {
        "min_gia": max(0.0, default_tc - 2.0), "max_gia": default_tc + 1.0,
        "quan": [], "phuong": [], "min_ngang": 3.7, "min_pn": 0, # [MỚI] Thêm min_pn mặc định
        "mat": "MAT" in str(kid_tags_str), "noh": "NOH" in str(kid_tags_str), 
        "tma": "TMA" in str(kid_tags_str), "ntc": False, "no_bad": True
    }
    if os.path.exists(FILE_PREFS):
        try:
            with open(FILE_PREFS, "r", encoding="utf-8") as f:
                all_prefs = json.load(f)
                if kid_id in all_prefs:
                    saved = all_prefs[kid_id]
                    for k, v in saved.items():
                        default_prefs[k] = v
        except: pass
    return default_prefs

def load_local_data():
    """Đọc dữ liệu từ Cache; tự động kéo từ Google Sheets nếu thiếu dữ liệu (Cloud hoặc khởi tạo lần đầu)"""
    try:
        def safe_read(filepath):
            # Kiểm tra file có tồn tại và có dung lượng lớn hơn 0
            if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                try:
                    # Ép toàn bộ dữ liệu là kiểu chuỗi (str) khi đọc
                    df = pd.read_csv(filepath, dtype=str, encoding='utf-8-sig')
                    df.columns = df.columns.str.strip()
                    return df
                except pd.errors.EmptyDataError:
                    # NẾU BỊ LỖI FILE RỖNG ("No columns to parse") -> Trả về bảng trống êm ái
                    return pd.DataFrame()
                except Exception:
                    return pd.DataFrame()
            return pd.DataFrame()

        df_h = safe_read(FILE_GSK)
        df_k = safe_read(FILE_KID)
        df_l = safe_read(FILE_LOG)
        
        # Nếu đang chạy trên Cloud HOẶC thiếu bất kỳ file dữ liệu nào -> Tự động kéo từ Google Sheets
        if df_h.empty:
            df_h = pull_khoi_nha()
            if df_h is None or df_h.empty:
                df_h = safe_read(FILE_GSK)
                
        if df_k.empty or df_l.empty:
            df_k_pulled, df_l_pulled = pull_khoi_khach_va_log(pull_kids=df_k.empty, pull_logs=df_l.empty)
            if df_k.empty and df_k_pulled is not None and not df_k_pulled.empty:
                df_k = df_k_pulled
            else:
                df_k = safe_read(FILE_KID)
                
            if df_l.empty and df_l_pulled is not None and not df_l_pulled.empty:
                df_l = df_l_pulled
            else:
                df_l = safe_read(FILE_LOG)
        
        return df_h, df_k, df_l
    except Exception as e:
        st.error(f"Lỗi đọc / khởi tạo Cache: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def save_kid_prefs(kid_id, prefs_dict):
    """Ghi nhớ thói quen lọc của khách hàng vào ổ cứng"""
    all_prefs = {}
    if os.path.exists(FILE_PREFS):
        try:
            with open(FILE_PREFS, "r", encoding="utf-8") as f:
                all_prefs = json.load(f)
        except: pass
    all_prefs[kid_id] = prefs_dict
    with open(FILE_PREFS, "w", encoding="utf-8") as f:
        json.dump(all_prefs, f, ensure_ascii=False, indent=4)

def update_offline_logs(df_to_save):
    """Ghi đè 6 cột chuẩn xuống cache offline"""
    try:
        df_to_save.to_csv(FILE_LOG, index=False)
        return True
    except:
        return False

def extract_highlight(text):
    """Trích xuất các đặc điểm, từ khóa và tag từ cột mô tả chi tiết"""
    if not text or pd.isna(text): return ""
    t_upper = str(text).upper()
    found = []
    
    # 1. Các tag cố định
    tags = ["TOH", "2MT", "CGO", "P1C", "T1C", "GAC", "GCH", "DAD", "NTC", "SA4", "NOH", "MTR", "QHH", "TTT", "DTT", "CVI", "GCV", "VLA", "VPH", "TMA", "MAT", "HXT", "HXH", "HBG", "KLP"]
    for t in tags:
        if t in t_upper and t not in found:
            found.append(t)
            
    # 2. Các tag động theo mẫu Regex (PNxx, SCNxx, SLGxx, QHxx, DTNxx)
    dynamic_matches = re.findall(r'\b(PN|SCN|SLG|QH|DTN)\s*(\d+)\b', t_upper)
    for prefix, num in dynamic_matches:
        tag = f"{prefix}{num}"
        if tag not in found:
            found.append(tag)
            
    return ", ".join(found)

def extract_note(text):
    """Trích xuất ghi chú riêng N(...) từ cột mô tả chi tiết"""
    if not text or pd.isna(text): return ""
    s = str(text)
    match = re.search(r'(?i)N\(([\s\S]*?)\)', s)
    if match:
        return match.group(1).strip()
    return ""

def filter_houses(df_houses, min_gia, max_gia, selected_quan, selected_phuong, min_ngang, min_pn, min_tang, min_dt, require_tma, require_ntc, no_bad_fengshui, require_ttt, require_dtt, require_2mt, require_cgo, only_mat, req_hxt, req_hxh, req_hbg):
    if df_houses.empty: return pd.DataFrame()
    res = df_houses.copy()
    
    def find_col(key):
        for c in res.columns:
            if str(c).strip().lower() == str(key).strip().lower(): return c
        return key

    c_gia = find_col(CONFIG_GSK_CM["GIA"])
    c_quan = find_col(CONFIG_GSK_CM["QUAN"])
    c_phuong = find_col(CONFIG_GSK_CM["PHUONG"])
    c_ngang = find_col(CONFIG_GSK_CM["NGANG"])
    c_mota = find_col(CONFIG_GSK_CM["MOTACHITIET"])
    c_pl = find_col(CONFIG_GSK_CM["PL"])
    c_sonha = find_col(CONFIG_GSK_CM["SONHA"])
    c_hem = find_col(CONFIG_GSK_CM.get("HEM", "hem"))
    c_dt = find_col(CONFIG_GSK_CM.get("DIENTICH", "dientich"))

    if c_gia in res.columns: res[c_gia] = clean_numeric(res[c_gia])
    if c_ngang in res.columns: res[c_ngang] = clean_numeric(res[c_ngang])
    if c_dt in res.columns: res[c_dt] = clean_numeric(res[c_dt])
    
    c_dai = find_col(CONFIG_GSK_CM["DAI"])
    if c_dai in res.columns: res[c_dai] = clean_numeric(res[c_dai])

    if c_gia in res.columns:
        res = res[(res[c_gia] >= min_gia) & (res[c_gia] <= max_gia)]
    
    if selected_quan and c_quan in res.columns:
        res[c_quan] = res[c_quan].astype(str).str.strip().str.title()
        res = res[res[c_quan].isin([str(q).title() for q in selected_quan])]

    if selected_phuong and c_phuong in res.columns:
        res[c_phuong] = res[c_phuong].astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.title()
        res = res[res[c_phuong].isin([str(p).title() for p in selected_phuong])]
        
    if min_ngang > 0 and c_ngang in res.columns:
        res = res[res[c_ngang] >= float(min_ngang)]
        
    if min_dt > 0 and c_dt in res.columns:
        res = res[res[c_dt] >= float(min_dt)]
        
    if c_mota in res.columns:
        mota_str = res[c_mota].astype(str).str.upper()
        mask = pd.Series(True, index=res.index) 
        
        if min_pn > 0:
            pn_series = mota_str.str.extract(r'PN(\d+)')[0].fillna(0).astype(int)
            mask &= (pn_series >= min_pn)
            
        # [SỬA LẠI]: Pandas Vectorized cho chuẩn C4/Đất/Số
        c_ketcau = find_col(CONFIG_GSK_CM.get("KETCAU", "ketcau"))
        if min_tang > 0 and c_ketcau in res.columns:
            kc_series = res[c_ketcau].astype(str).str.strip().str.upper()
            kc_series = kc_series.replace({'C4': '1', 'ĐẤT': '0', 'DAT': '0'})
            tang_series = pd.to_numeric(kc_series, errors='coerce').fillna(0)
            mask &= (tang_series >= min_tang)

        if require_tma: mask &= mota_str.str.contains("TMA", na=False)
        if require_ntc: mask &= mota_str.str.contains("NTC", na=False)
        if require_ttt: mask &= mota_str.str.contains("TTT", na=False)
        if require_dtt: mask &= mota_str.str.contains("DTT", na=False)
        if require_2mt: mask &= mota_str.str.contains("2MT", na=False)
        if require_cgo: mask &= mota_str.str.contains("CGO", na=False)
        
        if no_bad_fengshui:
            bad_pattern = "TOH|DAD|QHH|GCH|GAC"
            mask &= ~mota_str.str.contains(bad_pattern, na=False)

        res = res[mask]

    if only_mat or req_hxt or req_hxh or req_hbg:
        if c_sonha in res.columns:
            is_mat_mask = ~res[c_sonha].astype(str).str.contains(r'\.', na=False)
            is_alley_mask = ~is_mat_mask
            
            final_pos_mask = pd.Series(False, index=res.index)
            
            if only_mat:
                final_pos_mask |= is_mat_mask
                
            if c_hem in res.columns:
                hem_val = clean_numeric(res[c_hem])
                
                if req_hxt: final_pos_mask |= (is_alley_mask & (hem_val == 1.0))
                if req_hxh: final_pos_mask |= (is_alley_mask & hem_val.isin([2.0, 0.0]))
                if req_hbg: final_pos_mask |= (is_alley_mask & (hem_val == 3.0))
            
            res = res[final_pos_mask]

    c_update = find_col(CONFIG_GSK_CM.get("UPDATE", "update"))
    if c_pl in res.columns:
        res['pl_u'] = res[c_pl].astype(str).str.strip().str.upper()
        res = res[res['pl_u'].isin(['TAR', 'HID', 'A'])]
        res['rank'] = res['pl_u'].map({'TAR': 1, 'A': 2, 'HID': 3})
        
        if c_update in res.columns:
            # Chỉnh lại tham số cho pd.to_datetime
            res['update_dt'] = pd.to_datetime(res[c_update], format='%d/%m/%Y', errors='coerce')
            res = res.sort_values(by=['rank', 'update_dt'], ascending=[True, False])
        else:
            res = res.sort_values(by='rank')

    if not res.empty and c_mota in res.columns:
        res['dacdiem'] = res[c_mota].apply(extract_highlight)
        res['note_rieng'] = res[c_mota].apply(extract_note)
    
    return res

def check_house_match_blk(row_nha, blk_string):
    """Khớp ngược 1 căn nhà với chuỗi Protocol BLK của khách"""
    prefs = parse_blk(blk_string)
    if not prefs or prefs['max_gia'] == 0: return False

    try:
        gia_raw = row_nha.get(CONFIG_GSK_CM["GIA"], 0)
        gia_nha = float(str(gia_raw).replace(',', '.')) if gia_raw else 0.0
        if not (prefs['min_gia'] <= gia_nha <= prefs['max_gia']): return False

        quan_nha = str(row_nha.get(CONFIG_GSK_CM["QUAN"], "")).strip().title()
        phuong_nha = str(row_nha.get(CONFIG_GSK_CM["PHUONG"], "")).strip().title().replace('.0', '')
        
        q_codes = prefs['quan_phuong'].keys()
        quan_hop_le = [REV_MAP_QUAN.get(q, q) for q in q_codes]
        if quan_hop_le and quan_nha not in quan_hop_le: return False
        
        for q_code, p_list in prefs['quan_phuong'].items():
            if REV_MAP_QUAN.get(q_code) == quan_nha and p_list:
                if phuong_nha not in p_list: return False

        ngang_raw = row_nha.get(CONFIG_GSK_CM["NGANG"], 0)
        ngang_nha = float(str(ngang_raw).replace(',', '.')) if ngang_raw else 0.0
        if prefs['min_ngang'] > 0 and ngang_nha < prefs['min_ngang']: return False

        if prefs.get('min_dt', 0) > 0:
            dt_raw = row_nha.get(CONFIG_GSK_CM.get("DIENTICH", "dientich"), 0)
            dt_nha = float(str(dt_raw).replace(',', '.')) if dt_raw else 0.0
            if dt_nha < prefs['min_dt']: return False

        mota = str(row_nha.get(CONFIG_GSK_CM.get("MOTACHITIET", "motachitiet"), "")).upper()
        if prefs.get('min_pn', 0) > 0:
            match_pn = re.search(r'PN(\d+)', mota)
            pn_nha = int(match_pn.group(1)) if match_pn else 0
            if pn_nha < prefs['min_pn']: return False
            
        # [SỬA LẠI]: Quy tắc đọc chuẩn Số/C4/Đất
        if prefs.get('min_tang', 0) > 0:
            kc = str(row_nha.get(CONFIG_GSK_CM.get("KETCAU", "ketcau"), "")).strip().upper()
            if kc in ["ĐẤT", "DAT"]:
                tang_nha = 0
            elif kc == "C4":
                tang_nha = 1
            else:
                try: tang_nha = float(kc)
                except: tang_nha = 0
                
            if tang_nha < prefs['min_tang']: return False

        tags = prefs['tags']
        sonha = str(row_nha.get(CONFIG_GSK_CM["SONHA"], ""))
        is_mat = "." not in sonha
        hem_raw = row_nha.get(CONFIG_GSK_CM.get("HEM", "hem"), 0)
        hem_val = float(str(hem_raw).replace(',', '.')) if hem_raw else 0.0
        
        req_pos = [t for t in ["MAT", "HXT", "HXH", "HBG"] if t in tags]
        if req_pos:
            pos_match = False
            if "MAT" in req_pos and is_mat: pos_match = True
            if "HXT" in req_pos and not is_mat and hem_val == 1.0: pos_match = True
            if "HXH" in req_pos and not is_mat and hem_val in [2.0, 0.0]: pos_match = True
            if "HBG" in req_pos and not is_mat and hem_val == 3.0: pos_match = True
            if not pos_match: return False

        if "TMA" in tags and "TMA" not in mota: return False
        if "NTC" in tags and "NTC" not in mota: return False
        if "TTT" in tags and "TTT" not in mota: return False
        if "DTT" in tags and "DTT" not in mota: return False
        if "2MT" in tags and "2MT" not in mota: return False
        if "CGO" in tags and "CGO" not in mota: return False
        
        if "KLP" in tags:
            for bad_tag in ["TOH", "DAD", "QHH", "GCH", "GAC"]:
                if bad_tag in mota: return False

        return True
    except Exception:
        return False
@st.dialog("🎯 Chọn Khách Hàng Phù Hợp", width="large")
def dialog_chon_khach_cho_nha(selected_houses_df, df_mykid, df_tab3_logs):
    """Giao diện popup AI tự động tìm khách - Tích hợp UI_WIDTH"""
    st.markdown("### Danh sách khách hàng khớp nhu cầu với rổ hàng")
    st.info("💡 Click vào ô ❌/🟠 để chọn khách (⚪). Nháy đúp vào cột 'Ngày hẹn' để mở lịch chọn ngày.")
    
    match_data = []
    hom_nay_str = pd.Timestamp.now().strftime("%Y-%m-%d") 
    
    for _, khach in df_mykid.iterrows():
        kid = str(khach.get('KID', '')).strip()
        plk = str(khach.get('PLK', '')).strip().upper()
        
        if plk == 'D': continue 
            
        blk = str(khach.get('bo_loc_KID', khach.get('thongtin_KID', '')))
        ttk = str(khach.get('thongtin_KID', '')).strip()
        
        plk_str = f"({plk})" if plk else ""
        khach_blk_display = f"{kid}{plk_str}. {ttk}"
        
        matched_uids = []
        for _, row_nha in selected_houses_df.iterrows():
            if check_house_match_blk(row_nha, blk):
                matched_uids.append(str(row_nha.get(CONFIG_GSK_CM["UID"], "")))
        
        if not matched_uids: continue 
            
        sent_to_this_kid = []
        if not df_tab3_logs.empty:
            sent_to_this_kid = df_tab3_logs[df_tab3_logs.iloc[:, 0].astype(str).str.strip() == kid]['UID'].astype(str).tolist()
            
        intersect_uids = list(set(matched_uids) & set(sent_to_this_kid))
        
        if len(intersect_uids) == 0: base_icon = "❌"
        elif len(intersect_uids) < len(matched_uids): base_icon = "🟠"
        else: base_icon = "✅" 
            
        match_data.append({
            "Trạng thái": base_icon, 
            "KID": kid, 
            "Khách Hàng": khach_blk_display,
            "Ngày hẹn": hom_nay_str,
            "Đã gửi": f"{len(intersect_uids)}/{len(matched_uids)}",
            "base_icon": base_icon, 
            "matched_str": ",".join(matched_uids), 
            "sent_str": ",".join(sent_to_this_kid)
        })
        
    if not match_data:
        st.warning("Rất tiếc, rổ hàng này không khớp với bất kỳ khách nào trong MyKID.")
        return

    df_match = pd.DataFrame(match_data)
    
    js_toggle = JsCode("""
    function(params) {
        setTimeout(function () {
            if (params.event && params.event.detail === 1) { 
                const value = params.value; 
                const field = params.colDef.field;
                if (value === '✅') return; 
                
                let newValue = value;
                if (value === '⚪') { newValue = params.node.data['base_icon']; } 
                else { newValue = '⚪'; }
                params.node.setDataValue(field, newValue);
            }
        }, 80);
    }
    """)

    date_editor_js = JsCode("""
    class DatePickerEditor {
        init(params) {
            this.eInput = document.createElement('input');
            this.eInput.type = 'date';
            this.eInput.style.width = '100%';
            this.eInput.style.height = '100%';
            this.eInput.style.border = 'none';
            this.eInput.style.outline = 'none';
            this.eInput.value = params.value; 
        }
        getGui() { return this.eInput; }
        afterGuiAttached() { 
            this.eInput.focus(); 
            if(this.eInput.showPicker) { this.eInput.showPicker(); } 
        }
        getValue() { return this.eInput.value; }
        isPopup() { return false; }
    }
    """)

    gb = GridOptionsBuilder.from_dataframe(df_match)
    gb.configure_default_column(sortable=True, filter=True, resizable=True, suppressSizeToFit=True)
    
    gb.configure_column('Trạng thái', onCellClicked=js_toggle, editable=False, width=UI_WIDTH["dl_trangthai"], minWidth=UI_WIDTH["dl_trangthai"], maxWidth=UI_WIDTH["dl_trangthai"], 
                        cellStyle={'cursor': 'pointer', 'fontSize': '16px', 'textAlign': 'center'})
    gb.configure_column('KID', width=UI_WIDTH["dl_kid"], minWidth=UI_WIDTH["dl_kid"], maxWidth=UI_WIDTH["dl_kid"])
    gb.configure_column('Khách Hàng', width=UI_WIDTH["dl_khachhang"], minWidth=UI_WIDTH["dl_khachhang"])
    
    gb.configure_column('Ngày hẹn', editable=True, width=UI_WIDTH["dl_ngayhen"], minWidth=UI_WIDTH["dl_ngayhen"], maxWidth=UI_WIDTH["dl_ngayhen"], 
                        cellEditor=date_editor_js, 
                        cellStyle={'color': '#007bff', 'fontWeight': 'bold', 'textAlign': 'center'})
                        
    gb.configure_column('Đã gửi', width=UI_WIDTH["dl_dagui"], minWidth=UI_WIDTH["dl_dagui"], maxWidth=UI_WIDTH["dl_dagui"])
    gb.configure_column('base_icon', hide=True)
    gb.configure_column('matched_str', hide=True)
    gb.configure_column('sent_str', hide=True)

    grid_response = AgGrid(
        df_match, gridOptions=gb.build(), allow_unsafe_jscode=True, 
        update_mode=GridUpdateMode.VALUE_CHANGED, data_return_mode=DataReturnMode.AS_INPUT,
        fit_columns_on_grid_load=False, theme='streamlit', height=350, key="grid_chon_khach_trong_dialog"
    )
            
    st.divider()
    if st.button("🚀 XUẤT LỆNH GỬI HÀNG LOẠT", type="primary", width="stretch"):
        if grid_response['data'] is not None:
            df_result = pd.DataFrame(grid_response['data'])
            selected_df = df_result[df_result['Trạng thái'] == '⚪']
            
            if selected_df.empty:
                st.error("Vui lòng click chọn (⚪) ít nhất 1 khách!")
                return
                
            success_count = 0
            for _, row in selected_df.iterrows():
                kid = str(row['KID'])
                matched_uids = row['matched_str'].split(',') if row['matched_str'] else []
                sent_uids = row['sent_str'].split(',') if row['sent_str'] else []
                uids_to_send = list(set(matched_uids) - set(sent_uids))
                
                ngay_hen_str = str(row['Ngày hẹn']).strip()
                try:
                    ngay_hen_date = pd.to_datetime(ngay_hen_str).date()
                except:
                    ngay_hen_date = pd.Timestamp.now().date()
                
                schedule_dict = {uid: ngay_hen_date for uid in uids_to_send if uid}
                
                if schedule_dict:
                    if save_pending_logs(schedule_dict, kid, df_mykid):
                        success_count += 1
                    
            if success_count > 0:
                st.success(f"✅ Đã lên lệnh gửi thành công cho {success_count} khách!")
                st.rerun()
            else:
                st.info("Không có dữ liệu mới để xuất lệnh.")
# ==========================================
# 3. CÁC HÀM COMPONENT GIAO DIỆN (UI COMPONENTS)
# ==========================================
# KHỐI 1: TÁCH RIÊNG JAVASCRIPT (Giúp code Python sạch sẽ hơn)
# ==========================================
def get_aggrid_js_codes(c_link_hidden, c_link_ggd_hidden):
    return {
        "toggle": JsCode("""
        function(params) {
            // Clear any existing timeout for this cell
            if (params.node._clickTimeout) {
                clearTimeout(params.node._clickTimeout);
                params.node._clickTimeout = null;
            }
            
            // Set timeout to handle single click (delayed to wait for potential double-click)
            params.node._clickTimeout = setTimeout(function() {
                params.node._clickTimeout = null;
                if (params.event && params.event.detail === 1) { 
                    const field = params.colDef.field;
                    const value = params.node.data[field];
                    if (value === '✅ Đã gửi' || value === '🟡 Chờ gửi' || value === '🔴 Black List') return; 
                    let newValue;
                    if (value === '🔘 Đã chọn') {
                        newValue = params.node._originalState || '❌ Chưa gửi';
                    } else {
                        params.node._originalState = value;
                        newValue = '🔘 Đã chọn';
                    }
                    params.node.setDataValue(field, newValue);
                }
            }, 200); // Wait 200ms to check for double-click
        }
        """),
        "double_click_handler": JsCode("""
        function(params) {
            // Clear the single-click timeout to prevent it from executing
            if (params.node._clickTimeout) {
                clearTimeout(params.node._clickTimeout);
                params.node._clickTimeout = null;
            }
            
            if (params.event && params.event.detail === 2) { 
                const value = params.value;
                const field = params.colDef.field;
                let newValue;
                
                if (value === '🔴 Black List') {
                    // Lưu trạng thái gốc và chuyển về 🔘
                    params.node._originalState = '🔴 Black List';
                    newValue = '🔘 Đã chọn';
                } else if (value === '❌ Chưa gửi') {
                    // Lưu trạng thái gốc và chuyển về 🔘
                    params.node._originalState = '❌ Chưa gửi';
                    newValue = '🔘 Đã chọn';
                } else if (value === '🔘 Đã chọn') {
                    // Quay về trạng thái gốc
                    newValue = params.node._originalState || '❌ Chưa gửi';
                } else {
                    return;
                }
                params.node.setDataValue(field, newValue);
            }
        }
        """),
        "reset_blacklist": JsCode("""
        function(params) {
            if (params.event && params.event.detail === 2) { 
                const value = params.value;
                const field = params.colDef.field;
                let newValue;
                if (value === '🔴 Black List') {
                    newValue = '🔘 Đã chọn';
                } else if (value === '🔘 Đã chọn') {
                    newValue = '🔴 Black List';
                } else {
                    return;
                }
                params.node.setDataValue(field, newValue);
            }
        }
        """),
        "copy_text": JsCode("""
        function(params) {
            if (params.value) {
                const textToCopy = params.value.toString().split('http')[0].trim();
                const textArea = document.createElement("textarea");
                textArea.value = textToCopy;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
            }
        }
        """),
        "sonha_dclick": JsCode(f"""
        function(params) {{
            const linkVal = params.node.data['{c_link_hidden}'];
            if (linkVal && linkVal.startsWith('http')) {{ window.open(linkVal, '_blank'); }}
        }}
        """),
        "open_ggd_click": JsCode(f"""
        function(params) {{
            if ({str(browser_photos_enabled(IS_CLOUD)).lower()}) {{ params.node.setDataValue('_folder_trigger', Date.now().toString()); return; }}
            const linkVal = params.node.data['{c_link_ggd_hidden}'];
            if (linkVal && linkVal.startsWith('http')) {{ 
                window.open(linkVal, '_blank'); 
            }} else {{
                // Nếu chưa có link Google Drive thì kích hoạt mở thư mục Offline (Local)
                params.node.setDataValue('_folder_trigger', Date.now().toString());
            }}
        }}
        """),
        # Sửa DCL từ mở link sang phát tín hiệu mở Folder offline
        "tenduong_dclick": JsCode("""
        function(params) {
            if (params.event && params.event.detail === 2) { // Kiểm tra đúng Double Click
                params.node.setDataValue('_folder_trigger', Date.now().toString());
            }
        }
        """),
        "sonha_style": JsCode(f"""
        function(params) {{
            const link = params.node.data['{c_link_hidden}'];
            if (link && link.startsWith('http')) {{
                return {{'color': '#007bff', 'textDecoration': 'underline', 'fontWeight': 'bold', 'cursor': 'pointer'}};
            }}
            return {{ 'cursor': 'pointer' }};
        }}
        """),
        "ggd_col_style": JsCode(f"""
        function(params) {{
            const link = params.node.data['{c_link_ggd_hidden}'];
            if (link && link.startsWith('http')) {{
                return {{'cursor': 'pointer', 'backgroundColor': '#1e293b', 'color': '#38bdf8', 'textAlign': 'center', 'fontWeight': 'bold', 'border': '1px solid #334155', 'borderRadius': '4px'}};
            }}
            return {{'cursor': 'pointer', 'textAlign': 'center', 'color': '#64748b'}};
        }}
        """),
        "tenduong_style": JsCode(f"""
        function(params) {{
            const link = params.node.data['{c_link_ggd_hidden}'];
            if (link && link.startsWith('http')) {{
                return {{'color': '#007bff', 'textDecoration': 'underline', 'fontWeight': 'bold', 'cursor': 'pointer'}};
            }}
            return {{ 'cursor': 'pointer' }};
        }}
        """),
        "copy_cus": JsCode("""
        function(params) {
            if (params.value) {
                const textArea = document.createElement("textarea");
                textArea.value = params.value;
                document.body.appendChild(textArea);
                textArea.select();
                try { document.execCommand('copy'); alert('📋 Đã copy thông tin nhà!'); } catch (err) {}
                document.body.removeChild(textArea);
            }
        }
        """)
    }

# ==========================================
# KHỐI 2: TÁCH RIÊNG THUẬT TOÁN ĐỊNH GIÁ 
# ==========================================
def apply_dinh_gia(df, c_mota, c_dt, c_q):
    def parse_num(val):
        try: return float(str(val).strip().replace(',', '.'))
        except: return 0.0

    def calc(row):
        try:
            mota = str(row.get(c_mota, ""))
            sm_num = parse_num(row.get(c_dt, 0))  # Diện tích (SM)
            dongia = parse_num(row.get(c_q, 0))   # Đơn giá (DG)

            # Thay "" thành None để Streamlit (PyArrow) không bị lỗi ép kiểu số
            if dongia <= 0 or sm_num <= 0: 
                return None

            slg_match = re.search(r'(?i)SLG\s*([0-9.,]+)', mota)
            slg_val = float(slg_match.group(1).replace(',', '.')) if slg_match else 0.0

            scn_match = re.search(r'(?i)SCN\s*([0-9.,]+)', mota)
            scn_val = float(scn_match.group(1).replace(',', '.')) if scn_match else 0.0

            scn_final = scn_val if scn_val > 0 else sm_num
            sm_final = max(sm_num, scn_final)
            slg_final = slg_val if slg_val > 0 else scn_final

            scn_final = max(scn_final, slg_final)
            sm_final = max(sm_final, scn_final)

            sdg_val = slg_final + (scn_final - slg_final) * 0.5 + (sm_final - scn_final) * 0.25

            return round((sdg_val * dongia) / 1000, 1)
            
        except: pass
        
        # Thay "" thành None
        return None
        
    df['Định giá'] = df.apply(calc, axis=1)
    return df# ==========================================
# KHỐI 3: HÀM RENDER AGGRID CHÍNH (Đã được làm sạch)
# ==========================================

def render_aggrid(results, df_log, kid_id):
    """Bảng chọn nhà Tab 1 - Đã vá lỗi AgGrid Cache và tìm kiếm cột chuẩn xác"""
    target_kid = str(kid_id).strip()
    # 1. BẮT LẤY CHẾ ĐỘ HIỆN TẠI
    app_mode = st.session_state.get('app_mode', 'GUI_KHACH')
    
    log_status_map = {}
    
    if not df_log.empty:
        try:
            df_log_kid = df_log[df_log.iloc[:, 0].astype(str).str.strip() == target_kid]
            for _, row in df_log_kid.iterrows():
                uid = str(row.iloc[1]).strip()
                status = str(row.iloc[4]).strip().lower()
                log_status_map[uid] = status
        except: pass

    def mapping_trang_thai(uid):
        uid_str = str(uid).strip()
        if st.session_state.get('app_mode', 'GUI_KHACH') == 'TIM_KHACH':
            return '❌ Chưa gửi'
        if uid_str not in log_status_map: return '❌ Chưa gửi'
        status = log_status_map[uid_str]
        if status == 'đã gửi': return '✅ Đã gửi'
        elif status == 'chưa gửi': return '🟡 Chờ gửi'
        elif status == 'black_list': return '🔴 Black List'
        return '❌ Chưa gửi'

    # 2. HÀM TÌM CỘT THÔNG MINH (Chống lỗi phân biệt hoa/thường/khoảng trắng)
    def get_real_col(key):
        for c in results.columns:
            if str(c).strip().lower() == str(key).strip().lower(): return c
        return key

    # Lấy tên cột chuẩn an toàn
    c_uid = get_real_col(CONFIG_GSK_CM["UID"])
    if c_uid not in results.columns: results[c_uid] = ""
    results['Trạng thái'] = results[c_uid].apply(mapping_trang_thai)
    
    c_sonha = get_real_col(CONFIG_GSK_CM["SONHA"])
    c_tenduong = get_real_col(CONFIG_GSK_CM["TENDUONG"])
    c_quan = get_real_col(CONFIG_GSK_CM["QUAN"])
    c_phuong = get_real_col(CONFIG_GSK_CM["PHUONG"])
    c_ngang = get_real_col(CONFIG_GSK_CM["NGANG"])
    c_dai = get_real_col(CONFIG_GSK_CM["DAI"])
    c_gia = get_real_col(CONFIG_GSK_CM["GIA"])
    c_ketcau = get_real_col(CONFIG_GSK_CM["KETCAU"])
    c_pl = get_real_col(CONFIG_GSK_CM["PL"])
    
    c_link_hidden = COL_LINK_URL  
    c_link_ggd_hidden = COL_LINK_GGD 
    
    c_mota = get_real_col(CONFIG_GSK_CM.get("MOTACHITIET", "motachitiet"))
    c_dt = get_real_col(CONFIG_GSK_CM.get("DIENTICH", "dientich"))
    c_q = get_real_col(CONFIG_GSK_CM.get("DINHGIA_Q", "dinhgia")) 
    c_update = get_real_col(CONFIG_GSK_CM.get("UPDATE", "update"))
    c_cus = get_real_col(CONFIG_GSK_CM.get("CUS", "cus"))
    
    for col in [c_mota, c_dt, c_q, c_update, c_cus]:
        if col not in results.columns:
            results[col] = ""
            
    results = apply_dinh_gia(results, c_mota, c_dt, c_q)

    num_cols = [c_ngang, c_dai, c_gia]
    for c in num_cols:
        if c in results.columns: results[c] = clean_numeric(results[c])

    # === BẮT ĐẦU THÊM KHỐI SẮP XẾP ƯU TIÊN ===
    if c_pl in results.columns:
        # 1. Định vị Rank: TAR = 1, A = 2, các loại khác = 3
        results['_rank_pl'] = results[c_pl].astype(str).str.strip().str.upper().apply(
            lambda x: 1 if x == 'TAR' else (2 if x == 'A' else 3)
        )
        
        # 2. Ép chuẩn thời gian cho cột Update và Sắp xếp
        if c_update in results.columns:
            # dayfirst=True giúp đọc chuẩn ngày Việt Nam (DD/MM/YYYY)
            results['_dt_update'] = pd.to_datetime(results[c_update], format='mixed', dayfirst=True, errors='coerce')
            
            # Sắp xếp kép: Rank tăng dần (1->2->3) và Ngày giảm dần (Mới -> Cũ)
            results = results.sort_values(by=['_rank_pl', '_dt_update'], ascending=[True, False])
        else:
            results = results.sort_values(by='_rank_pl', ascending=True)
    # === KẾT THÚC KHỐI SẮP XẾP ===

    # Tạo cột hiển thị nút GGD (gán nhãn 📂 nếu có link, ngược lại để trống)
    results['GGD'] = results[c_link_ggd_hidden].apply(lambda x: '📂' if str(x).strip().startswith('http') else '📁')

    # Luôn trích xuất dacdiem và note_rieng trực tiếp từ motachitiet để đảm bảo dữ liệu mới nhất
    if c_mota in results.columns:
        results['dacdiem'] = results[c_mota].apply(extract_highlight)
        results['note_rieng'] = results[c_mota].apply(extract_note)
    else:
        if 'dacdiem' not in results.columns: results['dacdiem'] = ""
        if 'note_rieng' not in results.columns: results['note_rieng'] = ""

    # Danh sách hiển thị dùng TÊN CỘT THỰC TẾ
    display_cols = [
        'Trạng thái', c_pl, c_quan, c_phuong, 
        c_sonha, 'GGD', c_tenduong, c_ngang, 
        c_dai, c_dt, c_gia, 'Định giá', c_ketcau, 
        'dacdiem', c_update, c_uid, c_cus, 'note_rieng',
        c_link_hidden, c_link_ggd_hidden
    ]
    
    # CHỐT CHẶN AN TOÀN: Bơm cột rỗng nếu Sheet thực sự thiếu (Chống KeyError)
    for col in display_cols:
        if col not in results.columns:
            results[col] = ""

    df_display = results[display_cols].copy()
    df_display['_folder_trigger'] = '' 

    js = get_aggrid_js_codes(c_link_hidden, c_link_ggd_hidden)
    
    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_default_column(filter=True, sortable=False, resizable=True, suppressSizeToFit=True)

    gb.configure_column('Trạng thái', onCellClicked=js["toggle"], onCellDoubleClicked=js["double_click_handler"], editable=False, pinned='left', width=UI_WIDTH["t1_trangthai"], minWidth=UI_WIDTH["t1_trangthai"], maxWidth=UI_WIDTH["t1_trangthai"])
    gb.configure_column(c_pl, width=UI_WIDTH["t1_pl"], minWidth=UI_WIDTH["t1_pl"], maxWidth=UI_WIDTH["t1_pl"])
    gb.configure_column(c_quan, width=UI_WIDTH["t1_quan"], minWidth=UI_WIDTH["t1_quan"], maxWidth=UI_WIDTH["t1_quan"])
    gb.configure_column(c_phuong, width=UI_WIDTH["t1_phuong"], minWidth=UI_WIDTH["t1_phuong"], maxWidth=UI_WIDTH["t1_phuong"])
    
    gb.configure_column(c_sonha, width=UI_WIDTH["t1_sonha"], minWidth=UI_WIDTH["t1_sonha"], maxWidth=UI_WIDTH["t1_sonha"], onCellClicked=js["copy_text"], onCellDoubleClicked=js["sonha_dclick"], cellStyle=js["sonha_style"])
    gb.configure_column('GGD', header_name="Ảnh", width=UI_WIDTH["t1_ggd"], minWidth=UI_WIDTH["t1_ggd"], maxWidth=UI_WIDTH["t1_ggd"],
                        onCellClicked=js["open_ggd_click"],
                        cellStyle=js["ggd_col_style"])
    gb.configure_column(c_tenduong, width=UI_WIDTH["t1_tenduong"], minWidth=UI_WIDTH["t1_tenduong"], maxWidth=UI_WIDTH["t1_tenduong"], 
                        onCellClicked=js["copy_text"], 
                        onCellDoubleClicked=js["tenduong_dclick"], 
                        cellStyle={'color': '#38bdf8', 'textDecoration': 'underline', 'fontWeight': 'bold', 'cursor': 'pointer'})
    
    gb.configure_column(c_ngang, type=["numericColumn"], width=UI_WIDTH["t1_ngang"], minWidth=UI_WIDTH["t1_ngang"], maxWidth=UI_WIDTH["t1_ngang"])
    gb.configure_column(c_dai, type=["numericColumn"], width=UI_WIDTH["t1_dai"], minWidth=UI_WIDTH["t1_dai"], maxWidth=UI_WIDTH["t1_dai"])
    
    gb.configure_column(c_dt, header_name="Diện tích", type=["numericColumn"], 
                        width=UI_WIDTH.get("t1_dientich", 55), 
                        minWidth=UI_WIDTH.get("t1_dientich", 55), 
                        maxWidth=UI_WIDTH.get("t1_dientich", 55))

    gia_sale_style = JsCode("""
    function(params) {
        if (params.value && params.data['Định giá']) {
            const gia = parseFloat(params.value);
            const dinhGia = parseFloat(params.data['Định giá']);
            if (!isNaN(gia) && !isNaN(dinhGia) && gia < dinhGia) {
                return {'color': '#10B981', 'fontWeight': 'bold'};
            }
        }
        return null;
    }
    """)
    gb.configure_column(c_gia, type=["numericColumn"], width=UI_WIDTH["t1_gia"], minWidth=UI_WIDTH["t1_gia"], maxWidth=UI_WIDTH["t1_gia"], cellStyle=gia_sale_style)
    gb.configure_column('Định giá', type=["numericColumn"], width=UI_WIDTH["t1_dinhgia"], minWidth=UI_WIDTH["t1_dinhgia"], maxWidth=UI_WIDTH["t1_dinhgia"], cellStyle={'color': '#D97706', 'fontWeight': 'bold'})
    
    gb.configure_column(c_ketcau, width=UI_WIDTH["t1_ketcau"], minWidth=UI_WIDTH["t1_ketcau"], maxWidth=UI_WIDTH["t1_ketcau"])
    gb.configure_column('dacdiem', header_name="Đặc điểm", width=UI_WIDTH["t1_dacdiem"], minWidth=UI_WIDTH["t1_dacdiem"], maxWidth=UI_WIDTH["t1_dacdiem"])
    gb.configure_column(c_update, header_name="Cập nhật", width=UI_WIDTH["t1_update"], minWidth=UI_WIDTH["t1_update"], maxWidth=UI_WIDTH["t1_update"])
    gb.configure_column(c_uid, header_name="UID", width=UI_WIDTH["t1_uid"], minWidth=UI_WIDTH["t1_uid"], maxWidth=UI_WIDTH["t1_uid"])
    
    gb.configure_column(c_cus, header_name="📋 Copy TT", width=UI_WIDTH["t1_cus"], minWidth=UI_WIDTH["t1_cus"], maxWidth=UI_WIDTH["t1_cus"],
                        onCellClicked=js["copy_cus"], 
                        cellStyle={'cursor': 'pointer', 'color': '#007bff', 'textDecoration': 'underline'})

    gb.configure_column('note_rieng', header_name="📝 Ghi chú", width=UI_WIDTH.get("t1_note", 650), minWidth=350, resizable=True, 
                        cellStyle={'color': '#f59e0b', 'fontWeight': '500'})

    gb.configure_column('_folder_trigger', hide=True)
    gb.configure_column(c_link_hidden, hide=True)
    gb.configure_column(c_link_ggd_hidden, hide=True)

    refresh_count = st.session_state.get('refresh_counter', 0)
    
    # 3. ÉP AGGRID TẠO BẢNG MỚI KHI ĐỔI CHẾ ĐỘ BẰNG CÁCH CHÈN app_mode VÀO KEY
    ag_response = AgGrid(
        df_display, gridOptions=gb.build(), allow_unsafe_jscode=True, 
        update_mode=GridUpdateMode.VALUE_CHANGED, 
        data_return_mode=DataReturnMode.FILTERED_AND_SORTED,
        fit_columns_on_grid_load=False, theme='streamlit', height=450,
        key=f"grid_tab1_master_{app_mode}_{target_kid}_{len(df_display)}_{refresh_count}" 
    )

    if ag_response['data'] is not None:
        updated_df = pd.DataFrame(ag_response['data'])
        if 'last_tab1_trigger' not in st.session_state:
            st.session_state['last_tab1_trigger'] = 0.0

        df_triggers = updated_df[updated_df['_folder_trigger'].astype(str) != ''].copy()
        if not df_triggers.empty:
            df_triggers['trigger_num'] = pd.to_numeric(df_triggers['_folder_trigger'], errors='coerce').fillna(0.0)
            latest_idx = df_triggers['trigger_num'].idxmax()
            latest_row = df_triggers.loc[latest_idx]
            latest_val = float(latest_row['trigger_num'])
            
            if latest_val > st.session_state['last_tab1_trigger']:
                st.session_state['last_tab1_trigger'] = latest_val
                
                if browser_photos_enabled(IS_CLOUD):
                    request_photos(latest_row, district=c_quan, street=c_tenduong, number=c_sonha, uid=c_uid, drive=c_link_ggd_hidden)
                elif ROOT_DIR == "":
                    st.toast("❌ Chưa cấu hình đúng ổ đĩa ROOT_DIR!", icon="🚨")
                else:
                    quan_c = remove_vietnamese_accent(str(latest_row.get(c_quan, ''))).title()
                    duong_c = remove_vietnamese_accent(str(latest_row.get(c_tenduong, ''))).title()
                    sonha_c = str(latest_row.get(c_sonha, '')).strip()
                    
                    folder_path = os.path.join(ROOT_DIR, quan_c, duong_c, f"{sonha_c} {duong_c}")
                    if os.path.exists(folder_path):
                        folder_path_clean = os.path.normpath(folder_path)
                        if IS_CLOUD:
                            st.toast(f"📂 Folder path (Cloud): {folder_path_clean}", icon="ℹ️")
                        else:
                            subprocess.Popen(f'explorer "{folder_path_clean}"')
                    else:
                        st.toast(f"⚠️ Thư mục không tồn tại: {sonha_c} {duong_c}", icon="⚠️")

    return pd.DataFrame(ag_response['data'])

def prepare_tab3_data(df_log, df_houses):
    """Khối 1: Chuẩn bị dữ liệu Tab 3 (Pandas Vectorized & Mapping) - Không dính dáng đến UI"""
    if df_log.empty:
        return pd.DataFrame()

    cols_standard = ["KID", "UID", "thongtin_KID", "ngay_gui", "trang_thai", "phan_hoi", "timestamp"]
    
    try:
        if len(df_log.columns) >= 7:
            df_log = df_log.iloc[:, :7].copy() 
            df_log.columns = cols_standard
        else:
            df_log = df_log.copy()
            df_log['timestamp'] = ""
    except: 
        df_log = df_log.copy()

    df_log['ngay_gui_log'] = pd.to_datetime(df_log['timestamp'], errors='coerce').dt.strftime('%d/%m/%Y').fillna('')
    df_log = df_log.sort_values(by="timestamp", ascending=False).fillna("")
    df_log['UID_clean'] = df_log['UID'].astype(str).str.strip()

    # ==========================================
    # XỬ LÝ VECTORIZED PANDAS & TỪ ĐIỂN
    # ==========================================
    c_uid = CONFIG_GSK_CM["UID"]
    c_sonha = CONFIG_GSK_CM["SONHA"]
    c_tenduong = CONFIG_GSK_CM["TENDUONG"]
    c_gia = CONFIG_GSK_CM["GIA"]
    c_pl = CONFIG_GSK_CM["PL"]
    c_cus = CONFIG_GSK_CM.get("CUS", "cus")
    c_quan = CONFIG_GSK_CM["QUAN"]

    if not df_houses.empty:
        df_h_clean = df_houses.copy()
        df_h_clean[c_uid] = df_h_clean[c_uid].astype(str).str.strip()
        
        # Mapping chi tiết mã SOLD-CTB, SOLD-SBT, SOLD-ADE bằng Pandas Dictionary Map
        df_h_clean['_pl_clean'] = df_h_clean[c_pl].astype(str).str.strip().str.upper()
        df_h_clean['_is_sold'] = df_h_clean['_pl_clean'].isin(['CTB', 'SBT', 'ADE'])
        
        sold_mapping = {'CTB': ' [SOLD-CTB]', 'SBT': ' [SOLD-SBT]', 'ADE': ' [SOLD-ADE]'}
        df_h_clean['_sold_text'] = df_h_clean['_pl_clean'].map(sold_mapping).fillna("")
        
        # Ghép chuỗi hiển thị nhà có kèm nhãn đã bán chi tiết
        df_h_clean['_display'] = df_h_clean[c_sonha].astype(str) + " " + df_h_clean[c_tenduong].astype(str) + " - " + df_h_clean[c_gia].astype(str) + "T" + df_h_clean['_sold_text']
        
        dict_display = dict(zip(df_h_clean[c_uid], df_h_clean['_display']))
        dict_is_sold = dict(zip(df_h_clean[c_uid], df_h_clean['_is_sold']))
        dict_cus = dict(zip(df_h_clean[c_uid], df_h_clean[c_cus].astype(str)))
        dict_quan = dict(zip(df_h_clean[c_uid], df_h_clean[c_quan].astype(str)))
        dict_sonha = dict(zip(df_h_clean[c_uid], df_h_clean[c_sonha].astype(str)))
        dict_tenduong = dict(zip(df_h_clean[c_uid], df_h_clean[c_tenduong].astype(str)))
        
        if COL_LINK_URL in df_h_clean.columns:
            dict_link = dict(zip(df_h_clean[c_uid], df_h_clean[COL_LINK_URL].astype(str)))
        else:
            dict_link = {}
    else:
        dict_display, dict_is_sold, dict_cus, dict_quan, dict_sonha, dict_tenduong, dict_link = {}, {}, {}, {}, {}, {}, {}

    # ==========================================
    # BUILD BẢNG ĐẦU RA DF_DISPLAY
    # ==========================================
    df_display = pd.DataFrame()
    df_display['KID'] = df_log['KID'].astype(str)
    df_display['Thông tin KH'] = df_log.get('thongtin_KID', '').astype(str)
    
    df_display['Nhà gửi'] = df_log['UID_clean'].map(dict_display).fillna(df_log['UID_clean'])
    df_display['🗺️ QH'] = df_log['UID_clean'].map(dict_link).fillna('').apply(lambda x: '🌍 Mở' if str(x).startswith('http') else '')
    df_display['📂 Ảnh'] = '📁 Mở'
    df_display['Ngày gửi nhà'] = df_log.get('ngay_gui', '').astype(str)
    df_display['Ngày gửi log'] = df_log['ngay_gui_log']
    df_display['Trạng thái'] = df_log.get('trang_thai', 'chưa gửi').astype(str)
    df_display['Phản hồi'] = df_log.get('phan_hoi', '').astype(str)
    df_display['timestamp'] = df_log['timestamp'].astype(str)
    
    df_display['_is_sold'] = df_log['UID_clean'].map(dict_is_sold).fillna(False)
    df_display['_uid_key'] = df_log['UID_clean']
    df_display['_cus_hidden'] = df_log['UID_clean'].map(dict_cus).fillna('')
    df_display['_quan'] = df_log['UID_clean'].map(dict_quan).fillna('')
    df_display['_sonha'] = df_log['UID_clean'].map(dict_sonha).fillna('')
    df_display['_tenduong'] = df_log['UID_clean'].map(dict_tenduong).fillna('')
    df_display['_folder_trigger'] = ''
    df_display['_link_qh'] = df_log['UID_clean'].map(dict_link).fillna('')
    drive_map = dict(zip(df_houses[c_uid].astype(str).str.strip(), df_houses[COL_LINK_GGD].fillna('').astype(str))) if not df_houses.empty and COL_LINK_GGD in df_houses.columns else {}
    df_display['_link_drive'] = df_log['UID_clean'].map(drive_map).fillna('')

    return df_display

def render_tab3_ui(df_display):
    """Khối 2: Hiển thị giao diện AgGrid Tab 3 và xử lý Logic Silent Auto-Save (GIỮ NGUYÊN FILTER/SORT)"""
    if df_display.empty:
        st.info("Chưa có nhật ký gửi nhà.")
        return

    cols_standard = ["KID", "UID", "thongtin_KID", "ngay_gui", "trang_thai", "phan_hoi", "timestamp"]

    # ==========================================
    # MÃ JAVASCRIPT & AGGRID CẤU HÌNH
    # ==========================================
    toggle_status_jscode = JsCode("""
    function(params) {
        if (params.event && params.event.detail === 1) { 
            const currentValue = params.value; 
            let newValue = (currentValue === 'chưa gửi') ? 'đã gửi' : 'chưa gửi';
            params.node.setDataValue(params.colDef.field, newValue);

            // Bơm trực tiếp Timestamp vào Grid bằng JS để không cần chờ Python Rerun (Chống giật/nháy)
            if (newValue === 'đã gửi') {
                let now = new Date();
                let nowStr = now.getFullYear() + '-' +
                             String(now.getMonth() + 1).padStart(2, '0') + '-' +
                             String(now.getDate()).padStart(2, '0') + ' ' +
                             String(now.getHours()).padStart(2, '0') + ':' +
                             String(now.getMinutes()).padStart(2, '0') + ':' +
                             String(now.getSeconds()).padStart(2, '0');
                params.node.setDataValue('timestamp', nowStr);
                
                let logDateStr = String(now.getDate()).padStart(2, '0') + '/' +
                                 String(now.getMonth() + 1).padStart(2, '0') + '/' +
                                 now.getFullYear();
                params.node.setDataValue('Ngày gửi log', logDateStr);
            }
        }
    }
    """)

    trigger_folder_jscode = JsCode("""
    function(params) {
        setTimeout(function() {
            if (params.event && params.event.detail === 1) {
                params.node.setDataValue('_folder_trigger', Date.now().toString());
            }
        }, 50);
    }
    """)

    open_qh_jscode = JsCode("""
    function(params) {
        if (params.event && params.event.detail === 1) {
            const link = params.node.data['_link_qh'];
            if (link && link.startsWith('http')) {
                window.open(link, '_blank');
            }
        }
    }
    """)

    single_copy_jscode = JsCode("""
    function(params) {
        if (!params.value || !params.node.data['_cus_hidden']) return;
        setTimeout(function() {
            if (params.event && params.event.detail === 1) {
                const textToCopy = params.node.data['_cus_hidden'];
                const houseName = params.node.data['_sonha'] + ' ' + params.node.data['_tenduong'];

                const textArea = document.createElement("textarea");
                textArea.value = textToCopy;
                document.body.appendChild(textArea);
                textArea.select();
                try { document.execCommand('copy'); } catch (err) {}
                document.body.removeChild(textArea);

                const toast = document.createElement('div');
                toast.innerHTML = '✅ Copied: <b>' + houseName + '</b>';
                toast.style.position = 'fixed';
                toast.style.bottom = '30px';
                toast.style.right = '30px';
                toast.style.backgroundColor = '#10B981'; 
                toast.style.color = 'white';
                toast.style.padding = '12px 20px';
                toast.style.borderRadius = '6px';
                toast.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1)';
                toast.style.fontFamily = 'system-ui, -apple-system, sans-serif';
                toast.style.fontSize = '14px';
                toast.style.zIndex = '99999';
                toast.style.transition = 'opacity 0.4s ease-out';

                document.body.appendChild(toast);
                setTimeout(() => { toast.style.opacity = '0'; }, 1500);
                setTimeout(() => { document.body.removeChild(toast); }, 2000);
            }
        }, 80);
    }
    """)

    date_editor_jscode = JsCode("""
    class DatePickerEditor {
        init(params) {
            this.eInput = document.createElement('input');
            this.eInput.type = 'date';
            this.eInput.style.width = '100%';
            this.eInput.style.height = '100%';
            this.eInput.style.border = 'none';
            this.eInput.style.outline = 'none';
            this.eInput.style.backgroundColor = 'transparent';
            this.eInput.style.color = 'inherit';
            this.eInput.value = params.value; 
        }
        getGui() { return this.eInput; }
        afterGuiAttached() { 
            this.eInput.focus(); 
            if(this.eInput.showPicker) { this.eInput.showPicker(); } 
        }
        getValue() { return this.eInput.value; }
        isPopup() { return false; }
    }
    """)

    row_style_jscode = JsCode("""
    function(params) {
        if (params.data && params.data._is_sold) {
            return { 'color': '#6b7280', 'fontStyle': 'italic', 'backgroundColor': '#1f2937' };
        }
        if (params.data && params.data['Trạng thái'] === 'đã gửi') {
            return { 'backgroundColor': '#064e3b', 'color': '#34d399', 'fontWeight': 'bold' };
        }
        return null;
    }
    """)

    gb = GridOptionsBuilder.from_dataframe(df_display)
    gb.configure_column('_link_drive', hide=True)
    gb.configure_default_column(sortable=True, filter=True, resizable=False, suppressSizeToFit=True)
    gb.configure_selection(selection_mode="multiple", use_checkbox=True, header_checkbox=True)
    
    for hidden_col in ['_is_sold', '_uid_key', 'timestamp', '_cus_hidden', '_quan', '_sonha', '_tenduong', '_folder_trigger', '_link_qh']:
        gb.configure_column(hidden_col, hide=True)

    gb.configure_column('KID', width=UI_WIDTH["t3_kid"], minWidth=UI_WIDTH["t3_kid"], maxWidth=UI_WIDTH["t3_kid"])
    gb.configure_column('Thông tin KH', width=UI_WIDTH["t3_thongtin"], minWidth=UI_WIDTH["t3_thongtin"], maxWidth=UI_WIDTH["t3_thongtin"])
    
    gb.configure_column('Nhà gửi', width=UI_WIDTH["t3_nhagui"], minWidth=UI_WIDTH["t3_nhagui"], maxWidth=UI_WIDTH["t3_nhagui"], 
                        onCellClicked=single_copy_jscode, 
                        cellStyle={'cursor': 'copy', 'color': '#38bdf8', 'textDecoration': 'underline', 'fontWeight': 'bold'})
    
    gb.configure_column('🗺️ QH', width=UI_WIDTH["t3_qh"], minWidth=UI_WIDTH["t3_qh"], maxWidth=UI_WIDTH["t3_qh"],
                        onCellClicked=open_qh_jscode,
                        cellStyle=JsCode("""
                        function(params) {
                            if (params.value === '🌍 Mở') {
                                return {'cursor': 'pointer', 'backgroundColor': '#1e293b', 'color': '#38bdf8', 'textAlign': 'center', 'fontWeight': 'bold', 'border': '1px solid #333', 'borderRadius': '4px'};
                            }
                            return {'textAlign': 'center'};
                        }
                        """))

    gb.configure_column('📂 Ảnh', width=UI_WIDTH["t3_anh"], minWidth=UI_WIDTH["t3_anh"], maxWidth=UI_WIDTH["t3_anh"],
                        onCellClicked=trigger_folder_jscode,
                        cellStyle={'cursor': 'pointer', 'backgroundColor': '#121212', 'textAlign': 'center', 'fontWeight': 'bold', 'border': '1px solid #333', 'borderRadius': '4px'})
                        
    gb.configure_column('Ngày gửi nhà', editable=True, cellEditor=date_editor_jscode, width=UI_WIDTH["t3_ngaygui"], minWidth=UI_WIDTH["t3_ngaygui"], maxWidth=UI_WIDTH["t3_ngaygui"], cellStyle={'color': '#007bff', 'fontWeight': 'bold'})
    gb.configure_column('Ngày gửi log', width=UI_WIDTH["t3_ngaylog"], minWidth=UI_WIDTH["t3_ngaylog"], maxWidth=UI_WIDTH["t3_ngaylog"])
    
    gb.configure_column('Trạng thái', onCellClicked=toggle_status_jscode, editable=False, width=UI_WIDTH["t3_trangthai"], minWidth=UI_WIDTH["t3_trangthai"], maxWidth=UI_WIDTH["t3_trangthai"], cellStyle={'cursor': 'pointer'})
    gb.configure_column('Phản hồi', editable=True, width=UI_WIDTH["t3_phanhoi"], minWidth=UI_WIDTH["t3_phanhoi"], maxWidth=UI_WIDTH["t3_phanhoi"])
    
    gb.configure_grid_options(
        getRowStyle=row_style_jscode, 
        suppressSizeToFit=True,
        getRowId=JsCode("function(params) { return String(params.data.KID) + '-' + String(params.data._uid_key); }")
    )
    
    refresh_count = st.session_state.get('refresh_counter', 0)

    # Đổi DataReturnMode thành AS_INPUT, kèm theo key động để chặn lặp
    ag_response = AgGrid(df_display, gridOptions=gb.build(), allow_unsafe_jscode=True, 
                         update_mode=GridUpdateMode.MODEL_CHANGED | GridUpdateMode.VALUE_CHANGED, 
                         data_return_mode=DataReturnMode.AS_INPUT, 
                         fit_columns_on_grid_load=False, theme='streamlit', height=450,
                         key=f"zalo_dashboard_grid_master_{len(df_display)}_{refresh_count}") 

    st.markdown("---")
    
    if ag_response['data'] is not None:
        updated_df = pd.DataFrame(ag_response['data'])
        
        # 1. BẮT TÍN HIỆU MỞ FOLDER OFFLINE
        if 'last_folder_trigger' not in st.session_state:
            st.session_state['last_folder_trigger'] = 0.0
            
        df_triggers = updated_df[updated_df['_folder_trigger'].astype(str) != ''].copy()
        
        if not df_triggers.empty:
            df_triggers['trigger_num'] = pd.to_numeric(df_triggers['_folder_trigger'], errors='coerce').fillna(0.0)
            latest_idx = df_triggers['trigger_num'].idxmax()
            latest_row = df_triggers.loc[latest_idx]
            latest_val = float(latest_row['trigger_num'])
            
            if latest_val > st.session_state['last_folder_trigger']:
                st.session_state['last_folder_trigger'] = latest_val
                
                if browser_photos_enabled(IS_CLOUD):
                    request_photos(latest_row, district='_quan', street='_tenduong', number='_sonha', uid='_uid_key', drive='_link_drive')
                elif ROOT_DIR == "":
                    st.toast("❌ Chưa cấu hình đúng ổ đĩa ROOT_DIR!", icon="🚨")
                else:
                    quan_c = remove_vietnamese_accent(str(latest_row.get('_quan', ''))).title()
                    duong_c = remove_vietnamese_accent(str(latest_row.get('_tenduong', ''))).title()
                    sonha_c = str(latest_row.get('_sonha', '')).strip()
                    
                    folder_path = os.path.join(ROOT_DIR, quan_c, duong_c, f"{sonha_c} {duong_c}")
                    if os.path.exists(folder_path):
                        folder_path_clean = os.path.normpath(folder_path)
                        if IS_CLOUD:
                            st.toast(f"📂 Folder path (Cloud): {folder_path_clean}", icon="ℹ️")
                        else:
                            subprocess.Popen(f'explorer "{folder_path_clean}"')
                    else:
                        st.toast(f"⚠️ Thư mục không tồn tại: {sonha_c} {duong_c}", icon="⚠️")

        # 2. BẮT TÍN HIỆU XÓA LOG BẰNG CHECKBOX
        sel_rows_raw = ag_response.get('selected_rows')
        selected_df = pd.DataFrame(sel_rows_raw) if sel_rows_raw is not None else pd.DataFrame()
        
        if not selected_df.empty:
            if st.button(f"🗑️ Xóa ({len(selected_df)}) dòng log Zalo đã chọn", type="primary"):
                try:
                    current_log = pd.read_csv(FILE_LOG, dtype=str).fillna("")
                    for _, r in selected_df.iterrows():
                        k = str(r.get('KID', '')).strip()
                        u = str(r.get('_uid_key', '')).strip()
                        current_log = current_log[~((current_log['KID'].astype(str).str.strip() == k) & (current_log['UID'].astype(str).str.strip() == u))]
                    current_log.to_csv(FILE_LOG, index=False, encoding='utf-8-sig')
                    
                    st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                    st.toast("🗑️ Đã xóa log phân phối thành công!")
                    st.rerun() 
                except Exception as e: st.error(f"Lỗi khi xóa: {e}")

        # 3. BẮT TÍN HIỆU SILENT AUTO-SAVE KHI SỬA Ô (SIÊU TỐC - KHÔNG NHÁY BẢNG)
        if not updated_df.empty:
            def safe_str(val):
                return str(val).strip().lower() if pd.notna(val) and str(val).strip().lower() not in ['nan', 'none', 'null', '<na>'] else ""
                
            old_tt_map = {str(u).strip() + str(k).strip(): safe_str(v) for u, k, v in zip(df_display['_uid_key'], df_display['KID'], df_display['Trạng thái'])}
            old_ph_map = {str(u).strip() + str(k).strip(): safe_str(v) for u, k, v in zip(df_display['_uid_key'], df_display['KID'], df_display['Phản hồi'])}
            old_ng_map = {str(u).strip() + str(k).strip(): safe_str(v) for u, k, v in zip(df_display['_uid_key'], df_display['KID'], df_display['Ngày gửi nhà'])}

            new_tt_map = {str(u).strip() + str(k).strip(): safe_str(v) for u, k, v in zip(updated_df['_uid_key'], updated_df['KID'], updated_df['Trạng thái'])}
            new_ph_map = {str(u).strip() + str(k).strip(): safe_str(v) for u, k, v in zip(updated_df['_uid_key'], updated_df['KID'], updated_df['Phản hồi'])}
            new_ng_map = {str(u).strip() + str(k).strip(): safe_str(v) for u, k, v in zip(updated_df['_uid_key'], updated_df['KID'], updated_df['Ngày gửi nhà'])}

            new_tt_real = {str(u).strip() + str(k).strip(): str(v) for u, k, v in zip(updated_df['_uid_key'], updated_df['KID'], updated_df['Trạng thái']) if pd.notna(v)}
            new_ph_real = {str(u).strip() + str(k).strip(): str(v) for u, k, v in zip(updated_df['_uid_key'], updated_df['KID'], updated_df['Phản hồi']) if pd.notna(v)}
            new_ng_real = {str(u).strip() + str(k).strip(): str(v) for u, k, v in zip(updated_df['_uid_key'], updated_df['KID'], updated_df['Ngày gửi nhà']) if pd.notna(v)}
            
            # Kéo Timestamp siêu tốc từ thao tác JS vừa chèn vào UI
            new_ts_real = {str(u).strip() + str(k).strip(): str(v) for u, k, v in zip(updated_df['_uid_key'], updated_df['KID'], updated_df['timestamp']) if pd.notna(v)}

            has_change_t3 = False
            for key in new_tt_map.keys():
                if key in old_tt_map:
                    if old_tt_map[key] != new_tt_map[key] or old_ph_map[key] != new_ph_map[key] or old_ng_map[key] != new_ng_map[key]:
                        has_change_t3 = True
                        break
            
            if has_change_t3:
                current_log = pd.read_csv(FILE_LOG, dtype=str).fillna("")
                current_log['comp_key'] = current_log['UID'].astype(str).str.strip() + current_log['KID'].astype(str).str.strip()
                
                mask = current_log['comp_key'].isin(new_tt_real.keys())
                if mask.any():
                    current_log.loc[mask, 'trang_thai'] = current_log.loc[mask, 'comp_key'].map(new_tt_real).fillna(current_log.loc[mask, 'trang_thai'])
                    current_log.loc[mask, 'phan_hoi'] = current_log.loc[mask, 'comp_key'].map(new_ph_real).fillna(current_log.loc[mask, 'phan_hoi'])
                    current_log.loc[mask, 'ngay_gui'] = current_log.loc[mask, 'comp_key'].map(new_ng_real).fillna(current_log.loc[mask, 'ngay_gui'])
                    
                    # Ép Timestamp mới vào file Log để giữ tính đồng bộ thời gian với Tab 1 và Tab 2
                    current_log.loc[mask, 'timestamp'] = current_log.loc[mask, 'comp_key'].map(new_ts_real).fillna(current_log.loc[mask, 'timestamp'])
                
                current_log['phan_hoi'] = current_log['phan_hoi'].fillna("").astype(str).str.strip().replace(["nan", "None", "NaN", "null"], "")
                current_log = current_log.drop(columns=['comp_key'])
                
                # Ghi ngầm xuống file log mà KHÔNG kích hoạt st.rerun() để tránh chặn tương tác của người dùng
                current_log.to_csv(FILE_LOG, index=False, encoding='utf-8-sig')

def save_pending_logs(schedule_dict, kid_id, df_kids):
    """Lưu lịch gửi mới kèm dấu thời gian chính xác để cố định thứ tự"""
    try:
        file_exists = os.path.isfile(FILE_LOG)
        existing_pairs = set()
        if os.path.exists(FILE_LOG):
            try:
                tmp = pd.read_csv(FILE_LOG, dtype=str)
                if not tmp.empty:
                    for _, r in tmp.iterrows(): 
                        existing_pairs.add((str(r.iloc[0]).strip(), str(r.iloc[1]).strip()))
            except: pass

        kid_row = df_kids[df_kids['KID'].astype(str).str.strip() == str(kid_id).strip()]
        ttk_col = next((c for c in df_kids.columns if 'thongtin' in c.lower() or 'ttk' in c.lower()), df_kids.columns[1])
        ttk_snapshot = str(kid_row[ttk_col].values[0]) if not kid_row.empty else ""

        new_entries = []
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for uid, ngay_hen in schedule_dict.items():
            # Kiểm tra chống trùng lặp (KID + UID)
            if (str(kid_id).strip(), str(uid).strip()) not in existing_pairs:
                new_entries.append([
                    str(kid_id).strip(),
                    str(uid).strip(),
                    ttk_snapshot,
                    ngay_hen.strftime("%Y-%m-%d"),
                    "chưa gửi",
                    "",
                    now_str 
                ])
        
        # Nếu danh sách rỗng (do nhà đã từng được gửi trước đó) -> Báo lỗi và dừng lại
        if not new_entries:
            st.warning("⚠️ Lỗi: Căn nhà này đã từng được gửi hoặc đang nằm trong khay chờ của khách này rồi!")
            return False 

        with open(FILE_LOG, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["KID", "UID", "thongtin_KID", "ngay_gui", "trang_thai", "phan_hoi", "timestamp"])
            writer.writerows(new_entries)
                
        st.toast(f"✅ Đã thêm {len(new_entries)} lịch gửi mới!")
        return True # Trả về True nếu lưu thành công
    except Exception as e:
        st.error(f"Lỗi ghi log: {e}")
        return False
# ==========================================
# 3.5. XÁC THỰC ĐĂNG NHẬP & DUY TRÌ PHIÊN (PERSISTENT CLOUD AUTH)
# ==========================================
def generate_auth_token(username, password):
    """Tạo mã token chữ ký xác thực phiên làm việc an toàn"""
    raw = f"DTK_AUTH_{username}_{password}_SECURE_TOKEN_2025"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]

def check_authentication():
    """Bắt buộc đăng nhập khi chạy trên Cloud; tự động ghi nhớ phiên trên Tablet khi F5/reload"""
    if not IS_CLOUD:
        return True

    # 1. Đã xác thực trong session hiện tại
    if st.session_state.get('authenticated', False):
        return True

    # Lấy danh sách tài khoản hợp lệ từ Streamlit Secrets (an toàn)
    valid_users = {}
    try:
        if hasattr(st, "secrets"):
            if "users" in st.secrets:
                # Hỗ trợ cấu hình dạng: [users] admin = "matkhau"
                valid_users = {str(k).strip(): str(v).strip() for k, v in dict(st.secrets["users"]).items()}
            elif "APP_PASSWORD" in st.secrets:
                # Hỗ trợ cấu hình dạng: APP_USERNAME = "admin", APP_PASSWORD = "..."
                u = str(st.secrets.get("APP_USERNAME", "admin")).strip()
                p = str(st.secrets.get("APP_PASSWORD", "")).strip()
                if p:
                    valid_users[u] = p
    except Exception:
        pass

    # Cloud deployments must configure their own users in Streamlit Secrets.
    if not valid_users:
        st.error("Chưa cấu hình tài khoản đăng nhập. Hãy thêm [users] vào Streamlit Secrets của CRM V2.")
        st.stop()

    # 2. Tự động phục hồi phiên đăng nhập từ URL Query Params (Giữ đăng nhập khi F5)
    try:
        if hasattr(st, "query_params"):
            q_user = str(st.query_params.get("u", "")).strip()
            q_auth = str(st.query_params.get("auth", "")).strip()
            if q_user and q_auth and q_user in valid_users:
                expected_auth = generate_auth_token(q_user, valid_users[q_user])
                if q_auth == expected_auth:
                    st.session_state['authenticated'] = True
                    st.session_state['logged_in_user'] = q_user
                    return True
    except Exception:
        pass

    # 3. Tự động phục hồi phiên từ Browser LocalStorage (Giữ đăng nhập khi mở lại web/PWA)
    auto_restore_js = """
    <script>
    (function() {
        try {
            const u = localStorage.getItem("dtk_crm_user");
            const token = localStorage.getItem("dtk_crm_token");
            if (u && token && !window.location.search.includes("auth=")) {
                const url = new URL(window.location.href);
                url.searchParams.set("u", u);
                url.searchParams.set("auth", token);
                window.location.replace(url.toString());
            }
        } catch(e) {}
    })();
    </script>
    """
    st.markdown(auto_restore_js, unsafe_allow_html=True)

    # 4. Giao diện Form Đăng Nhập
    _, col_login, _ = st.columns([1, 1.3, 1])
    with col_login:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>🔒 ĐĂNG NHẬP HỆ THỐNG</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #aaa;'>Đại Thế Kỷ Advisor CRM - Cloud Edition</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        with st.form("cloud_login_form", clear_on_submit=False):
            username_input = st.text_input("👤 Tên đăng nhập:", placeholder="Nhập tên tài khoản...").strip()
            password_input = st.text_input("🔑 Mật khẩu:", type="password", placeholder="Nhập mật khẩu...").strip()
            remember_me = st.checkbox("Ghi nhớ đăng nhập trên thiết bị này", value=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            submitted = st.form_submit_button("🚀 ĐĂNG NHẬP", width="stretch", type="primary")

            if submitted:
                if username_input in valid_users and valid_users[username_input] == password_input:
                    auth_token = generate_auth_token(username_input, password_input)
                    st.session_state['authenticated'] = True
                    st.session_state['logged_in_user'] = username_input
                    
                    # Lưu vào Query Params
                    try:
                        if hasattr(st, "query_params"):
                            st.query_params["u"] = username_input
                            st.query_params["auth"] = auth_token
                    except Exception:
                        pass
                        
                    # Lưu vào LocalStorage
                    if remember_me:
                        st.markdown(f"""
                        <script>
                        try {{
                            localStorage.setItem("dtk_crm_user", "{username_input}");
                            localStorage.setItem("dtk_crm_token", "{auth_token}");
                        }} catch(e) {{}}
                        </script>
                        """, unsafe_allow_html=True)
                        
                    st.toast(f"✅ Chào mừng {username_input} đã đăng nhập thành công!", icon="🎉")
                    st.rerun()
                else:
                    st.error("❌ Tên đăng nhập hoặc mật khẩu không chính xác!")

    st.stop() # Dừng vẽ toàn bộ giao diện phía sau khi chưa đăng nhập

# Kiểm tra quyền truy cập ngay đầu chu trình giao diện
check_authentication()

# ==========================================
# 4. GIAO DIỆN CHÍNH (MAIN UI APP)
# ==========================================

st.title("CRM V2")
st.caption(f"Phiên bản {VERSION} · Dữ liệu local riêng của V2")
st.markdown("---")

with st.sidebar:
    st.caption(f"CRM V2 · {VERSION}")
    if not IS_CLOUD:
        st.selectbox("Cách xem ảnh", ["Thư mục Windows", "Ảnh trên thiết bị (trình duyệt)"], key="v2_photo_mode")
    st.header("Trạm Đồng Bộ 🔄")
    if IS_CLOUD:
        st.success(f"☁️ Cloud User: **{st.session_state.get('logged_in_user', 'Admin')}**")
    else:
        st.info("💻 Chế độ: **Local (Offline-First)**")
        
    st.info("💡 Hướng dẫn:\n- Cả 2 tác vụ TẢI VỀ và UP LÊN đều có bước So sánh & Báo cáo để bạn kiểm duyệt trước khi ghi đè, đảm bảo an toàn dữ liệu.\n\n*(Ghi chú: Khối Nhà được tải bằng nút 🔄 LÀM MỚI BẢNG ở Tab 1)*")
    
    if st.button("📥 TẢI KK VỀ (Pull)", width="stretch"):
        trigger_sync_khoi_khach(direction="pull")
        
    st.markdown("<br>", unsafe_allow_html=True)
        
    if st.button("📤 UP KK LÊN (Push)", type="primary", width="stretch"):
        trigger_sync_khoi_khach(direction="push")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 TẢI TẤT CẢ TỪ CLOUD (Reset All)", width="stretch"):
        with st.spinner("Đang kéo toàn bộ dữ liệu từ Google Sheets..."):
            try:
                pull_all_data()
                st.cache_data.clear()
                st.toast("✅ Đã tải toàn bộ dữ liệu thành công!")
                st.rerun()
            except Exception as e:
                st.error(f"Lỗi: {e}")

    # Nút Đăng xuất cho bản Cloud
    if IS_CLOUD and st.session_state.get('authenticated'):
        st.markdown("---")
        if st.button("🚪 Đăng Xuất", width="stretch"):
            st.session_state['authenticated'] = False
            st.session_state.pop('logged_in_user', None)
            try:
                if hasattr(st, "query_params"):
                    st.query_params.clear()
            except Exception:
                pass
            st.markdown("""
            <script>
            try {
                localStorage.removeItem("dtk_crm_user");
                localStorage.removeItem("dtk_crm_token");
                const url = new URL(window.location.href);
                url.search = '';
                window.history.replaceState({}, document.title, url.toString());
            } catch(e) {}
            </script>
            """, unsafe_allow_html=True)
            st.rerun()

@st.fragment
def crm_main_interface():
    df_houses, df_kids, df_log = load_local_data()
    apply_created_customer_selection(df_kids)
    if 'customer_created_message' in st.session_state:
        st.success(st.session_state.pop('customer_created_message'))
    
    # Cache data for PWA when online (disabled for cloud debugging)
    if not IS_CLOUD and st.session_state.get('pwa_is_online', True):
        cache_data_for_pwa(df_houses, df_kids, df_log)
    
    # Initial data load check
    if df_houses.empty and df_kids.empty and df_log.empty:
        st.warning("🚀 Chưa có dữ liệu nào. Hãy tải dữ liệu từ Google Sheets để bắt đầu.")
        if st.button("🔄 TẢI TOÀN BỘ DỮ LIỆU TỪ GOOGLE SHEETS", type="primary", width="stretch"):
            with st.spinner("Đang tải toàn bộ dữ liệu..."):
                try:
                    pull_all_data()
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Lỗi tải dữ liệu: {e}")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Tải Khối Nhà", width="stretch"):
                with st.spinner("Đang tải Khối Nhà..."):
                    try:
                        pull_khoi_nha()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi tải Khối Nhà: {e}")
        
        with col2:
            if st.button("📥 Tải Khối Khách", width="stretch"):
                with st.spinner("Đang tải Khối Khách..."):
                    try:
                        pull_khoi_khach_va_log()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi tải Khối Khách: {e}")
        
        with col3:
            if st.button("📝 Tải Nhật Ký", width="stretch"):
                with st.spinner("Đang tải Nhật Ký..."):
                    try:
                        pull_khoi_khach_va_log()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi tải Nhật Ký: {e}")
        
        st.info("💡 Hoặc sử dụng các nút đồng bộ trong sidebar bên trái")
    
    if 'app_mode' not in st.session_state:
        st.session_state['app_mode'] = 'GUI_KHACH'
    is_tim_mode = st.session_state['app_mode'] == 'TIM_KHACH'

    tab1, tab2, tab3 = st.tabs(["🎯 Khớp Nhu Cầu", "👥 Danh Sách MyKID", "📝 Nhật Ký Zalo (Dashboard)"])

    with tab1:
        st.header("🎯 Gợi ý nhà phù hợp cho khách" if not is_tim_mode else "🎯 Chọn Siêu Phẩm (Tìm Khách)")
        
        if df_houses.empty or df_kids.empty:
            st.warning("Thiếu dữ liệu nguồn (Khối Nhà hoặc Khối Khách).")
            if st.button("🔄 Tải toàn bộ dữ liệu từ Google Sheets", width="stretch"):
                with st.spinner("Đang tải toàn bộ dữ liệu..."):
                    try:
                        pull_all_data()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi tải dữ liệu: {e}")
        else:
            # 1. CHUẨN BỊ DANH SÁCH KHÁCH HÀNG & PHÂN LOẠI
            plk_unique = sorted([p for p in df_kids['PLK'].astype(str).str.strip().str.upper().unique() if p and p.lower() not in ['nan', 'none']])
            filter_options = ["Tất cả (A,B,C)"] + [f"Khách {p}" for p in plk_unique if p != 'D'] + ["Khách D (Đã bỏ)"]
            
            if 'last_saved_kid' not in st.session_state:
                st.session_state['last_saved_kid'] = ""
                if os.path.exists(FILE_LAST_KID):
                    try:
                        with open(FILE_LAST_KID, "r", encoding="utf-8") as f:
                            st.session_state['last_saved_kid'] = f.read().strip()
                    except: pass

            # Xử lý làm sạch số liệu kho nhà
            df_h_clean = df_houses.copy()
            for col in [CONFIG_GSK_CM["NGANG"], CONFIG_GSK_CM["DAI"], CONFIG_GSK_CM["GIA"]]:
                if col in df_h_clean.columns: df_h_clean[col] = clean_numeric(df_h_clean[col])
            
            pl_col = CONFIG_GSK_CM["PL"]
            if pl_col in df_h_clean.columns:
                active_houses = df_h_clean[df_h_clean[pl_col].astype(str).str.strip().str.upper().isin(['TAR', 'HID', 'A'])]
            else:
                active_houses = df_h_clean

            districts = active_houses[CONFIG_GSK_CM["QUAN"]].astype(str).str.strip().str.title().unique().tolist()

            # =========================================================
            # PHÂN NHÁNH GIAO DIỆN: CLOUD (FULL-WIDTH) vs LOCAL (2 CỘT)
            # =========================================================
            if IS_CLOUD:
                # -----------------------------------------------------
                # GIAO DIỆN CLOUD: BẢNG NHÀ FULL-WIDTH TRÊN, BỘ LỌC DƯỚI
                # -----------------------------------------------------
                st.subheader("1. Chọn khách" if not is_tim_mode else "1. Rổ hàng (Đã Mở Khóa)")
                filter_col, select_col = st.columns([1, 2.5])
                
                selected_filter = filter_col.selectbox("Lọc mức độ:", filter_options, disabled=is_tim_mode, key="cloud_plk_filter")
                
                if selected_filter == "Tất cả (A,B,C)":
                    df_kids_active = df_kids[df_kids['PLK'].astype(str).str.strip().str.upper() != 'D'].copy()
                elif selected_filter == "Khách D (Đã bỏ)":
                    df_kids_active = df_kids[df_kids['PLK'].astype(str).str.strip().str.upper() == 'D'].copy()
                else:
                    target_plk = selected_filter.replace("Khách ", "").strip()
                    df_kids_active = df_kids[df_kids['PLK'].astype(str).str.strip().str.upper() == target_plk].copy()
                
                kid_mapping = {}
                for _, row in df_kids_active.iterrows():
                    k = str(row.get('KID', '')).strip()
                    plk = str(row.get('PLK', '')).strip().upper()
                    ttk = str(row.get('thongtin_KID', '')).strip()
                    plk_str = f"({plk})" if plk else ""
                    display_str = f"{k}{plk_str}. {ttk}"
                    kid_mapping[display_str] = k
                    
                kid_list = list(kid_mapping.keys())
                if not kid_list:
                    select_col.warning(f"Không có {selected_filter.lower()}.")
                    st.stop()
                    
                selectbox_key = f"kid_selectbox_{selected_filter}"
                if selectbox_key not in st.session_state or st.session_state[selectbox_key] not in kid_list:
                    default_val = kid_list[0]
                    if st.session_state.get('last_saved_kid'):
                        for display_name in kid_list:
                            if kid_mapping[display_name] == st.session_state['last_saved_kid']:
                                default_val = display_name
                                break
                    st.session_state[selectbox_key] = default_val

                selected_kid_str = select_col.selectbox(
                    "Đang chăm sóc:", 
                    kid_list, 
                    disabled=is_tim_mode, 
                    key=selectbox_key
                )
                
                kid_id = kid_mapping[selected_kid_str]
                
                if st.session_state['last_saved_kid'] != kid_id:
                    try:
                        with open(FILE_LAST_KID, "w", encoding="utf-8") as f:
                            f.write(str(kid_id))
                        st.session_state['last_saved_kid'] = kid_id
                    except: pass
                
                kid_row = df_kids[df_kids['KID'].astype(str).str.strip() == str(kid_id)].iloc[0]
                
                if not is_tim_mode:
                    ghi_chu_text = str(kid_row.get('ghi_chu', '')).strip()
                    if ghi_chu_text and ghi_chu_text.lower() not in ['nan', 'none', 'null', '<na>']:
                        st.info(f"📝 **Ghi chú / Lịch sử xem:**\n\n{ghi_chu_text}")

                blk_str = str(kid_row.get('bo_loc_KID', '')).strip()
                if blk_str.lower() in ['nan', 'none', '']:
                    blk_str = str(kid_row.get('thongtin_KID', '')).strip()
                
                if ('active_kid' not in st.session_state or 
                    st.session_state.active_kid != kid_id or 
                    st.session_state.get('active_blk') != blk_str):
                    
                    st.session_state.active_kid = kid_id
                    st.session_state.active_blk = blk_str
                    
                    if not is_tim_mode:
                        prefs = parse_blk(blk_str)
                        st.session_state.f_min_gia = float(prefs.get('min_gia', 0.0))
                        parsed_max_gia = float(prefs.get('max_gia', 0.0))
                        st.session_state.f_max_gia = parsed_max_gia if parsed_max_gia > 0 else 100.0
                        st.session_state.f_ngang = float(prefs.get('min_ngang', 0.0))
                        st.session_state.f_min_pn = float(prefs.get('min_pn', 0.0)) 
                        st.session_state.f_min_tang = float(prefs.get('min_tang', 0.0)) 
                        st.session_state.f_min_dt = float(prefs.get('min_dt', 0.0)) 
                        
                        q_codes = list(prefs.get('quan_phuong', {}).keys())
                        st.session_state.f_quan = [REV_MAP_QUAN.get(q, q) for q in q_codes]
                        st.session_state.f_phuong = [p for sub in prefs.get('quan_phuong', {}).values() for p in sub]
                        st.session_state.f_tags = prefs.get('tags', [])

                suffix = "tim" if is_tim_mode else str(kid_id)

                # Lấy giá trị bộ lọc hiện tại
                min_gia = float(st.session_state.get(f"mg_{suffix}", st.session_state.f_min_gia))
                max_gia = float(st.session_state.get(f"xg_{suffix}", st.session_state.f_max_gia))
                
                valid_default_q = [q for q in st.session_state.f_quan if q in districts]
                sel_q = st.session_state.get(f"q_{suffix}", valid_default_q)
                
                list_p = active_houses[active_houses[CONFIG_GSK_CM["QUAN"]].str.title().isin(sel_q)][CONFIG_GSK_CM["PHUONG"]].astype(str).str.replace(r'\.0$', '', regex=True).unique().tolist() if sel_q else []
                valid_default_p = [p for p in st.session_state.f_phuong if p in list_p]
                sel_p = st.session_state.get(f"p_{suffix}", valid_default_p)
                
                min_n = float(st.session_state.get(f"mn_{suffix}", st.session_state.f_ngang))
                min_pn = float(st.session_state.get(f"mpn_{suffix}", st.session_state.f_min_pn))
                min_tang = float(st.session_state.get(f"mtg_{suffix}", st.session_state.get('f_min_tang', 0.0)))
                min_dt = float(st.session_state.get(f"mdt_{suffix}", st.session_state.f_min_dt))

                f_mat = bool(st.session_state.get(f"mat_{suffix}", "MAT" in st.session_state.f_tags))
                f_hxt = bool(st.session_state.get(f"hxt_{suffix}", "HXT" in st.session_state.f_tags))
                f_hxh = bool(st.session_state.get(f"hxh_{suffix}", "HXH" in st.session_state.f_tags))
                f_hbg = bool(st.session_state.get(f"hbg_{suffix}", "HBG" in st.session_state.f_tags))

                f_tma = bool(st.session_state.get(f"tma_{suffix}", "TMA" in st.session_state.f_tags))
                f_ntc = bool(st.session_state.get(f"ntc_{suffix}", "NTC" in st.session_state.f_tags))
                f_klp = bool(st.session_state.get(f"klp_{suffix}", "KLP" in st.session_state.f_tags))
                f_2mt = bool(st.session_state.get(f"2mt_{suffix}", "2MT" in st.session_state.f_tags))
                f_cgo = bool(st.session_state.get(f"cgo_{suffix}", "CGO" in st.session_state.f_tags))
                f_ttt = bool(st.session_state.get(f"ttt_{suffix}", "TTT" in st.session_state.f_tags))
                f_dtt = bool(st.session_state.get(f"dtt_{suffix}", "DTT" in st.session_state.f_tags))

                # --- 3. BẢNG KẾT QUẢ TÌM KIẾM (FULL-WIDTH TRÀN VIỀN) ---
                st.subheader("3. Kết quả tìm kiếm (Kho Hàng Phù Hợp)")
                args = (min_gia, max_gia, sel_q, sel_p, min_n, min_pn, min_tang, min_dt, f_tma, f_ntc, f_klp, f_ttt, f_dtt, f_2mt, f_cgo, f_mat, f_hxt, f_hxh, f_hbg)
                results = filter_houses(df_h_clean, *args)
                
                if not results.empty:
                    st.success(f"🔍 Tìm thấy **{len(results)}** căn thỏa tiêu chí!")
                    edited_df = render_aggrid(results, df_log, kid_id)
                    
                    st.divider()
                    st.subheader("4. Tác vụ xử lý")
                    
                    u_key = CONFIG_GSK_CM["UID"]
                    selected_uids = edited_df[edited_df['Trạng thái'] == '🔘 Đã chọn'][u_key].tolist()
                    
                    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)
                    
                    with btn_col1:
                        if st.button("🔄 LÀM MỚI BẢNG", width="stretch"):
                            pull_latest_houses_only()
                            st.cache_data.clear()
                            st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                            st.rerun()
                            
                    with btn_col2:
                        if st.button("💾 LƯU BỘ LỌC", width="stretch", disabled=is_tim_mode):
                            d_qp = {}
                            for q in sel_q:
                                q_code = MAP_QUAN.get(q, f"Q{q.replace('Quận ', '').replace(' ', '').upper()}")
                                d_qp[q_code] = [str(p) for p in sel_p]
                            
                            tags = [t for t, v in zip(["MAT","HXT","HXH","HBG","TMA","NTC","KLP","TTT","DTT","2MT","CGO"], 
                                                      [f_mat, f_hxt, f_hxh, f_hbg, f_tma, f_ntc, f_klp, f_ttt, f_dtt, f_2mt, f_cgo]) if v]
                            
                            old_blk = str(df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'bo_loc_KID'].values[0])
                            if not old_blk or old_blk == 'nan': 
                                old_blk = str(df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'thongtin_KID'].values[0])
                            
                            name_kh = parse_blk(old_blk).get('ten', 'Khach')
                            new_blk = build_blk(name_kh, min_gia, max_gia, d_qp, min_n, min_pn, min_tang, min_dt, tags)
                            
                            df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'bo_loc_KID'] = new_blk
                            df_kids.to_csv(FILE_KID, index=False)
                            st.toast("✅ Đã lưu bộ lọc thành công!")
                            
                    with btn_col3:
                        if st.button("📤 GỬI KHÁCH", type="primary" if not is_tim_mode else "secondary", width="stretch"):
                            if is_tim_mode:
                                st.session_state['app_mode'] = 'GUI_KHACH'
                                st.session_state['active_kid'] = ""
                                st.rerun()
                            else:
                                if len(selected_uids) == 0:
                                    st.warning("⚠️ Vui lòng click chọn (🔘) ít nhất 1 căn nhà!")
                                else:
                                    removed_bl_count = 0
                                    if not df_log.empty:
                                        for uid in selected_uids:
                                            bl_idx = df_log[(df_log.iloc[:, 0].astype(str).str.strip() == str(kid_id)) & 
                                                          (df_log.iloc[:, 1].astype(str).str.strip() == str(uid)) &
                                                          (df_log.iloc[:, 4].astype(str).str.strip() == 'black_list')].index
                                            if len(bl_idx) > 0:
                                                df_log = df_log.drop(bl_idx[0])
                                                removed_bl_count += 1
                                        
                                        if removed_bl_count > 0:
                                            df_log.to_csv(FILE_LOG, index=False)
                                    
                                    schedule_dict = {}
                                    for uid in selected_uids:
                                        schedule_dict[uid] = st.session_state.get(f"d_{uid}", datetime.now().date())
                                        
                                    d_qp = {}
                                    for q in sel_q:
                                        q_code = MAP_QUAN.get(q, f"Q{q.replace('Quận ', '').replace(' ', '').upper()}")
                                        d_qp[q_code] = [str(p) for p in sel_p]
                                    
                                    tags = [t for t, v in zip(["MAT","HXT","HXH","HBG","TMA","NTC","KLP","TTT","DTT","2MT","CGO"], 
                                                              [f_mat, f_hxt, f_hxh, f_hbg, f_tma, f_ntc, f_klp, f_ttt, f_dtt, f_2mt, f_cgo]) if v]
                                    kid_row = df_kids[df_kids['KID'].astype(str).str.strip() == str(kid_id)]
                                    if not kid_row.empty:
                                        ttk_col = next((c for c in df_kids.columns if 'thongtin' in c.lower() or 'ttk' in c.lower()), df_kids.columns[1])
                                        ttk_value = str(kid_row[ttk_col].values[0])
                                        name_kh = ttk_value.split('.')[0] if '.' in ttk_value else ttk_value
                                    else:
                                        name_kh = str(kid_id)
                                    
                                    new_blk = build_blk(name_kh, min_gia, max_gia, d_qp, min_n, min_pn, min_tang, min_dt, tags)
                                    df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'bo_loc_KID'] = new_blk
                                    df_kids.to_csv(FILE_KID, index=False)
                                    
                                    is_success = save_pending_logs(schedule_dict, kid_id, df_kids)
                                    if is_success:
                                        st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                                        st.rerun()
                    
                    with btn_col4:
                        if st.button("🔴 BLACK LIST", type="secondary", width="stretch"):
                            if is_tim_mode:
                                st.warning("⚠️ Vui lòng chọn khách hàng trước!")
                            else:
                                if len(selected_uids) == 0:
                                    st.warning("⚠️ Vui lòng click chọn (🔘) ít nhất 1 căn nhà!")
                                else:
                                    if not df_log.empty:
                                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        for uid in selected_uids:
                                            existing_idx = df_log[(df_log.iloc[:, 0].astype(str).str.strip() == str(kid_id)) & 
                                                              (df_log.iloc[:, 1].astype(str).str.strip() == str(uid))].index
                                            
                                            if len(existing_idx) > 0:
                                                df_log.loc[existing_idx[0], df_log.columns[4]] = "black_list"
                                                df_log.loc[existing_idx[0], df_log.columns[5]] = current_time
                                            else:
                                                new_row = {df_log.columns[0]: str(kid_id), 
                                                          df_log.columns[1]: str(uid),
                                                          df_log.columns[2]: "",
                                                          df_log.columns[3]: "",
                                                          df_log.columns[4]: "black_list",
                                                          df_log.columns[5]: current_time}
                                                df_log = pd.concat([df_log, pd.DataFrame([new_row])], ignore_index=True)
                                        
                                        df_log.to_csv(FILE_LOG, index=False)
                                        st.toast(f"✅ Đã thêm {len(selected_uids)} nhà vào Black List!")
                                        st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                                        st.rerun()
                                    else:
                                        st.warning("⚠️ Chưa có dữ liệu log!")

                    with btn_col5:
                        if st.button("🎯 TÌM KHÁCH", type="primary" if is_tim_mode else "secondary", width="stretch"):
                            if not is_tim_mode:
                                st.session_state['app_mode'] = 'TIM_KHACH'
                                st.session_state.f_min_gia = 0.0
                                st.session_state.f_max_gia = 1000.0 
                                st.session_state.f_ngang = 0.0
                                st.session_state.f_min_pn = 0.0
                                st.session_state.f_min_tang = 0.0
                                st.session_state.f_min_dt = 0.0
                                st.session_state.f_quan = []
                                st.session_state.f_phuong = []
                                st.session_state.f_tags = []
                                st.rerun()
                            else:
                                if not selected_uids:
                                    st.warning("⚠️ Vui lòng click chọn (🔘) ít nhất 1 căn nhà trước!")
                                else:
                                    selected_houses_df = results[results[u_key].isin(selected_uids)]
                                    dialog_chon_khach_cho_nha(selected_houses_df, df_kids, df_log)
                    
                    if not is_tim_mode:
                        if selected_uids:
                            st.write("🗓️ **Chọn ngày hẹn cho các căn sắp gửi:**")
                            original_selected = results[results[u_key].isin(selected_uids)]
                            for _, row in original_selected.iterrows():
                                uid = row[u_key]
                                cols = st.columns([3, 2])
                                cols[0].write(f"🏠 {row[CONFIG_GSK_CM['SONHA']]} {row[CONFIG_GSK_CM['TENDUONG']]} - {row[CONFIG_GSK_CM['GIA']]}T")
                                cols[1].date_input("Hẹn:", key=f"d_{uid}", label_visibility="collapsed")
                        else:
                            st.info("💡 Đang ở chế độ chăm sóc. Bấm 🔘 trên bảng để đưa nhà vào khay gửi khách.")
                    else:
                        st.success("🔓 **Bảng đã được MỞ KHÓA TẤT CẢ.** Hãy tick (🔘) vào các siêu phẩm và bấm lại nút [🎯 TÌM KHÁCH] để AI chạy Matching.")

                # --- 2. TINH CHỈNH BỘ LỌC (ĐƯA XUỐNG DƯỚI BẢNG NHÀ) ---
                st.divider()
                st.subheader("⚙️ 2. Tinh chỉnh bộ lọc nhu cầu")
                if is_tim_mode:
                    st.info("🔓 Kho hàng đang mở khóa toàn bộ. Bạn có thể tự chỉnh lọc bằng tay bên dưới để khoanh vùng.")

                cf1, cf2, cf3, cf4 = st.columns(4)
                cf1.number_input("Giá từ (Tỷ)", value=st.session_state.f_min_gia, step=1.0, key=f"mg_{suffix}")
                cf2.number_input("Đến (Tỷ)", value=st.session_state.f_max_gia, step=1.0, key=f"xg_{suffix}")
                cf3.multiselect("Chọn Quận", districts, default=valid_default_q, key=f"q_{suffix}")
                cf4.multiselect("Chọn Phường", list_p, default=valid_default_p, key=f"p_{suffix}")

                cf5, cf6, cf7, cf8 = st.columns(4)
                cf5.number_input("Ngang (m)", value=st.session_state.f_ngang, step=1.0, key=f"mn_{suffix}")
                cf6.number_input("Số PN", value=int(st.session_state.f_min_pn), step=1, format="%d", key=f"mpn_{suffix}") 
                cf7.number_input("Số Tầng", value=int(st.session_state.get('f_min_tang', 0.0)), step=1, format="%d", key=f"mtg_{suffix}") 
                cf8.number_input("DT (m2)", value=float(st.session_state.f_min_dt), step=5.0, key=f"mdt_{suffix}") 

                col_vitri, col_dacdiem = st.columns(2)
                with col_vitri:
                    st.write("**📍 Vị trí (HOẶC):**")
                    p1, p2, p3, p4 = st.columns(4)
                    p1.checkbox("Mặt tiền", value="MAT" in st.session_state.f_tags, key=f"mat_{suffix}")
                    p2.checkbox("Xe Tải", value="HXT" in st.session_state.f_tags, key=f"hxt_{suffix}")
                    p3.checkbox("Xe Hơi", value="HXH" in st.session_state.f_tags, key=f"hxh_{suffix}")
                    p4.checkbox("Ba Gác", value="HBG" in st.session_state.f_tags, key=f"hbg_{suffix}")

                with col_dacdiem:
                    st.write("**💎 Đặc điểm (VÀ):**")
                    render_cloud_features(st.session_state.f_tags, suffix)

                render_add_customer_button(df_houses, df_kids, 'add_customer_cloud')

            else:
                # -----------------------------------------------------
                # GIAO DIỆN LOCAL: GIỮ NGUYÊN BỐ CỤC 2 CỘT (COL_LEFT / COL_RIGHT)
                # -----------------------------------------------------
                col_left, col_right = st.columns([1, 3])
                
                with col_left:
                    st.subheader("1. Chọn khách" if not is_tim_mode else "1. Rổ hàng (Đã Mở Khóa)")
                    
                    filter_col, select_col = st.columns([1, 2.5])
                    selected_filter = filter_col.selectbox("Lọc mức độ:", filter_options, disabled=is_tim_mode, key="local_plk_filter")
                    
                    if selected_filter == "Tất cả (A,B,C)":
                        df_kids_active = df_kids[df_kids['PLK'].astype(str).str.strip().str.upper() != 'D'].copy()
                    elif selected_filter == "Khách D (Đã bỏ)":
                        df_kids_active = df_kids[df_kids['PLK'].astype(str).str.strip().str.upper() == 'D'].copy()
                    else:
                        target_plk = selected_filter.replace("Khách ", "").strip()
                        df_kids_active = df_kids[df_kids['PLK'].astype(str).str.strip().str.upper() == target_plk].copy()
                    
                    kid_mapping = {}
                    for _, row in df_kids_active.iterrows():
                        k = str(row.get('KID', '')).strip()
                        plk = str(row.get('PLK', '')).strip().upper()
                        ttk = str(row.get('thongtin_KID', '')).strip()
                        plk_str = f"({plk})" if plk else ""
                        display_str = f"{k}{plk_str}. {ttk}"
                        kid_mapping[display_str] = k
                        
                    kid_list = list(kid_mapping.keys())
                    if not kid_list:
                        select_col.warning(f"Không có {selected_filter.lower()}.")
                        st.stop()
                        
                    selectbox_key = f"kid_selectbox_{selected_filter}"
                    if selectbox_key not in st.session_state or st.session_state[selectbox_key] not in kid_list:
                        default_val = kid_list[0]
                        if st.session_state.get('last_saved_kid'):
                            for display_name in kid_list:
                                if kid_mapping[display_name] == st.session_state['last_saved_kid']:
                                    default_val = display_name
                                    break
                        st.session_state[selectbox_key] = default_val

                    selected_kid_str = select_col.selectbox(
                        "Đang chăm sóc:", 
                        kid_list, 
                        disabled=is_tim_mode, 
                        key=selectbox_key
                    )
                    
                    kid_id = kid_mapping[selected_kid_str]
                    if st.session_state['last_saved_kid'] != kid_id:
                        try:
                            with open(FILE_LAST_KID, "w", encoding="utf-8") as f:
                                f.write(str(kid_id))
                            st.session_state['last_saved_kid'] = kid_id
                        except: pass
                    
                    kid_row = df_kids[df_kids['KID'].astype(str).str.strip() == str(kid_id)].iloc[0]
                    if not is_tim_mode:
                        ghi_chu_text = str(kid_row.get('ghi_chu', '')).strip()
                        if ghi_chu_text and ghi_chu_text.lower() not in ['nan', 'none', 'null', '<na>']:
                            st.info(f"📝 **Ghi chú / Lịch sử xem:**\n\n{ghi_chu_text}")

                    blk_str = str(kid_row.get('bo_loc_KID', '')).strip()
                    if blk_str.lower() in ['nan', 'none', '']:
                        blk_str = str(kid_row.get('thongtin_KID', '')).strip()
                    
                    if ('active_kid' not in st.session_state or 
                        st.session_state.active_kid != kid_id or 
                        st.session_state.get('active_blk') != blk_str):
                        
                        st.session_state.active_kid = kid_id
                        st.session_state.active_blk = blk_str
                        
                        if not is_tim_mode:
                            prefs = parse_blk(blk_str)
                            st.session_state.f_min_gia = float(prefs.get('min_gia', 0.0))
                            parsed_max_gia = float(prefs.get('max_gia', 0.0))
                            st.session_state.f_max_gia = parsed_max_gia if parsed_max_gia > 0 else 100.0
                            st.session_state.f_ngang = float(prefs.get('min_ngang', 0.0))
                            st.session_state.f_min_pn = float(prefs.get('min_pn', 0.0)) 
                            st.session_state.f_min_tang = float(prefs.get('min_tang', 0.0)) 
                            st.session_state.f_min_dt = float(prefs.get('min_dt', 0.0)) 
                            
                            q_codes = list(prefs.get('quan_phuong', {}).keys())
                            st.session_state.f_quan = [REV_MAP_QUAN.get(q, q) for q in q_codes]
                            st.session_state.f_phuong = [p for sub in prefs.get('quan_phuong', {}).values() for p in sub]
                            st.session_state.f_tags = prefs.get('tags', [])

                    suffix = "tim" if is_tim_mode else str(kid_id)

                    st.subheader("2. Tinh chỉnh bộ lọc")
                    if is_tim_mode:
                        st.info("🔓 Kho hàng đang mở khóa toàn bộ. Bạn có thể tự chỉnh lọc bằng tay bên dưới để khoanh vùng.")
                        
                    min_gia = st.number_input("Giá từ (Tỷ)", value=st.session_state.f_min_gia, step=1.0, key=f"mg_{suffix}")
                    max_gia = st.number_input("Đến (Tỷ)", value=st.session_state.f_max_gia, step=1.0, key=f"xg_{suffix}")
                    
                    valid_default_q = [q for q in st.session_state.f_quan if q in districts]
                    sel_q = st.multiselect("Chọn Quận", districts, default=valid_default_q, key=f"q_{suffix}")
                    
                    list_p = active_houses[active_houses[CONFIG_GSK_CM["QUAN"]].str.title().isin(sel_q)][CONFIG_GSK_CM["PHUONG"]].astype(str).str.replace(r'\.0$', '', regex=True).unique().tolist() if sel_q else []
                    valid_default_p = [p for p in st.session_state.f_phuong if p in list_p]
                    sel_p = st.multiselect("Chọn Phường", list_p, default=valid_default_p, key=f"p_{suffix}")
                    
                    col_n1, col_n2 = st.columns(2)
                    min_n = col_n1.number_input("Ngang (m)", value=st.session_state.f_ngang, step=1.0, key=f"mn_{suffix}")
                    min_pn = col_n2.number_input("Số PN", value=int(st.session_state.f_min_pn), step=1, format="%d", key=f"mpn_{suffix}") 
                    
                    col_n3, col_n4 = st.columns(2)
                    min_tang = col_n3.number_input("Số Tầng", value=int(st.session_state.get('f_min_tang', 0.0)), step=1, format="%d", key=f"mtg_{suffix}") 
                    min_dt = col_n4.number_input("DT (m2)", value=float(st.session_state.f_min_dt), step=5.0, key=f"mdt_{suffix}") 
                    
                    st.write("**📍 Vị trí (HOẶC):**")
                    p1, p2 = st.columns(2)
                    f_mat = p1.checkbox("Mặt tiền", value="MAT" in st.session_state.f_tags, key=f"mat_{suffix}")
                    f_hxt = p2.checkbox("Xe Tải", value="HXT" in st.session_state.f_tags, key=f"hxt_{suffix}")
                    f_hxh = p1.checkbox("Xe Hơi", value="HXH" in st.session_state.f_tags, key=f"hxh_{suffix}")
                    f_hbg = p2.checkbox("Ba Gác", value="HBG" in st.session_state.f_tags, key=f"hbg_{suffix}")

                    st.write("**💎 Đặc điểm (VÀ):**")
                    t1, t2 = st.columns(2)
                    f_tma = t1.checkbox("Thang máy", value="TMA" in st.session_state.f_tags, key=f"tma_{suffix}")
                    f_ntc = t2.checkbox("Nội thất", value="NTC" in st.session_state.f_tags, key=f"ntc_{suffix}")
                    f_klp = t1.checkbox("Không lỗi", value="KLP" in st.session_state.f_tags, key=f"klp_{suffix}")
                    f_2mt = t2.checkbox("2 Mặt tiền", value="2MT" in st.session_state.f_tags, key=f"2mt_{suffix}")
                    f_cgo = t1.checkbox("Căn góc", value="CGO" in st.session_state.f_tags, key=f"cgo_{suffix}")
                    f_ttt = t2.checkbox("Tây Tứ Trạch", value="TTT" in st.session_state.f_tags, key=f"ttt_{suffix}")
                    f_dtt = t1.checkbox("Đông Tứ Trạch", value="DTT" in st.session_state.f_tags, key=f"dtt_{suffix}")

                    render_add_customer_button(df_houses, df_kids, 'add_customer_local')

                with col_right:
                    st.subheader("3. Kết quả tìm kiếm")
                    args = (min_gia, max_gia, sel_q, sel_p, min_n, min_pn, min_tang, min_dt, f_tma, f_ntc, f_klp, f_ttt, f_dtt, f_2mt, f_cgo, f_mat, f_hxt, f_hxh, f_hbg)
                    results = filter_houses(df_h_clean, *args)
                    
                    if not results.empty:
                        st.success(f"🔍 Tìm thấy **{len(results)}** căn thỏa tiêu chí!")
                        edited_df = render_aggrid(results, df_log, kid_id)
                        
                        st.divider()
                        st.subheader("4. Tác vụ xử lý")
                        
                        u_key = CONFIG_GSK_CM["UID"]
                        selected_uids = edited_df[edited_df['Trạng thái'] == '🔘 Đã chọn'][u_key].tolist()
                        
                        btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)
                        
                        with btn_col1:
                            if st.button("🔄 LÀM MỚI BẢNG", width="stretch"):
                                pull_latest_houses_only()
                                st.cache_data.clear()
                                st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                                st.rerun()
                                
                        with btn_col2:
                            if st.button("💾 LƯU BỘ LỌC", width="stretch", disabled=is_tim_mode):
                                d_qp = {}
                                for q in sel_q:
                                    q_code = MAP_QUAN.get(q, f"Q{q.replace('Quận ', '').replace(' ', '').upper()}")
                                    d_qp[q_code] = [str(p) for p in sel_p]
                                
                                tags = [t for t, v in zip(["MAT","HXT","HXH","HBG","TMA","NTC","KLP","TTT","DTT","2MT","CGO"], 
                                                          [f_mat, f_hxt, f_hxh, f_hbg, f_tma, f_ntc, f_klp, f_ttt, f_dtt, f_2mt, f_cgo]) if v]
                                
                                old_blk = str(df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'bo_loc_KID'].values[0])
                                if not old_blk or old_blk == 'nan': 
                                    old_blk = str(df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'thongtin_KID'].values[0])
                                
                                name_kh = parse_blk(old_blk).get('ten', 'Khach')
                                new_blk = build_blk(name_kh, min_gia, max_gia, d_qp, min_n, min_pn, min_tang, min_dt, tags)
                                
                                df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'bo_loc_KID'] = new_blk
                                df_kids.to_csv(FILE_KID, index=False)
                                
                                st.toast("✅ Đã lưu bộ lọc thành công!")
                                
                        with btn_col3:
                            if st.button("📤 GỬI KHÁCH", type="primary" if not is_tim_mode else "secondary", width="stretch"):
                                if is_tim_mode:
                                    st.session_state['app_mode'] = 'GUI_KHACH'
                                    st.session_state['active_kid'] = ""
                                    st.rerun()
                                else:
                                    if len(selected_uids) == 0:
                                        st.warning("⚠️ Vui lòng click chọn (🔘) ít nhất 1 căn nhà!")
                                    else:
                                        removed_bl_count = 0
                                        if not df_log.empty:
                                            for uid in selected_uids:
                                                bl_idx = df_log[(df_log.iloc[:, 0].astype(str).str.strip() == str(kid_id)) & 
                                                              (df_log.iloc[:, 1].astype(str).str.strip() == str(uid)) &
                                                              (df_log.iloc[:, 4].astype(str).str.strip() == 'black_list')].index
                                                if len(bl_idx) > 0:
                                                    df_log = df_log.drop(bl_idx[0])
                                                    removed_bl_count += 1
                                            
                                            if removed_bl_count > 0:
                                                df_log.to_csv(FILE_LOG, index=False)
                                        
                                        schedule_dict = {}
                                        for uid in selected_uids:
                                            schedule_dict[uid] = st.session_state.get(f"d_{uid}", datetime.now().date())
                                            
                                        d_qp = {}
                                        for q in sel_q:
                                            q_code = MAP_QUAN.get(q, f"Q{q.replace('Quận ', '').replace(' ', '').upper()}")
                                            d_qp[q_code] = [str(p) for p in sel_p]
                                        
                                        tags = [t for t, v in zip(["MAT","HXT","HXH","HBG","TMA","NTC","KLP","TTT","DTT","2MT","CGO"], 
                                                                  [f_mat, f_hxt, f_hxh, f_hbg, f_tma, f_ntc, f_klp, f_ttt, f_dtt, f_2mt, f_cgo]) if v]
                                        kid_row = df_kids[df_kids['KID'].astype(str).str.strip() == str(kid_id)]
                                        if not kid_row.empty:
                                            ttk_col = next((c for c in df_kids.columns if 'thongtin' in c.lower() or 'ttk' in c.lower()), df_kids.columns[1])
                                            ttk_value = str(kid_row[ttk_col].values[0])
                                            name_kh = ttk_value.split('.')[0] if '.' in ttk_value else ttk_value
                                        else:
                                            name_kh = str(kid_id)
                                        
                                        new_blk = build_blk(name_kh, min_gia, max_gia, d_qp, min_n, min_pn, min_tang, min_dt, tags)
                                        df_kids.loc[df_kids['KID'].astype(str) == str(kid_id), 'bo_loc_KID'] = new_blk
                                        df_kids.to_csv(FILE_KID, index=False)
                                        
                                        is_success = save_pending_logs(schedule_dict, kid_id, df_kids)
                                        if is_success:
                                            st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                                            st.rerun()
                        
                        with btn_col4:
                            if st.button("🔴 BLACK LIST", type="secondary", width="stretch"):
                                if is_tim_mode:
                                    st.warning("⚠️ Vui lòng chọn khách hàng trước!")
                                else:
                                    if len(selected_uids) == 0:
                                        st.warning("⚠️ Vui lòng click chọn (🔘) ít nhất 1 căn nhà!")
                                    else:
                                        if not df_log.empty:
                                            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            for uid in selected_uids:
                                                existing_idx = df_log[(df_log.iloc[:, 0].astype(str).str.strip() == str(kid_id)) & 
                                                                  (df_log.iloc[:, 1].astype(str).str.strip() == str(uid))].index
                                                
                                                if len(existing_idx) > 0:
                                                    df_log.loc[existing_idx[0], df_log.columns[4]] = "black_list"
                                                    df_log.loc[existing_idx[0], df_log.columns[5]] = current_time
                                                else:
                                                    new_row = {df_log.columns[0]: str(kid_id), 
                                                              df_log.columns[1]: str(uid),
                                                              df_log.columns[2]: "",
                                                              df_log.columns[3]: "",
                                                              df_log.columns[4]: "black_list",
                                                              df_log.columns[5]: current_time}
                                                    df_log = pd.concat([df_log, pd.DataFrame([new_row])], ignore_index=True)
                                            
                                            df_log.to_csv(FILE_LOG, index=False)
                                            st.toast(f"✅ Đã thêm {len(selected_uids)} nhà vào Black List!")
                                            st.session_state['refresh_counter'] = st.session_state.get('refresh_counter', 0) + 1
                                            st.rerun()
                                        else:
                                            st.warning("⚠️ Chưa có dữ liệu log!")

                        with btn_col5:
                            if st.button("🎯 TÌM KHÁCH", type="primary" if is_tim_mode else "secondary", width="stretch"):
                                if not is_tim_mode:
                                    st.session_state['app_mode'] = 'TIM_KHACH'
                                    st.session_state.f_min_gia = 0.0
                                    st.session_state.f_max_gia = 1000.0 
                                    st.session_state.f_ngang = 0.0
                                    st.session_state.f_min_pn = 0.0
                                    st.session_state.f_min_tang = 0.0
                                    st.session_state.f_min_dt = 0.0
                                    st.session_state.f_quan = []
                                    st.session_state.f_phuong = []
                                    st.session_state.f_tags = []
                                    st.rerun()
                                else:
                                    if not selected_uids:
                                        st.warning("⚠️ Vui lòng click chọn (🔘) ít nhất 1 căn nhà trước!")
                                    else:
                                        selected_houses_df = results[results[u_key].isin(selected_uids)]
                                        dialog_chon_khach_cho_nha(selected_houses_df, df_kids, df_log)
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        if not is_tim_mode:
                            if selected_uids:
                                st.write("🗓️ **Chọn ngày hẹn cho các căn sắp gửi:**")
                                original_selected = results[results[u_key].isin(selected_uids)]
                                for _, row in original_selected.iterrows():
                                    uid = row[u_key]
                                    cols = st.columns([3, 2])
                                    cols[0].write(f"🏠 {row[CONFIG_GSK_CM['SONHA']]} {row[CONFIG_GSK_CM['TENDUONG']]} - {row[CONFIG_GSK_CM['GIA']]}T")
                                    cols[1].date_input("Hẹn:", key=f"d_{uid}", label_visibility="collapsed")
                            else:
                                st.info("💡 Đang ở chế độ chăm sóc. Bấm 🔘 trên bảng để đưa nhà vào khay gửi khách.")
                        else:
                            st.success("🔓 **Bảng đã được MỞ KHÓA TẤT CẢ.** Hãy tick (🔘) vào các siêu phẩm và bấm lại nút [🎯 TÌM KHÁCH] để AI chạy Matching.")

    with tab2:
        st.header("👥 Danh Sách MyKID (Radar Chăm Sóc)")
        render_add_customer_button(df_houses, df_kids, 'add_customer_mykid')
        st.info("💡 Bảng tự động tính ngày tương tác cuối dựa trên Nhật ký gửi nhà. Ưu tiên tập trung Khách A (🔴) và B (🟠).")
        
        if df_kids.empty:
            st.warning("Chưa có dữ liệu khách hàng từ MyKID.")
            if st.button("📥 Tải Khối Khách từ Google Sheets", width="stretch"):
                with st.spinner("Đang tải Khối Khách..."):
                    try:
                        pull_khoi_khach_va_log()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi tải Khối Khách: {e}")
        else:
            render_tab2_mykid(df_kids, df_log)

    with tab3:
        st.header("📝 Bảng điều khiển Zalo (Zalo Dashboard)")
        st.info("💡 Click đúp vào ô 'Phản hồi' hoặc 'Ngày gửi nhà' để sửa. Bấm 1-click vào cột Trạng thái để đổi màu.")
        
        if df_log.empty:
            st.warning("Chưa có dữ liệu nhật ký.")
            if st.button("📥 Tải Nhật Ký từ Google Sheets", width="stretch"):
                with st.spinner("Đang tải Nhật Ký..."):
                    try:
                        pull_khoi_khach_va_log()
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi tải Nhật Ký: {e}")
        else:
            df_display_t3 = prepare_tab3_data(df_log, df_houses)
            render_tab3_ui(df_display_t3)

    if browser_photos_enabled(IS_CLOUD):
        render_photo_viewer()

# ==========================================
# PWA OFFLINE SYNC HANDLERS
# ==========================================
def handle_pwa_sync():
    """Xử lý đồng bộ dữ liệu từ PWA offline"""
    if st.session_state.get('pwa_offline_data'):
        offline_data = st.session_state['pwa_offline_data']
        
        # Sync customers
        if offline_data.get('customers'):
            try:
                df_kids = pd.read_csv(FILE_KID, dtype=str).fillna("") if os.path.exists(FILE_KID) else pd.DataFrame()
                offline_customers = pd.DataFrame(offline_data['customers'])
                
                # Merge offline changes
                for _, offline_customer in offline_customers.iterrows():
                    kid = str(offline_customer.get('KID', '')).strip()
                    if kid and kid in df_kids['KID'].astype(str).values:
                        # Update existing customer
                        idx = df_kids[df_kids['KID'].astype(str) == kid].index[0]
                        for col in offline_customer.index:
                            if col in df_kids.columns:
                                df_kids.loc[idx, col] = offline_customer[col]
                    else:
                        # Add new customer
                        df_kids = pd.concat([df_kids, pd.DataFrame([offline_customer])], ignore_index=True)
                
                df_kids.to_csv(FILE_KID, index=False, encoding='utf-8-sig')
                st.toast("✅ Đã đồng bộ dữ liệu khách hàng từ offline!")
            except Exception as e:
                st.error(f"Lỗi sync khách hàng: {e}")
        
        # Sync houses
        if offline_data.get('houses'):
            try:
                df_houses = pd.read_csv(FILE_GSK, dtype=str).fillna("") if os.path.exists(FILE_GSK) else pd.DataFrame()
                offline_houses = pd.DataFrame(offline_data['houses'])
                
                # Merge offline changes
                for _, offline_house in offline_houses.iterrows():
                    uid = str(offline_house.get('UID', '')).strip()
                    if uid and uid in df_houses[CONFIG_GSK_CM["UID"]].astype(str).values:
                        # Update existing house
                        idx = df_houses[df_houses[CONFIG_GSK_CM["UID"]].astype(str) == uid].index[0]
                        for col in offline_house.index:
                            if col in df_houses.columns:
                                df_houses.loc[idx, col] = offline_house[col]
                
                df_houses.to_csv(FILE_GSK, index=False, encoding='utf-8-sig')
                st.toast("✅ Đã đồng bộ dữ liệu nhà từ offline!")
            except Exception as e:
                st.error(f"Lỗi sync nhà: {e}")
        
        # Sync logs
        if offline_data.get('logs'):
            try:
                df_log = pd.read_csv(FILE_LOG, dtype=str).fillna("") if os.path.exists(FILE_LOG) else pd.DataFrame()
                offline_logs = pd.DataFrame(offline_data['logs'])
                
                # Merge offline changes
                df_log = pd.concat([df_log, offline_logs], ignore_index=True)
                df_log.to_csv(FILE_LOG, index=False, encoding='utf-8-sig')
                st.toast("✅ Đã đồng bộ nhật ký từ offline!")
            except Exception as e:
                st.error(f"Lỗi sync nhật ký: {e}")
        
        # Clear offline data after sync
        st.session_state['pwa_offline_data'] = None
        st.rerun()

def cache_data_for_pwa(df_houses, df_kids, df_log):
    """Cache dữ liệu hiện tại cho PWA offline"""
    pwa_data = {
        'customers': df_kids.to_dict('records') if not df_kids.empty else [],
        'houses': df_houses.to_dict('records') if not df_houses.empty else [],
        'logs': df_log.to_dict('records') if not df_log.empty else []
    }
    
    # Gửi dữ liệu đến PWA integration script
    pwa_cache_script = f"""
    <script>
    if (window.PWAIntegration && window.PWAIntegration.cacheData) {{
        window.PWAIntegration.cacheData({json.dumps(pwa_data)});
    }}
    </script>
    """
    st.markdown(pwa_cache_script, unsafe_allow_html=True)

# Check for PWA sync request (disabled for cloud debugging)
if not IS_CLOUD and st.session_state.get('pwa_sync_request'):
    handle_pwa_sync()

crm_main_interface()
