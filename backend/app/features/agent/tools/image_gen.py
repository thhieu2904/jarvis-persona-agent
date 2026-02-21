"""
Image generation tool using Gemini 3 Pro Image (Nano Banana Pro).
Supports: text-to-image, grounded generation (with Google Search).
"""

import os
import base64
from langchain_core.tools import tool


@tool
def generate_image(prompt: str) -> str:
    """Tao hinh anh tu mo ta van ban.
    Dung khi nguoi dung yeu cau tao, ve, hoac minh hoa hinh anh.
    VD: "Ve cho minh hinh con meo", "Tao poster lich hoc", "Minh hoa thoi tiet hom nay".

    Args:
        prompt: Mo ta hinh anh can tao bang tieng Anh hoac tieng Viet.
               VD: "A cute cat studying at university", "Poster lich hoc dai hoc"
    
    Returns:
        Thong bao thanh cong va duong dan file anh da luu.
    """
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("LLM_API_KEY"))

        response = client.models.generate_content(
            model=os.getenv("IMAGE_MODEL", "gemini-3-pro-image-preview"),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        # Extract image parts
        text_parts = []
        image_count = 0
        saved_paths = []

        for part in response.candidates[0].content.parts:
            if part.text:
                text_parts.append(part.text)
            elif part.inline_data:
                image_count += 1
                # Save image to temp file
                img_data = part.inline_data.data
                ext = "png" if "png" in part.inline_data.mime_type else "jpg"
                filename = f"generated_image_{image_count}.{ext}"
                filepath = os.path.join(os.getcwd(), filename)
                
                with open(filepath, "wb") as f:
                    f.write(img_data)
                saved_paths.append(filepath)

        result = ""
        if text_parts:
            result += " ".join(text_parts) + "\n"
        if saved_paths:
            result += f"Da tao {image_count} hinh anh:\n"
            for p in saved_paths:
                result += f"  - {p}\n"
        else:
            result += "Khong tao duoc hinh anh. Thu mo ta chi tiet hon."

        return result

    except Exception as e:
        return f"Loi tao hinh anh: {str(e)}"


# Export
image_tools = [generate_image]
