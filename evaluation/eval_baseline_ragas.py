import os
import sys
import json
import asyncio
import pandas as pd
from datasets import Dataset

# Đảm bảo import được các module từ thư mục gốc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# TRỌNG TÂM: Import các hàm từ Baseline Pipeline thay vì NLU Engine (Hệ thống chính)
from chatbot.baseline_rule_based import (
    advanced_rule_based_extract_intent,
    execute_graph_query,
    baseline_summarize_answer
)

# Import từ Ragas và LangChain
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    answer_correctness,
    context_recall,
)
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

# 1. Cấu hình môi trường Google AI Studio API Key
def get_gemini_api_key():
    from app.models.base_db import db
    # 1. Thử lấy từ Database settings
    try:
        db_key = db.get_setting("gemini_api_key")
        if db_key: return db_key
    except Exception:
        pass
    # 2. Thử lấy từ settings
    try:
        if getattr(settings, "GEMINI_API_KEY", None): return settings.GEMINI_API_KEY
    except Exception:
        pass
    # 3. Thử lấy từ os.environ
    env_key = os.environ.get("GEMINI_API_KEY")
    if env_key: return env_key
    # 4. Thử lấy từ fallback keys của Database
    try:
        fallback_str = db.get_setting("gemini_fallback_keys")
        if fallback_str:
            keys = [k.strip() for k in fallback_str.split(",") if k.strip()]
            for k in keys:
                if (k.startswith("'") and k.endswith("'")) or (k.startswith('"') and k.endswith('"')):
                    k = k[1:-1].strip()
                if k: return k
    except Exception:
        pass
    return None

gemini_key = get_gemini_api_key()
if not gemini_key:
    raise ValueError("Chưa cấu hình Google Gemini API Key trong hệ thống.")
os.environ["GOOGLE_API_KEY"] = gemini_key

# Đảm bảo thư mục lưu kết quả Baseline tồn tại
OUTPUT_DIR = getattr(settings, "DIR_BASELINE_EVAL_OUT", os.path.join(settings.DIR_EVALUATION, "baseline_output"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 2. Khởi tạo Giám khảo (Ragas Judge) và Embedding bằng Gemini
print("🔄 Đang khởi tạo Giám khảo AI (Gemini) cho Baseline...")
try:
    judge_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0
    )
    
    judge_embeddings = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004"
    )
except Exception as e:
    print(f"❌ Lỗi khởi tạo Giám khảo AI / Embedding: {e}")
    exit()

async def process_baseline_single_question(item):
    """Hàm chạy luồng Baseline (Rule-based -> Direct Neo4j -> Single-Agent)"""
    question = item["question"]
    try:
        # Bước 1: Baseline NLU bóc tách intent (Dùng Rule/Regex tĩnh)
        nlu_res = advanced_rule_based_extract_intent(question)
        
        if not nlu_res or not nlu_res.get("cypher"):
            return question, "Lỗi NLU Baseline", "UNKNOWN", []

        # Bước 2: Truy vấn Neo4j trực tiếp bằng hàm của Baseline
        graph_data = await execute_graph_query(nlu_res["cypher"])
        
        # Bước 3: Baseline AI sinh câu trả lời (Không qua Agent 3 Giám khảo)
        actual_answer = await baseline_summarize_answer(
            user_query=question,
            graph_data=graph_data,
            model_name=settings.MODEL_ID
        )
        
        return question, actual_answer, nlu_res["intent"], graph_data
    
    except Exception as e:
        print(f"❌ Lỗi Baseline tại ID {item.get('id', 'Unknown')}: {e}")
        return question, "Lỗi hệ thống Baseline.", "ERROR", []

