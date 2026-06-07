# DeGiro XIRR Calculator

Computes your true annualised return (XIRR) from a DeGiro transaction CSV export, accounting for deposits, withdrawals, transaction costs, and your current portfolio value.

## Why XIRR?

XIRR (Extended Internal Rate of Return) uses the exact date of each cash flow, making it accurate for irregular deposits and withdrawals — which is always the case in real portfolios. DeGiro's built-in P&L figures often exclude unrealised gains, dividends, or FX effects; XIRR gives you a single number that reflects your actual economic return.

## Requirements

- Python 3.8+
- `pandas`

```bash
pip install pandas
```

No other dependencies — the XIRR solver is implemented from scratch using bisection.

## Usage

### 1. Export your transactions from DeGiro

In DeGiro: **Account statement → Download → CSV**

### 2. Add a portfolio value row

Append a row at the end of your CSV with the description `Portfolio Value (end)` and your current portfolio value. This is the terminal cash flow used for the XIRR calculation.

```
01-03-2026,16:00,01-03-2026,,,Portfolio Value (end),,EUR,"1200,00",EUR,"1200,00",
```

The date should be today (or the date you want to compute the return up to). The value should match the total portfolio value shown in DeGiro, not just the cash balance.

### 3. Edit the first row

Make sure it is
```
Date,Time,Value date,Product,ISIN,Description,FX,Change,Amount,**Balance**,,Order Id
```

### 4. Run the script

```bash
python xirr.py transactions.csv
```

## How cash flows are classified

| Description (exact match, case-insensitive) | Type |
|---|---|
| `iDEAL Deposit` | Deposit (money in) |
| `SEPA Instant Terugstorting` | Withdrawal (money out) |
| `Portfolio Value (end)` | Terminal value |
| Anything else | Ignored |

Internal transfers between your Flatex cash account and DeGiro investment account are intentionally ignored to avoid double-counting.

## Output

```
Total deposited:   €   1000.00
Total withdrawn:   €    100.00
Portfolio value:   €   1200.00
Net invested:      €    900.00
P&L:               €    300.00

XIRR: 441.17%
```

## CSV format

The script expects the standard DeGiro CSV export format:

```
Date,Time,Value date,Product,ISIN,Description,FX,Change,Amount,Balance,,Order Id
01-01-2026,10:00,01-01-2026,,,iDEAL Deposit,,EUR,"1000,00",EUR,"1000,00",
```

Dutch number formatting (`"1.000,00"`) is handled automatically.
