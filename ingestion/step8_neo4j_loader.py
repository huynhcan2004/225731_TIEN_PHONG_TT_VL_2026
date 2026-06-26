"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 9 — ULTIMATE NEO4J RAG LOADER (DIAMOND LEVEL)              ║
║  Chức năng: Xóa sạch CSDL cũ, nạp dữ liệu Diamond vào Neo4j.     ║
║  HOTFIX 1: Chuyển đổi sang Ollama (bge-m3 - 1024 chiều).         ║
║  HOTFIX 2: CƠ CHẾ CACHE EMBEDDING - Không gọi API trùng lặp.     ║
║  HOTFIX 3: BƠM DỮ LIỆU ĐỊNH LƯỢNG - Nạp Data Richness & Score.   ║
║  HOTFIX 4: KNOWLEDGE-ENRICHED EMBEDDING - Chống nhầm bệnh lý.    ║
║  HOTFIX 5: BGE-M3 INTEGRATION - Nhúng Search Vector Hint cực sâu.║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import glob
import os
import time
from neo4j import GraphDatabase
import ollama  # Dùng Ollama để đồng bộ 100% với file app_yhct.py
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings

# ==========================================================
# 1. CẤU HÌNH KẾT NỐI & MODEL (LẤY TỪ SETTINGS)
# ==========================================================
# Các thông số bảo mật đã được quản lý an toàn trong file .env
URI = settings.NEO4J_URI
USER = settings.NEO4J_USER
PWD = settings.NEO4J_PWD
DB_NAME = settings.NEO4J_DB_NAME # Đổi thành "neo4j" nếu bản Neo4j Community không hỗ trợ đa DB

# Đường dẫn từ Medallion Architecture
INPUT_DIR = settings.DIR_GOLD_LINKED
# Đổi tên file Cache để tránh xung đột với vector 768 chiều cũ của Nomic
CACHE_PATH = "config/checkpoints/embeddings_cache_bgem3.json" 

os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

# ⚠️ SỬ DỤNG ĐÚNG MÔ HÌNH BGE-M3 (1024 CHIỀU)
EMBEDDING_MODEL_NAME = 'bge-m3'
VECTOR_DIMENSIONS = 1024  # Số chiều vector của bge-m3

