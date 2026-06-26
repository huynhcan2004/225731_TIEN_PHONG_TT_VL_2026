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

# =========================================================
# BỘ LỌC CHỐNG NHIỄU DỮ LIỆU (VIETNAMESE ANTI-NOISE FILTER)
# =========================================================
def build_strict_cond(alias, keyword, keyword_id):
    """
    Hàm sinh điều kiện Cypher thông minh tối ưu cho Tiếng Việt.
    - Từ đơn (Không có khoảng trắng): Bắt buộc khớp ranh giới từ (Word Boundary) để chống bão rác.
      (Áp dụng hoàn hảo cho Tứ khí: Hàn, Nhiệt, Ôn, Lương và Ngũ vị: Cay, Đắng, Ngọt...)
    - Từ ghép (Có khoảng trắng): Dùng CONTAINS linh hoạt.
    """
    if not keyword:
        return "true"
        
    if " " not in keyword:
        # Xử lý các từ đơn như 'ôn', 'hàn', 'nhiệt', 'cay', 'đắng'
        return f"""(
            toUpper({alias}.id) = '{keyword_id}' OR 
            toLower({alias}.canonical_name) = '{keyword}' OR 
            toLower({alias}.canonical_name) STARTS WITH '{keyword} ' OR 
            toLower({alias}.canonical_name) ENDS WITH ' {keyword}' OR 
            toLower({alias}.canonical_name) CONTAINS ' {keyword} '
        )"""
    else:
        # Xử lý các cụm từ ghép như 'ích mẫu', 'thương truật'
        return f"(toLower({alias}.canonical_name) CONTAINS '{keyword}' OR toUpper({alias}.id) CONTAINS '{keyword_id}')"


