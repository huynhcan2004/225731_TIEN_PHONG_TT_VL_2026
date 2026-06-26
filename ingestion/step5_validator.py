"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 5 — FINAL GATE: NEO4J-READY VALIDATOR & SANITIZER          ║
║  Pure Python. Ontology-Driven. Self-Healing Schema.              ║
║  Tính năng: Khôi phục Confidence Score, Tính DRI & Tự vá ID lỗi  ║
║  BẢN NÂNG CẤP: Ép chuẩn Tiền tố 100%, Chữa lành Logic Điều trị   ║
║  TRIẾT LÝ: BẢO TỒN VĂN BẢN (CLAIMS) - CHUẨN HÓA ĐỊNH DANH (IDS)  ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import re
import json
import glob
import time
import copy
import sys
from dataclasses import dataclass, field
from typing import Any
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from utils.helpers import remove_accents, apply_latex_format, clean_text

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG
# ==========================================================
# Sử dụng Kiến trúc Medallion từ file settings
INPUT_DIR      = settings.DIR_SILVER_AUDITED
OUTPUT_DIR     = settings.DIR_GOLD_VALIDATED
QUARANTINE_DIR = settings.DIR_QUARANTINE
REPORT_PATH    = settings.FILE_VAL_REPORT
SUMMARY_MD_PATH= str(settings.FILE_VAL_REPORT).replace(".jsonl", "_summary_report.md")
LOG_DIR        = settings.DIR_VAL_REPAIR_LOGS
ONTOLOGY_FILE  = settings.ONTOLOGY_PATH

