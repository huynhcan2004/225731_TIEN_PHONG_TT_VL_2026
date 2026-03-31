"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 5 — FINAL GATE: NEO4J-READY VALIDATOR & SANITIZER          ║
║  Pure Python. Ontology-Driven. Self-Healing Schema.              ║
║  Tính năng: Khôi phục Confidence Score, Tính DRI & Tự vá ID lỗi  ║
║  BẢN NÂNG CẤP: Ép chuẩn Tiền tố 100%, Chữa lành Logic Điều trị   ║
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
ONTOLOGY_FILE  = settings.ONTOLOGY_PATH

os.makedirs(OUTPUT_DIR,      exist_ok=True)
os.makedirs(QUARANTINE_DIR,  exist_ok=True)
os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

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
    """
    1. Bù đắp confidence_score bị null trực tiếp vào dữ liệu (In-place mutation).
    2. Tính toán DRI (Richness) và C-Score (Reliability).
    """
    conf_list = []
    
    # --- A. Bù đắp dữ liệu null & Thu thập điểm ---
    
    # Xử lý Claims
    for c in data.get("claims", []):
        if c.get("confidence_score") is None:
            c["confidence_score"] = get_default_conf(c.get("source", {}).get("source_id", ""))
        conf_list.append(float(c["confidence_score"]))

    # Xử lý Relationships
    for r in data.get("relationships", []):
        if r.get("confidence_score") is None:
            r["confidence_score"] = get_default_conf(r.get("source", {}).get("source_id", ""))
        conf_list.append(float(r["confidence_score"]))

    # --- B. Tính toán chỉ số Tin cậy ---
    total_conf = sum(conf_list)
    avg_conf = total_conf / len(conf_list) if conf_list else 1.0

    # --- C. Tính Data Richness Index (DRI) ---
    dri = 0.0
    entity = data.get("entity", {})
    rels = data.get("relationships", [])

    # Identity (Max 20)
    if entity.get("ten_khoa_hoc"): dri += 10.0
    if entity.get("ho_thuc_vat"): dri += 5.0
    if len(entity.get("variants", [])) > 0: dri += 5.0

    # TCM Logic (Max 20)
    claims = data.get("claims", [])
    if claims:
        dt = claims[0].get("dac_tinh_yhct", {})
        if dt.get("vi"): dri += 5.0
        if dt.get("tinh"): dri += 5.0
        if dt.get("quy_kinh"): dri += 10.0

    # Modern & Clinical (Max 60)
    counts = {"HC": 0, "DL": 0, "BT": 0, "B": 0, "CN": 0}
    for r in rels:
        rt = r.get("relation_type", "")
        if rt == "CO_CHUA_HOAT_CHAT": counts["HC"] += 1
        elif rt == "CO_TAC_DUNG_DUOC_LY": counts["DL"] += 1
        elif rt == "CO_TRONG_BAI_THUOC": counts["BT"] += 1
        elif rt.startswith("CHU_TRI"): counts["B"] += 1
        elif rt == "CO_CONG_NANG": counts["CN"] += 1

    # Bổ sung điểm Công năng vào TCM Logic nếu còn dư slot
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
    """
    BẢN NÂNG CẤP: Bóc tách MỌI loại tiền tố rác để lấy lõi tuyệt đối,
    sau đó ép chết vào target_prefix để đảm bảo không bị phân mảnh đồ thị.
    Sử dụng remove_accents từ utils.helpers.
    """
    if not id_str: return ""
    core = str(id_str).upper()
    
    # Danh sách tất cả các tiền tố có thể xuất hiện do AI sáng tạo
    all_known_prefixes = list(ONTOLOGY["STRICT_RELATION_MAP"].values()) + ["VI_THUOC_", "BAI_THUOC_", "BT_", "VT_", "B_THUOC_", "S_THUOC_"]
    
    # Bóc vỏ tiền tố
    for pfx in sorted(all_known_prefixes, key=len, reverse=True): # Xếp dài xuống ngắn để bóc chính xác
        if core.startswith(pfx):
            core = core[len(pfx):]
            break
            
    # Xử lý các tiền tố lặp lại (ví dụ VT_VT_BAN_HA)
    core = remove_accents(core).strip('_')
    return f"{target_prefix}{core}"

