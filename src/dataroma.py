import requests
from bs4 import BeautifulSoup

def fetch_dataroma_moves(limit: int = 12) -> str:
    url = "https://www.dataroma.com/m/allact.php?typ=a"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", {"id": "grid"})
        rows = []
        if table:
            for tr in table.find_all("tr")[1:limit]:
                cols = [td.get_text(strip=True) for td in tr.find_all("td")]
                if len(cols) >= 4:
                    rows.append(f"{cols[0]} | Stock: {cols[1]} | Action: {cols[2]} | Shares/Pct: {cols[3]}")
        return "\n".join(rows) if rows else "No recent 13F activity."
    except Exception as e:
        return f"Dataroma scrape bypassed: {e}"
