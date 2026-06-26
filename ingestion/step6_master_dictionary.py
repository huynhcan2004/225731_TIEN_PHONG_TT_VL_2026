"""
╔══════════════════════════════════════════════════════════════════╗
║  STEP 6 — MASTER DICTIONARY GENERATOR (CLEAN ARCHITECTURE MODE)  ║
║  + GOLD ALIAS FIRST                                              ║
║  + LLM AS SUPPORT ONLY                                           ║
║  + NO FAKE SEMANTIC                                              ║
║  + STRICT CONTROL                                                ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os
import json
import glob
import time
import re
from google import genai
from google.genai import types
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from utils.helpers import remove_accents

# ==========================================================
# CONFIG
# ==========================================================
PROJECT_ID = "yhct-knowledge-graph"
LOCATION = "us-central1"
MODEL_ID = settings.MODEL_ID 

INPUT_DIR = settings.DIR_GOLD_VALIDATED
OUTPUT_DIR = settings.DIR_DICT_MASTER
MASTER_MAP_PATH = settings.FILE_DICT_FINAL
CHECKPOINT_PATH = settings.CHECKPOINT_DICT

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CHECKPOINT_PATH), exist_ok=True)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

# ==========================================================
# PREFIX → LABEL
# ==========================================================
PREFIX_LABEL_MAP = {
    "VT_": "ViThuoc", "VI_THUOC_": "ViThuoc",
    "BT_": "BaiThuoc", "BAI_THUOC_": "BaiThuoc",
    "B_": "Benh", "S_": "TrieuChung",
    "CN_": "CongNang", "HC_": "HoatChat",
    "DL_": "DuocLy", "K_": "KinhMach",
    "T_": "Tinh", "V_": "Vi", "G_": "DoiTuong"
}

# ==========================================================
# UTIL
# ==========================================================
def normalize_text(text):
    if not text:
        return ""
    text = remove_accents(text.lower().strip())
    text = re.sub(r'\s+', ' ', text)
    return text

def get_label_from_id(entity_id):
    for prefix, label in PREFIX_LABEL_MAP.items():
        if str(entity_id).startswith(prefix):
            return label
    return "ThucThe"

# ==========================================================
# PROMPT
# ==========================================================
AI_RECONCILE_PROMPT = """[VAI TRÒ]
Bạn là Kiến trúc sư trưởng và Chuyên gia Đồ thị Tri thức Y học cổ truyền (TCM Knowledge Graph).

[NHIỆM VỤ]
Tiếp nhận danh sách thực thể (ID + thông tin gợi ý), chuẩn hóa thành Master Dictionary để phục vụ hệ thống tìm kiếm thông minh.

[QUY TẮC 1: canonical_name]
- BẮT BUỘC có tiền tố phân loại: "Vị thuốc ...", "Bệnh ...", "Triệu chứng ...", "Công năng ...", "Bài thuốc ...", "Kinh ..." (giữ nguyên dạng kinh mạch).
- Viết đúng chính tả tiếng Việt, có dấu.

[QUY TẮC 2: CHIẾN LƯỢC ALIAS THEO LOẠI THỰC THỂ (Entity-Type Awareness)]
Tuyệt đối tuân thủ chiến lược sau dựa vào loại thực thể:

1. Nhóm Vị thuốc, Bài thuốc (Khuyến khích MỞ RỘNG):
   - Trọng tâm là tìm "Tên gọi khác", "Tên dân gian", "Tên địa phương" có thật.
   - VD: Ích mẫu -> ["Sung úy", "Chói đèn"].

2. Nhóm Bệnh, Triệu chứng (Khuyến khích KẾT NỐI HIỆN ĐẠI):
   - Trọng tâm là "Thuật ngữ Y học hiện đại tương đương" và "Cách gọi bình dân phổ biến".
   - VD: Tiêu khát -> ["Tiểu đường", "Đái tháo đường"].

3. Nhóm Công năng, Tính, Vị (VÔ CÙNG KHẮT KHE):
   - Trọng tâm là "Thuật ngữ chuyên môn tương đương". KHÔNG dùng từ giải thích dài dòng.
   - Nếu không có thuật ngữ y lý nào tương đương sát nghĩa, BẮT BUỘC trả về mảng rỗng [].
   - VD: Hoạt huyết -> ["Hành huyết"]. (Tuyệt đối không dùng "Lưu thông máu").

