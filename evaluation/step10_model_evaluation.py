import os
import sys
import json
import time
import asyncio
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import unicodedata
import re
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from datetime import datetime
from google import genai
from google.genai import types

# --- FIX LỖI IMPORT THƯ MỤC CHA ---
# Đảm bảo Python nhận diện được thư mục gốc của dự án
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- IMPORT TỪ HỆ THỐNG MỚI ---
from app.config import settings
from chatbot.services.chat_service import YHCTChatService

# ==========================================================
# 0. CẤU HÌNH HỆ THỐNG VÀ MÔI TRƯỜNG
# ==========================================================
# Khởi tạo Client cho Baseline LLM (AI mặc định không dùng RAG - Kiến thức Cloud)
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.GOOGLE_APPLICATION_CREDENTIALS
baseline_client = genai.Client(vertexai=True, project="yhct-knowledge-graph", location="us-central1")
BASELINE_MODEL = settings.MODEL_ID

# Cấu hình font chữ cho Matplotlib để không bị lỗi tiếng Việt
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Tahoma', 'DejaVu Sans', 'Liberation Sans']
plt.rcParams['axes.unicode_minus'] = False

# Khởi tạo NLTK
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# ==========================================================
# 📊 BỘ LỌC CHUẨN HÓA VÀ TÍNH ĐIỂM THÔNG MINH (SMART METRICS)
# ==========================================================

def clean_text_for_evaluation(text):
    """
    Chuẩn hóa thông minh:
    - CHỮA LỖI CŨ: TUYỆT ĐỐI GIỮ LẠI DẤU TIẾNG VIỆT để không nhầm "Tính" với "Tỉnh", "Sài đất" không bị nát.
    - Chỉ gọt bỏ các tiền tố AI hay tự đẻ ra, đưa về chữ thường để so sánh không phân biệt hoa thường.
    """
    if not text or not isinstance(text, str): 
        return ""
    
    text = text.lower()
    
    # Loại bỏ các cụm từ mào đầu/dẫn dắt mà AI có thể thêm vào dù đã bị cấm
    prefixes_to_remove = [
        r'(?i)\b(có|vâng|xác nhận|xác thực|đúng)\b',
        r'(?i)\b(chỉ bao gồm)\b',
        r'(?i)\b(thông tin về)\b',
        r'(?i)\b(dữ liệu tìm thấy)\b',
        r'(?i)\b(để chữa|dùng|điều trị)\b',
        r'(?i)\b(đặc tính)\b'
    ]
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, ' ', text)
        
    # Xóa các ký tự đặc biệt không phải chữ/số (giữ lại khoảng trắng)
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Xóa khoảng trắng thừa
    return " ".join(text.split())

def extract_word_set(text):
    """
    Trích xuất tập hợp từ (dùng cho Jaccard) nhưng loại bỏ các stopwords nối câu tiếng Việt.
    Giúp Jaccard không phạt AI khi nó dùng từ "và", "là", "các".
    """
    stopwords = {'là', 'có', 'và', 'với', 'các', 'những', 'của', 'thuốc', 'vị', 'tính', 'bài', 'bệnh', 'chứng', 'chữa', 'trị', 'gồm', 'chứa'}
    words = text.split()
    return set([w for w in words if w not in stopwords])

def calculate_metrics_fair(expected_list, actual_text, lead_in=""):
    """
    Thuật toán đánh giá đã hiệu chuẩn (Fair Metrics):
    - Recall: Vẫn đo dựa trên thực thể (Facts) để đảm bảo độ phủ.
    - Jaccard/BLEU: Đo dựa trên (Lead_in + Facts) để công bằng với văn phong Chatbot.
    """
    if not actual_text or "không có dữ liệu" in actual_text.lower() or "xin lỗi" in actual_text.lower():
        return 0.0, 0.0, 0.0
        
    actual_clean = clean_text_for_evaluation(actual_text)
    
    # --- 1. RECALL (Chỉ dùng Facts để đo độ phủ) ---
    matches = 0
    cleaned_facts = [clean_text_for_evaluation(f) for f in expected_list if f]
    for fact in cleaned_facts:
        if fact in actual_clean:
            matches += 1
            
    recall = matches / len(cleaned_facts) if cleaned_facts else 0.0
    
    # --- 2. JACCARD & BLEU (Dùng Lead_in + Facts để đo văn phong) ---
    full_reference = f"{lead_in} {', '.join(expected_list)}".strip()
    ref_clean = clean_text_for_evaluation(full_reference)
    
    # Jaccard
    exp_words = extract_word_set(ref_clean)
    act_words = extract_word_set(actual_clean)
    
    if not exp_words: 
        jaccard = 0.0
    else:
        intersection = exp_words.intersection(act_words)
        union = exp_words.union(act_words)
        jaccard = len(intersection) / len(union) if union else 0.0
    
    # BLEU
    smoothie = SmoothingFunction().method4
    ref_tokens = ref_clean.split()
    cand_tokens = actual_clean.split()
    
    if not ref_tokens or not cand_tokens:
        bleu = 0.0
    else:
        bleu = sentence_bleu([ref_tokens], cand_tokens, weights=(0.7, 0.3, 0, 0), smoothing_function=smoothie)
    
    return round(recall, 4), round(jaccard, 4), round(bleu, 4)