class Neo4jRAGUploader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.session_kwargs = {}
        if DB_NAME and DB_NAME != "neo4j":
            self.session_kwargs["database"] = DB_NAME

    def close(self):
        self.driver.close()

    def clear_database(self):
        """XÓA SẠCH DỮ LIỆU VÀ INDEX CŨ TRƯỚC KHI NẠP"""
        print("🧹 Đang dọn dẹp Cơ sở dữ liệu Neo4j...")
        with self.driver.session(**self.session_kwargs) as session:
            # 1. Xóa toàn bộ Nút và Cạnh (Dùng Transactions để chống tràn RAM)
            try:
                session.run("CALL { MATCH (n) DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS")
                print("   -> Đã xóa sạch toàn bộ Thực thể và Quan hệ cũ (Safe Delete).")
            except Exception as e:
                # Dự phòng cho các bản Neo4j cũ không hỗ trợ CALL {} IN TRANSACTIONS
                try:
                    session.run("MATCH (n) DETACH DELETE n")
                    print("   -> Đã xóa sạch toàn bộ Thực thể và Quan hệ cũ (Standard Delete).")
                except Exception as ex:
                    print(f"   -> Lỗi khi xóa dữ liệu: {ex}")
            
            # 2. Xóa Vector Index cũ
            try:
                session.run("DROP INDEX entity_vector_index")
                print("   -> Đã xóa Vector Index cũ.")
            except Exception:
                pass # Bỏ qua nếu index chưa tồn tại

            # 3. Xóa Full-text Index cũ để tránh xung đột dữ liệu
            try:
                session.run("DROP INDEX entity_search_index")
                print("   -> Đã xóa Full-text Index cũ.")
            except Exception:
                pass

    def setup_indexes(self):
        """Thiết lập các Index tối thượng cho hệ thống RAG"""
        print(f"⚡ Đang thiết lập Hệ thống Index mới ({VECTOR_DIMENSIONS} chiều)...")
        with self.driver.session(**self.session_kwargs) as session:
            # 1. Unique Constraint (Tránh trùng lặp dữ liệu ID)
            try:
                session.run("CREATE CONSTRAINT thucthe_id_unique IF NOT EXISTS FOR (n:ThucThe) REQUIRE n.id IS UNIQUE")
            except Exception as e: print(f" - Note Constraint: {e}")

            # 2. Full-text Index (Hỗ trợ gõ không dấu)
            try:
                session.run("""
                CREATE FULLTEXT INDEX entity_search_index IF NOT EXISTS 
                FOR (n:ThucThe) ON EACH [n.canonical_name, n.aliases]
                """)
            except Exception as e: print(f" - Note Fulltext: {e}")

            # 3. Vector Index (Khớp đúng số chiều của mô hình hiện tại)
            try:
                session.run(f"""
                CREATE VECTOR INDEX entity_vector_index IF NOT EXISTS
                FOR (n:ThucThe) ON (n.embedding)
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: {VECTOR_DIMENSIONS},
                    `vector.similarity_function`: 'cosine'
                }}}}
                """)
            except Exception as e: print(f" - Note Vector Index: {e}")
        print("✅ Đã thiết lập xong nền tảng Index!")

    def upload_global_graph(self, nodes_list, rels_list):
        """Nạp toàn bộ siêu đồ thị vào Neo4j bằng lô (Batching)"""
        print(f"🚀 Bắt đầu bơm {len(nodes_list)} Thực thể và {len(rels_list)} Quan hệ vào Neo4j...")
        
        with self.driver.session(**self.session_kwargs) as session:
            # --- NẠP NODES + VECTORS LÊN NEO4J ---
            batch_size = 1000
            for i in range(0, len(nodes_list), batch_size):
                batch = nodes_list[i:i+batch_size]
                session.run("""
                UNWIND $nodes AS node
                MERGE (n:ThucThe {id: node.id})
                SET n += node.properties
                WITH n, node
                CALL apoc.create.setLabels(n, ['ThucThe', node.label]) YIELD node as labeledNode
                RETURN count(*)
                """, nodes=batch)
                print(f"   -> Đã nạp Nodes lô {i//batch_size + 1}: {len(batch)} thực thể")

            # --- NẠP QUAN HỆ (RELATIONSHIPS) ---
            rel_batch_size = 2000
            for i in range(0, len(rels_list), rel_batch_size):
                batch = rels_list[i:i+rel_batch_size]
                session.run("""
                UNWIND $rels AS rel
                MATCH (a:ThucThe {id: rel.from})
                MATCH (b:ThucThe {id: rel.to})
                CALL apoc.merge.relationship(a, rel.relation_type, {}, rel.properties, b, {}) YIELD rel as r
                RETURN count(*)
                """, rels=batch)
                print(f"   -> Đã nối Quan hệ lô {i//rel_batch_size + 1}: {len(batch)} cạnh")

# ==========================================================
# 🧠 TRÌNH TIỀN XỬ LÝ (PRE-PROCESSOR) & EMBEDDING CACHE
# ==========================================================

