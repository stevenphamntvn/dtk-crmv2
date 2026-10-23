"""Customer filter protocol shared by local and cloud."""
import re
import pandas as pd

def parse_blk(blk_string):
    """Giải mã chuỗi Protocol chuẩn nguyên khối (Nâng cấp thêm PNx, DTxx, và TGx)"""
    data = {"ten": "", "min_gia": 0, "max_gia": 0, "quan_phuong": {}, "min_ngang": 0, "min_pn": 0, "min_tang": 0, "min_dt": 0, "tags": []}
    if not blk_string or pd.isna(blk_string): return data
    
    blk_str = str(blk_string).strip().upper()
    parts = blk_str.split('.')
    if parts: data["ten"] = parts[0]
    
    match_gia = re.search(r'G(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)T', blk_str)
    if match_gia:
        data["min_gia"], data["max_gia"] = float(match_gia.group(1)), float(match_gia.group(2))
    
    q_parts = re.findall(r'(Q[A-Z0-9]+)(?:\(([\d,]+)\))?', blk_str)
    for q_code, p_list in q_parts:
        data["quan_phuong"][q_code] = p_list.split(',') if p_list else []
        
    match_ngang = re.search(r'N(\d+(?:\.\d+)?)M', blk_str)
    if match_ngang: data["min_ngang"] = float(match_ngang.group(1))

    match_pn = re.search(r'PN(\d+)', blk_str)
    if match_pn: data["min_pn"] = int(match_pn.group(1))
        
    match_dt = re.search(r'DT(\d+(?:\.\d+)?)', blk_str)
    if match_dt: data["min_dt"] = float(match_dt.group(1))
    
    # [NÂNG CẤP]: Bắt số tầng tối thiểu từ chuỗi TGx
    match_tang = re.search(r'TG(\d+)', blk_str)
    if match_tang: data["min_tang"] = int(match_tang.group(1))
        
    for tag in ["MAT", "HXT", "HXH", "HBG", "TMA", "KLP", "NTC", "TTT", "DTT", "2MT", "CGO"]:
        if tag in blk_str: data["tags"].append(tag)
            
    return data

def build_blk(ten_khach, min_gia, max_gia, dict_qp_codes, min_ngang, min_pn, min_tang, min_dt, tags):
    """Đóng gói chuỗi Protocol chuẩn (Có thêm Tầng)"""
    parts = [str(ten_khach)]
    parts.append(f"G{float(min_gia):g}-{float(max_gia):g}T")
    
    q_list = []
    for q_code, ps in dict_qp_codes.items():
        q_list.append(f"{q_code}({','.join(ps)})" if ps else f"{q_code}")
    if q_list: parts.append("+".join(q_list))
    
    if min_ngang > 0: parts.append(f"N{float(min_ngang):g}M")
    if min_pn > 0: parts.append(f"PN{int(min_pn)}") 
    if min_tang > 0: parts.append(f"TG{int(min_tang)}") # [NÂNG CẤP] Nạp TGx
    if min_dt > 0: parts.append(f"DT{float(min_dt):g}")
    if tags: parts.append(".".join(tags))
    return ".".join(parts)