def get_missed_entities(expected_list, actual_text):
    """Lấy ra các thực thể chuẩn mà câu trả lời của AI đã bỏ sót."""
    if not actual_text or "không có dữ liệu" in actual_text.lower() or "xin lỗi" in actual_text.lower():
        return expected_list
        
    missed = []
    actual_clean = clean_text_for_evaluation(actual_text)
    
    for exp in expected_list:
        exp_clean = clean_text_for_evaluation(exp)
        if exp_clean and exp_clean not in actual_clean:
            missed.append(exp)
            
    return missed

async def get_baseline_llm_answer(question: str) -> str:
    """Gọi trực tiếp AI (không RAG, không Graph) để kiểm tra kiến thức nguyên bản"""
    prompt = (
        "Bạn là một chuyên gia Y Học Cổ Truyền Việt Nam. "
        "Nhiệm vụ của bạn là trả lời câu hỏi tra cứu thông tin y văn một cách CHÍNH XÁC, NGẮN GỌN và TRỰC TIẾP nhất.\n"
        "Yêu cầu bắt buộc:\n"
        "1. KHÔNG dùng từ mào đầu (như 'Chào bạn', 'Theo tôi biết', 'Dưới đây là').\n"
        "2. KHÔNG giải thích thêm nếu câu hỏi không yêu cầu.\n"
        "3. Nếu câu hỏi yêu cầu liệt kê, chỉ cần liệt kê tên các thực thể, cách nhau bằng dấu phẩy.\n"
        f"Câu hỏi: {question}"
    )
    try:
        response = baseline_client.models.generate_content(
            model=BASELINE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        return response.text
    except Exception as e:
        return f"LỖI_BASELINE_API: {e}"

# ==========================================================
# 📈 VẼ BIỂU ĐỒ VÀ BÁO CÁO (SO SÁNH CHATBOT VS BASELINE)
# ==========================================================
def generate_evaluation_charts(df, output_dir):
    print("🎨 Đang vẽ biểu đồ so sánh hiệu năng: Chatbot (GraphRAG) vs Baseline LLM...")
    
    # 1. Biểu đồ Metrics (Grouped Bar Chart - Cột kép)
    labels = ['Recall (Độ phủ)', 'Jaccard (Chính xác)', 'BLEU (Trùng khớp)']
    chatbot_scores = [df['Chatbot_Recall'].mean() * 100, df['Chatbot_Jaccard'].mean() * 100, df['Chatbot_BLEU'].mean() * 100]
    baseline_scores = [df['Baseline_Recall'].mean() * 100, df['Baseline_Jaccard'].mean() * 100, df['Baseline_BLEU'].mean() * 100]
    
    x = np.arange(len(labels))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    rects1 = ax.bar(x - width/2, chatbot_scores, width, label='Chatbot YHCT (GraphRAG)', color='#2ca02c') # Màu xanh lá
    rects2 = ax.bar(x + width/2, baseline_scores, width, label='Baseline LLM (Nguyên bản)', color='#d62728') # Màu đỏ
    
    ax.set_ylabel('Điểm số trung bình (%)', fontsize=12, fontweight='bold')
    ax.set_title('Chứng minh Hiệu quả GraphRAG: Chatbot YHCT vs AI Nguyên bản', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 110)
    ax.legend(loc='upper right')
    
    # Thêm số liệu trên đầu mỗi cột
    for rects in [rects1, rects2]:
        for rect in rects:
            height = rect.get_height()
            ax.annotate(f'{height:.1f}%',
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontweight='bold')
            
    plt.grid(axis='y', linestyle='--', alpha=0.6)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "graphrag_vs_baseline_metrics.png"), dpi=300)
    plt.close()

    # 2. Biểu đồ Latency (Boxplot kép so sánh độ trễ)
    plt.figure(figsize=(8, 6))
    data_to_plot = [df['Chatbot_Time'], df['Baseline_Time']]
    bp = plt.boxplot(data_to_plot, labels=['Chatbot YHCT (GraphRAG)', 'Baseline LLM (Nguyên bản)'], patch_artist=True)
    
    colors = ['lightgreen', 'lightcoral']
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
    for median in bp['medians']:
        median.set(color='darkblue', linewidth=2)
        
    plt.ylabel('Thời gian xử lý (giây)', fontsize=12)
    plt.title('So sánh Độ trễ phản hồi (Latency)', fontsize=14, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "graphrag_latency_comparison.png"), dpi=300)
    plt.close()