def smart_normalize_id(raw_id, target_prefix=None):
    """
    Hàm tổng quát: Trích xuất phần lõi, tra cứu từ điển SYNONYM_MAP và ép chuẩn Prefix.
    Tự động chữa lành các lỗi do AI sinh ra (như NGOT_CAM, CAN_KINH...).
    """
    if not raw_id: return ""
    
    # Chuyển hoa và bào dấu
    raw_id = remove_accents(str(raw_id).upper().strip())
    
    # 1. Tách tiền tố và phần lõi (Ví dụ: V_NGOT_CAM -> prefix: V_, core: NGOT_CAM)
    parts = raw_id.split('_', 1)
    if len(parts) > 1 and len(parts[0]) <= 3:
        prefix = parts[0] + "_"
        core = parts[1]
    else:
        prefix = ""
        core = raw_id

    # Đánh chặn đặc biệt: Cấm dùng VT_, bắt buộc dùng VI_THUOC_
    if prefix == "VT_" and target_prefix is None:
        target_prefix = "VI_THUOC_"

    # 2. Quét màng lọc SYNONYM_MAP để diệt rác nội hàm
    syn_map = ONTOLOGY.get("SYNONYM_MAP", {})
    standard_core = syn_map.get(core, core) # Lấy giá trị chuẩn, nếu ko có giữ nguyên

    # 3. Lắp ráp lại với tiền tố mục tiêu
    final_prefix = target_prefix if target_prefix else prefix
    return f"{final_prefix}{standard_core}"

def process_node(node: Any) -> Any:
    """Sử dụng apply_latex_format và clean_text từ utils.helpers"""
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

    # BẢN NÂNG CẤP: Chuẩn hóa ngữ nghĩa (Semantic Normalization) cho Properties
    props = entity.get("properties", {})
    if isinstance(props, dict):
        for pk, pv in props.items():
            if isinstance(pv, str):
                if pk in ["bo_phan_dung", "che_bien_tho", "thu_hai"]:
                    props[pk] = pv.lower().strip() # Ép thường các thuộc tính mô tả
    entity["properties"] = props

    for sci_field in ("ten_khoa_hoc", "ho_thuc_vat"):
        val = entity.get(sci_field, "")
        if val and isinstance(val, str) and not val.startswith("$"):
            wrapped = f"${val.strip()}$"
            result.add(Issue("FIXED", "MISSING_LATEX_SCINAME", f"entity.{sci_field}", f"Bọc LaTeX: {val}->{wrapped}", val, wrapped))
            entity[sci_field] = wrapped
    return data

def validate_claims(data: dict, result: ValidationResult) -> dict:
    """
    Sửa đổi: Sử dụng hàm smart_normalize_id để TỰ ĐỘNG SỬA MỌI LỖI TÍNH/VỊ/KINH 
    dựa vào cấu hình SYNONYM_MAP thay vì chỉ Warning.
    """
    claims = data.get("claims", [])
    if not claims: return data
    
    for i, claim in enumerate(claims):
        if not isinstance(claim, dict): continue
        path_base = f"claims[{i}]"
        
        if not claim.get("source", {}).get("source_id"):
            result.add(Issue("ERROR", "MISSING_SOURCE_ID", f"{path_base}.source", "Thiếu source_id"))
        
        dac_tinh = claim.get("dac_tinh_yhct", {})
        if not dac_tinh: continue
        
        # 🚨 Tự động nắn Schema cho dac_tinh_yhct dựa trên Ontology
        field_configs = [("vi", "V_"), ("tinh", "T_"), ("quy_kinh", "K_")]
        
        for field_name, target_pfx in field_configs:
            if field_name in dac_tinh:
                vals = dac_tinh[field_name]
                if not vals: continue
                
                is_list = isinstance(vals, list)
                val_list = vals if is_list else [vals]
                fixed_list = []
                
                for v in val_list:
                    standard_id = smart_normalize_id(v, target_pfx)
                    if standard_id != v:
                        result.add(Issue("FIXED", f"REPAIR_CLAIM_{field_name.upper()}", f"{path_base}.{field_name}", f"Vá ID lỗi: {v} -> {standard_id}"))
                    fixed_list.append(standard_id)
                
                # Ghi đè lại vào data, đảm bảo không bị trùng lặp
                dac_tinh[field_name] = list(set(fixed_list)) if is_list else fixed_list[0]

    return data

