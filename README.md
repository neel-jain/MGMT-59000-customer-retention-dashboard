# Customer Growth & Retention Intelligence Dashboard

An interactive Streamlit dashboard for analyzing `NR_dataset.xlsx`. It helps commercial and marketing teams:

1. **Identify growth opportunities** — emerging high-potential customers, categories, and region/channel combinations within the existing customer base.
2. **Detect early warning signs of decline** — low satisfaction, revenue-at-risk, and inactive/recency-flagged customers.
3. **Get data-driven recommendations** — auto-generated, filter-aware action items to guide commercial and marketing strategy.

## Files

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit application |
| `NR_dataset.xlsx` | Source dataset (must sit alongside `app.py`) |
| `requirements.txt` | Python dependencies |

Fields used: `label`, `purchaseamount`, `customerregion`, `productcategory`, `retailchannel`, `customerid`, `transactiondate` (plus `customersatisfaction` as a supporting churn-risk signal).

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Deploy to GitHub + Streamlit Community Cloud

1. **Create a GitHub repository** and push these three files (keep them in the repo root, or update the `DATA_PATH` in `app.py` if you nest them in a subfolder):

   ```bash
   git init
   git add app.py requirements.txt NR_dataset.xlsx README.md
   git commit -m "Initial dashboard commit"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo>.git
   git push -u origin main
   ```

2. **Deploy on Streamlit Community Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
   - Click **"New app"**.
   - Select your repository, branch (`main`), and set the main file path to `app.py`.
   - Click **"Deploy"**.

   Streamlit Cloud will install `requirements.txt` automatically and launch the app. Because `NR_dataset.xlsx` is committed to the repo, no extra data upload step is needed.

3. **Updates**: any future `git push` to the connected branch will automatically redeploy the app.

## Notes

- The dashboard is fully filter-driven (sidebar: date range, region, channel, category, segment label) — every KPI, chart, and recommendation on every tab recalculates from the current selection.
- Charts are built with Plotly for interactivity (hover, zoom, legend toggling).
- If you refresh `NR_dataset.xlsx` with new data, keep the same column names (`label`, `CustomerID`, `TransactionDate`, `ProductCategory`, `PurchaseAmount`, `CustomerRegion`, `RetailChannel`, and optionally `CustomerSatisfaction`) and the dashboard will work without code changes.
