import logging
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from app.core.dependencies import get_current_user_id, get_db
from app.core.database import get_supabase_client
from supabase import Client

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Knowledge Base"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    domain: str = Form(..., description="Must be one of: study, work, personal, other"),
    subject: str = Form(None),
    user_id: str = Depends(get_current_user_id),
):
    """
    Tải lên tài liệu (PDF, DOCX, TXT) để dạy cho AI.
    - Lưu file vào Supabase Storage (knowledge-base).
    - Tạo bản ghi trạng thái `processing`.
    - Gọi background task bóc tách, băm nhỏ và nhúng Vector.
    """
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT, and MD files are allowed.")
    
    valid_domains = {"study", "work", "personal", "other"}
    if domain not in valid_domains:
        raise HTTPException(status_code=400, detail=f"Invalid domain. Must be one of: {valid_domains}")

    db = get_supabase_client()
    
    # 1. Khởi tạo đường dẫn an toàn trên Storage
    # knowledge-base/{user_id}/{domain}/{filename}
    safe_filename = secure_filename(file.filename)
    storage_path = f"{user_id}/{domain}/{safe_filename}"
    
    try:
        # Đọc file ra memory
        file_bytes = await file.read()
        
        # 1.1 Chặn dung lượng File (50MB Limit cho Luồng 2 RAG)
        MAX_SIZE_PERSISTENT = 50 * 1024 * 1024 # 50MB
        if len(file_bytes) > MAX_SIZE_PERSISTENT:
             raise HTTPException(status_code=413, detail="File too large. Maximum size for Knowledge Base upload is 50MB.")
        
        # 2. Upload lên Supabase Storage
        res_storage = db.storage.from_("knowledge-base").upload(
            file=file_bytes,
            path=storage_path,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )
        
        # Lấy URL Public (Bỏ public_url vì bucket là private, lưu thẳng storage_path để bảo mật)
        # public_url = db.storage.from_("knowledge-base").get_public_url(storage_path)

        # 3. Tạo bản ghi quản lý vào bảng study_materials
        insert_data = {
            "user_id": user_id,
            "file_name": safe_filename,
            "file_type": file.content_type,
            "file_url": storage_path,  # Lưu storage path thay vì Signed URL hết hạn
            "domain": domain,
            "subject": subject,
            "processing_status": "processing"
        }
        res_db = db.table("study_materials").insert(insert_data).execute()
        material = res_db.data[0]
        material_id = material["id"]

        # 4. Gọi Background Task Rút trích Text và Embedding
        from app.background.document_tasks import process_document_pipeline
        background_tasks.add_task(
            process_document_pipeline, 
            material_id=material_id, 
            user_id=user_id, 
            file_bytes=file_bytes, 
            filename=safe_filename,
            content_type=file.content_type
        )

        return {
            "status": "success",
            "message": "Upload successful. Document is being processed in the background.",
            "data": material
        }

    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


import unicodedata
import re

def secure_filename(filename: str) -> str:
    """Loại bỏ dấu tiếng Việt, ký tự đặc biệt, thay khoảng trắng bằng gạch dưới."""
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[^\w\.-]', '_', filename)
    return filename