def build_cypher_template(intent, k1, k2="", use_vector=False):
    k1_lower = unicodedata.normalize('NFC', k1.lower().strip()).replace("'", "\\'")
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

    # =========================================================
    # MACRO 1: TRUY VẤN THEO SCHEMA (Đã phẳng hóa & Hybrid)
    # =========================================================
    if intent in SCHEMA_MAPPING:
        rel, direction, target_lbl = SCHEMA_MAPPING[intent]
        k1_clean = k1_lower.replace("bài thuốc ", "").replace("vị thuốc ", "").strip()
        cond_k1 = build_strict_cond("s", k1_clean, k1_id)
        
        arrow_left = "<-" if direction == "<-" else "-"
        arrow_right = "->" if direction == "->" else "-"

        exact_query = f"""
            MATCH (s) 
            WHERE {cond_k1}
            MATCH (s){arrow_left}[r:{rel}]{arrow_right}(t:{target_lbl})
            RETURN s.canonical_name AS ChuThe, 
                   type(r) AS QuanHe, 
                   t.canonical_name AS DoiTuong,
                   coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung,
                   coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung,
                   coalesce(r.ghi_chu, '') AS GhiChu
            ORDER BY s.canonical_name ASC
            LIMIT {MAX_RESULTS}
        """

        hybrid_query = f"""
            CALL {{
                MATCH (s) 
                WHERE {cond_k1}
                MATCH (s){arrow_left}[r:{rel}]{arrow_right}(t:{target_lbl})
                RETURN s.canonical_name AS ChuThe, type(r) AS QuanHe, t.canonical_name AS DoiTuong,
                       coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, 2.0 as score
                UNION
                CALL db.index.vector.queryNodes("{VECTOR_INDEX_NAME}", {MAX_RESULTS}, $query_vector) YIELD node as s, score
                WHERE score >= 0.93
                MATCH (s){arrow_left}[r:{rel}]{arrow_right}(t:{target_lbl})
                RETURN s.canonical_name AS ChuThe, type(r) AS QuanHe, t.canonical_name AS DoiTuong,
                       coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, score
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY CASE WHEN final_score = 2.0 THEN 0 ELSE 1 END, final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query

    # =========================================================
    # MACRO 2: MULTI_HOP TỪ VỊ THUỐC -> BÀI THUỐC -> BỆNH
    # =========================================================
    elif intent == "TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC":
        k1_clean = k1_lower.replace("bài thuốc ", "").replace("vị thuốc ", "").strip()
        cond_k1 = build_strict_cond("v", k1_clean, k1_id)
        
        exact_query = f"""
            MATCH (v:ViThuoc)
            WHERE {cond_k1}
            MATCH (v)<-[:BAO_GOM_VI_THUOC]-(b:BaiThuoc)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(t)
            WHERE (t:Benh OR t:TrieuChung)
            RETURN v.canonical_name AS ChuThe, 
                   "Tham gia bài thuốc [" + b.canonical_name + "] để chữa" AS QuanHe, 
                   t.canonical_name AS DoiTuong, 
                   coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, 
                   coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, 
                   coalesce(r.ghi_chu, '') AS GhiChu
            ORDER BY v.canonical_name ASC
            LIMIT {MAX_RESULTS}
        """
        
        hybrid_query = f"""
            CALL {{
                MATCH (v:ViThuoc)
                WHERE {cond_k1}
                MATCH (v)<-[:BAO_GOM_VI_THUOC]-(b:BaiThuoc)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(t)
                WHERE (t:Benh OR t:TrieuChung)
                RETURN v.canonical_name AS ChuThe, "Tham gia bài thuốc [" + b.canonical_name + "] để chữa" AS QuanHe, t.canonical_name AS DoiTuong, 
                       coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, 2.0 as score
                UNION
                CALL db.index.vector.queryNodes("{VECTOR_INDEX_NAME}", {MAX_RESULTS}, $query_vector) YIELD node as v, score
                WHERE score >= 0.93 AND v:ViThuoc
                MATCH (v)<-[:BAO_GOM_VI_THUOC]-(b:BaiThuoc)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(t)
                WHERE (t:Benh OR t:TrieuChung)
                RETURN v.canonical_name AS ChuThe, "Tham gia bài thuốc [" + b.canonical_name + "] để chữa" AS QuanHe, t.canonical_name AS DoiTuong, 
                       coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, score
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY CASE WHEN final_score = 2.0 THEN 0 ELSE 1 END, final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query

    # =========================================================
    # MACRO BỔ SUNG CHO CÂU HỎI BOOLEAN (XÁC NHẬN CÓ/KHÔNG)
    # =========================================================
    elif intent == "KIEM_TRA_BOOLEAN":
        k1_clean = k1_lower.replace("bài thuốc ", "").replace("vị thuốc ", "").strip()
        k2_clean = k2_lower.replace("triệu chứng ", "").replace("bệnh ", "").replace("chứng ", "").strip()
        cond_k1 = build_strict_cond("s", k1_clean, k1_id)
        cond_k2 = build_strict_cond("t", k2_clean, k2_id)
        
        exact_query = f"""
            MATCH (s)
            WHERE {cond_k1}
            MATCH (s)-[r:CO_TINH|CO_VI|QUY_KINH|CO_CONG_NANG|CO_TINH_VI_QUY_KINH|CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(t)
            WHERE {cond_k2}
            RETURN s.canonical_name AS ChuThe, 
                   "Xác nhận: " + type(r) AS QuanHe, 
                   t.canonical_name AS DoiTuong,
                   coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, 
                   coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, 
                   coalesce(r.ghi_chu, '') AS GhiChu
            LIMIT {MAX_RESULTS}
        """
        
        hybrid_query = f"""
            CALL {{
                MATCH (s)
                WHERE {cond_k1}
                MATCH (s)-[r:CO_TINH|CO_VI|QUY_KINH|CO_CONG_NANG|CO_TINH_VI_QUY_KINH|CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(t)
                WHERE {cond_k2}
                RETURN s.canonical_name AS ChuThe, "Xác nhận: " + type(r) AS QuanHe, t.canonical_name AS DoiTuong,
                       coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, 2.0 as score
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query

    # =========================================================
    # MACRO 3: TÌM THUỐC THEO BỆNH LÝ (Bản Sửa Lỗi Vét Cạn & Chuẩn hóa cột)
    # =========================================================
    elif intent in ["TIM_THUOC_CHUA_BENH", "TIM_BAI_THUOC_CHUA_BENH"]:
        primary_label = "ViThuoc" if intent == "TIM_THUOC_CHUA_BENH" else "BaiThuoc"
        k1_clean = k1_lower.replace("bệnh ", "").replace("chứng ", "").strip()
        cond_k1 = build_strict_cond("d", k1_clean, k1_id)

        exact_query = f"""
            MATCH (d:ThucThe)
            WHERE (d:Benh OR d:TrieuChung)
            AND ({cond_k1} OR any(alt IN d.aliases WHERE toLower(alt) CONTAINS '{k1_clean}'))
            MATCH (p)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]->(d)
            RETURN d.canonical_name AS ChuThe, 
                   "Được chữa bằng (" + labels(p)[0] + ")" AS QuanHe, 
                   p.canonical_name AS DoiTuong, 
                   coalesce(p.lieu_dung, r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung,
                   coalesce(p.cach_dung, r.cach_dung, 'Chưa ghi nhận') AS CachDung,
                   coalesce(p.mo_ta_tom_tat, r.ghi_chu, '') AS GhiChu
            ORDER BY CASE WHEN labels(p)[0] = '{primary_label}' THEN 1 ELSE 2 END ASC
            LIMIT {MAX_RESULTS}
        """
        
        hybrid_query = f"""
            CALL {{
                MATCH (d:ThucThe)
                WHERE (d:Benh OR d:TrieuChung)
                AND ({cond_k1} OR any(alt IN d.aliases WHERE toLower(alt) CONTAINS '{k1_clean}'))
                MATCH (p)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]->(d)
                RETURN d.canonical_name AS ChuThe, "Được chữa bằng (" + labels(p)[0] + ")" AS QuanHe, p.canonical_name AS DoiTuong, 
                       coalesce(p.lieu_dung, r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(p.cach_dung, r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(p.mo_ta_tom_tat, r.ghi_chu, '') AS GhiChu, 2.0 as score, CASE WHEN labels(p)[0] = '{primary_label}' THEN 1 ELSE 2 END as priority
                
                UNION
                
                CALL db.index.vector.queryNodes("{VECTOR_INDEX_NAME}", {MAX_RESULTS}, $query_vector) YIELD node as d, score
                WHERE any(l IN labels(d) WHERE l IN ["Benh", "TrieuChung"]) AND score >= 0.93
                MATCH (p)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]->(d)
                RETURN d.canonical_name AS ChuThe, "Được chữa bằng (" + labels(p)[0] + ")" AS QuanHe, p.canonical_name AS DoiTuong, 
                       coalesce(p.lieu_dung, r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(p.cach_dung, r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(p.mo_ta_tom_tat, r.ghi_chu, '') AS GhiChu, score, CASE WHEN labels(p)[0] = '{primary_label}' THEN 1 ELSE 2 END as priority
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, priority, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY priority ASC, CASE WHEN final_score = 2.0 THEN 0 ELSE 1 END, final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query

    # =========================================================
    # MACRO 4: TRUY VẤN NGƯỢC (Đặc tính -> Thuốc)
    # =========================================================
    elif intent == "TIM_THUOC_THEO_TINH_VI_KINH":
        k1_clean = k1_lower.replace("tính ", "").replace("vị ", "").replace("kinh ", "").strip()
        cond_k1 = build_strict_cond("t", k1_clean, k1_id)
        
        exact_query = f"""
            MATCH (t) 
            WHERE (t:TinhVi OR t:KinhMach) 
            AND {cond_k1}
            MATCH (s:ViThuoc)-[r:CO_TINH|CO_VI|QUY_KINH]->(t)
            RETURN t.canonical_name AS ChuThe, 
                   type(r) AS QuanHe, 
                   s.canonical_name AS DoiTuong, 
                   'Chưa ghi nhận' AS LieuDung, 
                   'Chưa ghi nhận' AS CachDung, 
                   '' AS GhiChu
            ORDER BY t.canonical_name ASC
            LIMIT {MAX_RESULTS}
        """
        
        hybrid_query = f"""
            CALL {{
                MATCH (t) 
                WHERE (t:TinhVi OR t:KinhMach) 
                AND {cond_k1}
                MATCH (s:ViThuoc)-[r:CO_TINH|CO_VI|QUY_KINH]->(t)
                RETURN t.canonical_name AS ChuThe, type(r) AS QuanHe, s.canonical_name AS DoiTuong, 
                       'Chưa ghi nhận' AS LieuDung, 'Chưa ghi nhận' AS CachDung, '' AS GhiChu, 2.0 as score
                UNION
                CALL db.index.vector.queryNodes("{VECTOR_INDEX_NAME}", {MAX_RESULTS}, $query_vector) YIELD node as t, score
                WHERE score >= 0.93 AND (t:TinhVi OR t:KinhMach)
                MATCH (s:ViThuoc)-[r:CO_TINH|CO_VI|QUY_KINH]->(t)
                RETURN t.canonical_name AS ChuThe, type(r) AS QuanHe, s.canonical_name AS DoiTuong, 
                       'Chưa ghi nhận' AS LieuDung, 'Chưa ghi nhận' AS CachDung, '' AS GhiChu, score
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY CASE WHEN final_score = 2.0 THEN 0 ELSE 1 END, final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query

    # =========================================================
    # MACRO 5: TRUY VẤN GIAO THOA ĐA TẦNG (Phép Giao Toán Học 2-Hops)
    # =========================================================
    elif intent == "TIM_DA_QUAN_HE": 
        cond_c1 = build_strict_cond("c1", k1_lower, k1_id)
        cond_c2 = build_strict_cond("c2", k2_lower, k2_id)
        
        exact_query = f"""
            MATCH (s:ViThuoc)
            MATCH (s)-[:CO_TINH|CO_VI|QUY_KINH|CO_CONG_NANG|CHU_TRI_BENH]->(c1) 
            WHERE {cond_c1}
            MATCH (s)-[:CO_TINH|CO_VI|QUY_KINH|CO_CONG_NANG|CHU_TRI_BENH]->(c2) 
            WHERE {cond_c2}
            RETURN s.canonical_name AS ChuThe, 
                   "Thỏa mãn đồng thời" AS QuanHe, 
                   c1.canonical_name + " và " + c2.canonical_name AS DoiTuong, 
                   'Chưa ghi nhận' AS LieuDung, 
                   'Chưa ghi nhận' AS CachDung, 
                   '' AS GhiChu
            LIMIT {MAX_RESULTS}
        """
        
        hybrid_query = f"""
            CALL {{
                MATCH (s:ViThuoc)
                MATCH (s)-[:CO_TINH|CO_VI|QUY_KINH|CO_CONG_NANG|CHU_TRI_BENH]->(c1) 
                WHERE {cond_c1}
                MATCH (s)-[:CO_TINH|CO_VI|QUY_KINH|CO_CONG_NANG|CHU_TRI_BENH]->(c2) 
                WHERE {cond_c2}
                RETURN s.canonical_name AS ChuThe, "Thỏa mãn đồng thời" AS QuanHe, c1.canonical_name + " và " + c2.canonical_name AS DoiTuong, 
                       'Chưa ghi nhận' AS LieuDung, 'Chưa ghi nhận' AS CachDung, '' AS GhiChu, 2.0 as score
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query

    # =========================================================
    # MACRO 6: TRUY VẤN CHI TIẾT CÁCH DÙNG (How-to Query)
    # =========================================================
    elif intent == "TIM_HUONG_DAN_SU_DUNG":
        if not k2_lower or k2_lower.strip() == "":
            for separator in [" chữa ", " trị ", " điều trị "]:
                if separator in k1_lower:
                    parts = k1_lower.split(separator, 1)
                    k1_lower = parts[0].strip()
                    k2_lower = parts[1].strip()
                    break

        k1_clean = k1_lower.replace("bài thuốc ", "").replace("vị thuốc ", "").strip()
        k2_clean = k2_lower.replace("triệu chứng ", "").replace("bệnh ", "").replace("chứng ", "").strip()
        cond_s = build_strict_cond("s", k1_clean, k1_id)
        cond_t = build_strict_cond("t", k2_clean, k2_id)
        
        exact_query = f"""
            MATCH (s:ThucThe)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]-(t:ThucThe)
            WHERE ({cond_s})
            AND ({cond_t})
            RETURN s.canonical_name AS ChuThe,
                   type(r) AS QuanHe,
                   t.canonical_name AS DoiTuong,
                   coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung,
                   coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung,
                   coalesce(r.ghi_chu, '') AS GhiChu
            LIMIT {MAX_RESULTS}
        """
        
        hybrid_query = f"""
            CALL {{
                MATCH (s:ThucThe)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG|CO_CONG_NANG]-(t:ThucThe)
                WHERE ({cond_s})
                AND ({cond_t})
                RETURN s.canonical_name AS ChuThe, type(r) AS QuanHe, t.canonical_name AS DoiTuong, coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, 2.0 as score
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query

    # =========================================================
    # FALLBACK: TỔNG QUAN (Vét cạn cho các câu hỏi không rõ Intent)
    # =========================================================
    else:
        cond_s = build_strict_cond("s", k1_lower, k1_id)
        
        exact_query = f"""
            MATCH (s:ThucThe) 
            WHERE {cond_s}
            OPTIONAL MATCH (s)-[r]->(t:ThucThe)
            RETURN s.canonical_name AS ChuThe, 
                   coalesce(type(r), 'Thông tin chung') AS QuanHe, 
                   coalesce(t.canonical_name, 'Không có') AS DoiTuong,
                   coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung,
                   coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung,
                   coalesce(r.ghi_chu, '') AS GhiChu
            ORDER BY s.canonical_name ASC
            LIMIT {MAX_RESULTS}
        """
        
        hybrid_query = f"""
            CALL {{
                MATCH (s:ThucThe) 
                WHERE {cond_s}
                OPTIONAL MATCH (s)-[r]->(t:ThucThe)
                RETURN s.canonical_name AS ChuThe, coalesce(type(r), 'Thông tin chung') AS QuanHe, coalesce(t.canonical_name, 'Không có') AS DoiTuong, coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, 2.0 as score
                
                UNION
                
                CALL db.index.vector.queryNodes("{VECTOR_INDEX_NAME}", {MAX_RESULTS}, $query_vector) YIELD node as s, score
                WHERE score >= 0.93
                OPTIONAL MATCH (s)-[r]->(t:ThucThe)
                RETURN s.canonical_name AS ChuThe, coalesce(type(r), 'Thông tin chung') AS QuanHe, coalesce(t.canonical_name, 'Không có') AS DoiTuong, coalesce(r.lieu_luong, r.lieu_dung, 'Chưa ghi nhận') AS LieuDung, coalesce(r.cach_dung, 'Chưa ghi nhận') AS CachDung, coalesce(r.ghi_chu, '') AS GhiChu, score
            }}
            WITH ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, max(score) as final_score
            RETURN ChuThe, QuanHe, DoiTuong, LieuDung, CachDung, GhiChu, final_score as score
            ORDER BY CASE WHEN final_score = 2.0 THEN 0 ELSE 1 END, final_score DESC
            LIMIT {MAX_RESULTS}
        """
        return hybrid_query if use_vector else exact_query