def validate_relationships(data: dict, result: ValidationResult) -> dict:
    hub_id = data.get("entity", {}).get("id", "UNKNOWN")
    rels   = data.get("relationships", [])
    if not isinstance(rels, list): return data

    merged_registry = {}
    lazy_keywords = ["không tìm thấy", "không đề cập", "không có thông tin", "chưa rõ", "không được nhắc đến"]

    for i, rel in enumerate(rels):
        if not isinstance(rel, dict): continue
        rel = copy.deepcopy(rel)
        path = f"relationships[{i}]"
        
        rt = rel.get("relation_type", "")
        to_val = str(rel.get("to", "")).strip()
        props = rel.get("properties", {}) or {}
        
        # =========================================================
        # 🛡️ 1. BỘ LỌC CHỐNG ẢO GIÁC (ANTI-HALLUCINATION)
        # =========================================================
        is_hallucinated = False
        if isinstance(props, dict):
            desc = str(props.get("mo_ta_chi_tiet", "")).lower()
            
            if any(kw in desc for kw in lazy_keywords):
                result.add(Issue("FIXED", "KILL_LAZY_HALLUCINATION", path, f"Xóa quan hệ do AI báo không có thông tin: {to_val}"))
                continue 

            if to_val.startswith(("K_", "T_", "V_")):
                core_val = to_val.split('_', 1)[-1].lower()
                # Cảnh báo nhẹ nếu thuộc tính không mô tả đúng bản chất
                if core_val and core_val not in desc:
                    result.add(Issue("WARNING", "WEAK_EVIDENCE", path, f"Dữ liệu {to_val} thiếu bằng chứng trực tiếp trong mô tả"))
        
        if is_hallucinated:
            continue 

        # =========================================================
        # 🛡️ 2. CHUẨN HÓA ID BẰNG TỪ ĐIỂN TỔNG QUÁT (SMART NORMALIZE)
        # =========================================================
        f_val = rel.get("from", "")
        clean_from = hub_id if force_id_standard(f_val) == force_id_standard(hub_id) else (f"BT_{remove_accents(f_val[3:])}" if str(f_val).startswith("BT_") else hub_id)
        
        if not to_val or to_val in ONTOLOGY["VAGUE_IDS"]: continue

        # Xác định tiền tố mục tiêu từ Ontology
        req_pfx = ONTOLOGY["STRICT_RELATION_MAP"].get(rt, "")
        
        # Đưa vào cỗ máy Smart Normalize để tra cứu & cắt gọt rác
        clean_to = smart_normalize_id(to_val, target_prefix=req_pfx if req_pfx else None)
        
        # BẢN NÂNG CẤP: Đánh chặn tuyệt đối VT_ thành VI_THUOC_
        if clean_to.startswith("VT_"):
            old_to = clean_to
            clean_to = clean_to.replace("VT_", "VI_THUOC_", 1)
            result.add(Issue("FIXED", "STRICT_PREFIX_ENFORCEMENT", path, f"Ép chuẩn tiền tố Vị thuốc: {old_to} -> {clean_to}"))

        if clean_to != to_val and not to_val.startswith("VT_"):
             result.add(Issue("FIXED", "SMART_REPAIR_ID", path, f"Khắc phục ID lỗi: {to_val} -> {clean_to}"))

        core_to = clean_to.split('_', 1)[-1] if '_' in clean_to else clean_to

        # =========================================================
        # 🚨 BỘ LỌC THÉP VÀ CHỮA LÀNH LOGIC (HEALING ENGINE)
        # =========================================================
        
        # Chữa lành 1: Bệnh/Triệu chứng ảo giác chứa tên vị thuốc (VD: B_THUOC_BAN_HA)
        if rt in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"]:
            if "THUOC_" in clean_to:
                old_to = clean_to
                clean_to = clean_to.replace("THUOC_", "")
                result.add(Issue("FIXED", "HEAL_HALLUCINATED_DISEASE", path, f"Chữa ID bệnh ảo: {old_to} -> {clean_to}"))
                core_to = clean_to.split('_', 1)[-1]
                
            # Chữa lành 2: Vị thuốc chữa Vị thuốc (Chuyển thành Bao gồm vị thuốc)
            if clean_to.startswith("VI_THUOC_"):
                old_rt = rt
                rt = "BAO_GOM_VI_THUOC"
                result.add(Issue("FIXED", "HEAL_INVALID_TREATMENT", path, f"Nắn logic điều trị: {old_rt} -> {rt} vì đích là {clean_to}"))

        # Ép chuẩn Công năng trỏ nhầm
        if rt == "CO_CONG_NANG":
            if clean_to.startswith("T_"):
                rt = "CO_TINH"
                result.add(Issue("FIXED", "RECLASSIFY_NATURE", path, f"Nắn quan hệ: CO_CONG_NANG -> CO_TINH do đích là {clean_to}"))
            elif clean_to.startswith("V_"):
                rt = "CO_VI"
                result.add(Issue("FIXED", "RECLASSIFY_TASTE", path, f"Nắn quan hệ: CO_CONG_NANG -> CO_VI do đích là {clean_to}"))
            elif clean_to.startswith("K_"):
                rt = "QUY_KINH"
                result.add(Issue("FIXED", "RECLASSIFY_MERIDIAN", path, f"Nắn quan hệ: CO_CONG_NANG -> QUY_KINH do đích là {clean_to}"))
        
        # Bẻ lái công năng
        if core_to.startswith(tuple(ONTOLOGY["TCM_FUNCTION_PREFIXES"])) or core_to in ONTOLOGY["TCM_FUNCTION_EXACT_MATCH"]:
            if rt in ["CHU_TRI_BENH", "CHU_TRI_TRIEU_CHUNG"]:
                old_rt = rt
                clean_to, rt = f"CN_{core_to}", "CO_CONG_NANG"
                result.add(Issue("FIXED", "RECLASSIFY_FUNCTION", path, f"Nắn Công năng: {old_rt}->{rt}"))
                
        # =========================================================
        # 🛡️ 3. THUẬT TOÁN HỢP NHẤT TRI THỨC (MERGE LOGIC)
        # =========================================================
        # Bỏ qua quan hệ tự trỏ chính mình (Self-loop)
        if clean_from == clean_to and rt == "BAO_GOM_VI_THUOC":
            result.add(Issue("FIXED", "REMOVE_SELF_LOOP", path, f"Xóa quan hệ tự trỏ: {clean_from} -> {clean_to}"))
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

    # =========================================================
    # 🛡️ 4. HẬU XỬ LÝ (PRUNING VAGUE CATEGORIES)
    # =========================================================
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
                    result.add(Issue("FIXED", "PRUNE_VAGUE_CATEGORY", "relationships", f"Xóa bệnh chung chung đã gộp: {r['to']}"))
                    continue
        final_rels.append(r)

    data["relationships"] = final_rels
    return data

