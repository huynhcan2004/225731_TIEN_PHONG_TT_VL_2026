import os
import json
import time
import random
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings

# ==========================================================
# ⚠️ THƯ VIỆN KẾT NỐI NEO4J
# ==========================================================
try:
    from langchain_community.graphs import Neo4jGraph
except ImportError:
    print("❌ Vui lòng cài đặt: pip install langchain-community neo4j")
    exit()

# ==========================================================
# 1. CẤU HÌNH HỆ THỐNG NEO4J (Đồng bộ từ Settings)
# ==========================================================
URI = settings.NEO4J_URI
USER = settings.NEO4J_USER
PWD = settings.NEO4J_PWD
DB_NAME = settings.NEO4J_DB_NAME  # Bản Neo4j Community thường dùng database mặc định là 'neo4j'

# Đồng bộ thư mục lưu trữ theo kiến trúc Medallion
OUTPUT_DIR = settings.DIR_EVALUATION
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "complex_kg_qa_dataset.json")

# ==========================================================
# 2. HỆ THỐNG TẠO CÂU HỎI TỰ ĐỘNG (4 PATTERN NÂNG CAO)
# ==========================================================
def generate_complex_dataset(limit_per_pattern=25, limit_facts=50):
    """
    Hàm sinh dữ liệu mẫu với tính năng ĐỒNG BỘ HÓA CỨNG:
    - limit_per_pattern: Số lượng câu hỏi tạo ra cho mỗi loại Pattern.
    - limit_facts: Giới hạn số lượng thực thể tối đa trong câu trả lời (Top-N).
    """
    print("🔄 Đang kết nối tới Đồ thị Neo4j...")
    try:
        graph = Neo4jGraph(url=URI, username=USER, password=PWD, database=DB_NAME)
        print("✅ Kết nối thành công! Đang tiến hành sinh bộ dữ liệu 4 Pattern...")
    except Exception as e:
        print(f"❌ Lỗi kết nối Neo4j: {e}")
        return

    dataset = []
    item_id = 1

    # =========================================================
    # PATTERN 1: SINGLE RELATION (Hỏi thuộc tính đơn)
    # Bao gồm: Tính, Vị, Quy kinh, Hoạt chất, Công năng
    # =========================================================
    print(f"⏳ Đang tạo {limit_per_pattern} câu hỏi nhóm: SINGLE RELATION...")
    query_p1 = f"""
    MATCH (v:ViThuoc)-[r:CO_VI|CO_TINH|QUY_KINH|CO_CHUA_HOAT_CHAT|CO_CONG_NANG]->(t)
    WHERE t.canonical_name IS NOT NULL AND trim(t.canonical_name) <> ""
    RETURN v.id AS entity_id, v.canonical_name AS Thuoc, type(r) AS RelType, labels(t)[0] AS Loai, collect(DISTINCT t.canonical_name) AS Facts
    ORDER BY rand() LIMIT {limit_per_pattern}
    """
    records_p1 = graph.query(query_p1)
    for rec in records_p1:
        # LỌC TRÙNG, SẮP XẾP VÀ GIỚI HẠN N DỮ LIỆU ĐẦU TIÊN
        facts = sorted(list(set(rec['Facts'])))[:limit_facts]
        if not facts: continue
        
        rel_type = rec['RelType']
        thuoc = rec['Thuoc']
        
        if rel_type == "CO_VI":
            q_text = f"Vị thuốc {thuoc} có những vị nào?"
            l_text = f"Theo y văn, vị thuốc {thuoc} có các vị sau:"
        elif rel_type == "CO_TINH":
            q_text = f"Vị thuốc {thuoc} có tính gì?"
            l_text = f"Theo y văn, vị thuốc {thuoc} có tính:"
        elif rel_type == "QUY_KINH":
            q_text = f"Vị thuốc {thuoc} quy vào những kinh nào?"
            l_text = f"Theo y văn, vị thuốc {thuoc} quy kinh:"
        elif rel_type == "CO_CHUA_HOAT_CHAT":
            q_text = f"Vị thuốc {thuoc} có chứa những hoạt chất nào?"
            l_text = f"Phân tích dược lý cho thấy {thuoc} chứa các hoạt chất:"
        else: # CO_CONG_NANG
            q_text = f"Vị thuốc {thuoc} có những công năng gì?"
            l_text = f"Trong Y học cổ truyền, {thuoc} có công năng:"

        dataset.append({
            "entity": rec['entity_id'] if rec['entity_id'] else f"VI_THUOC_{thuoc.upper().replace(' ', '_')}",
            "id": item_id,
            "pattern_type": "single_relation",
            "cypher_pattern": f"(v:ViThuoc {{canonical_name: '{thuoc}'}})-[:{rel_type}]->(t:{rec['Loai']})",
            "question": q_text,
            "lead_in": l_text,
            "expected_facts": facts,
            # Chỉ lưu danh sách từ khóa để tối ưu điểm BLEU
            "expected_answer_full": ", ".join(facts)
        })
        item_id += 1

    # =========================================================
    # PATTERN 2: MULTI-HOP (Tính chất bắc cầu: Thuốc -> Bài thuốc -> Bệnh)
    # =========================================================
    print(f"⏳ Đang tạo {limit_per_pattern} câu hỏi nhóm: MULTI HOP...")
    query_p2 = f"""
    MATCH (v:ViThuoc)<-[:BAO_GOM_VI_THUOC]-(p:BaiThuoc)-[:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(d)
    WHERE toLower(v.canonical_name) <> toLower(d.canonical_name)
      AND d.canonical_name IS NOT NULL AND trim(d.canonical_name) <> ""
    RETURN v.id AS entity_id, v.canonical_name AS Thuoc, collect(DISTINCT d.canonical_name) AS Facts
    ORDER BY rand() LIMIT {limit_per_pattern}
    """
    records_p2 = graph.query(query_p2)
    for rec in records_p2:
        # LỌC TRÙNG, SẮP XẾP VÀ GIỚI HẠN N DỮ LIỆU ĐẦU TIÊN
        facts = sorted(list(set(rec['Facts'])))[:limit_facts]
        if not facts: continue

        thuoc = rec['Thuoc']
        dataset.append({
            "entity": rec['entity_id'] if rec['entity_id'] else f"VI_THUOC_{thuoc.upper().replace(' ', '_')}",
            "id": item_id,
            "pattern_type": "multi_hop",
            "cypher_pattern": f"(v:ViThuoc {{canonical_name: '{thuoc}'}})<-[:BAO_GOM_VI_THUOC]-(b:BaiThuoc)-[:CHU_TRI_BENH]->(benh:Benh)",
            "question": f"Bài thuốc chứa vị thuốc {thuoc} thì thường dùng để chữa bệnh gì?",
            "lead_in": f"Dựa trên các bài thuốc có chứa {thuoc}, vị thuốc này tham gia điều trị:",
            "expected_facts": facts,
            # Chỉ lưu danh sách từ khóa để tối ưu điểm BLEU
            "expected_answer_full": ", ".join(facts)
        })
        item_id += 1

    # =========================================================
    # PATTERN 3: REVERSE SEARCH (Hỏi xác nhận Có/Không về đặc tính)
    # =========================================================
    print(f"⏳ Đang tạo {limit_per_pattern} câu hỏi nhóm: REVERSE SEARCH...")
    query_p3 = f"""
    MATCH (v:ViThuoc)-[r:CO_CHUA_HOAT_CHAT|CO_VI|CO_TINH|QUY_KINH]->(target)
    WHERE target.canonical_name IS NOT NULL AND trim(target.canonical_name) <> ""
    RETURN v.id AS entity_id, v.canonical_name AS Thuoc, type(r) AS RelType, target.canonical_name AS Fact, labels(target)[0] AS Loai
    ORDER BY rand() LIMIT {limit_per_pattern}
    """
    records_p3 = graph.query(query_p3)
    for rec in records_p3:
        rel_type = rec['RelType']
        thuoc = rec['Thuoc']
        fact = rec['Fact'] # Câu hỏi dạng xác nhận (Yes/No) nên chỉ có 1 fact
        loai = rec['Loai']
        
        if rel_type == "CO_CHUA_HOAT_CHAT":
            q_text = f"Vị thuốc {thuoc} có chứa hoạt chất {fact} không?"
            l_text = f"Xác nhận về thành phần của {thuoc}:"
        elif rel_type in ["CO_VI", "CO_TINH"]:
            q_text = f"Vị thuốc {thuoc} có mang đặc điểm {fact} không?"
            l_text = f"Xác nhận về tính vị của {thuoc}:"
        else:
            q_text = f"Vị thuốc {thuoc} có quy vào {fact} không?"
            l_text = f"Xác nhận về quy kinh của {thuoc}:"

        dataset.append({
            "entity": rec['entity_id'] if rec['entity_id'] else f"VI_THUOC_{thuoc.upper().replace(' ', '_')}",
            "id": item_id,
            "pattern_type": "reverse_search",
            "cypher_pattern": f"(v:ViThuoc {{canonical_name: '{thuoc}'}})-[:{rel_type}]->(t:{loai} {{canonical_name: '{fact}'}})",
            "question": q_text,
            "lead_in": l_text,
            "expected_facts": ["Có", fact],
            "expected_answer_full": f"Có, {fact}" # Rút gọn trực tiếp
        })
        item_id += 1

    # =========================================================
    # PATTERN 4: MULTI-RELATION (Hỏi mở giao thoa nhiều điều kiện)
    # =========================================================
    print(f"⏳ Đang tạo {limit_per_pattern} câu hỏi nhóm: MULTI RELATION...")
    query_p4 = f"""
    MATCH (v:ViThuoc)-[:CO_VI|CO_TINH]->(tv)
    MATCH (v)<-[:BAO_GOM_VI_THUOC]-(p:BaiThuoc)-[:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(d)
    WHERE toLower(v.canonical_name) <> toLower(d.canonical_name)
      AND tv.canonical_name IS NOT NULL AND d.canonical_name IS NOT NULL
    WITH tv.canonical_name AS TenDacTinh, labels(tv)[0] as LoaiDacTinh, d.canonical_name AS TenBenh, collect(DISTINCT v.canonical_name) AS Thuocs
    WHERE size(Thuocs) > 1 
    RETURN TenDacTinh, LoaiDacTinh, TenBenh, Thuocs
    ORDER BY rand() LIMIT {limit_per_pattern}
    """
    records_p4 = graph.query(query_p4)
    for rec in records_p4:
        # LỌC TRÙNG, SẮP XẾP VÀ GIỚI HẠN N DỮ LIỆU ĐẦU TIÊN
        thuocs = sorted(list(set(rec['Thuocs'])))[:limit_facts]
        if not thuocs: continue

        ten_dac_tinh = rec['TenDacTinh']
        loai_dac_tinh = rec['LoaiDacTinh']
        ten_benh = rec['TenBenh']
        
        q_text = f"Những vị thuốc nào vừa có đặc điểm {ten_dac_tinh}, vừa có khả năng tham gia điều trị {ten_benh}?"
        l_text = f"Các vị thuốc đáp ứng cả 2 điều kiện ({ten_dac_tinh} và tham gia chữa {ten_benh}) là:"

        dataset.append({
            "entity": f"GIAO_THOA_{ten_dac_tinh.upper().replace(' ', '_')}_{ten_benh.upper().replace(' ', '_')}",
            "id": item_id,
            "pattern_type": "multi_relation",
            "cypher_pattern": f"MATCH (v:ViThuoc)-[]->(:{loai_dac_tinh} {{canonical_name: '{ten_dac_tinh}'}}), (v)<-[]-(:BaiThuoc)-[]->(:Benh {{canonical_name: '{ten_benh}'}})",
            "question": q_text,
            "lead_in": l_text,
            "expected_facts": thuocs,
            # Chỉ lưu danh sách từ khóa để tối ưu điểm BLEU
            "expected_answer_full": ", ".join(thuocs)
        })
        item_id += 1

    # ==========================================================
    # LƯU KẾT QUẢ RA FILE JSON
    # ==========================================================
    print(f"\n💾 Đang ghi {len(dataset)} câu hỏi ra file {OUTPUT_FILE}...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print(f"🎉 HOÀN TẤT! Đã tạo thành công bộ dữ liệu với 4 loại Pattern.")
    print(f"👉 Dữ liệu đã được SẮP XẾP và GIỚI HẠN tối đa {limit_facts} thực thể/câu.")
    print("=" * 70)

if __name__ == "__main__":
    start_time = time.time()
    # Chạy hàm: Tạo 25 câu mỗi Pattern (tổng 100 câu), giới hạn tối đa 5 kết quả mỗi câu
    generate_complex_dataset(limit_per_pattern=25, limit_facts=5)
    print(f"⏱ Tổng thời gian chạy: {round(time.time() - start_time, 2)} giây.")