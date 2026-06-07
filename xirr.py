import pandas as pd

# ---------- 1. Load & parse ----------
df = pd.read_csv("Account.csv", header=0)

# Dutch number format: remove dots (thousands sep) and replace comma with period
def parse_amount(s):
    if pd.isna(s):
        return 0.0
    s = str(s).strip().strip('"').replace(".", "").replace(",", ".")
    return float(s)

df["amount"] = df["Amount"].apply(parse_amount)
df["date"] = pd.to_datetime(df["Date"], format="%d-%m-%Y")

# ---------- 2. Classify cash flows ----------
# Deposits: money INTO broker (negative from your perspective)
# Withdrawals: money OUT of broker back to you (positive from your perspective)
DEPOSIT_KEYWORDS    = ["ideal deposit"]
WITHDRAWAL_KEYWORDS = ["sepa instant terugstorting", "flatex terugstorting"]
COST_DESCRIPTIONS = [
    "degiro transactiekosten en/of kosten van derden",
    "degiro aansluitingskosten"
]

def cashflow(row):
    desc = str(row["Description"]).lower()
    if "portfolio value" in desc:
        return row["amount"]
    elif any(k in desc for k in DEPOSIT_KEYWORDS):
        return -row["amount"]
    elif any(k in desc for k in WITHDRAWAL_KEYWORDS):
        return -row["amount"]
    else:
        return None

df["cf"] = df.apply(cashflow, axis=1)
cash_flows = df[df["cf"].notna()][["date", "cf"]].sort_values("date").reset_index(drop=True)
costs_df = df[df["Description"].str.lower().isin(COST_DESCRIPTIONS)]
total_costs = -costs_df["amount"].sum()  # amounts are negative in CSV, flip for display

print(cash_flows)

# ---------- 4. XIRR ----------
def xirr(cash_flows, date_col="date", cf_col="cf"):
    dates = cash_flows[date_col].tolist()
    flows = cash_flows[cf_col].tolist()
    t0 = dates[0]

    def npv(r):
        return sum(
            cf / (1 + r) ** ((d - t0).days / 365)
            for cf, d in zip(flows, dates)
        )

    # Find a bracket where NPV changes sign
    lo, hi = -0.9999, 10.0
    if npv(lo) * npv(hi) > 0:
        raise ValueError("Could not bracket the root — check your cash flows have sign changes")

    for _ in range(200):
        mid = (lo + hi) / 2
        if abs(hi - lo) < 1e-8:
            return mid
        if npv(mid) * npv(lo) <= 0:
            hi = mid
        else:
            lo = mid

    return (lo + hi) / 2


# ---------- 5. Per-stock P&L ----------

def classify_stock_row(row):
    desc = str(row["Description"]).lower()
    if pd.isna(row["ISIN"]) or str(row["ISIN"]).strip() == "":
        return None
    if "verkoop" in desc:
        return "sale"
    elif "koop" in desc:
        return "purchase"
    elif "dividendbelasting" in desc:
        return "dividend_tax"
    elif "dividend" in desc:
        return "dividend"
    elif "transactiebelasting" in desc:
        return "transaction_tax"
    elif "transactiekosten" in desc:
        return "transaction_cost"
    elif "current value" in desc:
        return "current_value"
    return None





rate = xirr(cash_flows)
deposits    = cash_flows[cash_flows["cf"] < 0]["cf"].sum()
withdrawals = cash_flows[cash_flows["cf"] > 0]["cf"].sum()  # excludes portfolio value
terminal    = cash_flows[cash_flows["cf"] > 0]["cf"].max()  # portfolio value is the largest positive

print(f"Total deposited:   €{-deposits:>10.2f}")
print(f"Total withdrawn:   €{withdrawals - terminal:>10.2f}")  # excluding terminal
print(f"Portfolio value:   €{terminal:>10.2f}")
print(f"Net invested:      €{-deposits - (withdrawals - terminal):>10.2f}")
print(f"P&L:               €{terminal - (-deposits - (withdrawals - terminal)):>10.2f}")
print(f"\nXIRR: {rate:.2%}")

df["stock_type"] = df.apply(classify_stock_row, axis=1)
stock_df = df[df["stock_type"].notna()].copy()

# Group by ISIN + Product name
summary = []
for (isin, product), group in stock_df.groupby(["ISIN", "Product"]):
    purchases      = -group[group["stock_type"] == "purchase"]["amount"].sum()
    sales          =  group[group["stock_type"] == "sale"]["amount"].sum()
    dividends      =  group[group["stock_type"] == "dividend"]["amount"].sum()
    dividend_tax   = -group[group["stock_type"] == "dividend_tax"]["amount"].sum()
    trans_tax      = -group[group["stock_type"] == "transaction_tax"]["amount"].sum()
    trans_cost     = -group[group["stock_type"] == "transaction_cost"]["amount"].sum()
    current_value  =  group[group["stock_type"] == "current_value"]["amount"].sum()

    total_costs    = dividend_tax + trans_tax + trans_cost + purchases
    net_cash       = (sales + dividends + current_value
                      - total_costs)
    # net_cash > 0: made money, < 0: still invested or lost

    summary.append({
        "Product":       product,
        "ISIN":          isin,
        "Purchased":     purchases,
        "Sold":          sales,
        "Dividends":     dividends,
        "Costs & taxes": dividend_tax + trans_tax + trans_cost,
        "Net P&L":       net_cash,
    })

summary_df = pd.DataFrame(summary).sort_values("Net P&L", ascending=False)

print("\n=== Per-stock P&L ===")
pd.set_option("display.float_format", "€{:>10.2f}".format)
pd.set_option("display.max_rows", 100)
pd.set_option("display.width", 120)
print(summary_df.to_string(index=False))