4. Nhóm Hoạt chất, Dược lý (KHÔNG SUY LUẬN):
   - Đây là danh pháp khoa học. Hãy trả về mảng rỗng [] trừ khi có tên viết tắt cực kỳ phổ thông.

❌ NHỮNG ĐIỀU CẤM KỴ TOÀN CỤC:
- Không rã từ ghép (VD: "Tê liệt" thì giữ nguyên, KHÔNG tách thành "tê", "liệt").
- Không dùng từ quá chung chung làm mất đặc trưng bệnh (VD: "Hư lao" thì dùng "Suy nhược", "Lao lực", cấm dùng "mệt mỏi").
- Không dùng các câu văn mô tả, giải thích (Cấm dùng "là tình trạng...", "thường do...").
- Bắt buộc trả về tiếng Việt có dấu đầy đủ.

[VÍ DỤ CHUẨN ĐỂ HỌC TẬP]
- Input: Vị thuốc Bạch thược -> aliases: ["Thược dược", "Kim thược dược"]
- Input: Triệu chứng Hồi hộp -> aliases: ["Đánh trống ngực", "Tim đập nhanh"]
- Input: Bệnh Hư lao -> aliases: ["Suy nhược cơ thể", "Lao lực", "Hư tổn"] 
- Input: Công năng Lợi tiểu -> aliases: ["Lợi niệu"] (Chỉ dùng từ chuyên môn)
- Input: Công năng Giảm đau -> aliases: ["Chỉ thống"]
- Input: Hoạt chất Saponin -> aliases: []

[SEARCH VECTOR HINT]
Viết 1 câu < 25 từ: "[Tên chuẩn] thuộc nhóm [label], thường liên quan đến..."

[OUTPUT JSON – BẮT BUỘC]
{
  "entities": [
    {
      "canonical_id": "...",
      "canonical_name": "...",
      "label": "...",
      "aliases": ["..."],
      "search_vector_hint": "..."
    }
  ]
}