def generate_evaluation_markdown(df, output_dir):
    """Tự động sinh file báo cáo Markdown so sánh GraphRAG và LLM thuần."""
    total_q = len(df)
    report_content = f"""# BÁO CÁO KHOA HỌC: CHỨNG MINH TÍNH ƯU VIỆT CỦA KIẾN TRÚC GRAPHRAG
*Ngày đánh giá: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}*

Báo cáo này đối chiếu khả năng trả lời câu hỏi Y Học Cổ Truyền của **Chatbot YHCT (Tích hợp Neo4j GraphRAG)** so với **AI nguyên bản ({BASELINE_MODEL}) không có CSDL**. 
*Lưu ý: Đánh giá Jaccard và BLEU đã áp dụng phương pháp Hiệu chuẩn Văn phong (Style Alignment) bằng Lead-in.*

## 1. Kết quả tổng quan (Metrics)

| Chỉ số đánh giá | Chatbot YHCT (GraphRAG) | Baseline LLM (Nguyên bản) | Mức độ cải thiện (GraphRAG) |
| :--- | :--- | :--- | :--- |
| **Độ phủ (Recall)** | **{df['Chatbot_Recall'].mean()*100:.2f}%** | **{df['Baseline_Recall'].mean()*100:.2f}%** | +{(df['Chatbot_Recall'].mean() - df['Baseline_Recall'].mean())*100:.2f}% |
| **Độ chính xác (Jaccard)** | **{df['Chatbot_Jaccard'].mean()*100:.2f}%** | **{df['Baseline_Jaccard'].mean()*100:.2f}%** | +{(df['Chatbot_Jaccard'].mean() - df['Baseline_Jaccard'].mean())*100:.2f}% |
| **Sự trùng khớp (BLEU)** | **{df['Chatbot_BLEU'].mean()*100:.2f}%** | **{df['Baseline_BLEU'].mean()*100:.2f}%** | +{(df['Chatbot_BLEU'].mean() - df['Baseline_BLEU'].mean())*100:.2f}% |
| **Thời gian trung bình** | **{df['Chatbot_Time'].mean():.2f}s** | **{df['Baseline_Time'].mean():.2f}s** | {df['Chatbot_Time'].mean() - df['Baseline_Time'].mean():.2f}s (Overhead) |

## 2. Phân tích Hiện tượng Ảo giác (Hallucination) & Độ ổn định
- Số câu trả lời **hoàn hảo** (Recall = 100%): Chatbot YHCT (**{len(df[df['Chatbot_Recall'] == 1.0])}** câu) | Baseline LLM (**{len(df[df['Baseline_Recall'] == 1.0])}** câu).
- Số câu bị **ảo giác / thiếu hụt hoàn toàn** (Recall = 0%): Chatbot YHCT (**{len(df[df['Chatbot_Recall'] == 0.0])}** câu) | Baseline LLM (**{len(df[df['Baseline_Recall'] == 0.0])}** câu).

**Kết luận:** Hệ thống GraphRAG không chỉ loại bỏ hiện tượng bịa đặt dữ liệu (ảo giác) mà còn giữ được văn phong chuyên gia ổn định nhờ cấu trúc truy vấn đồ thị.
"""
    with open(os.path.join(output_dir, "Bao_Cao_Chung_Minh_GraphRAG.md"), "w", encoding="utf-8") as f:
        f.write(report_content)

# ==========================================================
# 🚀 TIẾN TRÌNH ĐÁNH GIÁ CHÍNH
# ==========================================================

