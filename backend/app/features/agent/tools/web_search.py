"""
General-purpose tools: web search & website scraping.
Uses DuckDuckGo (free, no API key needed).
"""

from langchain_core.tools import tool
from ddgs import DDGS


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
        Ket qua tim kiem tu internet (3-5 ket qua dau tien).
    """
    try:
        results = DDGS().text(query, max_results=5)
        if not results:
            return "Khong tim thay ket qua tren internet."

        output = ""
        for r in results:
            output += f"- {r.get('title', '')}: {r.get('body', '')}\n"
            output += f"  Link: {r.get('href', '')}\n\n"
        return output

    except Exception as e:
        return f"Loi khi tim kiem: {str(e)}"


@tool
def scrape_website(url: str) -> str:
    """Doc noi dung chi tiet cua mot trang web bat ky.
    Dung khi can doc noi dung tu mot link cu the ma nguoi dung cung cap 
    hoac tu ket qua search_web.

    Args:
        url: Dia chi URL day du cua trang web (VD: "https://example.com/article")
    
    Returns:
        Noi dung text cua trang web (gioi han 2000 ky tu).
    """
    try:
        results = DDGS().text(f"site:{url}", max_results=1)
        if results:
            return results[0].get("body", "Khong doc duoc noi dung.")
        return "Khong truy cap duoc trang web nay."
    except Exception as e:
        return f"Loi khi doc trang web: {str(e)}"


# Export
web_tools = [search_web, scrape_website]
