# Decision Log — Skylark Drones BI Agent

**Candidate:** Campus Assignment Submission  
**Role:** AI / Business Intelligence Agent  

---

## 1. Key Assumptions I Made

When I started working on the two provided datasets (`Deal funnel Data.xlsx` and `Work_Order_Tracker Data.xlsx`), I noticed right away that the data reflects real-world business tracking:

1. **Deal Status & Win Rate Calculation:**
   * In the Deals board, `Deal Status` has values like `Open`, `Won`, `Dead`, and `On Hold`.
   * I treated `Won` as closed-won and `Dead` as closed-lost. For calculating the commercial win rate, I used the formula: `Won / (Won + Dead)`. This gave a win rate of **39.1%** across 69 decided deals (27 Won, 42 Dead).
   * I excluded `On Hold` deals from the active pipeline and win rate calculation since they are paused opportunities.

2. **Probability-Weighted Pipeline:**
   * The `Closure Probability` column contains categorical values (`High`, `Medium`, `Low`) rather than numeric percentages.
   * I mapped these conservatively: **High = 75%**, **Medium = 50%**, **Low = 25%**.
   * For deals where probability was left blank, I flagged them in the data hygiene caveats rather than silently assuming 0% or 100%. This yielded a weighted pipeline of **₹57.88 Cr** out of ₹128.51 Cr unweighted open pipeline.

3. **Interpreting "Revenue at Risk" from Real Board Fields:**
   * Looking at `Work_Order_Tracker Data.xlsx`, I saw there is no single column named "Risk". However, there are projects marked as **`Pause / struck`**, **`Details pending from Client`**, and incomplete work orders with significant **`Amount Receivable (Masked)`**.
   * I defined *Revenue at Risk* as the total monetary value tied to projects that are currently stalled or incomplete with overdue receivables. In the dataset, this totals **₹1.93 Cr** across 5 primary stalled client accounts (like `WOCOMPANY_047`, `WOCOMPANY_002`, `Sakura`).

4. **Handling Masked Data & Clean Display:**
   * The company and deal names are masked for confidentiality (e.g. `COMPANY089`, `WOCOMPANY_002`, `Naruto`, `Sasuke`, `Sakura`).
   * I made sure the agent preserves and displays these exact identifiers so the user can trace every summary metric back to specific line items.

---

## 2. Trade-offs Chosen and Why

1. **Dynamic Column Title Discovery vs. Hardcoded Column IDs:**
   * *Trade-off:* Monday.com generates random internal column IDs for every board.
   * *Decision:* I implemented dynamic schema introspection that looks up columns by human-readable titles at query time. This ensures that if someone imports the Excel sheets into a fresh Monday board, the agent still connects and reads them without breaking.

2. **Zero-Dependency Tabular Engine + Dual Interface:**
   * *Trade-off:* Heavy libraries like `pandas` can sometimes run into binary DLL blocks on restricted Windows machines, while `streamlit` requires terminal setup.
   * *Decision:* I built a pure-Python tabular data handler (`tabular_data.py`) and a lightweight web interface (`web_server.py`) that runs instantly using Python standard library with zero external dependencies. At the same time, I kept `app.py` ready for 1-click cloud deployment on Streamlit Community Cloud.

3. **Transparent Data Hygiene Score vs. Black-Box Score:**
   * *Decision:* Rather than calculating an arbitrary number, I defined the Data Hygiene Score as the exact percentage of critical fields populated across both boards (checking Deal Status, Deal Value, Sector, Owner, Execution Status, and Dates). This gives a transparent score of **72.7%** and explicitly lists missing fields so founders know what to fix.

4. **Hybrid Query Engine (Fast Rule Router + LLM Function Calling):**
   * *Decision:* I added support for Google Gemini (`GEMINI_API_KEY`) and Anthropic Claude (`ANTHROPIC_API_KEY`) with tool calling, but also built a fast deterministic offline engine. This guarantees that basic queries (sector pipeline, win rates, revenue at risk, leadership briefings) return accurate math with 0 token cost and zero downtime.

---

## 3. What I Would Do Differently With More Time

1. **Real-Time Webhook Synchronization:** Set up Monday.com webhook endpoints (`item_created`, `column_value_changed`) to push live updates directly to the agent instead of polling.
2. **Automated Monday.com Write-back & Slack Alerts:** Allow the agent to automatically post comments on delayed Monday items or send instant alerts to the project manager on Slack when an SLA slips.
3. **Machine Learning Delay Predictor:** Train a lightweight predictive model on historical project duration, acreage, and weather seasonality to flag high-risk work orders *before* they get delayed.
4. **Fuzzy Account Matching:** Implement smart entity resolution to link deals and work orders even when client naming has minor spelling discrepancies.

---

## 4. How I Interpreted "Leadership Updates"

When I looked at how drone operations work at a company like Skylark Drones, I realized that founders don't just need a list of closed deals or flight hours. The real challenge is **bridging the gap between sales promises and operational execution**:

* Sales teams celebrate Closed Won deals, but Operations might be stuck with execution bottlenecks or pending client deliverables.
* Therefore, I designed the **Leadership Update Generator** to synthesize:
  1. **Commercial Momentum:** Closed Won revenue, Win Rate, and probability-weighted pipeline.
  2. **Operational Delivery Health:** Completed projects, active ongoing work orders, and execution SLA.
  3. **Critical Red Flags & Revenue at Risk:** Explicitly naming delayed/paused work orders and calculating the exact revenue at stake.
  4. **Actionable Leadership Next Steps:** Assigning clear follow-ups for executive closing support and field unblocking.
  5. **1-Click Export:** Making the briefing copyable for Slack/Email or downloadable as a clean Markdown report for boardroom meetings.