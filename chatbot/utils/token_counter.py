import tiktoken

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Đếm số lượng token của chuỗi văn bản.
    Mặc định dùng tokenizer của OpenAI, có thể áp dụng tương đối cho các LLM khác.
    """
    if not text:
        return 0
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback nếu tên model không khớp chuẩn OpenAI
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))