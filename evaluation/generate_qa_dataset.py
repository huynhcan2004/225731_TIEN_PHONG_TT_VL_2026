import os
import json
import time
import random
import sys
import unicodedata
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# ==========================================================
# ⚠️ NEO4J
# ==========================================================
try:
    from langchain_community.graphs import Neo4jGraph
except ImportError:
    print("❌ pip install langchain-community neo4j")
    exit()

URI = settings.NEO4J_URI
USER = settings.NEO4J_USER
PWD = settings.NEO4J_PWD
DB_NAME = settings.NEO4J_DB_NAME

OUTPUT_DIR = settings.DIR_EVALUATION
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "complex_kg_qa_dataset.json")

# ==========================================================
# 🧠 INTENT GROUP
# ==========================================================
INTENT_GROUP_MAPPING = {
    "TIM_VI": "ATTRIBUTE",
    "TIM_TINH": "ATTRIBUTE",
    "TIM_QUY_KINH": "ATTRIBUTE",
    "TIM_HOAT_CHAT_CUA_THUOC": "ATTRIBUTE",
    "TIM_CONG_NANG": "ATTRIBUTE",
    "TIM_TAC_DUNG_DUOC_LY": "ATTRIBUTE",
    "TIM_CONG_DUNG_CUA_THUOC": "ATTRIBUTE",

    "TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC": "REASONING",
    "TIM_THUOC_CHUA_BENH": "REASONING",
    "TIM_BAI_THUOC_CHUA_BENH": "REASONING",

    "KIEM_TRA_BOOLEAN": "BOOLEAN",

    "TIM_DA_QUAN_HE": "MULTI_CONSTRAINT",

    "TIM_HUONG_DAN_SU_DUNG": "HOW_TO",

    "UNKNOWN": "OTHER"
}

# ==========================================================
# UTILS (LÀM SẠCH DỮ LIỆU & TẠO CONTEXT)
# ==========================================================
def remove_accents(s):
    if not s: return ""
    s = str(s).replace("Đ", "D").replace("đ", "d")
    nkfd = unicodedata.normalize('NFKD', s)
    res = "".join([c for c in nkfd if not unicodedata.combining(c)])
    return re.sub(r'[^a-zA-Z0-9_]', '_', res).strip('_').upper()

def clean_entity_name(name):
    """Lọc sạch các tag kỹ thuật và tiền tố để tránh lặp từ."""
    if not name: return ""
    name = str(name)
    
    # 1. Lọc bỏ các tag kỹ thuật
    name = re.sub(r'\[.*?\]', '', name)
    
    # 2. Xóa các tiền tố thừa thường gặp
    prefixes = [
        "Vị thuốc", "vị thuốc", 
        "Bài thuốc", "bài thuốc", 
        "Triệu chứng", "triệu chứng", 
        "Bệnh", "bệnh", 
        "Công năng", "công năng", 
        "Hoạt chất", "hoạt chất", 
        "Hợp chất", "hợp chất",
        "Tính", "tính"
    ]
    for p in prefixes:
        name = name.replace(p, "")
        
    # 3. Dọn dẹp khoảng trắng
    name = " ".join(name.split())
    
    # 4. Viết hoa chữ cái đầu cho chuẩn
    if len(name) > 0:
        name = name[0].upper() + name[1:]
        
    return name

def clean_metadata(text):
    """Xóa các ký hiệu LaTeX / Markdown thừa."""
    if not text: return ""
    return str(text).replace("$", "").strip()

def assign_intent(rel_type):
    if rel_type == "CO_VI": return "TIM_VI"
    elif rel_type == "CO_TINH": return "TIM_TINH"
    elif rel_type == "QUY_KINH": return "TIM_QUY_KINH"
    elif rel_type == "CO_CHUA_HOAT_CHAT": return "TIM_HOAT_CHAT_CUA_THUOC"
    elif rel_type == "CO_CONG_NANG": return "TIM_CONG_NANG"
    elif rel_type == "CO_TAC_DUNG_DUOC_LY": return "TIM_TAC_DUNG_DUOC_LY"
    else: return "UNKNOWN"