@router.post("/extract-text")
async def extract_text_only(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
):
    """
    (Luồng 1: Temporary Context) - Upload từ Chat
    Tải file lên, chỉ bóc tách chữ trả về ngay cho Frontend để nhét vào LUÔN context của LLM.
    KHÔNG lưu Vector, KHÔNG gọi Background Task Chunking.
    File gốc vẫn được lưu tạm vào Storage `knowledge-base/{user_id}/temp/{filename}` để phòng hờ user muốn "Save to Knowledge Base" sau này.
    """
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, TXT, and MD files are allowed.")
        
    db = get_supabase_client()
    safe_filename = secure_filename(file.filename)
    storage_path = f"{user_id}/temp/{safe_filename}"
    
    try:
        file_bytes = await file.read()
        
        # 1. Chặn dung lượng File (10MB Limit) để tránh crash RAM và tràn Context LLM
        MAX_SIZE = 10 * 1024 * 1024 # 10MB
        if len(file_bytes) > MAX_SIZE:
             raise HTTPException(status_code=413, detail="File too large. Maximum size for temporary upload is 10MB.")

        # 2. Lưu tạm file gốc lên S3 (vào thư mục /temp)
        db.storage.from_("knowledge-base").upload(
            file=file_bytes,
            path=storage_path,
            file_options={"content-type": file.content_type, "upsert": "true"}
        )
        
        # 3. Bỏ qua get_public_url vì bucket Private sẽ lỗi 403.
        # Frontend chỉ cần storage_path để hiển thị UI và gọi API lưu vĩnh viễn sau này.
        
        # 4. Bóc chữ trực tiếp, không chunk, không RAG
        from app.background.document_tasks import extract_text_from_bytes
        raw_docs = extract_text_from_bytes(file_bytes, safe_filename)
        
        if not raw_docs:
            full_text = ""
        else:
            full_text = "\n\n".join([doc.page_content for doc in raw_docs])
            
        return {
            "status": "success",
            "message": "Text extracted successfully for temporary context.",
            "data": {
                "file_name": safe_filename,
                "storage_path": storage_path,
                "content": full_text
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Text extraction failed: {str(e)}")

@router.post("/promote")
async def promote_temp_to_knowledge_base(
    background_tasks: BackgroundTasks,
    storage_path: str = Form(..., description="The temporary storage path returned by extract-text API"),
    domain: str = Form(..., description="Target domain: study, work, personal, other"),
    subject: str = Form(None),
    user_id: str = Depends(get_current_user_id)
):
    """
    (Luồng Chat Kế thừa) - Move File từ Temp sang Lưu Trữ và chạy RAG
    Nhận `storage_path` cũ từ UI Chat -> Move file sang thư mục mới -> Gọi Background Task.
    """
    valid_domains = {"study", "work", "personal", "other"}
    if domain not in valid_domains:
        raise HTTPException(status_code=400, detail=f"Invalid domain. Must be one of: {valid_domains}")
        
    if not storage_path.startswith(f"{user_id}/temp/"):
        raise HTTPException(status_code=400, detail="Invalid temporary storage path.")

    db = get_supabase_client()
    filename = storage_path.split("/")[-1]
    new_storage_path = f"{user_id}/{domain}/{filename}"
    
    try:
        # 1. Move file trên Storage
        # https://supabase.com/docs/reference/python/storage-from-move
        db.storage.from_("knowledge-base").move(storage_path, new_storage_path)
        
        # Determine content type manually (weak heuristic but enough for DB recording)
        content_type = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if filename.endswith(".docx") else "text/plain"

        # 2. Add into study_materials DB
        insert_data = {
            "user_id": user_id,
            "file_name": filename,
            "file_type": content_type,
            "file_url": new_storage_path,
            "domain": domain,
            "subject": subject,
            "processing_status": "processing"
        }
        res_db = db.table("study_materials").insert(insert_data).execute()
        material_id = res_db.data[0]["id"]
        
        # 3. Download the bytes strictly for the Background task extraction
        # Because process_document_pipeline expects bytes as input currently
        file_res = db.storage.from_("knowledge-base").download(new_storage_path)
        
        # 4. Trigger the exact same RAG pipeline
        from app.background.document_tasks import process_document_pipeline
        background_tasks.add_task(
            process_document_pipeline, 
            material_id=material_id, 
            user_id=user_id, 
            file_bytes=file_res, 
            filename=filename,
            content_type=content_type
        )
        
        return {
            "status": "success",
            "message": "File promoted successfully. RAG Background task started.",
            "data": res_db.data[0]
        }
        
    except Exception as e:
        logger.error(f"Error promoting file {storage_path}: {str(e)}")
        # If moving failed for some edge case, or if already moved
        raise HTTPException(status_code=500, detail=f"Promotion failed: {str(e)}")


@router.get("/")
async def get_study_materials(user_id: str = Depends(get_current_user_id)):
    """
    Lấy danh sách sách, tài liệu trong Knowledge Base của User.
    Kèm theo presigned URL tải file (hết hạn sau 60 phút) vì bucket Private.
    """
    db = get_supabase_client()
    try:
        res = db.table("study_materials").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        materials = res.data
        
        # Sinh signed URL cho từng file (do stored path trong 'file_url' column)
        for m in materials:
            storage_path = m.get("file_url")
            if storage_path and not storage_path.startswith("http"):
                try:
                    signed_url = db.storage.from_("knowledge-base").create_signed_url(storage_path, 3600)
                    m["download_url"] = signed_url.get("signedURL")
                except Exception as ex:
                    logger.warning(f"Could not generate signed URL for {storage_path}: {ex}")
                    m["download_url"] = None
            else:
                m["download_url"] = storage_path
                
        return {
            "status": "success",
            "data": materials
        }
    except Exception as e:
        logger.error(f"Error fetching materials: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch materials: {str(e)}")


@router.delete("/{material_id}")
async def delete_study_material(
    material_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Xóa tài liệu khỏi Knowledge Base.
    - Xóa metadata trong DB (Cascasde xóa luôn Vector Embeddings).
    - Xóa dọn file gốc trên Supabase S3 (Storage) để tránh rác.
    """
    db = get_supabase_client()
    try:
        # Lấy file_url (lúc này là storage path) để xóa trên Storage
        res = db.table("study_materials").select("file_url").eq("id", material_id).eq("user_id", user_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Material not found")
            
        storage_path = res.data[0].get("file_url")
        
        # 1. Xóa trên DB (Cascade vật lý)
        db.table("study_materials").delete().eq("id", material_id).eq("user_id", user_id).execute()
        
        # 2. Dọn rác S3
        if storage_path and not storage_path.startswith("http"):
             db.storage.from_("knowledge-base").remove([storage_path])
             
        return {"status": "success", "message": "Material and associated storage clean up successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting material: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete material: {str(e)}")