KHÔNG thêm text ngoài JSON. KHÔNG markdown. KHÔNG giải thích.
"""

DICTIONARY_SCHEMA = types.Schema(
    type="OBJECT",
    properties={
        "entities": types.Schema(
            type="ARRAY",
            items=types.Schema(
                type="OBJECT",
                properties={
                    "canonical_id": types.Schema(type="STRING"),
                    "canonical_name": types.Schema(type="STRING"),
                    "label": types.Schema(type="STRING"),
                    "aliases": types.Schema(type="ARRAY", items=types.Schema(type="STRING")),
                    "search_vector_hint": types.Schema(type="STRING")
                },
                required=["canonical_id", "canonical_name", "label", "aliases", "search_vector_hint"]
            )
        )
    },
    required=["entities"]
)

# ==========================================================
# STAGE 1 — GOLD HARVEST + GOLD ALIAS
# ==========================================================
def stage_1():
    files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    master_raw_vocab = {}
    valid_prefixes = tuple(PREFIX_LABEL_MAP.keys())

    for p in files:
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                entity = data.get("entity", {})
                root_id = entity.get("id")

                if root_id:
                    c_id = str(root_id).strip().upper()
                    if c_id.startswith(valid_prefixes):

                        # 🔥 GOLD ALIAS (QUAN TRỌNG NHẤT)
                        gold_aliases = []

                        for key in ["ten_khac", "ten_dan_gian", "alias"]:
                            vals = entity.get(key)
                            if isinstance(vals, list):
                                gold_aliases.extend(vals)
                            elif isinstance(vals, str):
                                gold_aliases.append(vals)

                        master_raw_vocab[c_id] = {
                            "c_name": entity.get("display_name"),
                            "label": get_label_from_id(c_id),
                            "gold_aliases": list(set(gold_aliases))
                        }

                for node in data.get("nodes", []):
                    nid = node.get("id")
                    if nid and nid.startswith(valid_prefixes):
                        master_raw_vocab.setdefault(nid, {
                            "c_name": node.get("properties", {}).get("canonical_name"),
                            "label": get_label_from_id(nid),
                            "gold_aliases": []
                        })

            except:
                continue

    return master_raw_vocab

# ==========================================================
# 🔥 ENRICH (ĐƯA LÊN TRÊN ĐỂ GỌI TRONG STAGE 2)
# ==========================================================
def enrich_aliases(entity, gold_aliases):
    name = entity.get("canonical_name", "").lower()

    # Thêm tính vị, kinh mạch để đảm bảo lột sạch 100% tiền tố
    core_name = re.sub(
        r'^(vị thuốc|bệnh|triệu chứng|công năng|kinh mạch|kinh|hoạt chất|dược lý|bài thuốc|tính vị|tính|vị)\s+',
        '',
        name
    ).strip()

    aliases = set()

    # 🔥 1. ALWAYS ADD CORE NAME (Sửa lỗi logic if not aliases ở lượt trước)
    # Tên lõi bắt buộc phải được đưa vào để đẻ ra bản không dấu, bất chấp LLM nói gì
    if core_name:
        aliases.add(core_name)

    # 🔥 2. GOLD ALIAS (ƯU TIÊN CAO NHẤT)
    for a in gold_aliases:
        if a:
            aliases.add(a.strip().lower())

    # 🔥 3. LLM (nếu có)
    for a in entity.get("aliases", []):
        a = a.strip().lower()
        if a:
            aliases.add(a)

    # 🔥 4. SEARCH VARIANT
    extra = set()
    for a in aliases:
        na = remove_accents(a)
        if na:
            extra.add(na)
            extra.add(na.replace(" ", ""))

    aliases.update(extra)

    # Lọc rác rỗng nếu có
    entity["aliases"] = [a for a in list(aliases) if a]
    return entity

# ==========================================================
# STAGE 2 — LLM (ĐÃ CHÈN ENRICH_ALIASES ĐỂ LƯU VÀO CHECKPOINT)
# ==========================================================
def stage_2(raw_vocab):
    checkpoint = load_checkpoint()
    pending = [k for k in raw_vocab if k not in checkpoint]

    for i in range(0, len(pending), 20):
        batch = pending[i:i+20]

        payload = [
            {"id": k, "hint": raw_vocab[k]["c_name"]}
            for k in batch
        ]

        try:
            res = client.models.generate_content(
                model=MODEL_ID,
                config=types.GenerateContentConfig(
                    system_instruction=AI_RECONCILE_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=DICTIONARY_SCHEMA
                ),
                contents=[json.dumps(payload, ensure_ascii=False)]
            )

            parsed = json.loads(res.text)

            for ent in parsed["entities"]:
                cid = ent.get("canonical_id")
                if not cid: continue
                
                # 🔥 LÀM GIÀU DỮ LIỆU NGAY TẠI ĐÂY
                gold_aliases = raw_vocab.get(cid, {}).get("gold_aliases", [])
                ent = enrich_aliases(ent, gold_aliases)
                
                # Cập nhật vào checkpoint
                checkpoint[cid] = ent

            save_checkpoint(checkpoint)
            time.sleep(0.5) # Nghỉ ngơi nhẹ để tránh quá tải API

        except Exception as e:
            print(f"ERROR tại batch {i}:", e)
            time.sleep(2)

    return checkpoint

# ==========================================================
# FILTER
# ==========================================================
def strict_filter(master_map, raw_vocab):
    final = []

    for cid, ent in master_map.items():
        # Dù đã enrich ở stage_2, chạy lại lần nữa vẫn an toàn (nhờ Set)
        # Phòng trường hợp file checkpoint cũ chưa được enrich
        gold_aliases = raw_vocab.get(cid, {}).get("gold_aliases", [])
        ent = enrich_aliases(ent, gold_aliases)
        
        cleaned = []
        seen = set()

        for a in ent.get("aliases", []):
            if not a:
                continue

            if a not in seen:
                seen.add(a)
                cleaned.append(a)

        ent["aliases"] = cleaned
        final.append(ent)

    return sorted(final, key=lambda x: x["canonical_id"])

# ==========================================================
# IO
# ==========================================================
def load_checkpoint():
    if os.path.exists(CHECKPOINT_PATH):
        with open(CHECKPOINT_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def save_checkpoint(data):
    with open(CHECKPOINT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==========================================================
# RUN
# ==========================================================
def run():
    start_time = time.time()

    print("🚀 START STEP 6")

    raw = stage_1()
    print("RAW:", len(raw))

    master = stage_2(raw)

    final = strict_filter(master, raw)

    with open(MASTER_MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print("DONE:", len(final))
    print("TIME:", round(time.time() - start_time, 2))


if __name__ == "__main__":
    run()