def random_difficulty():
    """Điều chỉnh tỷ lệ phân bổ độ khó: 50% easy, 30% medium, 20% hard"""
    return random.choices(["easy", "medium", "hard"], weights=[0.5, 0.3, 0.2], k=1)[0]

def format_context_string(entity_type, entity_name, attributes_dict):
    """
    Tạo chuỗi context chuẩn y khoa để chống ảo giác LLM.
    Định dạng:
    Dữ liệu dược điển:
    [Loại thực thể]: [Tên]
    - [Thuộc tính]: [Các giá trị]
    """
    context_lines = ["Dữ liệu dược điển:", f"{entity_type}: {entity_name}"]
    for attr_name, values in attributes_dict.items():
        if isinstance(values, list):
            val_str = ", ".join(values)
        else:
            val_str = str(values)
        context_lines.append(f"- {attr_name}: {val_str}")
    return "\n".join(context_lines)


# ==========================================================
# 🚀 MAIN GENERATOR
# ==========================================================
def generate_complex_dataset(limit_per_pattern=25, limit_facts=5):
    print("🔄 Connecting Neo4j...")
    try:
        if not DB_NAME or DB_NAME == "neo4j":
            graph = Neo4jGraph(url=URI, username=USER, password=PWD, refresh_schema=False)
        else:
            graph = Neo4jGraph(url=URI, username=USER, password=PWD, database=DB_NAME, refresh_schema=False)
        print(f"✅ Connected to database: {DB_NAME or 'Default DB'}")
    except Exception as e:
        print(f"❌ Neo4j error: {e}")
        return

    dataset = []
    item_id = 1

    # =========================================================
    # 1. SINGLE RELATION (ATTRIBUTE)
    # =========================================================
    print("⏳ SINGLE RELATION")
    query = f"""
    MATCH (v:ViThuoc)-[r:CO_VI|CO_TINH|QUY_KINH|CO_CHUA_HOAT_CHAT|CO_CONG_NANG|CO_TAC_DUNG_DUOC_LY]->(t)
    WITH v, type(r) AS rel, collect(DISTINCT t.canonical_name) AS facts
    RETURN v.canonical_name AS thuoc, rel, facts
    ORDER BY rand() LIMIT {limit_per_pattern}
    """

    for rec in graph.query(query):
        thuoc = clean_entity_name(rec["thuoc"])
        rel = rec["rel"]
        facts = [clean_entity_name(f) for f in sorted(list(set(rec["facts"])))[:limit_facts]]
        if not facts: continue

        intent = assign_intent(rel)
        intent_group = INTENT_GROUP_MAPPING.get(intent, "OTHER")

        # Ánh xạ nhãn cho Context
        attr_label = {
            "CO_VI": "Vị",
            "CO_TINH": "Tính",
            "QUY_KINH": "Quy kinh",
            "CO_CHUA_HOAT_CHAT": "Hoạt chất",
            "CO_CONG_NANG": "Công năng",
            "CO_TAC_DUNG_DUOC_LY": "Tác dụng dược lý"
        }.get(rel, "Đặc tính")

        # Sinh Context
        context = format_context_string("Vị thuốc", thuoc, {attr_label: facts})

        # Đa dạng hóa câu hỏi
        question_templates = {
            "TIM_VI": [f"Vị thuốc {thuoc.lower()} có vị gì?", f"Cho tôi biết vị của {thuoc.lower()}."],
            "TIM_TINH": [f"Vị thuốc {thuoc.lower()} có tính gì?", f"Tính chất của {thuoc.lower()} là gì?"],
            "TIM_QUY_KINH": [f"Vị thuốc {thuoc.lower()} quy vào kinh nào?", f"Kinh mạch nào liên quan đến {thuoc.lower()}?"],
            "TIM_HOAT_CHAT_CUA_THUOC": [f"Vị thuốc {thuoc.lower()} chứa hoạt chất gì?", f"Thành phần hóa học của {thuoc.lower()} gồm những gì?"],
            "TIM_CONG_NANG": [f"Vị thuốc {thuoc.lower()} có công năng gì?", f"Hãy cho biết công năng của {thuoc.lower()}."],
            "TIM_TAC_DUNG_DUOC_LY": [f"Tác dụng dược lý của {thuoc.lower()} ra sao?", f"Cơ chế tác dụng của {thuoc.lower()} là gì?"]
        }
        question = random.choice(question_templates.get(intent, [f"Thông tin về vị thuốc {thuoc.lower()} là gì?"]))

        dataset.append({
            "id": item_id,
            "pattern_type": "single_relation",
            "intent": intent,
            "intent_group": intent_group,
            "entity": f"VI_THUOC_{remove_accents(thuoc)}",
            "question": question,
            "context": context,  # <-- TRƯỜNG CONTEXT MỚI
            "expected_facts": facts,
            "expected_answer_full": ", ".join(facts),
            "difficulty": random_difficulty()
        })
        item_id += 1

    # =========================================================
    # 2. MULTI HOP (REASONING)
    # =========================================================
    print("⏳ MULTI HOP")
    query = f"""
    MATCH (v:ViThuoc)<-[:BAO_GOM_VI_THUOC]-(b:BaiThuoc)-[:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(d)
    WHERE d:Benh OR d:TrieuChung
    WITH v, collect(DISTINCT d.canonical_name) AS facts
    RETURN v.canonical_name AS thuoc, facts
    ORDER BY rand() LIMIT {limit_per_pattern}
    """

    for rec in graph.query(query):
        thuoc = clean_entity_name(rec["thuoc"])
        facts = [clean_entity_name(f) for f in sorted(list(set(rec["facts"])))[:limit_facts]]
        if not facts: continue

        intent = "TIM_CONG_DUNG_BAI_THUOC_TU_VI_THUOC"
        context = format_context_string("Vị thuốc", thuoc, {"Tham gia bài thuốc chữa các bệnh": facts})

        questions = [
            f"Vị thuốc {thuoc.lower()} tham gia vào bài thuốc để chữa những bệnh gì?",
            f"Bệnh nào có thể chữa bằng bài thuốc chứa {thuoc.lower()}?"
        ]

        dataset.append({
            "id": item_id,
            "pattern_type": "multi_hop",
            "intent": intent,
            "intent_group": INTENT_GROUP_MAPPING[intent],
            "entity": f"VI_THUOC_{remove_accents(thuoc)}",
            "question": random.choice(questions),
            "context": context,
            "expected_facts": facts,
            "expected_answer_full": ", ".join(facts),
            "difficulty": random_difficulty()
        })
        item_id += 1

    # =========================================================
    # 3. BOOLEAN VERIFICATION (POSITIVE & NEGATIVE)
    # =========================================================
    print("⏳ BOOLEAN")

    # POSITIVE
    query_pos = f"""
    MATCH (v:ViThuoc)-[r:CO_VI|CO_TINH|CO_CHUA_HOAT_CHAT|QUY_KINH]->(t)
    RETURN v.canonical_name AS thuoc, t.canonical_name AS fact, type(r) AS rel
    ORDER BY rand() LIMIT {limit_per_pattern//2}
    """
    for rec in graph.query(query_pos):
        thuoc = clean_entity_name(rec["thuoc"])
        fact = clean_entity_name(rec["fact"])
        rel = rec["rel"]
        
        attr_label = {"CO_VI": "Vị", "CO_TINH": "Tính", "QUY_KINH": "Quy kinh", "CO_CHUA_HOAT_CHAT": "Hoạt chất"}.get(rel, "Đặc tính")
        context = format_context_string("Vị thuốc", thuoc, {attr_label: [fact]})

        question = f"Vị thuốc {thuoc.lower()} có {attr_label.lower()} {fact.lower()} không?"

        dataset.append({
            "id": item_id,
            "pattern_type": "reverse_search_positive",
            "intent": "KIEM_TRA_BOOLEAN",
            "intent_group": "BOOLEAN",
            "entity": f"VI_THUOC_{remove_accents(thuoc)}",
            "question": question,
            "context": context,
            "expected_facts": ["Có"],
            "expected_answer_full": f"Có, vị thuốc {thuoc.lower()} có {attr_label.lower()} {fact.lower()}",
            "difficulty": random_difficulty()
        })
        item_id += 1

    # NEGATIVE
    query_neg = f"""
    MATCH (v:ViThuoc), (h:HoatChat)
    WHERE NOT (v)-[:CO_CHUA_HOAT_CHAT]->(h)
    RETURN v.canonical_name AS thuoc, h.canonical_name AS fact
    ORDER BY rand() LIMIT {limit_per_pattern//2}
    """
    for rec in graph.query(query_neg):
        thuoc = clean_entity_name(rec["thuoc"])
        fact = clean_entity_name(rec["fact"])

        # Context khẳng định rõ ràng để bẫy LLM
        context = format_context_string("Vị thuốc", thuoc, {"Ghi chú hoạt chất": [f"Không chứa {fact.lower()}"]})

        dataset.append({
            "id": item_id,
            "pattern_type": "reverse_search_negative",
            "intent": "KIEM_TRA_BOOLEAN",
            "intent_group": "BOOLEAN",
            "entity": f"VI_THUOC_{remove_accents(thuoc)}",
            "question": f"Vị thuốc {thuoc.lower()} có chứa hoạt chất {fact.lower()} không?",
            "context": context,
            "expected_facts": ["Không"],
            "expected_answer_full": f"Không, vị thuốc {thuoc.lower()} không chứa hoạt chất {fact.lower()}",
            "difficulty": random_difficulty()
        })
        item_id += 1

    # =========================================================
    # 4. MULTI RELATION (MULTI_CONSTRAINT)
    # =========================================================
    print("⏳ MULTI RELATION")
    query = f"""
    MATCH (v:ViThuoc)-[:CO_TINH]->(t)
    MATCH (v)-[:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(d)
    WITH t.canonical_name AS tinh, d.canonical_name AS benh, collect(DISTINCT v.canonical_name) AS thuocs
    WHERE size(thuocs) > 1
    RETURN tinh, benh, thuocs
    ORDER BY rand() LIMIT {limit_per_pattern}
    """

    for rec in graph.query(query):
        tinh = clean_entity_name(rec["tinh"])
        benh = clean_entity_name(rec["benh"])
        thuocs = [clean_entity_name(t) for t in sorted(list(set(rec["thuocs"])))[:limit_facts]]
        if not thuocs: continue

        context = format_context_string("Bộ lọc tìm kiếm", f"Tính {tinh.lower()} và trực tiếp chữa {benh.lower()}", {"Các vị thuốc thỏa mãn": thuocs})

        dataset.append({
            "id": item_id,
            "pattern_type": "multi_relation",
            "intent": "TIM_DA_QUAN_HE",
            "intent_group": "MULTI_CONSTRAINT",
            "entity": f"GIAO_THOA_{remove_accents(tinh)}",
            "question": f"Thuốc nào vừa có tính {tinh.lower()} vừa trực tiếp chữa bệnh {benh.lower()}?",
            "context": context,
            "expected_facts": thuocs,
            "expected_answer_full": ", ".join(thuocs),
            "difficulty": random_difficulty()
        })
        item_id += 1
        
    # =========================================================
    # 5. HOW TO (TRÍCH XUẤT CHÍNH XÁC FACT)
    # =========================================================
    print("⏳ HOW TO (EXACT SEARCH FOR METADATA)")
    query_howto = f"""
    MATCH (s:ThucThe)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(t:ThucThe)
    WHERE r.lieu_luong IS NOT NULL OR r.lieu_dung IS NOT NULL OR r.cach_dung IS NOT NULL
    RETURN s.canonical_name AS thuoc, t.canonical_name AS benh, 
           coalesce(r.lieu_luong, r.lieu_dung) AS lieu_dung,
           r.cach_dung AS cach_dung
    ORDER BY rand() LIMIT {limit_per_pattern}
    """

    for rec in graph.query(query_howto):
        thuoc = clean_entity_name(rec["thuoc"])
        benh = clean_entity_name(rec["benh"])
        
        lieu_dung = clean_metadata(rec["lieu_dung"])
        cach_dung = clean_metadata(rec["cach_dung"])

        facts = []
        context_dict = {}
        if lieu_dung: 
            facts.append(lieu_dung)
            context_dict["Liều dùng"] = [lieu_dung]
        if cach_dung: 
            facts.append(cach_dung)
            context_dict["Cách dùng"] = [cach_dung]

        if not facts: continue

        context = format_context_string("Điều trị bệnh", benh, {f"Sử dụng {thuoc}": [f"{k}: {v[0]}" for k, v in context_dict.items()]})

        dataset.append({
            "id": item_id,
            "pattern_type": "how_to_usage",
            "intent": "TIM_HUONG_DAN_SU_DUNG",
            "intent_group": "HOW_TO",
            "entity": f"HUONG_DAN_{remove_accents(thuoc)}",
            "question": f"Để chữa bệnh {benh.lower()}, vị thuốc {thuoc.lower()} được dùng với liều lượng và cách thức như thế nào?",
            "context": context,
            "expected_facts": facts, 
            "expected_answer_full": f"Để chữa bệnh {benh.lower()}, vị thuốc {thuoc.lower()} có liều dùng: {lieu_dung or 'Theo chỉ định'} và cách dùng: {cach_dung or 'Theo chỉ định'}",
            "difficulty": random_difficulty()
        })
        item_id += 1

    # =========================================================
    # 6. TREATMENT SEARCH (HYBRID SEARCH)
    # =========================================================
    print("⏳ TREATMENT SEARCH")
    query_treatment = f"""
    MATCH (p)-[r:CHU_TRI_BENH|CHU_TRI_TRIEU_CHUNG]->(d)
    WHERE d:Benh OR d:TrieuChung
    WITH d.canonical_name AS benh, collect(DISTINCT p.canonical_name) AS thuocs
    WHERE size(thuocs) > 0
    RETURN benh, thuocs
    ORDER BY rand() LIMIT {limit_per_pattern}
    """

    for rec in graph.query(query_treatment):
        benh = clean_entity_name(rec["benh"])
        thuocs = [clean_entity_name(t) for t in sorted(list(set(rec["thuocs"])))[:limit_facts]]

        context = format_context_string("Bệnh/Triệu chứng", benh, {"Các thuốc chữa trị": thuocs})

        dataset.append({
            "id": item_id,
            "pattern_type": "treatment_search",
            "intent": "TIM_THUOC_CHUA_BENH",
            "intent_group": "REASONING",
            "entity": f"TREATMENT_{remove_accents(benh)}",
            "question": f"Bệnh {benh.lower()} có thể dùng vị thuốc hoặc bài thuốc nào để chữa?",
            "context": context,
            "expected_facts": thuocs,
            "expected_answer_full": ", ".join(thuocs),
            "difficulty": random_difficulty()
        })
        item_id += 1

    # =========================================================
    # SAVE
    # =========================================================
    print(f"\n💾 Saving {len(dataset)} samples...")
    random.shuffle(dataset)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print("🎉 DONE")

# ==========================================================
# RUN
# ==========================================================
if __name__ == "__main__":
    start = time.time()
    random.seed(42)
    generate_complex_dataset(limit_per_pattern=40, limit_facts=30)
    print(f"⏱ Time: {round(time.time()-start,2)}s")