def process_and_embed_data(input_dir):
    """Gom toàn bộ file JSON lại, gán thông số định lượng và bọc Vector giàu ngữ nghĩa"""
    files = glob.glob(os.path.join(input_dir, "*.json"))
    if not files:
        print(f"❌ Không tìm thấy file JSON tại {input_dir}.")
        return [], []

    global_nodes = {}  # {node_id: node_object}
    global_rels = {}   # {(from, type, to): rel_object}

    print(f"🔍 Đang gom dữ liệu từ {len(files)} file để xây Siêu Đồ Thị...")

    # 1. Gom Nodes và Relationships
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Trích xuất Metadata để gán cho Node thực thể chính (Vị thuốc)
        meta_richness = 0.0
        meta_reliability = 0.0
        if "metadata" in data and "scientific_metrics" in data["metadata"]:
            metrics = data["metadata"]["scientific_metrics"]
            meta_richness = float(metrics.get("data_richness_index", 0.0))
            meta_reliability = float(metrics.get("reliability_c_score", 0.0))

        main_entity_id = data.get("entity", {}).get("id", "")

        for node in data.get("nodes", []):
            nid = node["id"]
            
            # Gán điểm số cho Hub Node
            if nid == main_entity_id:
                if "properties" not in node:
                    node["properties"] = {}
                node["properties"]["data_richness_index"] = meta_richness
                node["properties"]["reliability_c_score"] = meta_reliability

            # 🟢 SỬA LỖI GHI ĐÈ NODE PHỤ (Safe Merge Properties)
            if nid not in global_nodes:
                global_nodes[nid] = node
            else:
                for k, v in node.get("properties", {}).items():
                    # Chỉ ghi đè nếu thuộc tính hiện tại đang rỗng, bảo vệ dữ liệu quý
                    if v and not global_nodes[nid]["properties"].get(k):
                        global_nodes[nid]["properties"][k] = v

        for rel in data.get("relationships", []):
            edge_key = (rel["from"], rel["relation_type"], rel["to"])
            
            if "properties" not in rel:
                rel["properties"] = {}
                
            rel["properties"]["from_name"] = global_nodes.get(rel["from"], {}).get("properties", {}).get("canonical_name", "Unknown")
            rel["properties"]["to_name"] = global_nodes.get(rel["to"], {}).get("properties", {}).get("canonical_name", "Unknown")

            if "confidence_score" in rel:
                rel["properties"]["confidence_score"] = float(rel["confidence_score"])
            
            if edge_key not in global_rels:
                global_rels[edge_key] = rel
            else:
                old_desc = str(global_rels[edge_key]["properties"].get("mo_ta_chi_tiet", ""))
                new_desc = str(rel["properties"].get("mo_ta_chi_tiet", ""))
                if new_desc and new_desc not in old_desc:
                    global_rels[edge_key]["properties"]["mo_ta_chi_tiet"] = (old_desc + " | " + new_desc).strip(" | ")
                
                old_score = global_rels[edge_key]["properties"].get("confidence_score", 0.0)
                new_score = rel["properties"].get("confidence_score", 0.0)
                if new_score > old_score:
                    global_rels[edge_key]["properties"]["confidence_score"] = new_score

    print(f"📊 Đã gom được {len(global_nodes)} Node duy nhất và {len(global_rels)} Quan hệ duy nhất.")
    
    # 2. XÂY DỰNG CHỮ KÝ TRI THỨC (KNOWLEDGE-ENRICHED CONTEXT)
    print("🧬 Đang xây dựng 'Chữ ký tri thức' từ các Quan hệ để chống nhiễu Vector...")
    node_context = {nid: "" for nid in global_nodes.keys()}

    for rel in global_rels.values():
        frm = rel["from"]
        to = rel["to"]
        rel_type = rel["relation_type"]
        
        from_name = rel["properties"]["from_name"]
        to_name = rel["properties"]["to_name"]
        
        # Bơm thông tin vào 2 đầu thực thể dựa trên loại quan hệ
        if rel_type == "CHU_TRI_BENH":
            node_context[frm] += f" Chủ trị bệnh: {to_name}."
            if to in node_context: node_context[to] += f" Được điều trị bởi vị thuốc: {from_name}."
        elif rel_type == "CO_CHUA_HOAT_CHAT":
            node_context[frm] += f" Thành phần chứa: {to_name}."
            if to in node_context: node_context[to] += f" Tìm thấy trong cây: {from_name}."
        elif rel_type == "CO_CONG_NANG":
            node_context[frm] += f" Có công năng: {to_name}."
        elif rel_type == "CO_VI":
            node_context[frm] += f" Vị của thuốc: {to_name}."
        elif rel_type == "CO_TINH":
            node_context[frm] += f" Tính của thuốc: {to_name}."
        elif rel_type == "BAO_GOM_VI_THUOC":
            node_context[frm] += f" Bài thuốc chứa: {to_name}."
            if to in node_context: node_context[to] += f" Dùng trong bài thuốc: {from_name}."

    # 3. Xử lý Vector Embedding với cơ chế CACHE
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
            print(f"💽 Đã tải {len(cache)} Vectors từ bộ nhớ đệm (Cache BGE-M3).")

    nodes_list = list(global_nodes.values())
    rels_list = list(global_rels.values())
    
    print(f"🤖 Đang nhúng Vector siêu ngữ cảnh qua Ollama [{EMBEDDING_MODEL_NAME}]...")
    new_embeddings_count = 0
    
    for i, node in enumerate(nodes_list):
        nid = node["id"]
        
        if nid in cache:
            node["properties"]["embedding"] = cache[nid]
            continue

        name = node.get("properties", {}).get("canonical_name", "")
        aliases = node.get("properties", {}).get("aliases", [])
        aliases_str = ", ".join(aliases) if isinstance(aliases, list) else str(aliases)
        label_vn = node.get("label", "ThucThe")
        
        # 🟢 BẮT LẤY ĐỊNH NGHĨA SEARCH VECTOR HINT TỪ STEP 7
        search_vector_hint = node.get("properties", {}).get("search_vector_hint", "")
        
        # Trích xuất thêm mô tả thô (nếu có)
        raw_desc = str(node.get("properties", {}).get("che_bien_tho", "") or node.get("properties", {}).get("mo_ta_chi_tiet", "") or "")
        
        # 🟢 CHUỖI NHÚNG BGE-M3: Tên + Bí danh + HINT + Quan hệ tri thức + Mô tả
        extra_info = node_context.get(nid, "").strip()
        text_to_embed = (
            f"Thực thể YHCT: {name}. "
            f"Phân loại: {label_vn}. "
            f"Tên gọi khác: {aliases_str}. "
            f"Định nghĩa & Gợi ý tìm kiếm: {search_vector_hint} "
            f"Đặc điểm lâm sàng & Quan hệ: {extra_info} "
            f"Mô tả cơ bản: {raw_desc[:250]}" # Cắt 250 ký tự để tập trung vào quan hệ
        ).strip()
        
        try:
            response = ollama.embeddings(model=EMBEDDING_MODEL_NAME, prompt=text_to_embed)
            node["properties"]["embedding"] = response["embedding"]
            cache[nid] = response["embedding"]
            new_embeddings_count += 1
            
            if new_embeddings_count % 50 == 0:
                print(f"   ... Đã nhúng mới {new_embeddings_count} thực thể.")
                
        except Exception as e:
            raise RuntimeError(f"❌ Lỗi Ollama (hãy chắc chắn Ollama đang bật và đã pull {EMBEDDING_MODEL_NAME}): {e}")

    # Lưu lại Cache
    if new_embeddings_count > 0:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"💾 Đã lưu {new_embeddings_count} vector mới vào Cache.")
    else:
        print("⚡ 100% Thực thể đã dùng Cache. Không tốn một giọt API nào!")

    return nodes_list, rels_list