os.makedirs(OUTPUT_DIR,      exist_ok=True)
os.makedirs(QUARANTINE_DIR,  exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
os.makedirs(LOG_DIR,         exist_ok=True)

QUARANTINE_THRESHOLD = 70

# ==========================================================
# 2. QUẢN LÝ TỪ ĐIỂN TÁCH BIỆT (EXTERNAL ONTOLOGY)
# ==========================================================
def load_ontology():
    """Nạp hiến pháp đồ thị từ file JSON bên ngoài (Chế độ Fail-Fast)."""
    if not os.path.exists(ONTOLOGY_FILE):
        print(f"❌ LỖI CHÍ MẠNG: Không tìm thấy file từ điển tại {ONTOLOGY_FILE}")
        print(f"Vui lòng tạo file ontology.json theo chuẩn trước khi chạy Step 5.")
        sys.exit(1)
    
    with open(ONTOLOGY_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

ONTOLOGY = load_ontology()

# BẢN ĐỒ MỎ NEO (Xác thực chéo Hán Việt - Thuần Việt)
ANCHOR_MAP = {
    "cay": ["cay", "tân"], "chua": ["chua", "toan"], "ngot": ["ngọt", "cam"],
    "dang": ["đắng", "khổ"], "man": ["mặn", "hàm"], "nhat": ["nhạt", "đạm"],
    "han": ["hàn", "lạnh"], "luong": ["lương", "mát"], "binh": ["bình"],
    "on": ["ôn", "ấm"], "nhiet": ["nhiệt", "nóng"], "can": ["can", "gan"],
    "tam": ["tâm", "tim"], "ty": ["tỳ", "lá lách"], "phe": ["phế", "phổi"],
    "than": ["thận"], "tam_bao": ["tâm bào"], "tam_tieu": ["tam tiêu"],
    "dai_trang": ["đại tràng", "ruột già"], "tieu_trang": ["tiểu tràng", "ruột non"],
    "bang_quang": ["bàng quang", "bọng đái"], "vi": ["vị", "dạ dày"], 
    "dom": ["đởm", "mật"], "dan": ["đởm", "mật"]
}

# ==========================================================
# 3. TRUY VẤN & ISSUE TRACKER
# ==========================================================

@dataclass
class Issue:
    level:    str
    code:     str
    path:     str
    detail:   str
    original: str = ""
    fixed_to: str = ""

@dataclass
class ValidationResult:
    fname:    str
    score:    int = 100
    richness_score: float = 0.0
    avg_confidence: float = 0.0
    total_conf_score: float = 0.0 # Tổng điểm tin cậy
    issues:   list = field(default_factory=list)
    passed:   bool = True

    def add(self, issue: Issue):
        self.issues.append(issue)
        if issue.level == "ERROR":
            self.score = max(0, self.score - 15)
            self.passed = False
        elif issue.level == "WARNING":
            self.score = max(0, self.score - 5)

    def summary(self) -> dict:
        return {
            "fname":    self.fname,
            "score":    self.score,
            "richness": round(self.richness_score, 2),
            "avg_confidence": round(self.avg_confidence, 4),
            "passed":   self.passed,
            "errors":   sum(1 for i in self.issues if i.level == "ERROR"),
            "warnings": sum(1 for i in self.issues if i.level == "WARNING"),
            "fixed":    sum(1 for i in self.issues if i.level == "FIXED"),
            "issues":   [vars(i) for i in self.issues],
            "ts":       time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

# ==========================================================
# 4. THUẬT TOÁN KHOA HỌC: XỬ LÝ CONFIDENCE & DRI
# ==========================================================

def get_default_conf(source_id: str) -> float:
    """Trả về điểm tin cậy mặc định dựa trên nguồn nếu bị null."""
    sid = str(source_id).upper()
    if "CT_VT_VN" in sid: return 0.95  # Y văn chính thống
    if "STEP4" in sid or "AUDIT" in sid: return 0.85 # Hệ thống kiểm duyệt
    return 0.75 # Trích xuất AI chưa định danh

def process_and_score_scientific(data: dict) -> tuple[float, float, float]:
    conf_list = []
    
    for c in data.get("claims", []):
        if c.get("confidence_score") is None:
            c["confidence_score"] = get_default_conf(c.get("source", {}).get("source_id", ""))
        conf_list.append(float(c["confidence_score"]))

    for r in data.get("relationships", []):
        if r.get("confidence_score") is None:
            r["confidence_score"] = get_default_conf(r.get("source", {}).get("source_id", ""))
        conf_list.append(float(r["confidence_score"]))

    total_conf = sum(conf_list)
    avg_conf = total_conf / len(conf_list) if conf_list else 1.0

    dri = 0.0
    entity = data.get("entity", {})
    rels = data.get("relationships", [])

    if entity.get("ten_khoa_hoc"): dri += 10.0
    if entity.get("ho_thuc_vat"): dri += 5.0
    if len(entity.get("variants", [])) > 0: dri += 5.0

    claims = data.get("claims", [])
    if claims:
        dt = claims[0].get("dac_tinh_yhct", {})
        if dt.get("vi"): dri += 5.0
        if dt.get("tinh"): dri += 5.0
        if dt.get("quy_kinh"): dri += 10.0

    counts = {"HC": 0, "DL": 0, "BT": 0, "B": 0, "CN": 0}
    for r in rels:
        rt = r.get("relation_type", "")
        if rt == "CO_CHUA_HOAT_CHAT": counts["HC"] += 1
        elif rt == "CO_TAC_DUNG_DUOC_LY": counts["DL"] += 1
        elif rt == "CO_TRONG_BAI_THUOC": counts["BT"] += 1
        elif rt.startswith("CHU_TRI"): counts["B"] += 1
        elif rt == "CO_CONG_NANG": counts["CN"] += 1

    if counts["CN"] > 0 and dri < 40.0:
        dri = min(40.0, dri + (counts["CN"] * 2.0))

    score_truc3 = (min(counts["HC"], 5) * 3.0) + (min(counts["DL"], 3) * 5.0)
    dri += min(30.0, score_truc3)

    score_truc4 = (min(counts["B"], 10) * 1.5) + (min(counts["BT"], 3) * 5.0)
    dri += min(30.0, score_truc4)

    return min(100.0, dri), avg_conf, total_conf

# ==========================================================
# 5. UTILITY & VALIDATION (TÍCH HỢP TỪ ĐIỂN TỔNG QUÁT BẢN NÂNG CẤP)
# ==========================================================

def force_id_standard(id_str, target_prefix="VI_THUOC_"):
    if not id_str: return ""
    core = str(id_str).upper()
    all_known_prefixes = list(ONTOLOGY["STRICT_RELATION_MAP"].values()) + ["VI_THUOC_", "BAI_THUOC_", "BT_", "VT_", "B_THUOC_", "S_THUOC_", "TRIEU_CHUNG_", "BENH_LY_", "BENH_"]
    
    for pfx in sorted(all_known_prefixes, key=len, reverse=True):
        if core.startswith(pfx):
            core = core[len(pfx):]
            break
            
    core = remove_accents(core).strip('_')
    return f"{target_prefix}{core}"

def smart_normalize_id(raw_id, target_prefix=None):
    """Bóc vỏ không giới hạn độ dài, diệt rác nội hàm, đóng gói an toàn."""
    if not raw_id: return ""
    raw_id = remove_accents(str(raw_id).upper().strip())
    
    all_known_prefixes = ["VI_THUOC_", "BAI_THUOC_", "TRIEU_CHUNG_", "BENH_LY_", "BENH_", "THUOC_", "NHOMBENH_", "BT_", "VT_", "CN_", "HC_", "DL_", "B_", "S_", "T_", "V_", "K_", "G_"]
    
    prefix = ""
    core = raw_id
    for pfx in sorted(all_known_prefixes, key=len, reverse=True):
        if raw_id.startswith(pfx):
            prefix = pfx
            core = raw_id[len(pfx):].strip('_')
            break

    if prefix in ["VT_", "VI_THUOC_"] and target_prefix is None:
        target_prefix = "VI_THUOC_"

    syn_map = ONTOLOGY.get("SYNONYM_MAP", {})
    standard_core = syn_map.get(core, core) 

    prefix_mapping = {
        "VI_THUOC_": "VI_THUOC_", "VT_": "VI_THUOC_", "BAI_THUOC_": "BT_", "BT_": "BT_",
        "TRIEU_CHUNG_": "S_", "S_": "S_", "BENH_LY_": "B_", "BENH_": "B_", "B_": "B_",
        "CN_": "CN_", "HC_": "HC_", "DL_": "DL_", "T_": "T_", "V_": "V_", "K_": "K_", "G_": "G_"
    }
    final_prefix = target_prefix if target_prefix else prefix_mapping.get(prefix, prefix)
    
    return f"{final_prefix}{standard_core}".strip('_')

def process_node(node: Any) -> Any:
    if isinstance(node, dict): return {k: process_node(v) for k, v in node.items()}
    if isinstance(node, list): return [process_node(i) for i in node]
    if isinstance(node, str): return apply_latex_format(clean_text(node))
    return node

def validate_entity(data: dict, result: ValidationResult) -> dict:
    entity = data.get("entity")
    if not entity or not isinstance(entity, dict):
        result.add(Issue("ERROR", "MISSING_ENTITY", "entity", "Thiếu block entity"))
        return data

    etype = entity.get("entity_type", "")
    if etype not in ONTOLOGY["VALID_ENTITY_TYPES"]:
        fixed = "VI_THUOC"
        result.add(Issue("FIXED", "INVALID_ENTITY_TYPE", "entity.entity_type", f"etype '{etype}' sai → {fixed}", etype, fixed))
        entity["entity_type"] = fixed

    eid = entity.get("id", "")
    canonical_id = force_id_standard(eid, "VI_THUOC_")
    if not eid or canonical_id.split('_')[-1] in ONTOLOGY["VAGUE_IDS"]:
        result.add(Issue("ERROR", "MISSING_ID", "entity.id", f"ID rỗng/chung: '{eid}'"))
    elif eid != canonical_id:
        result.add(Issue("FIXED", "ID_UNIFICATION", "entity.id", f"Đồng nhất ID chính: {eid}->{canonical_id}", eid, canonical_id))
        entity["id"] = canonical_id

    if not entity.get("canonical_name"):
        fallback = entity.get("ten_raw") or entity.get("id", "UNKNOWN")
        result.add(Issue("FIXED", "MISSING_CANONICAL", "entity.canonical_name", f"Thêm canonical_name: {fallback}"))
        entity["canonical_name"] = fallback

    props = entity.get("properties", {})
    if isinstance(props, dict):
        for pk, pv in props.items():
            if isinstance(pv, str) and pk in ["bo_phan_dung", "che_bien_tho", "thu_hai"]:
                props[pk] = pv.lower().strip()
    entity["properties"] = props

    for sci_field in ("ten_khoa_hoc", "ho_thuc_vat"):
        val = entity.get(sci_field, "")
        if val and isinstance(val, str) and not val.startswith("$"):
            wrapped = f"${val.strip()}$"
            result.add(Issue("FIXED", "MISSING_LATEX_SCINAME", f"entity.{sci_field}", f"Bọc LaTeX: {val}->{wrapped}", val, wrapped))
            entity[sci_field] = wrapped
    return data

def validate_claims(data: dict, result: ValidationResult) -> dict:
    claims = data.get("claims", [])
    if not claims: return data
    for i, claim in enumerate(claims):
        if not isinstance(claim, dict): continue
        if not claim.get("source", {}).get("source_id"):
            result.add(Issue("ERROR", "MISSING_SOURCE_ID", f"claims[{i}].source", "Thiếu source_id"))
    return data

def validate_relationships(data: dict, result: ValidationResult) -> dict:
    """🔴 CỖ MÁY XỬ LÝ QUAN HỆ (Đã đảo trình tự: Chuẩn hóa -> Chữa Lành -> Soi Bằng Chứng)"""
    hub_id = data.get("entity", {}).get("id", "UNKNOWN")
    rels   = data.get("relationships", [])
    if not isinstance(rels, list): return data

    merged_registry = {}
    lazy_keywords = ["không tìm thấy", "không có thông tin", "không được nhắc đến"]

    for i, rel in enumerate(rels):
        if not isinstance(rel, dict): continue
        rel = copy.deepcopy(rel)
        path = f"relationships[{i}]"
        
        rt = rel.get("relation_type", "")
        to_val = str(rel.get("to", "")).strip()
        f_val = str(rel.get("from", "")).strip()
        props = rel.get("properties", {}) or {}

        # =========================================================
        # 1. CHUẨN HÓA ID TRƯỚC (Bóc rác để so khớp chính xác)
        # =========================================================
        # LỖI 3 FIX: Sử dụng smart_normalize_id để chống bỏ lọt Bài Thuốc
        raw_clean_from = smart_normalize_id(f_val)
        if raw_clean_from == smart_normalize_id(hub_id) or raw_clean_from.startswith("BT_"):
            clean_from = raw_clean_from
        else:
            clean_from = hub_id

        req_pfx = ONTOLOGY["STRICT_RELATION_MAP"].get(rt, "")
        clean_to = smart_normalize_id(to_val, target_prefix=req_pfx if req_pfx else None)
        
        if clean_to.startswith("VT_"):
            clean_to = clean_to.replace("VT_", "VI_THUOC_", 1)

        core_to = clean_to.split('_', 1)[-1].lower() if '_' in clean_to else clean_to.lower()

        # Loại bỏ các ID thuộc diện rác (VAGUE_IDS)
        if not to_val or clean_to in ONTOLOGY["VAGUE_IDS"] or core_to.upper() in ONTOLOGY["VAGUE_IDS"]: 
            result.add(Issue("FIXED", "PRUNE_VAGUE_ID", path, f"Xóa quan hệ trỏ tới rác: {clean_to}"))
            continue

        # =========================================================
        # 2. CHỮA LÀNH LOGIC (HEALING ENGINE) - Nắn lại rt và clean_to
        # =========================================================
        if rt in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"]:
            if "THUOC_" in clean_to:
                clean_to = clean_to.replace("THUOC_", "")
                core_to = clean_to.split('_', 1)[-1].lower()
                result.add(Issue("FIXED", "HEAL_HALLUCINATED_DISEASE", path, f"Chữa ID bệnh: {clean_to}"))
            if clean_to.startswith("VI_THUOC_"):
                rt = "BAO_GOM_VI_THUOC"
                
        if rt == "CO_CONG_NANG":
            if clean_to.startswith("T_"): rt = "CO_TINH"
            elif clean_to.startswith("V_"): rt = "CO_VI"
            elif clean_to.startswith("K_"): rt = "QUY_KINH"
        
        # Bẻ lái công năng tự động (VD: B_AN_THAI -> CN_AN_THAI)
        core_upper = core_to.upper()
        if core_upper.startswith(tuple(ONTOLOGY["TCM_FUNCTION_PREFIXES"])) or core_upper in ONTOLOGY["TCM_FUNCTION_EXACT_MATCH"]:
            if rt in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"]:
                clean_to, rt = f"CN_{core_upper}", "CO_CONG_NANG"
                core_to = core_upper.lower()
                result.add(Issue("FIXED", "RECLASSIFY_FUNCTION", path, f"Nắn Công năng: {clean_to}"))

        # Sanity Check bọc lót
        expected_pfx = ONTOLOGY["STRICT_RELATION_MAP"].get(rt)
        if expected_pfx and not clean_to.startswith(expected_pfx):
            if clean_to.startswith("K_"): rt = "QUY_KINH"
            elif clean_to.startswith("T_"): rt = "CO_TINH"
            elif clean_to.startswith("V_"): rt = "CO_VI"

        # =========================================================
        # 3. BỘ LỌC CHỐNG ẢO GIÁC & TỪ ĐIỂN MỎ NEO (ANTI-HALLUCINATION)
        # =========================================================
        desc = str(props.get("mo_ta_chi_tiet", "")).lower()
        if any(kw in desc for kw in lazy_keywords):
            result.add(Issue("FIXED", "KILL_LAZY_HALLUCINATION", path, f"Xóa do AI lười: {clean_to}"))
            continue 

        if rt in ["CO_TINH", "CO_VI", "QUY_KINH"]:
            fatal_str = ["không được đề cập", "suy luận", "không thấy nói", "chưa rõ quy kinh", "có thể liên quan", "không đề cập trực tiếp", "dựa trên công năng"]
            if any(s in desc for s in fatal_str):
                result.add(Issue("FIXED", "KILL_DNA_HALLUCINATION", path, f"Xóa DNA ảo giác: {clean_to}"))
                continue
            
            # Đối soát mỏ neo
            anchors = ANCHOR_MAP.get(core_to, [core_to.replace("_", " ")])
            if not any(a in desc for a in anchors):
                if rt == "QUY_KINH":
                    result.add(Issue("FIXED", "REMOVE_HALLUCINATED_MERIDIAN", path, f"Xóa quy kinh ảo: {clean_to} (ko thấy chữ {anchors})"))
                    continue
                else:
                    result.add(Issue("WARNING", "WEAK_EVIDENCE", path, f"Cảnh báo thiếu chữ bằng chứng cho {clean_to}"))

        elif rt in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG", "BAO_GOM_VI_THUOC", "CO_CONG_NANG"]:
            if "suy luận" in desc or "có lẽ" in desc:
                # Nới lỏng cho từ khóa quan trọng để giữ lại tri thức mờ
                if core_to in ["an_thai", "chua_ho", "kham_tieng", "thong_tieu"]:
                    props["mo_ta_chi_tiet"] = props.get("mo_ta_chi_tiet", "") + " (Cần kiểm chứng từ nguyên tác)"
                    result.add(Issue("WARNING", "KEEP_CLINICAL_INFERENCE", path, f"Giữ lại {clean_to} nhưng đánh dấu kiểm chứng"))
                else:
                    result.add(Issue("FIXED", "KILL_CLINICAL_HALLUCINATION", path, f"Xóa điều trị suy luận vô căn cứ: {clean_to}"))
                    continue

        # =========================================================
        # 4. HỢP NHẤT TRI THỨC (MERGE LOGIC)
        # =========================================================
        if clean_from == clean_to and rt == "BAO_GOM_VI_THUOC":
            continue

        edge_key = (clean_from, clean_to, rt)
        source_id = rel.get("source", {}).get("source_id", "UNKNOWN")
        conf = float(rel.get("confidence_score") or 0.75)

        if edge_key not in merged_registry:
            rel["from"] = clean_from
            rel["to"] = clean_to
            rel["relation_type"] = rt
            rel["source"] = {"source_id": source_id, "all_sources": [source_id]}
            rel["confidence_score"] = conf
            
            if isinstance(props, dict):
                vai_tro = props.get("vai_tro", "")
                if vai_tro and vai_tro not in ONTOLOGY["VALID_VAI_TRO"]:
                    props["vai_tro"] = "Chưa rõ"
                rel["properties"] = props
            merged_registry[edge_key] = rel
        else:
            existing = merged_registry[edge_key]
            if source_id not in existing["source"]["all_sources"]:
                existing["source"]["all_sources"].append(source_id)
                existing["source"]["source_id"] = ", ".join(sorted(existing["source"]["all_sources"]))

            existing_props = existing.get("properties", {})
            for pk, pv in props.items():
                if pv:
                    if not existing_props.get(pk):
                        existing_props[pk] = pv
                    elif pk == "mo_ta_chi_tiet" and str(pv) not in str(existing_props[pk]):
                        existing_props[pk] = f"{existing_props[pk]} | {pv}"
            existing["confidence_score"] = max(existing["confidence_score"], conf)

    # Dọn dẹp Vague Categories
    merged_rels = list(merged_registry.values())
    remedy_map = {}
    for r in merged_rels:
        if r["relation_type"] in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"]:
            remedy_map.setdefault(r["from"], []).append(r["to"].split('_', 1)[-1])

    final_rels = []
    for r in merged_rels:
        if r["relation_type"] in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"]:
            core = r["to"].split('_', 1)[-1]
            if core in ONTOLOGY["VAGUE_DISEASE_CATEGORIES"]:
                if any(t not in ONTOLOGY["VAGUE_DISEASE_CATEGORIES"] for t in remedy_map.get(r["from"], [])):
                    continue # Bỏ qua
        final_rels.append(r)

    data["relationships"] = final_rels
    return data

def validate_nodes_and_garbage_collect(data: dict) -> dict:
    """🟢 ĐẠI QUÉT RÁC: Đồng bộ ngược từ Relationships để dọn sạch Node mồ côi"""
    hub_id = data.get("entity", {}).get("id")
    rels = data.get("relationships", [])
    old_nodes = data.get("nodes", [])
    
    # LỖI 1 FIX: Gom danh sách Bài thuốc hợp lệ (có thành phần)
    valid_bts = {r.get("from") for r in rels if str(r.get("relation_type")) == "BAO_GOM_VI_THUOC"}

    # 1. Gom tất cả ID đang có mặt trong mũi tên (CÓ CHỌN LỌC)
    safe_ids = {hub_id} if hub_id else set()
    valid_rels = [] # Lọc luôn các cạnh rác

    for r in rels:
        f_id = str(r.get("from", ""))
        t_id = str(r.get("to", ""))
        
        # Nếu from là Bài thuốc nhưng không có trong valid_bts -> Bỏ qua cạnh này, không nạp vào safe_ids
        if f_id.startswith("BT_") and f_id not in valid_bts:
            continue
            
        if f_id: safe_ids.add(f_id)
        if t_id: safe_ids.add(t_id)
        valid_rels.append(r)
        
    data["relationships"] = valid_rels # Cập nhật lại mảng rels sạch
        
    # 2. Quét mảng Nodes cũ, đuổi cổ bọn mồ côi, hợp nhất ID mới
    unique_nodes = {}
    for n in old_nodes:
        nid = str(n.get("id", ""))
        if "VI_THUOC" in nid or "VT_" in nid:
            standard_nid = smart_normalize_id(nid, "VI_THUOC_")
        else:
            standard_nid = smart_normalize_id(nid)
            
        if standard_nid == hub_id:
            standard_nid = hub_id
        
        # CHỈ GIỮ LẠI NHỮNG ĐỨA NẰM TRONG VÙNG AN TOÀN
        if standard_nid in safe_ids:
            n["id"] = standard_nid
            unique_nodes[standard_nid] = n
            
    # 3. Bơm bổ sung những Node bị đổi tên ở trên Relationships mà chưa có trong mảng
    prefix_to_label = {
        "B_": "Benh", "S_": "TrieuChung", "HC_": "HoatChat", 
        "DL_": "DuocLy", "CN_": "CongNang", "BT_": "BaiThuoc", 
        "VI_THUOC_": "ViThuoc", "VT_": "ViThuoc", "T_": "Tinh", 
        "V_": "Vi", "K_": "Kinh", "NHOMBENH_": "NhomBenh", "G_": "DoiTuong"
    }
    
    for sid in safe_ids:
        if sid not in unique_nodes and sid != hub_id:
            label = "ThucThe"
            core_name = sid
            # LỖI 2 FIX: Cắt chuỗi chính xác dựa trên độ dài prefix
            for prefix, lbl in prefix_to_label.items():
                if sid.startswith(prefix):
                    label = lbl
                    core_name = sid[len(prefix):].replace("_", " ").title()
                    break
            
            if core_name == sid and "_" in sid: # Fallback
                core_name = sid.split("_", 1)[-1].replace("_", " ").title()
                
            unique_nodes[sid] = {
                "id": sid,
                "label": label,
                "properties": {"canonical_name": core_name}
            }
            
    data["nodes"] = list(unique_nodes.values())
    return data

def validate_graph_completeness(data: dict, result: ValidationResult):
    rels = data.get("relationships", [])
    all_rels = {r.get("relation_type") for r in rels}

    if not any(rt.startswith("CHU_TRI") or rt in ["CO_CONG_NANG", "CO_TAC_DUNG_DUOC_LY"] for rt in all_rels):
        result.add(Issue("WARNING", "NO_TREATMENT_EDGE", "relationships", "Đồ thị thiếu mảng Điều trị/Dược lý"))

    hub_id = data.get("entity", {}).get("id", "")
    if not any(r.get("from") == hub_id or r.get("to") == hub_id for r in rels):
        result.add(Issue("ERROR", "ISOLATED_NODE", "relationships", f"Node chính '{hub_id}' bị cô lập"))

def validate_neo4j_constraints(data: dict, result: ValidationResult):
    NEO4J_FORBIDDEN = re.compile(r'[<>"\{\}\[\]\|\\^`]')
    eid = data.get("entity", {}).get("id", "")
    if NEO4J_FORBIDDEN.search(eid):
        result.add(Issue("ERROR", "NEO4J_INVALID_CHARS", "entity.id", f"ID '{eid}' chứa ký tự cấm Neo4j"))

# ==========================================================
# 6. RUNNER & REPORT GENERATOR
# ==========================================================

def run_final_gate(filepath: str) -> tuple[dict, ValidationResult]:
    fname = os.path.basename(filepath)
    res = ValidationResult(fname=fname)
    with open(filepath, "r", encoding="utf-8") as f: data = json.load(f)
    
    data = process_node(data)
    data = validate_entity(data, res)
    data = validate_claims(data, res)
    
    # Chạy Relationship (có khả năng sinh Node mới / xóa Edge)
    data = validate_relationships(data, res)
    # Chạy Garbage Collector để dọn Nút mồ côi
    data = validate_nodes_and_garbage_collect(data)
    
    validate_graph_completeness(data, res)
    validate_neo4j_constraints(data, res)

    dri, c_score, c_sum = process_and_score_scientific(data)
    res.richness_score = dri
    res.avg_confidence = c_score
    res.total_conf_score = c_sum

    data["metadata"] = {
        "scientific_metrics": {
            "data_richness_index": round(dri, 2),
            "reliability_c_score": round(c_score, 4),
            "total_confidence_sum": round(c_sum, 2)
        },
        "validator_pass_score": res.score,
        "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    if res.score < QUARANTINE_THRESHOLD: res.passed = False
    return data, res

def generate_markdown_report(stats: dict, file_summaries: list):
    sorted_summaries = sorted(file_summaries, key=lambda x: x['richness'], reverse=True)

    md_content = f"""# 🛡️ Báo cáo Kiểm toán Đồ thị Tri thức YHCT (Step 5)
*Thời gian xuất báo cáo: {time.strftime("%Y-%m-%d %H:%M:%S")}*
*Nguồn Ontology: `{ONTOLOGY_FILE}`*

## 1. Tóm tắt Thực thi Hệ thống (System Execution Summary)
| Chỉ số | Giá trị | Mô tả |
| :--- | :--- | :--- |
| **Tổng số thực thể (Entities)** | `{stats['total']}` | Tổng số file JSON đầu vào. |
| **Đạt chuẩn Neo4j (Passed)** | `{stats['passed']}` | Tỷ lệ pass: {round((stats['passed']/max(1, stats['total']))*100, 2)}% |
| **Cách ly (Quarantine)** | `{stats['quarantine']}` | Cần review thủ công. |
| **Lỗi đã tự động sửa (Auto-fixed)**| `{stats['total_fixed']}` | Khắc phục bởi Ontology Engine. |

---

## 2. Đánh giá Chất lượng Dữ liệu (Data Quality Assessment)
### Bảng xếp hạng Thực thể theo DRI (Top Entities by Data Richness)
| Xếp hạng | Tên Thực thể (File) | DRI Score (Max 100) | C-Score (0-1) | Trạng thái |
|:---:|---|:---:|:---:|:---:|
"""
    for idx, s in enumerate(sorted_summaries):
        status_icon = "✅" if s['passed'] else "🚨"
        md_content += f"| {idx+1} | `{s['fname']}` | **{s['richness']}** | {s['avg_confidence']} | {status_icon} |\n"

    md_content += "\n---\n## 3. Nhật ký Lỗi Nghiêm trọng (Critical Error Logs)\n"
    has_quarantine = False
    for s in file_summaries:
        if not s['passed']:
            has_quarantine = True
            md_content += f"### 🚨 `{s['fname']}` (Điểm Validator: {s['score']}/100)\n"
            for iss in s['issues']:
                if iss['level'] == 'ERROR':
                    md_content += f"- **[{iss['code']}]** tại `{iss['path']}`: {iss['detail']}\n"
            md_content += "\n"
    
    if not has_quarantine:
        md_content += "*Hệ thống không ghi nhận lỗi Critical nào ở vòng kiểm duyệt cuối.* \n"

    with open(SUMMARY_MD_PATH, "w", encoding="utf-8") as f:
        f.write(md_content)

def dump_detailed_log(summary: dict):
    if summary["fixed"] > 0 or summary["errors"] > 0 or summary["warnings"] > 0:
        log_file = os.path.join(LOG_DIR, f"{summary['fname'].replace('.json', '')}_audit.log")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"=== STEP 5 REPAIR AUDIT LOG ===\n")
            f.write(f"File: {summary['fname']}\n")
            f.write(f"Timestamp: {summary['ts']}\n")
            f.write(f"Validator Score: {summary['score']}/100\n")
            f.write(f"{'-'*40}\n")
            for iss in summary["issues"]:
                f.write(f"[{iss['level']}] {iss['code']} @ {iss['path']} \n")
                f.write(f"   -> {iss['detail']}\n")
                if iss['original'] or iss['fixed_to']:
                    f.write(f"   -> Đổi từ: {iss['original']} => Thành: {iss['fixed_to']}\n")
                f.write("\n")

def run_step5():
    files = sorted(glob.glob(os.path.join(INPUT_DIR, "*.json")))
    if not files: return print("❌ Không thấy file input.")
    
    print(f"🛡️  FINAL GATE | Dict: {ONTOLOGY_FILE}")
    print(f"   Ngưỡng Pass : {QUARANTINE_THRESHOLD}/100")
    print("=" * 60)

    stats = {"total": 0, "passed": 0, "quarantine": 0, "total_fixed": 0, "total_errors": 0, "total_warnings": 0}
    file_summaries = []

    for fp in files:
        fn = os.path.basename(fp)
        try:
            data, res = run_final_gate(fp)
            dest = os.path.join(OUTPUT_DIR if res.passed else QUARANTINE_DIR, fn)
            with open(dest, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            
            summary = res.summary()
            file_summaries.append(summary)
            
            with open(REPORT_PATH, "a", encoding="utf-8") as f: f.write(json.dumps(summary, ensure_ascii=False) + "\n")
            dump_detailed_log(summary)
            
            stats["total"] += 1
            if res.passed: stats["passed"] += 1
            else: stats["quarantine"] += 1
            stats["total_fixed"] += summary["fixed"]
            stats["total_errors"] += summary["errors"]
            stats["total_warnings"] += summary["warnings"]

            print(f"{'✅ PASS' if res.passed else '🚨 FAIL'} ({res.score}/100) | DRI: {res.richness_score} | C-Score: {res.avg_confidence:.2f} | Tự sửa: {summary['fixed']} | {fn}")
            if summary["errors"] > 0:
                for iss in summary["issues"]:
                    if iss["level"] == "ERROR": print(f"   ❌ {iss['path']}: {iss['detail']}")
        except Exception as e: 
            print(f"💥 Lỗi hệ thống tại {fn}: {e}")

    generate_markdown_report(stats, file_summaries)

    print("=" * 60)
    print(f"📊 TỔNG KẾT: {stats['passed']}/{stats['total']} file sẵn sàng nạp Neo4j.")
    if stats["quarantine"] > 0: print(f"⚠️  {stats['quarantine']} file bị cách ly tại {QUARANTINE_DIR}/")
    print(f"📑 Báo cáo Khoa học (Markdown) đã tạo tại: {SUMMARY_MD_PATH}")
    print(f"🔍 Log chi tiết (Audit) lưu tại thư mục: {LOG_DIR}")

if __name__ == "__main__":
    run_step5()