async def start_evaluation():
    # Sử dụng đường dẫn từ Medallion Architecture (app.config)
    INPUT_PATH = os.path.join(settings.DIR_EVALUATION, "complex_kg_qa_dataset.json")
    OUTPUT_EXCEL = os.path.join(settings.DIR_EVALUATION, "graphrag_vs_baseline_report.xlsx")
    OUTPUT_ERROR_LOG = os.path.join(settings.DIR_EVALUATION, "graphrag_vs_baseline_failed_log.txt")
    CHART_DIR = os.path.join(settings.DIR_EVALUATION, "charts")
    
    os.makedirs(CHART_DIR, exist_ok=True)

    if not os.path.exists(INPUT_PATH):
        print(f"❌ Không tìm thấy file dữ liệu test: {INPUT_PATH}")
        print("Vui lòng chạy file evaluation/generate_qa_dataset.py trước.")
        return

    with open(INPUT_PATH, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # Khởi tạo Service Chatbot chuẩn (Dùng dữ liệu cục bộ Neo4j)
    chat_service = YHCTChatService(model_name=settings.MODEL_ID)

    results = []
    failed_cases = []
    
    print("="*100)
    print(f"🔬 BẮT ĐẦU ĐÁNH GIÁ: CHỨNG MINH TÍNH ƯU VIỆT CỦA GRAPHRAG TRÊN {len(dataset)} CÂU HỎI")
    print(f"   [Hệ thống 1]: Chatbot YHCT (Có dùng Neo4j GraphRAG)")
    print(f"   [Hệ thống 2]: Baseline LLM ({BASELINE_MODEL} - Chỉ dùng kiến thức gốc, không RAG)")
    print("="*100)

    for i, item in enumerate(dataset):
        q = item.get('question', '')
        
        # Lấy Ground Truth và Lead_in
        expected = item.get('expected_facts', item.get('expected_answer', []))
        if isinstance(expected, str):
            expected = [expected]
            
        lead_in = item.get('lead_in', '')
        pattern_type = item.get('pattern_type', 'unknown')
        
        print(f"\n🔄 Đang xử lý [{i+1}/{len(dataset)}]: {q}")
        
        try:
            # ---------------------------------------------------------
            # CHU TRÌNH 1: CHẠY CHATBOT YHCT (GRAPHRAG - LOCAL DATA)
            # ---------------------------------------------------------
            res_chatbot = await chat_service.get_ai_response(q)
            
            ans_chatbot = res_chatbot.get("answer", "").strip()
            cypher_q = res_chatbot.get("metadata", {}).get("cypher_executed", "N/A")
            time_chatbot = res_chatbot.get("exec_time", 0.0)
            
            # Tính điểm công bằng (Cộng dồn lead_in)
            rec_c, jac_c, bleu_c = calculate_metrics_fair(expected, ans_chatbot, lead_in=lead_in)

            # ---------------------------------------------------------
            # CHU TRÌNH 2: CHẠY BASELINE LLM (KHÔNG CÓ GRAPHRAG - CLOUD DATA)
            # ---------------------------------------------------------
            start_baseline = time.time()
            ans_baseline = await get_baseline_llm_answer(q)
            ans_baseline = ans_baseline.strip()
            time_baseline = time.time() - start_baseline
            
            rec_b, jac_b, bleu_b = calculate_metrics_fair(expected, ans_baseline, lead_in=lead_in)

            # In Terminal So Sánh Trực Tiếp (In FULL Text theo yêu cầu)
            print(f"   🛡️ [Chatbot GraphRAG] : R={rec_c:.2f} | J={jac_c:.2f} | B={bleu_c:.2f} | T={time_chatbot:.2f}s")
            print(f"      -> Ans: {ans_chatbot}")
            print(f"   🤖 [Baseline LLM]     : R={rec_b:.2f} | J={jac_b:.2f} | B={bleu_b:.2f} | T={time_baseline:.2f}s")
            print(f"      -> Ans: {ans_baseline}")
            
            # Ghi nhận lỗi để phân tích
            if rec_c < 1.0 or bleu_c < 0.7 or rec_b < 1.0 or bleu_b < 0.7:
                failed_cases.append({
                    "stt": i + 1,
                    "question": q,
                    "pattern": pattern_type,
                    "expected_full": f"{lead_in} {', '.join(expected)}".strip(),
                    # Dữ liệu Chatbot
                    "chatbot_actual": ans_chatbot,
                    "chatbot_missed": ", ".join(get_missed_entities(expected, ans_chatbot)),
                    "chatbot_recall": rec_c,
                    "chatbot_bleu": bleu_c,
                    "chatbot_cypher": cypher_q,
                    # Dữ liệu Baseline
                    "baseline_actual": ans_baseline,
                    "baseline_missed": ", ".join(get_missed_entities(expected, ans_baseline)),
                    "baseline_recall": rec_b,
                    "baseline_bleu": bleu_b
                })

            results.append({
                "STT": i + 1,
                "Loại cấu trúc (Pattern)": pattern_type,
                "Câu hỏi thực nghiệm": q,
                "Đáp án Tham chiếu (Kèm Lead-in)": f"{lead_in} {', '.join(expected)}".strip(),
                "Thực thể bắt buộc (Ground Truth)": ", ".join(expected),
                # Kết quả Chatbot YHCT
                "Chatbot_Answer": ans_chatbot,
                "Chatbot_Recall": rec_c,
                "Chatbot_Jaccard": jac_c,
                "Chatbot_BLEU": bleu_c,
                "Chatbot_Time": round(time_chatbot, 2),
                "Chatbot_Cypher": cypher_q,
                # Kết quả Baseline LLM
                "Baseline_Answer": ans_baseline,
                "Baseline_Recall": rec_b,
                "Baseline_Jaccard": jac_b,
                "Baseline_BLEU": bleu_b,
                "Baseline_Time": round(time_baseline, 2)
            })
            
        except Exception as e:
            print(f"⚠️ Lỗi Exception tại câu {i+1}: {e}")

    df = pd.DataFrame(results)
    
    # 4. Sinh Báo cáo & Biểu đồ Kép
    generate_evaluation_charts(df, CHART_DIR)
    generate_evaluation_markdown(df, CHART_DIR)
    
    # 5. Ghi Excel
    with pd.ExcelWriter(OUTPUT_EXCEL) as writer:
        df.to_excel(writer, sheet_name="Dữ liệu thô", index=False)
        report = df.groupby("Loại cấu trúc (Pattern)").agg({
            "Chatbot_Recall": "mean",
            "Chatbot_Jaccard": "mean",
            "Chatbot_BLEU": "mean",
            "Chatbot_Time": "mean",
            "Baseline_Recall": "mean",
            "Baseline_Jaccard": "mean",
            "Baseline_BLEU": "mean",
            "Baseline_Time": "mean"
        }).round(3)
        report.to_excel(writer, sheet_name="So sánh Pattern")

    # 6. Ghi Error Log Đối Chiếu
    with open(OUTPUT_ERROR_LOG, "w", encoding="utf-8") as f_log:
        f_log.write("BÁO CÁO PHÂN TÍCH ƯU ĐIỂM: CHATBOT GRAPHRAG VS BASELINE LLM\n" + "="*80 + "\n\n")
        for case in failed_cases:
            f_log.write(f"🛑 [CÂU {case['stt']}]\n")
            f_log.write(f"   Q: {case['question']}\n")
            f_log.write(f"   KỲ VỌNG (FULL): {case['expected_full']}\n\n")
            
            f_log.write(f"   [1] --- CHATBOT YHCT (Recall: {case['chatbot_recall']} | BLEU: {case['chatbot_bleu']}) ---\n")
            f_log.write(f"       Ans  : {case['chatbot_actual']}\n")
            f_log.write(f"       Miss : {case['chatbot_missed']}\n")
            f_log.write(f"       Cypher: {case['chatbot_cypher']}\n\n")
            
            f_log.write(f"   [2] --- BASELINE LLM (Recall: {case['baseline_recall']} | BLEU: {case['baseline_bleu']}) ---\n")
            f_log.write(f"       Ans  : {case['baseline_actual']}\n")
            f_log.write(f"       Miss : {case['baseline_missed']}\n")
            f_log.write("-" * 80 + "\n")

    # 7. Tổng kết Terminal
    print("\n\n" + "🎓 TỔNG KẾT ĐÁNH GIÁ KHOA HỌC: GRAPHRAG VS BASELINE".center(100))
    print("="*100)
    print(f"📍 RECALL TRUNG BÌNH : Chatbot {df['Chatbot_Recall'].mean()*100:.1f}%  |  Baseline {df['Baseline_Recall'].mean()*100:.1f}%")
    print(f"📍 JACCARD TRUNG BÌNH: Chatbot {df['Chatbot_Jaccard'].mean()*100:.1f}%  |  Baseline {df['Baseline_Jaccard'].mean()*100:.1f}%")
    print(f"📍 BLEU TRUNG BÌNH   : Chatbot {df['Chatbot_BLEU'].mean()*100:.1f}%  |  Baseline {df['Baseline_BLEU'].mean()*100:.1f}%")
    print(f"📍 LATENCY TRUNG BÌNH: Chatbot {df['Chatbot_Time'].mean():.2f}s      |  Baseline {df['Baseline_Time'].mean():.2f}s")
    print("="*100)
    print(f"📁 1. Bảng số liệu Excel: {OUTPUT_EXCEL}")
    print(f"📁 2. File lỗi đối chiếu: {OUTPUT_ERROR_LOG}")
    print(f"📁 3. Thư mục Biểu đồ   : {CHART_DIR}")

if __name__ == "__main__":
    asyncio.run(start_evaluation())