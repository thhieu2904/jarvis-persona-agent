"""
General-purpose tools: web search & website scraping.
Uses Tavily — an AI-optimized search engine that returns clean,
contextual results instead of raw snippets.
"""

from langchain_core.tools import tool
from tavily import TavilyClient

from app.config import get_settings

_settings = get_settings()
_client = TavilyClient(api_key=_settings.TAVILY_API_KEY) if _settings.TAVILY_API_KEY else None


@tool
def search_web(query: str) -> str:
    """Tim kiem thong tin tren internet theo thoi gian thuc.
    BAT BUOC su dung khi nguoi dung hoi ve:
    - Thoi tiet (VD: "thoi tiet Tra Vinh hom nay")
    - Tin tuc, su kien moi nhat
    - Gia vang, chung khoan, ti gia
    - Bat ky thong tin nao can cap nhat moi nhat tu internet
    - Thong tin ma ban KHONG co san trong cac tool khac

    Args:
        query: Cau tim kiem ngan gon, sat nghia. VD: "thoi tiet Tra Vinh hom nay", "gia vang SJC"

    Returns:
        Ket qua tim kiem tu internet (toi da 5 ket qua, da loc noi dung uy tin).
    """
    if not _client:
        return "Loi: Chua cau hinh TAVILY_API_KEY trong file .env"

    try:
        response = _client.search(
            query=query,
            search_depth="advanced",  # Deeper search, reads page content
            max_results=5,
            include_answer=True,  # Tavily generates a short AI answer
        )

        # Start with the AI-generated answer if available
        output = ""
        if response.get("answer"):
            output += f"📌 Tóm tắt: {response['answer']}\n\n"

        output += "📰 Nguồn chi tiết:\n"
        for r in response.get("results", []):
            title = r.get("title", "")
            url = r.get("url", "")
            content = r.get("content", "")
            output += f"- {title}\n  {content}\n  Link: {url}\n\n"

        return output if output.strip() else "Không tìm thấy kết quả trên internet."

    except Exception as e:
        return f"Lỗi khi tìm kiếm: {str(e)}"


@tool
def scrape_website(url: str) -> str:
    """Doc noi dung chi tiet cua mot trang web bat ky.
    Dung khi can doc noi dung tu mot link cu the ma nguoi dung cung cap
    hoac tu ket qua search_web.

    Args:
        url: Dia chi URL day du cua trang web (VD: "https://example.com/article")

    Returns:
        Noi dung text cua trang web (da loc bo quang cao, menu rac).
    """
    if not _client:
        return "Loi: Chua cau hinh TAVILY_API_KEY trong file .env"

    try:
        response = _client.extract(urls=[url])

        results = response.get("results", [])
        if not results:
            return "Không truy cập được trang web này."

        # Return the extracted raw content (cleaned by Tavily)
        raw = results[0].get("raw_content", "")
        if not raw:
            raw = results[0].get("text", "Không đọc được nội dung.")

        # Limit to ~3000 chars to avoid overwhelming the LLM context
        if len(raw) > 3000:
            raw = raw[:3000] + "\n\n... (nội dung đã được cắt ngắn)"

        return raw

    except Exception as e:
        return f"Lỗi khi đọc trang web: {str(e)}"


# Export
web_tools = [search_web, scrape_website]
