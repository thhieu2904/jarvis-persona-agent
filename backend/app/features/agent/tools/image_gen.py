"""
Image generation tool using Gemini 3 Pro Image.
Generates images from text prompts and uploads them to Supabase Storage.
"""

import uuid
from datetime import datetime, timezone, timedelta
from langchain_core.tools import tool
from app.config import get_settings
from app.core.database import get_supabase_admin_client

STORAGE_BUCKET = "generated-images"
VN_TZ = timezone(timedelta(hours=7))


def _upload_to_supabase(img_data: bytes, mime_type: str) -> str:
    """Upload image bytes to Supabase Storage and return the public URL."""
    ext = "png" if "png" in mime_type else "jpg"
    content_type = f"image/{ext}"
    timestamp = datetime.now(VN_TZ).strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    filename = f"{timestamp}_{unique_id}.{ext}"

    supabase = get_supabase_admin_client()

    # Upload with correct content-type so browsers display inline
    supabase.storage.from_(STORAGE_BUCKET).upload(
        path=filename,
        file=img_data,
        file_options={"content-type": content_type},
    )

    # Build public URL
    public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(filename)
    return public_url


@tool
def generate_image(prompt: str) -> str:
    """Tao hinh anh tu mo ta van ban.
    Dung khi nguoi dung yeu cau tao, ve, hoac minh hoa hinh anh.
    VD: "Ve cho minh hinh con meo", "Tao poster lich hoc", "Minh hoa thoi tiet hom nay".

    Args:
        prompt: Mo ta hinh anh can tao bang tieng Anh hoac tieng Viet.
               VD: "A cute cat studying at university", "Poster lich hoc dai hoc"
    
    Returns:
        Markdown string containing the generated image(s) for display.
    """
    try:
        from google import genai
        from google.genai import types

        settings = get_settings()
        client = genai.Client(api_key=settings.LLM_API_KEY)

        response = client.models.generate_content(
            model=settings.IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        # Extract image parts
        text_parts = []
        image_urls = []

        for part in response.candidates[0].content.parts:
            if part.text:
                text_parts.append(part.text)
            elif part.inline_data:
                img_data = part.inline_data.data
                mime_type = part.inline_data.mime_type
                # Upload to Supabase Storage and get public URL
                public_url = _upload_to_supabase(img_data, mime_type)
                image_urls.append(public_url)

        # Build result string for LLM
        result = ""
        if text_parts:
            result += " ".join(text_parts) + "\n\n"

        if image_urls:
            result += f"prompt: {prompt}\n"
            result += "HINH ANH DA TAO (BAT BUOC hien thi bang cu phap Markdown nhu ben duoi):\n"
            for i, url in enumerate(image_urls, 1):
                result += f"![Hinh anh {i}]({url})\n"
        else:
            result += "Khong tao duoc hinh anh. Thu mo ta chi tiet hon."

        return result

    except Exception as e:
        return f"Loi tao hinh anh: {str(e)}"


# Export
image_tools = [generate_image]
