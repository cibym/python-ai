import csv
import os
from pathlib import Path
import yfinance as yf

CONFIG_DIR = Path("config")


def load_watchlist(
    file_path: Path = CONFIG_DIR / "Morningstar_Expanded_AI_Watchlist.csv",
) -> list:
  """Loads tickers from your Morningstar watchlist or portfolio CSV."""
  tickers = []
  if not file_path.exists():
    # Fallback to default core AI watchlist if file doesn't exist
    return ["NVDA", "ASML", "SAP", "MSFT", "GOOGL", "AVGO", "PLTR", "BESI.AS"]

  with open(file_path, "r", encoding="utf-8") as f:
    # Handles both comma-separated and semicolon-separated files
    sample = f.read(2048)
    f.seek(0)
    delimiter = ";" if ";" in sample and "," not in sample else ","
    reader = csv.DictReader(f, delimiter=delimiter)

    for row in reader:
      # Look for common column names used across our generated files
      ticker = (
          row.get("Ticker")
          or row.get("Symbol")
          or row.get("ticker")
          or row.get("symbol")
      )
      if ticker:
        tickers.append(ticker.strip())

  return list(set(tickers))  # Unique tickers


def evaluate_stock(ticker: str) -> dict:
  """Evaluates a single stock against value/growth criteria inspired by

  Graham, Lynch, and Carlin.
  """
  try:
    stock = yf.Ticker(ticker)
    info = stock.info

    name = info.get("shortName", ticker)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    target_price = info.get("targetMeanPrice")  # Analyst consensus target
    pe_ratio = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    market_cap = info.get("marketCap", 0)
    roe = info.get("returnOnEquity")
    recommendation = info.get("recommendationKey", "hold")

    if not current_price:
      return None

    # Calculate discount/upside to analyst target if available
    upside_potential = 0.0
    if target_price and current_price:
      upside_potential = ((target_price - current_price) / current_price) * 100

    # Classify market cap tier (Small/Mid cap = 100-bagger potential runway)
    cap_tier = "Large-Cap / Mega-Cap"
    if market_cap:
      if market_cap < 2_000_000_000:
        cap_tier = "Small-Cap (High 100x Potential)"
      elif market_cap < 10_000_000_000:
        cap_tier = "Mid-Cap (Balanced Growth)"

    # Value & Margin of Safety Rules (Carlin / Graham style)
    # Check if forward PE is reasonable or if there's a strong upside signal
    is_discounted = False
    notes = []

    if forward_pe and forward_pe < 25:
      is_discounted = True
      notes.append(f"Reasonable Forward P/E ({forward_pe:.1f})")

    if upside_potential > 15:
      is_discounted = True
      notes.append(
          f"Trading at discount to analyst targets (+{upside_potential:.1f}%"
          " upside)"
      )

    if roe and roe > 0.15:
      notes.append(f"Strong ROE ({(roe*100):.1f}%)")

    return {
        "ticker": ticker,
        "name": name,
        "price": current_price,
        "forward_pe": forward_pe if forward_pe else "N/A",
        "market_cap_tier": cap_tier,
        "upside": f"{upside_potential:.1f}%" if target_price else "N/A",
        "is_discounted": is_discounted,
        "notes": " | ".join(notes) if notes else "Standard watch item",
    }

  except Exception as e:
    print(f"Error evaluating {ticker}: {e}")
    return None


def run_screener() -> str:
  """Runs the screening process across the watchlist and formats a report."""
  tickers = load_watchlist()
  report_lines = [
      "🤖 **Daily AI & Value Stock Screener Report** 🤖",
      "---------------------------------------------------",
  ]

  matches_found = 0

  for ticker in tickers:
    data = evaluate_stock(ticker)
    if data:
      # We highlight stocks that meet our discount / value criteria
      if data["is_discounted"] or "Small-Cap" in data["market_cap_tier"]:
        matches_found += 1
        report_lines.append(
            f"🎯 **{data['ticker']} ({data['name']})**"
            f"\n   • Price: ${data['price']}"
            f"\n   • Valuation Tier: {data['market_cap_tier']}"
            f"\n   • Forward P/E: {data['forward_pe']}"
            f"\n   • Target Upside: {data['upside']}"
            f"\n   • Why Watch: {data['notes']}\n"
        )

  if matches_found == 0:
    report_lines.append(
        "No immediate deep discounts triggered today. Markets are holding"
        " steady."
    )

  return "\n".join(report_lines)


if __name__ == "__main__":
  print(run_screener())
