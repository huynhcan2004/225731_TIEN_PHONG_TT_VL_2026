"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 9 — ULTIMATE NEO4J RAG LOADER (BẢN ĐỒNG BỘ OLLAMA 100%)    ║
║  Chức năng: Xóa sạch CSDL cũ, nạp dữ liệu Diamond vào Neo4j.     ║
║  HOTFIX 1: Chuyển đổi sang Ollama (nomic-embed-text - 768 chiều).║
║  HOTFIX 2: CƠ CHẾ CACHE EMBEDDING - Không gọi API trùng lặp.     ║
║  HOTFIX 3: BƠM DỮ LIỆU ĐỊNH LƯỢNG - Nạp Data Richness & Score.   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import json
import glob
import os
import time
from neo4j import GraphDatabase
import ollama  # Dùng Ollama để đồng bộ 100% với file app_yhct.py

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings

# ==========================================================
# 1. CẤU HÌNH KẾT NỐI & MODEL (LẤY TỪ SETTINGS)
# ==========================================================
# Các thông số bảo mật đã được quản lý an toàn trong file .env
URI = settings.NEO4J_URI
USER = settings.NEO4J_USER
PWD = settings.NEO4J_PWD
DB_NAME = "neo4j" # Đổi thành "neo4j" nếu bản Neo4j Community không hỗ trợ đa DB

# Đường dẫn từ Medallion Architecture
INPUT_DIR = settings.DIR_GOLD_LINKED
CACHE_PATH = "config/checkpoints/embeddings_cache.json" # File lưu trữ Vector để tránh gọi lại API

os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

# ⚠️ SỬ DỤNG ĐÚNG MÔ HÌNH MÀ CHATBOT ĐANG DÙNG
EMBEDDING_MODEL_NAME = 'nomic-embed-text'
VECTOR_DIMENSIONS = 768  # Số chiều vector của nomic-embed-text

