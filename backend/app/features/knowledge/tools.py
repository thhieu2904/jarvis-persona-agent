"""
Knowledge feature: Agent tools for RAG-based knowledge retrieval.
These are LangChain @tool functions that the LangGraph agent can call.
"""

import json
from typing import Annotated
from langchain_core.tools import tool, InjectedToolArg

from app.core.dependencies import get_db
from app.features.knowledge.service import KnowledgeService


@tool
def search_memories(
    query: str,
    tags: list[str] | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Tìm kiếm trong ký ức/ghi chú của chủ nhân bằng ngữ nghĩa (semantic search).
    Dùng khi chủ nhân hỏi về thông tin đã từng lưu trữ, ví dụ:
    - "Hôm trước tao bảo lưu cái gì ấy nhỉ?"
    - "Mật khẩu wifi gì ấy?"
    - "Ghi chú về buổi họp tuần trước?"

    Args:
        query: Câu hỏi hoặc từ khóa tìm kiếm (tiếng Việt hoặc tiếng Anh).
        tags: Lọc theo tags cụ thể (tùy chọn). Ví dụ: ["wifi", "mật khẩu"]

    Returns:
        Danh sách ghi chú liên quan nhất, sắp xếp theo độ tương đồng.
    """
    db = get_db()
    service = KnowledgeService(db)

    results = service.search_notes_by_vector(
        user_id=user_id,
        query=query,
        top_k=5,
        tags=tags,
    )

    if not results:
        return json.dumps({
            "status": "success",
            "message": "Không tìm thấy ghi chú nào liên quan.",
            "memories": [],
        }, ensure_ascii=False)

    memories = []
    for r in results:
        memories.append({
            "id": r.get("id"),
            "content": r.get("content"),
            "note_type": r.get("note_type"),
            "tags": r.get("tags", []),
            "created_at": r.get("created_at"),
            "similarity": round(r.get("similarity", 0), 4),
        })

    return json.dumps({
        "status": "success",
        "message": f"Tìm thấy {len(memories)} ghi chú liên quan.",
        "memories": memories,
    }, ensure_ascii=False)


@tool
def save_memory(
    content: str,
    tags: list[str] | None = None,
    note_type: str = "memory",
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lưu thông tin quan trọng vào bộ nhớ dài hạn của chủ nhân.
    Dùng khi chủ nhân yêu cầu ghi nhớ điều gì đó, ví dụ:
    - "Nhớ hộ tao mật khẩu wifi là abc123"
    - "Lưu cái này vào não đi"
    - "Ghi nhớ: ngày mai họp lúc 3h"

    Agent NÊN tự động tóm tắt nội dung cuộc trò chuyện trước khi lưu.

    Args:
        content: Nội dung cần ghi nhớ (nên viết rõ ràng, đầy đủ ngữ cảnh).
        tags: Danh sách tag để phân loại. Ví dụ: ["wifi", "mật khẩu"]
        note_type: Loại ghi chú: "memory" (mặc định), "note", "idea", "snippet"

    Returns:
        Xác nhận đã lưu vào bộ nhớ.
    """
    from app.features.notes.service import NotesService

    db = get_db()
    service = NotesService(db)

    note = service.create_note(
        user_id=user_id,
        content=content,
        note_type=note_type,
        tags=tags or [],
    )

    # Trigger embedding calculation (synchronous inside tool since agent runs in background)
    from app.background.embedding_tasks import process_note_embedding
    process_note_embedding(note["id"], content)

    return json.dumps({
        "status": "success",
        "message": f"Đã lưu vào bộ nhớ: '{content[:50]}...'",
        "note_id": note["id"],
        "tags": tags or [],
    }, ensure_ascii=False)


from typing import Literal

@tool
def search_study_materials(
    query: str,
    domain: Literal['study', 'work', 'personal', 'other'] | None = None,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Tìm kiếm kiến thức trong kho tài liệu (PDF, Word) đã được lưu trữ của chủ nhân.
    Dùng khi người dùng hỏi về tài liệu trong kho MÀ KHÔNG đính kèm file trực tiếp.
    
    **QUAN TRỌNG**: KHÔNG gọi tool này nếu tin nhắn đã chứa thẻ [SYS_FILE: ...] và
    block <document_content>...</document_content> — nội dung file đã có sẵn trong tin nhắn,
    hãy đọc trực tiếp từ đó thay vì tìm trong kho.
    
    Args:
        query: Câu hỏi hoặc từ khóa muốn tìm kiếm trong tài liệu.
        domain: (Tùy chọn) Lọc theo thư mục tài liệu để tăng độ chính xác.
            - 'study': Tài liệu học thuật, giáo trình, đề cương môn học.
            - 'work': Tài liệu công việc, dự án, quy trình chuyên môn.
            - 'personal': Sở thích, sách self-help, nấu ăn, thể thao.
            - 'other': Tạp hóa các loại tài liệu không phân loại được.
            
    Returns:
        Danh sách 5 đoạn văn bản (chunks) liên quan nhất trích từ các tài liệu, kèm theo tên file.
        Agent cần đọc các đoạn trích này để tổng hợp câu trả lời cho người dùng.
    """
    db = get_db()
    service = KnowledgeService(db)

    results = service.search_materials_by_vector(
        user_id=user_id,
        query=query,
        top_k=5,
        domain=domain,
    )

    if not results:
        return json.dumps({
            "status": "success",
            "message": "Không tìm thấy tài liệu nào liên quan đến câu hỏi này.",
            "chunks": [],
        }, ensure_ascii=False)

    chunks = []
    for r in results:
        chunks.append({
            "file_name": r.get("file_name"),
            "domain": r.get("domain"),
            "page_number": r.get("page_number"),
            "content": r.get("content"),
            "similarity": round(r.get("similarity", 0), 4),
        })

    return json.dumps({
        "status": "success",
        "message": f"Tìm thấy {len(chunks)} đoạn tài liệu mã hóa bằng vector liên quan nhất.",
        "chunks": chunks,
    }, ensure_ascii=False)


import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.core.database import get_supabase_client

# Thread pool for background document processing (RAG pipeline)
_doc_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="rag_pipeline")

@tool
async def save_temp_document_to_knowledge_base(
    storage_path: str,
    domain: Literal['study', 'work', 'personal', 'other'],
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Lưu trữ vĩnh viễn (Dạy AI) một tài liệu đang được đính kèm tạm thời trong luồng chat.
    Dùng khi file người dùng gửi có chứa thẻ metadata [SYS_FILE: ...] và người dùng yêu cầu "Lưu file này lại", "Đưa file tài liệu này vào kho cho tôi".
    
    Args:
        storage_path: Đường dẫn lưu trữ được lấy từ phần "Path:" trong thẻ [SYS_FILE: ... - Path: storage_path].
                      Ví dụ: "abc123/temp/CHUONG_2_PHP_can_ban.pdf".
                      QUAN TRỌNG: Dùng đúng giá trị Path trong thẻ [SYS_FILE], không tự được cấu tạo lại.
        domain: Phân loại tài liệu vào 1 trong 4 thư mục: 'study', 'work', 'personal', 'other'. Tự suy luận từ yêu cầu của User.
        
    Returns:
        Kết quả di chuyển file và trạng thái chạy tiến trình học RAG.
    """
    db = get_supabase_client()
    # Derive file_name from the end of the storage_path
    file_name = storage_path.split("/")[-1]
    old_path = storage_path
    new_path = f"{user_id}/{domain}/{file_name}"
    
    try:
        # 1. Luân chuyển file từ nhánh /temp sang /domain cố định
        db.storage.from_("knowledge-base").move(old_path, new_path)
        
        # Determine content type manually
        content_type = "application/pdf" if file_name.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if file_name.endswith(".docx") else "text/plain"

        # 2. Tạo bản ghi quản lý vào bảng study_materials
        insert_data = {
            "user_id": user_id,
            "file_name": file_name,
            "file_type": content_type,
            "file_url": new_path,
            "domain": domain,
            "processing_status": "processing"
        }
        res_db = db.table("study_materials").insert(insert_data).execute()
        material_id = res_db.data[0]["id"]
        
        # 3. Tải nội dung bytes về để chạy RAG
        file_res = db.storage.from_("knowledge-base").download(new_path)
        
        # 4. Kích hoạt Background Task chạy RAG (Chunking + Embedding)
        # Dùng ThreadPoolExecutor thay vì bare threading.Thread cho lifecycle management tốt hơn
        from app.background.document_tasks import process_document_pipeline
        
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            _doc_executor,
            process_document_pipeline,
            material_id, user_id, file_res, file_name, content_type,
        )
        
        return json.dumps({
            "status": "success",
            "message": f"Đã bắt đầu quy trình lưu file '{file_name}' vào mục '{domain}'. Tài liệu đang được nhúng vector chạy ngầm.",
            "file_name": file_name,
            "domain": domain
        }, ensure_ascii=False)
        
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": f"Không thể lưu file (File có thể không tồn tại hoặc lỗi): {str(e)}"
        }, ensure_ascii=False)



