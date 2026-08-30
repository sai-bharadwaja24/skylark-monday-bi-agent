# 🚁 Skylark Drones — Monday.com BI Agent

**Assignment Submission:** Technical Assignment for AI / Business Intelligence Agent  
**Candidate Workspace:** Student / Campus Assignment  

---

## 📌 Project Overview

This project is an autonomous Business Intelligence agent that connects to **Monday.com GraphQL API v2**, analyzes data across two core boards (**Deals Funnel** and **Work Order Tracker**), cleans messy real-world data, and answers founder-level strategic questions through an interactive conversational web interface and leadership briefing studio.

---

## 🏗️ Architecture & How It Works

```
┌──────────────────────────────────────────────────────────┐
│                   Monday.com GraphQL API                 │
│         (Deals Funnel Board + Work Orders Board)         │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                      MondayClient                        │
│      - Dynamic Schema & Column Title Discovery           │
│      - Live GraphQL v2 Queries / Fallback Data Provider  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                  Data Resilience Engine                  │
│      - Multi-format Date Parsing & Quarters              │
│      - Dirty Currency Cleaning & Lakhs/Crore Conversion  │
│      - Sector & Work Order Status Normalization          │
│      - Data Hygiene Audit (72.7% Score)                  │
└────────────────────────────┬─────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────┐
│                    Cross-Board Engine                    │
│      - Relational Joins (Deals <-> Work Orders)          │
│      - Weighted Pipeline & Win Rate Math                 │
│      - Revenue at Risk Detection (Stalled Projects)      │
└────────────────────────────┬─────────────────────────────┘
                             │
               ┌─────────────┴─────────────┐
               ▼                           ▼
┌─────────────────────────────┐  ┌─────────────────────────────┐
│       BIAgentCore           │  │  LeadershipUpdateGenerator  │
│  - Strategic Intent Routing │  │  - Top Commercial Wins      │
│  - Multi-Part Answer Cards  │  │  - Operational Red Flags    │
│  - Suggested Follow-ups     │  │  - 1-Click Slack / Markdown │
└──────────────┬──────────────┘  └──────────────┬──────────────┘
               │                                │
               └──────────────┬─────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────┐
│                 Interactive Web Interface                │
│    - Chat Assistant | Leadership Studio | Visual Charts  │
│    - Zero-dependency local server (web_server.py)        │
│    - Streamlit Cloud ready (app.py)                      │
└──────────────────────────────────────────────────────────┘
```

---

## 📁 File Structure

* **`web_server.py`**: Standalone web app with conversational AI, executive KPI cards, leadership briefing studio, and visual charts (runs natively with Python standard library).
* **`app.py`**: Streamlit application ready for cloud deployment (supports Gemini and Claude).
* **`monday_client_core.py`**: Monday.com GraphQL API client with dynamic column discovery and pre-loaded 346 deals and 176 work orders.
* **`data_resilience_engine.py`**: Robust date parsing, currency normalization, status canonicalization, and data quality auditing.
* **`cross_board_engine.py`**: Cross-board relational joins, weighted pipeline math, and Revenue at Risk calculation.
* **`bi_agent_core.py`**: Natural language query router and 4-part executive response builder.
* **`leadership_update_generator.py`**: C-Suite executive update generator with 1-click Slack/Email formatting.
* **`tabular_data.py`**: Pure-Python zero-dependency table manipulation engine.
* **`test_suite.py`**: Automated unit test suite.
* **`DECISION_LOG.md`**: 2-page decision log covering assumptions, trade-offs, and leadership updates interpretation.

---

## 🚀 Quick Start (Running Locally)

### Option 1: Double-Click (Easiest)
Simply double-click **`run.bat`** in the folder. It will start the server and open **`http://localhost:8501`** in your browser.

### Option 2: Run via Terminal
```bash
python web_server.py
```
Open **`http://localhost:8501`** in any web browser.

### Option 3: Run the Automated Unit Tests
```bash
python test_suite.py
```
*(All 7 unit tests pass in < 0.05s).*

---

## ⚙️ Monday.com Configuration & API Setup

1. **Get your API Key:** Log into Monday.com ➔ Click your avatar (bottom left) ➔ **Developers** ➔ **My Access Tokens**.
2. **Board Setup:**
   * **Deals Board:** Import `Deal funnel Data.xlsx` (keep original columns: `Deal Name`, `Client Code`, `Deal Status`, `Masked Deal value`, `Closure Probability`, `Deal Stage`, `Sector/service`).
   * **Work Orders Board:** Import `Work_Order_Tracker Data.xlsx` (columns: `Deal name masked`, `Customer Name Code`, `Serial #`, `Execution Status`, `Amount in Rupees (Excl of GST) (Masked)`, `Amount Receivable (Masked)`).
3. **Configuration:** Add your credentials in `.streamlit/secrets.toml` or via the app sidebar.

---

## 🌐 1-Click Streamlit Cloud Deployment (Hosted URL)

1. Push this folder to your GitHub repository.
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and click **"Create app"**.
3. Select your repository and set Main File path to **`app.py`**.
4. In **Settings ➔ Secrets**, paste your keys:
   ```toml
   GEMINI_API_KEY = "AIzaSy..." # or ANTHROPIC_API_KEY
   MONDAY_API_TOKEN = "your-monday-token"
   MONDAY_DEALS_BOARD_ID = "123456789"
   MONDAY_WORK_ORDERS_BOARD_ID = "987654321"
   ```
5. Click **Deploy** to get your public submission link!