class Neo4jRAGUploader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_database(self):
        """XÓA SẠCH DỮ LIỆU VÀ INDEX CŨ TRƯỚC KHI NẠP"""
        print("🧹 Đang dọn dẹp Cơ sở dữ liệu Neo4j...")
        with self.driver.session(database=DB_NAME) as session:
            # 1. Xóa toàn bộ Nút và Cạnh (Sử dụng CALL {} IN TRANSACTIONS để tránh tràn RAM nếu dữ liệu lớn)
            try:
                session.run("MATCH (n) DETACH DELETE n")
                print("   -> Đã xóa sạch toàn bộ Thực thể và Quan hệ cũ.")
            except Exception as e:
                print(f"   -> Lỗi khi xóa dữ liệu (Có thể do quá lớn): {e}")
            
            # 2. Xóa Vector Index cũ (vì bản cũ đang là 384 chiều, bản mới là 768 chiều)
            try:
                session.run("DROP INDEX entity_vector_index")
                print("   -> Đã xóa Vector Index cũ (384 chiều).")
            except Exception:
                pass # Bỏ qua nếu index chưa tồn tại

            # [ĐÃ SỬA]: 3. Xóa Full-text Index cũ để tránh xung đột dữ liệu
            try:
                session.run("DROP INDEX entity_search_index")
                print("   -> Đã xóa Full-text Index cũ.")
            except Exception:
                pass

    def setup_indexes(self):
        """Thiết lập các Index tối thượng cho hệ thống RAG"""
        print("⚡ Đang thiết lập Hệ thống Index mới (768 chiều)...")
        with self.driver.session(database=DB_NAME) as session:
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

            # 3. Vector Index (Khớp đúng 768 chiều của nomic-embed-text)
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
        
        with self.driver.session(database=DB_NAME) as session:
            # --- NẠP NODES + VECTORS LÊN NEO4J ---
            # Chia lô 1000 nodes/lần để Neo4j không bị nghẽn
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
            # Chia lô 2000 rels/lần
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
    """Gom toàn bộ file JSON lại, gán thông số định lượng và bọc Vector"""
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

        # Lấy ID của vị thuốc chính trong file này
        main_entity_id = data.get("entity", {}).get("id", "")

        for node in data.get("nodes", []):
            nid = node["id"]
            
            # Gán Metadata định lượng cho Node chính
            if nid == main_entity_id:
                if "properties" not in node:
                    node["properties"] = {}
                node["properties"]["data_richness_index"] = meta_richness
                node["properties"]["reliability_c_score"] = meta_reliability

            if nid not in global_nodes:
                global_nodes[nid] = node
            else:
                # Gộp properties nếu thấy node này ở file khác có nhiều thông tin hơn
                for k, v in node["properties"].items():
                    if k not in global_nodes[nid]["properties"] and v:
                        global_nodes[nid]["properties"][k] = v

        for rel in data.get("relationships", []):
            edge_key = (rel["from"], rel["relation_type"], rel["to"])
            
            # Trích xuất và gán confidence_score vào properties của relationship
            if "properties" not in rel:
                rel["properties"] = {}
                
            # [ĐÃ SỬA]: Nạp thêm metadata tên vào quan hệ để Chatbot lấy ra dùng luôn không cần join 
            rel["properties"]["from_name"] = global_nodes.get(rel["from"], {}).get("properties", {}).get("canonical_name", "Unknown")
            rel["properties"]["to_name"] = global_nodes.get(rel["to"], {}).get("properties", {}).get("canonical_name", "Unknown")

            if "confidence_score" in rel:
                rel["properties"]["confidence_score"] = float(rel["confidence_score"])
            
            if edge_key not in global_rels:
                global_rels[edge_key] = rel
            else:
                # Gộp mô tả chi tiết nếu có
                old_desc = str(global_rels[edge_key]["properties"].get("mo_ta_chi_tiet", ""))
                new_desc = str(rel["properties"].get("mo_ta_chi_tiet", ""))
                if new_desc and new_desc not in old_desc:
                    global_rels[edge_key]["properties"]["mo_ta_chi_tiet"] = (old_desc + " | " + new_desc).strip(" | ")
                
                # Cập nhật confidence_score cao nhất nếu có xung đột
                old_score = global_rels[edge_key]["properties"].get("confidence_score", 0.0)
                new_score = rel["properties"].get("confidence_score", 0.0)
                if new_score > old_score:
                    global_rels[edge_key]["properties"]["confidence_score"] = new_score

    print(f"📊 Đã gom được {len(global_nodes)} Node duy nhất và {len(global_rels)} Quan hệ duy nhất.")
    
    # 2. Xử lý Vector Embedding với cơ chế CACHE
    cache = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            cache = json.load(f)
            print(f"💽 Đã tải {len(cache)} Vectors từ bộ nhớ đệm (Cache).")

    nodes_list = list(global_nodes.values())
    rels_list = list(global_rels.values())
    
    print(f"🤖 Đang nhúng Vector (Embedding) qua Ollama [{EMBEDDING_MODEL_NAME}]...")
    new_embeddings_count = 0
    
    for i, node in enumerate(nodes_list):
        nid = node["id"]
        
        # Nếu đã có trong Cache thì lấy ra dùng luôn
        if nid in cache:
            node["properties"]["embedding"] = cache[nid]
            continue

        # Nếu chưa có thì mới gọi Ollama
        name = node["properties"].get("canonical_name", "")
        aliases = node["properties"].get("aliases", [])
        aliases_str = ", ".join(aliases) if isinstance(aliases, list) else str(aliases)
        
        # [ĐÃ SỬA]: Bọc Vector giàu ngữ cảnh (Thêm loại thực thể và ngữ cảnh YHCT để chống nhiễu)
        label_vn = node.get("label", "ThucThe")
        text_to_embed = f"Thực thể: {name}. Loại: {label_vn}. Các tên gọi khác: {aliases_str}. Ngữ cảnh: Y học cổ truyền Việt Nam."
        
        try:
            response = ollama.embeddings(model=EMBEDDING_MODEL_NAME, prompt=text_to_embed)
            node["properties"]["embedding"] = response["embedding"]
            cache[nid] = response["embedding"]
            new_embeddings_count += 1
            
            # In tiến độ cho vui mắt
            if new_embeddings_count % 50 == 0:
                print(f"   ... Đã nhúng mới {new_embeddings_count} thực thể.")
                
        except Exception as e:
            raise RuntimeError(f"❌ Lỗi Ollama (hãy chắc chắn Ollama đang bật): {e}")

    # Lưu lại Cache cho lần chạy sau
    if new_embeddings_count > 0:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"💾 Đã lưu {new_embeddings_count} vector mới vào Cache.")
    else:
        print("⚡ 100% Thực thể đã dùng Cache. Tốc độ ánh sáng!")

    return nodes_list, rels_list

# ==========================================================
# 🧠 THỰC THI PIPELINE
# ==========================================================
def run_step_9():
    print("💎 BẮT ĐẦU: Wipe & Reload Đồ thị Diamond vào Neo4j")
    
    # Kiểm tra Ollama trước khi chạy
    try:
        ollama.list()
    except Exception:
        print("❌ LỖI CRITICAL: Không kết nối được với Ollama. Vui lòng mở ứng dụng Ollama trước khi nạp!")
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
        print("💡 Lưu ý: Hãy đảm bảo bạn đã cài đặt plugin APOC cho Neo4j.")
    finally:
        uploader.close()

    duration = round(time.time() - start_time, 2)
    print(f"\n🏆 HOÀN TẤT XUẤT SẮC! Đồ thị Knowledge Graph + Vector DB đã sẵn sàng (Đồng bộ 100%).")
    print(f"⏱ Tổng thời gian chạy: {duration} giây.")

if __name__ == "__main__":
    run_step_9()