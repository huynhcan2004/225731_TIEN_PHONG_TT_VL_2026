import unicodedata

# Cấu hình tra cứu
MAX_RESULTS = 30 
VECTOR_INDEX_NAME = "entity_vector_index" 

def clean_id(text):
    if not text: return ""
    text = str(text).replace("Đ", "D").replace("đ", "d")
    nkfd_form = unicodedata.normalize('NFKD', text)
    no_accent = "".join([c for c in nkfd_form if not unicodedata.combining(c)])
    return no_accent.upper().replace(" ", "_")

def build_cypher_template(intent, k1, k2="", use_vector=False):
    k1_lower = k1.lower().strip().replace("'", "\\'")
    k2_lower = k2.lower().strip().replace("'", "\\'") if k2 else ""
    k1_id = clean_id(k1_lower)
    k2_id = clean_id(k2_lower)

    # Chống lỗi NLU nhận nhầm Đa điều kiện
    if intent == "TIM_DA_QUAN_HE" and not k2_lower:
        intent = "TIM_TONG_QUAN_THUOC"

    # BẢNG ÁNH XẠ SCHEMA: Intent -> (Loại Quan Hệ, Chiều Mũi Tên, Nhãn Đích)
    SCHEMA_MAPPING = {
        "TIM_TINH": ("CO_TINH|CO_TINH_VI_QUY_KINH", "->", "ThucThe"),
        "TIM_VI": ("CO_VI|CO_TINH_VI_QUY_KINH", "->", "ThucThe"),
        "TIM_QUY_KINH": ("QUY_KINH|CO_TINH_VI_QUY_KINH", "->", "ThucThe"),
        "TIM_HOAT_CHAT_CUA_THUOC": ("CO_CHUA_HOAT_CHAT", "->", "ThucThe"),
        "TIM_CONG_NANG_DUOC_LY": ("CO_CONG_NANG|CO_TAC_DUNG_DUOC_LY", "->", "ThucThe"),
        "TIM_CONG_DUNG_CUA_THUOC": ("CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG", "->", "ThucThe"),
        "TIM_THANH_PHAN_BAI_THUOC": ("BAO_GOM_VI_THUOC", "->", "ViThuoc"),
        "TIM_BAI_THUOC_CUA_THUOC": ("BAO_GOM_VI_THUOC", "<-", "BaiThuoc") 
    }

    # ---------------------------------------------------------
    # MACRO 1: TRUY VẤN CÓ DẪN HƯỚNG (THEO SCHEMA)
    # ---------------------------------------------------------
    if intent in SCHEMA_MAPPING:
        rel, _, _ = SCHEMA_MAPPING[intent] # Bỏ qua direction và target_label
        return f"""
            MATCH (s) 
            WHERE toLower(s.canonical_name) CONTAINS '{k1_lower}' 
            OR toUpper(s.id) CONTAINS '{k1_id}'
            MATCH (s)-[r:{rel}]-(t)
            RETURN s.canonical_name AS ChuThe, 
                type(r) AS QuanHe, 
                collect(DISTINCT t.canonical_name) AS KetQua
            ORDER BY s.canonical_name ASC
            LIMIT {MAX_RESULTS}
        """

    # ---------------------------------------------------------
    # MACRO BỔ SUNG CHO MULTI_HOP (Bài thuốc chứa vị thuốc chữa bệnh gì)
    # ---------------------------------------------------------
    elif intent == "TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC":
        return f"""
            MATCH (v:ViThuoc)
            WHERE toLower(v.canonical_name) CONTAINS '{k1_lower}' OR v.id CONTAINS '{k1_id}'
            MATCH (v)<-[:BAO_GOM_VI_THUOC]-(b:BaiThuoc)-[:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(benh)
            WHERE benh:Benh OR benh:TrieuChung
            RETURN v.canonical_name AS ChuThe, 
                   "Tham gia điều trị (thông qua bài thuốc)" AS QuanHe, 
                   collect(DISTINCT benh.canonical_name) AS KetQua
            ORDER BY v.canonical_name ASC
            LIMIT {MAX_RESULTS}
        """

    # ---------------------------------------------------------
    # MACRO BỔ SUNG CHO CÂU HỎI BOOLEAN (XÁC NHẬN CÓ/KHÔNG)
    # ---------------------------------------------------------
    elif intent == "KIEM_TRA_BOOLEAN":
        return f"""
            MATCH (s:ViThuoc)
            WHERE toLower(s.canonical_name) CONTAINS '{k1_lower}' OR s.id CONTAINS '{k1_id}'
            MATCH (s)-[*1..2]-(t)
            WHERE toLower(t.canonical_name) CONTAINS '{k2_lower}' OR t.id CONTAINS '{k2_id}'
            RETURN s.canonical_name AS ChuThe, 
                   "Xác nhận có đặc tính" AS QuanHe, 
                   collect(DISTINCT t.canonical_name) AS KetQua
            LIMIT {MAX_RESULTS}
        """

    # ---------------------------------------------------------
    # MACRO 2: HYBRID SEARCH (Kết hợp Exact Match + Vector Search)
    # ---------------------------------------------------------
    elif intent in ["TIM_THUOC_CHUA_BENH", "TIM_BAI_THUOC_CHUA_BENH"]:
        return f"""
            // 1. Tìm chính xác tuyệt đối theo tên hoặc bí danh (Độ ưu tiên cao nhất)
            MATCH (d:ThucThe)
            WHERE (d:Benh OR d:TrieuChung)
            AND (toLower(d.canonical_name) = '{k1_lower}' OR '{k1_lower}' IN d.aliases)
            MATCH (p)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]->(d)
            RETURN d.canonical_name as Benh, p.canonical_name as GiaiPhap, labels(p)[0] as LoaiGiaiPhap, 1.0 as score
            
            UNION
            
            // 2. Tìm theo Vector (Độ phủ rộng cho từ đồng nghĩa mờ)
            CALL db.index.vector.queryNodes("{VECTOR_INDEX_NAME}", {MAX_RESULTS}, $query_vector) YIELD node as d, score
            WHERE any(l IN labels(d) WHERE l IN ["Benh", "TrieuChung"])
            MATCH (p)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]->(d)
            RETURN d.canonical_name as Benh, p.canonical_name as GiaiPhap, labels(p)[0] as LoaiGiaiPhap, score
        """ if use_vector else f"""
            MATCH (d:ThucThe) WHERE (d:Benh OR d:TrieuChung) AND (toLower(d.canonical_name) CONTAINS '{k1_lower}' OR '{k1_lower}' IN d.aliases)
            MATCH (p)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]->(d)
            RETURN DISTINCT d.canonical_name as Benh, p.canonical_name as GiaiPhap, labels(p)[0] as LoaiGiaiPhap
            LIMIT {MAX_RESULTS}
        """

    # ---------------------------------------------------------
    # MACRO 3: TRUY VẤN NGƯỢC (Đặc tính -> Thuốc)
    # ---------------------------------------------------------
    elif intent == "TIM_THUOC_THEO_TINH_VI_KINH":
        return f"""
            // 1. Tìm nút đặc tính (Tính/Vị/Kinh) dựa trên từ khóa người dùng
            MATCH (t:ThucThe) 
            WHERE (t:TinhVi OR t:KinhMach) 
            AND (toLower(t.canonical_name) CONTAINS '{k1_lower}' OR t.id CONTAINS '{k1_id}')
            
            // 2. Tìm các Vị thuốc nối đến đặc tính đó
            MATCH (s:ViThuoc)-[r:CO_TINH|CO_VI|QUY_KINH]->(t)
            RETURN t.canonical_name AS ChuThe, 
                   type(r) AS QuanHe, 
                   collect(DISTINCT s.canonical_name) AS KetQua
            LIMIT {MAX_RESULTS}
        """

    # ---------------------------------------------------------
    # MACRO 4: TRUY VẤN GIAO THOA ĐA TẦNG (Phép Giao Toán Học 2-Hops)
    # ---------------------------------------------------------
    elif intent == "TIM_DA_QUAN_HE": 
        return f"""
            MATCH (s:ViThuoc)
            MATCH (s)-[*1..2]-(c1) WHERE toLower(c1.canonical_name) CONTAINS '{k1_lower}' OR toUpper(c1.id) CONTAINS '{k1_id}'
            MATCH (s)-[*1..2]-(c2) WHERE toLower(c2.canonical_name) CONTAINS '{k2_lower}' OR toUpper(c2.id) CONTAINS '{k2_id}'
            RETURN "Các vị thuốc" AS ChuThe, 
                   "Thỏa mãn đa điều kiện" AS QuanHe, 
                   collect(DISTINCT s.canonical_name) AS KetQua
            LIMIT {MAX_RESULTS}
        """

    # ---------------------------------------------------------
    # FALLBACK: TỔNG QUAN
    # ---------------------------------------------------------
    else:
        return f"""
            MATCH (s:ThucThe) 
            WHERE toLower(s.canonical_name) CONTAINS '{k1_lower}' OR s.id CONTAINS '{k1_id}'
            OPTIONAL MATCH (s)-[r]->(t:ThucThe)
            RETURN s.canonical_name AS ChuThe, 
                   type(r) AS QuanHe, 
                   collect(DISTINCT t.canonical_name) AS KetQua
            ORDER BY s.canonical_name ASC
            LIMIT {MAX_RESULTS}
        """