async def run_baseline_evaluation(input_file="complex_kg_qa_dataset.json", sample_size=240):
    dataset_path = os.path.join(settings.DIR_EVALUATION, input_file)
    if not os.path.exists(dataset_path):
        print(f"❌ Không tìm thấy file dữ liệu tại: {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    test_samples = raw_data[:sample_size]
    
    evaluation_data = {
        "question": [],
        "contexts": [],
        "answer": [],
        "ground_truth": []
    }

    print(f"\n🤖 Baseline đang giải quyết {sample_size} câu hỏi...")
    
    # === CƠ CHẾ LƯU NHÁP (CHECKPOINT) AN TOÀN ===
    intermediate_output_path = os.path.join(OUTPUT_DIR, "baseline_inference_cache.json")
    
    for idx, item in enumerate(test_samples):
        print(f"[{idx+1}/{sample_size}] Baseline đang xử lý: {item['question']}")
        
        q, ans, intent, retrieved_graph = await process_baseline_single_question(item)
        
        evaluation_data["question"].append(q)
        
        # Đóng gói ngữ cảnh thô từ Baseline để Ragas đối chiếu
        actual_context_str = json.dumps(retrieved_graph, ensure_ascii=False) if retrieved_graph else "Không có dữ liệu"
        evaluation_data["contexts"].append([actual_context_str]) 
        
        evaluation_data["answer"].append(ans)
        evaluation_data["ground_truth"].append(item["expected_answer_full"])

        # Ghi đè file lưu nháp sau mỗi câu hỏi để tránh mất dữ liệu nếu đứt mạng
        with open(intermediate_output_path, "w", encoding="utf-8") as f:
            json.dump(evaluation_data, f, ensure_ascii=False, indent=4)

    # Chuyển thành dạng dữ liệu HuggingFace Dataset
    eval_dataset = Dataset.from_dict(evaluation_data)

    print(f"\n✅ Đã lưu kết quả suy luận thô (Inference Cache) an toàn tại: {intermediate_output_path}")
    print("⚖️ Đang chuyển dữ liệu Baseline cho Ragas chấm điểm (Có thể mất vài phút)...")
    
    try:
        result = evaluate(
            dataset=eval_dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,     
                answer_correctness,
            ],
            llm=judge_llm,
            embeddings=judge_embeddings
        )
    except Exception as e:
        print(f"❌ Ragas Evaluation thất bại: {e}")
        print(f"💡 Dữ liệu suy luận vẫn được an toàn tại: {intermediate_output_path}")
        return

    # Lưu báo cáo chi tiết cho Baseline
    df = result.to_pandas()
    output_csv = os.path.join(OUTPUT_DIR, "ragas_baseline_report.csv")
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")
    
    # Tính toán các chỉ số trung bình
    mean_faithfulness = df['faithfulness'].mean()
    mean_answer_relevancy = df['answer_relevancy'].mean()
    mean_context_precision = df['context_precision'].mean()
    mean_context_recall = df['context_recall'].mean()
    mean_answer_correctness = df['answer_correctness'].mean()

    # Lưu báo cáo tổng quan
    summary_data = {
        "system": "Advanced Sequential Pipeline (Baseline)",
        "sample_size": sample_size,
        "metrics": {
            "faithfulness": mean_faithfulness,
            "answer_relevancy": mean_answer_relevancy,
            "context_precision": mean_context_precision,
            "context_recall": mean_context_recall,
            "answer_correctness": mean_answer_correctness
        }
    }
    summary_json = os.path.join(OUTPUT_DIR, "ragas_baseline_summary.json")
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=4)

    # In kết quả ra màn hình
    print("\n" + "=".center(60, "="))
    print("📊 BÁO CÁO TỔNG QUAN BASELINE RAGAS SCORE")
    print(f"1. Faithfulness (Không ảo giác) : {mean_faithfulness:.4f}")
    print(f"2. Answer Relevance (Đúng ý)  : {mean_answer_relevancy:.4f}")
    print(f"3. Context Precision (Ngữ cảnh chuẩn): {mean_context_precision:.4f}")
    print(f"4. Context Recall (Độ phủ ngữ cảnh): {mean_context_recall:.4f}") 
    print(f"5. Answer Correctness (Chuẩn xác) : {mean_answer_correctness:.4f}")
    print("=".center(60, "="))
    print(f"✅ Báo cáo chi tiết Baseline đã lưu tại: {output_csv}")
    print(f"✅ Chỉ số trung bình Baseline đã lưu tại: {summary_json}")

if __name__ == "__main__":
    # Chạy thực nghiệm đánh giá 240 câu hỏi trên hệ thống Baseline
    asyncio.run(run_baseline_evaluation(sample_size=240))