@tool
def find_study_materials(
    query: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Tìm kiếm tài liệu trong kho Knowledge Base theo tên file.
    Dùng trước khi xóa tài liệu để lấy material_id chính xác.
    Cũng dùng khi user hỏi "Tôi đã có những tài liệu gì?" hoặc "Kiểm tra xem có file X chưa?".
    
    Args:
        query: Từ khóa tên file cần tìm. VD: "PHP", "Express", "giải tích".
    
    Returns:
        Danh sách tài liệu khớp, mỗi item có material_id, file_name, domain, status.
    """
    db = get_supabase_client()
    res = (
        db.table("study_materials")
        .select("id, file_name, domain, processing_status, created_at")
        .eq("user_id", user_id)
        .ilike("file_name", f"%{query}%")
        .limit(10)
        .execute()
    )
    materials = [
        {
            "material_id": r["id"],
            "file_name": r["file_name"],
            "domain": r["domain"],
            "status": r["processing_status"],
        }
        for r in (res.data or [])
    ]
    return json.dumps({
        "found": len(materials),
        "materials": materials,
    }, ensure_ascii=False)


@tool
def delete_study_material(
    material_id: str,
    user_id: Annotated[str, InjectedToolArg] = "",
) -> str:
    """Xóa vĩnh viễn một tài liệu khỏi Knowledge Base.
    Xóa file trên S3, xóa record trong DB, xóa toàn bộ vector embeddings liên quan.
    QUAN TRỌNG: Luôn gọi find_study_materials trước để lấy material_id chính xác.
    Luôn xác nhận với user tên file trước khi gọi tool này.
    
    Args:
        material_id: UUID của tài liệu, lấy từ kết quả find_study_materials.
    
    Returns:
        Kết quả xóa.
    """
    db = get_supabase_client()
    
    # 1. Ownership check + lấy file_url
    res = (
        db.table("study_materials")
        .select("file_name, file_url")
        .eq("id", material_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not res.data:
        return json.dumps({"status": "error", "message": "Không tìm thấy tài liệu hoặc bạn không có quyền xóa."}, ensure_ascii=False)
    
    file_name = res.data[0]["file_name"]
    file_url = res.data[0].get("file_url")
    
    # Synchronous delete so agent can report real success/failure
    # S3 first → DB only if S3 succeeds (avoids orphan files)
    db2 = get_supabase_client()
    if file_url and not file_url.startswith("http"):
        try:
            db2.storage.from_("knowledge-base").remove([file_url])
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Lỗi khi xóa file '{file_name}' trên hệ thống lưu trữ: {str(e)}. Chưa xóa dữ liệu, vui lòng thử lại.",
            }, ensure_ascii=False)
    
    # S3 deleted → now delete DB (CASCADE removes material_chunks)
    db2.table("study_materials").delete().eq("id", material_id).eq("user_id", user_id).execute()
    
    return json.dumps({
        "status": "success",
        "message": f"Đã xóa hoàn toàn tài liệu '{file_name}' khỏi kho kiến thức. AI đã quên nội dung tài liệu này.",
    }, ensure_ascii=False)


# Export all knowledge tools for the agent graph
knowledge_tools = [search_memories, save_memory, search_study_materials, save_temp_document_to_knowledge_base, find_study_materials, delete_study_material]