def validate_nodes(data: dict) -> dict:
    hub_id = data.get("entity", {}).get("id")
    nodes = data.get("nodes", [])
    unique_nodes = {}
    for n in nodes:
        nid = n.get("id", "")
        # Đảm bảo node mồ côi cũng được ép chuẩn VI_THUOC_
        nid_standard = force_id_standard(nid, "VI_THUOC_") if nid.startswith("VT_") else nid
        new_id = hub_id if force_id_standard(nid_standard) == force_id_standard(hub_id) else remove_accents(nid_standard)
        n["id"] = new_id
        if new_id == hub_id: n["label"] = "ViThuoc"
        unique_nodes[new_id] = n
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
    
    # 1. Clean & Validate
    data = process_node(data)
    data = validate_entity(data, res)
    data = validate_claims(data, res)
    data = validate_relationships(data, res)
    data = validate_nodes(data)
    
    validate_graph_completeness(data, res)
    validate_neo4j_constraints(data, res)

    # 2. Tính toán điểm Khoa học & Xử lý Null Confidence trực tiếp vào data
    dri, c_score, c_sum = process_and_score_scientific(data)
    res.richness_score = dri
    res.avg_confidence = c_score
    res.total_conf_score = c_sum

    # 3. Ghi đè vào Metadata của file JSON
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

if __name__ == "__main__":
    run_step5()