# ==========================================================
# 🧠 THỰC THI PIPELINE
# ==========================================================
def run_step_9():
    print(f"💎 BẮT ĐẦU: Wipe & Reload Đồ thị Diamond vào Neo4j (Model: {EMBEDDING_MODEL_NAME})")
    
    # Kiểm tra Ollama trước khi chạy
    try:
        ollama.list()
    except Exception:
        print("❌ LỖI CRITICAL: Không kết nối được với Ollama. Vui lòng bật app Ollama lên!")
        return

    # 1. Gom dữ liệu và Nhúng Vector thông minh
    start_time = time.time()
    nodes_list, rels_list = process_and_embed_data(INPUT_DIR)
    
    if not nodes_list:
        return

    # 2. Bơm thẳng vào Neo4j
    uploader = Neo4jRAGUploader(URI, USER, PWD)
    uploader.clear_database()
    uploader.setup_indexes()
    
    try:
        uploader.upload_global_graph(nodes_list, rels_list)
    except Exception as e:
        print(f"❌ Lỗi trong quá trình nạp Neo4j: {e}")
        print("💡 Lưu ý: Cần cài đặt plugin APOC trong thư mục plugins của Neo4j.")
    finally:
        uploader.close()

    duration = round(time.time() - start_time, 2)
    print(f"\n🏆 HOÀN TẤT XUẤT SẮC! Đồ thị vKG (Vector Knowledge Graph) đã được bơm đầy đủ.")
    print(f"⏱ Tổng thời gian chạy: {duration} giây.")

if __name__ == "__main__":
    run_step_9()