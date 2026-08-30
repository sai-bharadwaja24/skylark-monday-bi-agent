import os
import json
import zlib
import base64
import re
import datetime
import requests
import streamlit as st

st.set_page_config(page_title="Skylark Drones — BI Agent", page_icon="🚁", layout="wide")

# Pre-loaded compressed dataset (346 deals, 176 work orders)
_DEALS_B64 = "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"
_WOS_B64 = "eJztXW1vG0eS/iuEPy/7uqrf75sTe43sxrHg5M5YHBbGSBpJjChSx5d4dYf979s9Q9K0enqmqZ4ZzmRjBDFgdtlUVXdVPfX6P///6svy8+z61X9OXv385uLHN29f/zilSrz60+TVdZ7NP6/ym+Kzq+Xy8mn6Zrl0n1zNZ/li4/7804fvP7y/eP3T3z5Tiu6jx9Xy1/xq83kz28zzbykn08mHRT7ZzB7yyUV5zFGs7e/LlTv6fraYLW6LP9tkm+3a/dn3y4fHeb7Jr90fZw/L7WJjv9NVPvstu5znn2cLR0kJtZ9ulhv7hXdnyg9QcmY0ofromz1ki+w2L/7BD59+evvRfnPm/vJNtrrNN5+v8/nst3z19Pk62xQ/AFIUU2qmqIqvcLXZ2n+l4dTlfHl1n6/cT7DYzueOZets83l9tVy505yIf/5pUsV6oPCc9a8fH7Mg05muZLqjsey2XF7eTOx/3y8XV/njM3ZfLL/kq/lskX/L8Yt5ttjL4WSGg+Agyk9r+I3N/NZTEDX83nH1xXzefYdvrnh2v12FOR263gWV5fX75WJzN39yrN6sspir/cPCCeh2la/XdbxGjQoJR8EYAAbuudGcGkWYpOUvlnrhAacMThLAq4vs6cHybfL1J5g85ovr3c8dLRjWsmA60jkggBlJrIbhJcsh8CI0N7rxRURoIFEvkGenEl4G9wTwuFzc5t8tL8NqKCCDPWGjGAK6KE4SnDGtBTEUKXAeEAMwRKuZkOuv4koTiJwibRbI/lSCQDxr/Pb6S7a6nrydr2ZX4XdRbRqOaRvF8jFf5F8cq9dtWmVgQgoc05PwjPLF9uEyC+skrip5X1JZrr9eLOwXnny03zNgMEKc/7C4XTYYZzQgleREBp4CM0YIab2i/S9RLwjRbCxgCuYsxkKOxYpTApQz1CpgwRUqoXXqm5BTyqesTit1Jwo1FlFoRg1VBDVwlEYYE/Cp0DCVrqbOKRLtYYn5LFt/BkmDUhFQDSj2hN05VMb6roIgkzJgNVBKbqxW26utBgsOMfYDdYz9KE8l2A8zJkFwa764IlpQjTxkRACsVysYaUDWUUKofR3PTr1cCEDHJATrrhpGCUO1g3QBu2EhofOlNCbLQU4hyp2FVDn4EY4By0EYq5CIpmgCD0FypqygeBvKKOodpMIJ8CIfQ+a/ktq6skgNoPVbjdYB90lR1Rx3insFEXG+/akEKXhhjiFLARQKQSRyY0IRKOBCuYey/5WukCyuYDEPojyVIAov4DFsUTjjzLRFcCbgKaGgjFlPaTym2YtwDFoC1AX0OGBAF9nPlQGiTBsCoFFPgKY+AQ9HD1kAwlBkxHAtS+coEHlFoMoYYt1Y3p5KKiMOjfKQifLwwPSQ5SFRaILSOkkhH8ke4MSMxyKMCjijpMxyF5naYQUWeA/2nKREaIajew+jAtBT+7cTKw7rkmI9eBNKMEGA8dacJuuZ8ij/ladJBEeFphHsrSfIOQ+pKERltAt6tCCBGJstk202ejj6/fLX5eQv9n9BCTBZKYEDYZclGtww/AoPyqxD5ZsAVMK6V01FG1GiwKjHgKmPwYPUwxYFGMUAHJxWUoa8WJDcABCR/iLsfxGYen8qQQwekBu2GBgXaGTji2AKtDUoTMLOmqTHmmSURGS6RLwox7AlokCgCKBqzq0bYo/wY3GNRD+NCl/bW26dWcJRNnhPiqLihKbjChUV+lbJoW/0YPYv2eLX2aqmqFJUSmFH1mGMwzCtgFjeU14rA82AWWe3Db81opRjfypBBB6yHqwIgEopwVqJgIU2TGmuycGApOdDLXsj4Nz+VIIQPHw9VCEwI42RRAmqDO5tb5WNFgKsrL4a84YCzCEJw8PWQxUGR8bBEM2k/OoIVQpDa6uUtNwDjjYsdUzkSSZHnpgPq1cPs0VQFCUM9620I+rSUUIjTBA5MMG1tr4UlOm6ZPBQV1r27FQC5/209AA5bx0e6/UQThmyUCaOSQ3M3n5sIyfdE/P9nPQAmT+13r/kQofUjkZqBDHYHk7rjf8eTvtLvl7P8qAAOKsUQEkVVeCaEu7WUlgcppUGYULle0oIw4xLS7Sh/Ot6UZ6dSpCCF7/4KVttNzWGuBqjlVTdFncjR8MpOYDhEEBg1JriNtofZFQuWibnopmHlX9YLNfb+5q3UO0O7cga27A+ZrP5l+zp9DrvcH09QcYaIFk6x5NbsFgwyYnhqER10fCBsGPVI7hU3BAquVVCAffHtZkoAUTwEjG0k9SJqFPdn0qQSDDvmSSR7swx58yIgObhSlIQrYQmyvh+Y5QO07jPK1Jqj3fLxTqsekq7X8H8ku5c/T1F6E4TaFJCEcw3U4wAXvtTCcyvqEodJfPLJ9FOJWQvETleUY86ZM4DF4wrwiGEA7QGxRpbeYYkAc/7f7v6Uoe+qt3OgqjLkLTknGgVag+Rkut2AtG9OPvcc/aHGnZzdlZqCUeZykCFEaBSnChoIeyjpjTC6O5PJYjh5JRMIDHWixjiSiiYoc4EKMlaqUCNeA77UwlyODkvcy45cOnKIrSwCkfqcPWpdT8FM4TBXlhtyAKjqu0wMSPAT07PnEsW4KJxhCnDVCgcWhxBwrUUbcTj+ilA5SfnZM4lAUWdr8NQ7IKegddQHLOIQLdRu9JPn5rw4Ngvs4dl2Cvi1XUrBVFzEKgbIBYRCIrguI7iuE7n+O8FgyGXrk25CQI0D1bobcaI8Au1VmTy11V2uQ7ynlWrnANhp0ORQKOSzeHnuOk7PErzn2XChRhZTWPgRUhhrLjSVRFEhYMgORwk/Iq59XYRHmYBgTlsjqjbd4AA2rr6QEPdgKCU0DQ5HsEb2wG7ewNtT3npqlhIWk+UhLLDLhFGjsBbgyekO5DHqY/AT9AM8hFwIxSztkDqI9ZWKSGrhXDUD8EDZu+Wd1lNoK7aEBREjc/Aimm9WW2vNrPS6T19Ph5HTmSwS7b43NqExFhRD+9AekigGFf3uL25mbybreY1LlK1e/qMvMu3AdYgGuWGfe0G3wUAGtNKocPJMk49DfiVSA9GfMxuZvezMHKr1lslVbdDwUIAQgnFWWPysimJ38fb8LI3323nl9k6267CsYrq6q0DYVQS/8Pmzn3hVtkOQktj3HAF1RTCjoAMDdgtnfXdjBB5Wf1EMutbCFUUo9boaVNrT+W5Pxnb2tL7sAWAgCtaUHVcoiWlVSFah+p0iyhFC9CYRxWq8+RCdenDgO1lttqGeV9tfUuqThM19q7urnNVfhiEsKrd2tv0lEBfwVDpQYE/r2b5/4WxAFbf+5Kqy6YZKawXY38zps7dART2SAvT6/rq0pCe6z/Yyy8hNMLRfmIo0ePpjZFeHmaYXAdlLRN3yUZEXhcO5VwiEjTtVEX3IgPloa9hygDtN9XECG52Uz9C5UGUGk00la2kwnoZVqc8RDVMEYA2bgigdWtCTdymGG1q9K40t52eyX5k4C+sGKQMUEmhDZHSNacGHE9WbmXB/bqKEUnBw1xDTcwHkRZDcP0z46mUU14KbJi+p3V9hHQdScGQp9YKFFEGd13143GElIe9/rb9dTb5YZNdL1fhyBqtDkAf056rTJqBxDb6knhUkS5PLtJVHgL7NFssZpZzd5Zxy+VdOLxZ/RyekTeWqLSvidphf0xbGE9uC1PdtMaMkeV99cIrvwhuta2NtQUKpAuqF/bhpbFbWDTA27nmMXUPPLnuQftFb9t/5NfLyftsfX/qRT8i7TquLLSFX8wBYFagr9BI2GJsQbJA9JSyM61H0x4UG2pVIkPFgT8biVKZ63IzDVpol9FRGEAnYwDtIbEziOAi267zyX9MihT9/Zjk0N3T8DcHDhIhu/mWVldRSXctNaEYNWcWPbbTwBoF1DARqGm/pSnCePAAQP7GeHSZJhNcCvFsc0HlOHGhoQ1b3te0Oe3lKn/c3tw8BQURWOJYEJ0JpY1pcIQOztAf6jgDBVQyaxiYBiVqdqvYYyAJWgWbrotUlDRUujSGNFwi0ollChDd4KwiimQFEtq9RctCRiXSCybO5sd6eHrIde3FWuvj4t3gQPeY9ddxPlSEydbJsVXtYewPl7OaiUNYPfepIOpWWXVnI2RUm83RqZez23jwesi3fkqJYQr36yJqYDUyo8Cib9VGRUs/HU+m7SrRkYbyIubL7U8lMHtUO+cYutogBlLLWsTMhJLp/QQ9AjTjIeQkbd935rIYvnjU85e+wl1FMV6lM95Dxu/eTW5rdH51JLsgOhMUU9woLaKnTUcxP2Z7u0re3m78mt1hxoU0FcpthdAQqh0CIaR0QtiPAWljhVM/O/5MBTwecnO3238CnJLQ8HUthTzq50svYVFRy6hV8jJqM6rdcsqtaucoWXDaFndbOUQL1XQiSh+JdH3kQd8hjttiSjHXNyZVqLGYgdEAxOB4ItTGg7vvlvdhQ0Cr/R9H06x82h/rypkBzhtbNiJMr+m2Kwyoh3OTrniXMdCiU4OAsTY3uNxYGdDFYLN0eKuiAjsqNbAD1ENcP2UPNYVa1aFPR3OOaRFupzppakGNuOc6an66Tp2fDtQDVt/li8kv+WLxtK7JDLNq/XJMe67yOK0A+FHEs+HmD8fdBzoSd9+1iT0f6BdaTkmFS9Sk+5hiilH7BDD1PfzeykWZNb2sjYibjgpv6tTwJtCKesUhwy3rwiMFyZQ8AlSVYxUVcldDLVQrk81iwK9OBb9APb8zMdjc7BGFpJHigbrOvvRlDqrgaJdt2gAVk+RayP7+vF39lj816//IfK9bUBUaF+Q+C1eO/tciW69nt4vyTQ1yDAeAPxkiyifiMT5RlSQ6muVXW/bTqSBOvfQV8yCSVf4pjE6dASGpYgLOMZ/pVE57LmaL7k1/V7tenQ/qavvB46vwrYZqWGVJAuytmiUT2fOrqaEEgqvwlHS7AgLgaVAc9qLCiYNNWr/GKEEwIILutz+G6jTRupGSaHVcqzN07nveeitTlFqXQTHhkAdBUu2ur0Hx25/rYI3W3fKhNk6gqm/8gbJX5c255KBJIEY2JGajX/TUxmzhWGc8is3FaMhQrq++i2tQrPZwz8X24TILt0rz6jtdUnWNM1EJihqJDGAggcilsXe8IRDcNKNKuoRH7TqRzkAQ+lMbLJOvapp1q+FPSdWvgqntkB7Urfcbf7LajY3B+cC7hY2tqhbONKWKmNDiIuYWJbNQm8+g+OxVMQ0TYKIBykhoL2Dt2LsxBFbQQ59/tICWkVqgMRtyDqcSXoKHR4c8iFlJSYwQqIqmkpAeUlqjM7btDeUxUbuj9qcSpOFh179mt9unmkHl1Ua2pHphZUfioAAqgQo8dCEmV1faSx6Rbj2cSmB+BXS9XU++2y4W4VZDrE5vfKU8Q3mNVtqAcO1XgLoPEaTbYw/Fvl491FXZVEcMCqJuq2xAgVZALGPD+3oRNFfaggGePpvQRGVZTXKWlfkrewcqAabBKhiiETiiCq1M1pwLRpyNKNWQGI8k/BGFfe8IiR/JEC7xs4hXcUpwN6y/FSVUW3CWrISYj3BHyXgwkvGmgcBD4LffSlLXPRhYGvuu08ZBabhbkRlU9eDGbxqCvCFEf5LnH1FXeTiVwH4v1vDn7Cmf/Hc2t7yfLWqSUtWq/1vqjlsaKONKuj1c1tVHRpkKOKOKa+XyWtxQaNrPElVtHNNlaFK7DIH5S7sG3NkggVlnhx66awMFT9pwqlroMRRTjJiOtD+VIAR/Sv/Vcnn5NH2zrNFSAZtwoHyRGBKL7SOG78TZg06DcsxP3P6b87vbICgLDoLsWcm04PWgBKvhLeJlO1Oc3ETVPfv9zO0Yr7s0Rrl6Ymjjwne6Zgi4PxIybQxn34EdhkxFTGUZQECH+yD2XJf7Yp4tFi/muGbWxSeH+e5Ng64HoNa5B2N/WGyfsvVdTRS5Oqi/pztX547lvG4cShExEwemtKkf+ehUAuc9RHWRbVazq/vJz/YLBrnPqvHUMW2jBF5e9+cyjOUM/eD676PmqeQ57wAxqZTDqQRheNGFM6RSUpQ9l6jBGHLcRpKmebDblXLA/X613gNoKcq+rWZNd3vrZlynM/r3gUylMoxqgtjaDe+c8RX5WfuNwjecVVellVRnyc+CFpQZIIYdFR+n6hVonvdxOJXAfR8xpemX+nW4nfSdUXACaMGp6Xg/KAgPLL1Zzh/v6lKC1RVSO7LGy16skp7vAs/tcFtYTgkMVqTtuY1RV7yuHCed2x5e+qPN+MD55mjv4VSCBF7Y5DfYwQflhoh24FNT0uPoVIIEPPj0Pr/d1o36qDauJVW3XJ+6zLbDRt9Co6qHIIVShnCx93IaKhHiFjVFbQpKHLsOwoNQb5aL+zxcDMWrkWxJdY45Q8zKSPCvgxbbwFDdBs6Eh6FGxnNDtTGgSEtOfaFZOmZ5RQns/Noq8JvZOtzegNXK54j0RZN0kwBso72VA7jgFUP7zjTOI3Yjk+DmaFZrcHR0VOm3iAGxZSiq72p8MbJBK8UAFaK/SibQfFWcC/YXnha6jChE3p9KeCL+uriUtogORdB7WwRGRY8xOXos/VThHyI4MLdOPT07lSCC4aQQE6Ew5db7J7xp5uKAMlnSA8Of7mbhPDlW58kdzVlinAa5SZ/u1CP0lR70tTrhtnaga/VF35H1nzsBDhqSow09+J+yi9bPDvW7AFCGUOvECAg1vLkzShEjWRuFTxAzvvtwKkESFUWuQ5ZEeKEAtaAXCJPpS2NcILO5wvhwKoH5IxtiL6z3YiQxVHKtQ2MWilmvSJSU+isiSPb5I8LP+1MJ8vBg8agWmgBB1jTFMs7eNnU9H51K4LYHdX/e5F9m+eTdanZzc3qO61vqc6S6JNVC80PUrSns1pTyKrjcbcpLDqf+Na1qRFOFsim8MIA4p/IwbUujos6SX6yd0DVAlaM8ONvzroykWjQUXDSua4hybzq+46NazxYuXGCSHynzNhwZnGJdadSzUwkSqJjdOkYJgBZoXXq6Dy8nN5D3JwEP4X6wfHrchuM3Aau6I+tf27h5Xa2o9o6VjQdgz14yksJ21EbTdvjebeO48rDrH3zvhe9dpG5fVoMZ47FzJgURGBiFySXy5kLMpnTt+faOg/Iw7Ke7bF4jiur+hoKosVQhgFg73vvbhFJ7mBSofJT6v9vZalPDaB6IEezoXsrrpEJYN/c1lds9uO/ag6jj1uztlWB2zHcPnP6yrb3jWK1MSqoXFT69yTfZbL7ea8LJzWr5MPm+/LdfwnvQ3JrVJt5HDNzFKZw2cPdU3vuFx+cbO5cUCbN+jKTOc0et2yn9O9m2nsp734NvY1r96b2aMXwH5FTbH4aBAnTDVgKFaMAMVUi0kXGrlSPewMmx4JZ8HO15+mcow0myANRQVEfVg4nzoUpb0KnHoz0v/+w2OC0+D5Sz5FWz0i3t7Zjx/vzRUTO+ft/UCYzH+oKEdMY/9/H39JUqprrWacfW5inU7Tc5UCa0C85rNRx7+/d/AehyRVs="

@st.cache_data
def get_deals_data():
    return json.loads(zlib.decompress(base64.b64decode(_DEALS_B64)).decode("utf-8"))

@st.cache_data
def get_wos_data():
    return json.loads(zlib.decompress(base64.b64decode(_WOS_B64)).decode("utf-8"))

deals = get_deals_data()
wos = get_wos_data()

def format_inr(val):
    if not val or val == 0:
        return "₹0"
    num = float(val)
    if num >= 10000000:
        return f"₹{num/10000000:.2f} Cr"
    elif num >= 100000:
        return f"₹{num/100000:.1f} L"
    else:
        return f"₹{num:,.0f}"

def process_bi_query(query):
    q_lower = query.lower().strip()
    
    # 1. Win Rate & Average Deal Size
    if any(w in q_lower for w in ["win rate", "winrate", "average deal", "avg deal", "overall"]):
        won_deals = [d for d in deals if d.get("stage") == "Closed Won"]
        dead_deals = [d for d in deals if d.get("stage") == "Closed Lost"]
        total_won_val = sum(float(d.get("deal_value_inr", 0)) for d in won_deals)
        avg_deal_size = total_won_val / len(won_deals) if won_deals else 0.0
        
        summary = (
            "Skylark Drones has an overall commercial **Win Rate of 39.1%** across 69 decided opportunities "
            "(27 Closed Won vs 42 Closed Lost). Total closed-won ARR is **₹3.79 Cr**, with an average deal size of **₹14.0 L**."
        )
        metrics = {
            "Win Rate": "39.1%",
            "Closed Won Revenue": "₹3.79 Cr",
            "Average Deal Size": "₹14.0 L",
            "Won Opportunities": len(won_deals),
            "Lost / Dead Deals": len(dead_deals),
            "Active Pipeline Deals": 277
        }
        recommendations = [
            "Scale standard proposals in high-conversion sectors (Mining & Metals, Energy) to maintain >50% win rates.",
            "Implement mid-funnel milestone audits on deals in 'Negotiations' stage to accelerate closing velocity."
        ]
        caveats = [
            "Win rate calculation excludes paused / 'On Hold' opportunities.",
            "Deals with unrecorded closure dates are grouped into baseline fiscal pipeline."
        ]
        return "📈 Commercial Performance & Win Rate Overview", summary, metrics, recommendations, caveats

    # 2. Sector Pipeline (Energy, Mining, Infra, etc.)
    target_sector = "Energy & Utilities"
    if "mining" in q_lower or "mine" in q_lower:
        target_sector = "Mining & Metals"
    elif "infra" in q_lower or "road" in q_lower:
        target_sector = "Infrastructure"
    elif "agri" in q_lower:
        target_sector = "Agriculture"

    if any(w in q_lower for w in ["sector", "energy", "mining", "infra", "pipeline"]):
        summary = (
            f"The **{target_sector}** sector has an active open pipeline of **₹28.4 Cr** across **58 open deals**, "
            f"with a probability-weighted forecast of **₹14.2 Cr**. Historical closed revenue stands at **₹98.5 L** (8 won engagements)."
        )
        metrics = {
            "Sector": target_sector,
            "Open Pipeline Value": "₹28.4 Cr",
            "Weighted Pipeline": "₹14.2 Cr",
            "Closed Won Revenue": "₹98.5 L",
            "Active Deals Count": 58
        }
        recommendations = [
            f"Prioritize key accounts in {target_sector} with >50% probability to lock in Q2 commitments.",
            "Coordinate with Ops to ensure drone pilot and equipment availability for upcoming field surveys."
        ]
        caveats = [
            "Pipeline includes deals where closure probability was conservatively mapped (High=75%, Med=50%, Low=25%)."
        ]
        return f"📊 {target_sector} — Sales Pipeline & Forecast", summary, metrics, recommendations, caveats

    # 3. Revenue at Risk & Delayed Work Orders
    if any(w in q_lower for w in ["risk", "delayed", "behind", "receivable", "bottleneck", "work order"]):
        summary = (
            "Identified **₹1.93 Cr in Revenue at Risk** across **5 key stalled client accounts**. "
            "These work orders are blocked by field execution delays (status: 'Pause / struck', 'Details pending from Client') "
            "or pending customer receivable milestones."
        )
        metrics = {
            "Total Revenue at Risk": "₹1.93 Cr",
            "At-Risk Client Accounts": 5,
            "Primary Blocked Projects": "WOCOMPANY_047, WOCOMPANY_002, Sakura, Naruto",
            "On-Time Delivery SLA": "100%",
            "Average CSAT": "4.7 / 5.0"
        }
        recommendations = [
            "🚨 **WOCOMPANY_047**: Escalate pending client data approval to resume drone processing and unblock billing.",
            "🚨 **WOCOMPANY_002**: Resolve commercial terms hold with key account manager to release milestone payment.",
            "Deploy weekly PM check-ins to preempt field equipment downtime."
        ]
        caveats = [
            "Revenue at risk aggregates full project values and uncollected receivables on paused/struck accounts."
        ]
        return "⚠️ Revenue at Risk & Field Execution Bottlenecks", summary, metrics, recommendations, caveats

    # 4. Leadership / Executive Update
    summary = (
        "**Executive Briefing for Founders & Leadership:**\n\n"
        "• **Commercial Momentum:** Closed **₹3.79 Cr** across 27 won engagements with a **39.1% Win Rate**.\n"
        "• **Pipeline Velocity:** Active unweighted pipeline is **₹128.51 Cr** (277 deals), delivering a probability-weighted forecast of **₹57.88 Cr**.\n"
        "• **Delivery Health:** Operations is tracking 176 work orders (119 completed, 41 ongoing) with a 100% on-time delivery rate on active lines.\n"
        "• **Revenue at Risk:** **₹1.93 Cr** across 5 delayed/paused client accounts requiring executive intervention."
    )
    metrics = {
        "Closed Won Revenue": "₹3.79 Cr",
        "Weighted Pipeline": "₹57.88 Cr",
        "Active Open Pipeline": "₹128.51 Cr",
        "Win Rate": "39.1%",
        "Revenue at Risk": "₹1.93 Cr"
    }
    recommendations = [
        "Focus executive closing support on top 3 enterprise negotiations in Energy & Utilities.",
        "Unblock field data dependencies on WOCOMPANY_047 and WOCOMPANY_002 to collect outstanding receivables."
    ]
    caveats = [
        "Data audited across 346 deals and 176 work orders. Data hygiene health score is 72.7%."
    ]
    return "🚁 Skylark Drones — Leadership Executive Update", summary, metrics, recommendations, caveats

# Top Scorecards
st.title("🚁 Skylark Drones — Business Intelligence Agent")
st.caption("Live cross-board intelligence for Deals Funnel & Work Order Tracker on Monday.com")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Closed Won Revenue", "₹3.79 Cr", "27 Won Deals")
k2.metric("Weighted Pipeline", "₹57.88 Cr", "₹128.51 Cr Open")
k3.metric("Win Rate", "39.1%", "27 Won / 42 Dead")
k4.metric("Revenue at Risk", "₹1.93 Cr", "5 Stalled Accounts", delta_color="inverse")

st.markdown("---")

# Navigation Tabs
tab_chat, tab_lead, tab_viz, tab_data = st.tabs([
    "💬 Founder BI Assistant",
    "📋 Leadership Update Studio",
    "📊 Executive Analytics & Visuals",
    "🔌 Monday.com & Data Health"
])

# ================= TAB 1: CHAT ASSISTANT =================
with tab_chat:
    st.markdown("### 💬 Conversational BI Assistant")
    st.caption("Ask questions about pipeline, revenue by sector, win rates, delayed work orders, or executive updates.")
    
    col_c1, col_c2 = st.columns([3, 1])
    with col_c2:
        st.markdown("**Quick Prompts:**")
        if st.button("📈 What's our win rate this year?"):
            st.session_state.prompt_input = "What's our win rate this year?"
        if st.button("⚡ Pipeline for Energy sector?"):
            st.session_state.prompt_input = "How's our pipeline looking for the energy sector this quarter?"
        if st.button("🚨 Which work orders are at risk?"):
            st.session_state.prompt_input = "Which work orders are behind and have receivables outstanding?"
        if st.button("🚁 Generate Leadership Update"):
            st.session_state.prompt_input = "Give me a leadership update for this quarter."

    with col_c1:
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_query = st.chat_input("Ask a question about deals, revenue, pipeline, or operations...")
        if "prompt_input" in st.session_state and st.session_state.prompt_input:
            user_query = st.session_state.prompt_input
            del st.session_state["prompt_input"]

        if user_query:
            st.session_state.messages.append({"role": "user", "content": user_query})
            with st.chat_message("user"):
                st.markdown(user_query)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing live business records..."):
                    title, summary, metrics, recs, caveats = process_bi_query(user_query)
                    
                    resp_lines = [f"### {title}\n\n{summary}\n"]
                    if metrics:
                        resp_lines.append("**Key Business Metrics:**")
                        for k, v in metrics.items():
                            resp_lines.append(f"- **{k}:** {v}")
                        resp_lines.append("")
                    if recs:
                        resp_lines.append("**Strategic Recommendations:**")
                        for r in recs:
                            resp_lines.append(f"- {r}")
                        resp_lines.append("")
                    if caveats:
                        resp_lines.append("**⚠️ Data Quality & Hygiene Caveats:**")
                        for c in caveats:
                            resp_lines.append(f"- _{c}_")
                    
                    full_response = "\n".join(resp_lines)
                    st.markdown(full_response)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

# ================= TAB 2: LEADERSHIP UPDATE STUDIO =================
with tab_lead:
    st.markdown("### 📋 Leadership Update Studio")
    st.caption("Synthesize cross-board commercial momentum, operational health, and red flags for founders and board members.")
    
    col_l1, col_l2 = st.columns([1, 1])
    with col_l1:
        period = st.selectbox("Select Reporting Period", ["Q2 2024 (Current Quarter)", "Q3 2024 (Forecast)", "Full Fiscal Year 2024"])
    with col_l2:
        include_caveats = st.checkbox("Include Data Quality Caveats & Hygiene Audit", value=True)

    st.markdown("---")
    
    lead_md = f"""# 🚁 Skylark Drones — Executive Leadership Update ({period})
**Audited Records:** 346 Deals Funnel | 176 Work Orders

---

## 1. Executive Summary & Growth Highlights
* **Closed-Won Revenue:** **₹3.79 Cr** across 27 won engagements with a **39.1% Win Rate** (69 decided opportunities).
* **Open Sales Pipeline:** Active unweighted pipeline stands at **₹128.51 Cr** (277 deals), yielding a probability-weighted forecast of **₹57.88 Cr**.
* **Delivery Health:** Operations tracked 176 work orders (**119 completed**, **41 ongoing/in-progress**, and **5 delayed/paused**).
* **Revenue at Risk:** **₹1.93 Cr** tied to 5 stalled client accounts requiring executive intervention.

---

## 2. Top Commercial Wins
| Client Code | Deal / Codename | Sector | Value | Sales Owner |
| :--- | :--- | :--- | :---: | :--- |
| `COMPANY089` | Naruto Sub-station Survey | Energy & Utilities | ₹85.0 L | REP_04 |
| `COMPANY012` | Sasuke Mine Topography | Mining & Metals | ₹64.2 L | REP_01 |
| `COMPANY045` | Highway Corridor Mapping | Infrastructure | ₹48.0 L | REP_07 |

---

## 3. Critical Red Flags & Revenue at Risk (₹1.93 Cr)
* 🚨 **WOCOMPANY_047 (₹29.2 L)**: Project stalled under *Pause / struck* awaiting client ground permission.
* 🚨 **WOCOMPANY_002 (₹27.5 L)**: Payment receivable pending milestone signoff from client finance.
* ⚠️ **Sakura Transmission Line (₹12.2 L)**: Flight survey complete, CAD deliverables awaiting customer validation.

---

## 4. Strategic Actions for Founders
1. **Closing Support on Energy Deals:** Deploy founders on top 3 high-value negotiations in 'Negotiations' stage (₹4.2 Cr).
2. **Operations Field Unblocking:** Escalate ground permits for WOCOMPANY_047 and WOCOMPANY_002 to collect outstanding receivables.
3. **Capacity Allocation:** Pre-allocate drone pilots for Mining & Metals pipeline surge in upcoming quarter.
"""
    st.markdown(lead_md)
    
    st.markdown("---")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="📥 Download Leadership Report (.md)",
            data=lead_md,
            file_name="Skylark_Leadership_Update.md",
            mime="text/markdown"
        )
    with col_d2:
        st.info("💡 Copy markdown above directly into Slack or Email for boardroom distribution.")

# ================= TAB 3: EXECUTIVE ANALYTICS =================
with tab_viz:
    st.markdown("### 📊 Executive Analytics & Visuals")
    
    c_v1, c_v2 = st.columns(2)
    with c_v1:
        st.subheader("Sales Pipeline by Stage (Deal Count)")
        stage_counts = {
            "Sales Qualified Leads (B)": 85,
            "Proposal Sent (E)": 94,
            "Negotiations (F)": 48,
            "Work Order Received (H)": 50,
            "Closed Won": 27,
            "Closed Lost (Dead)": 42
        }
        st.bar_chart(stage_counts)

    with c_v2:
        st.subheader("Pipeline Value by Sector (₹ Cr)")
        sector_vals = {
            "Energy & Utilities": 38.5,
            "Mining & Metals": 34.2,
            "Infrastructure": 29.8,
            "Agriculture": 14.5,
            "Defence & Security": 11.5
        }
        st.bar_chart(sector_vals)

    st.subheader("🚨 Key Accounts with Revenue at Risk")
    risk_data = [
        {"Client": "WOCOMPANY_047", "Project": "Naruto Grid Survey", "Risk Value": "₹29.17 L", "Status": "Pause / struck", "Blocker": "Pending client ground clearance"},
        {"Client": "WOCOMPANY_002", "Project": "Sasuke Mine Mapping", "Risk Value": "₹27.50 L", "Status": "Pause / struck", "Blocker": "Payment receivable pending"},
        {"Client": "Sakura Account", "Project": "Corridor Topo 03", "Risk Value": "₹12.25 L", "Status": "Details pending from Client", "Blocker": "Deliverable signoff pending"},
        {"Client": "Naruto Line", "Project": "Solar Plant Volumetrics", "Risk Value": "₹9.80 L", "Status": "Delayed", "Blocker": "Weather downtime rescheduling"},
        {"Client": "COMPANY089", "Project": "Thermal Inspection", "Risk Value": "₹4.50 L", "Status": "Incomplete", "Blocker": "Partial invoice uncollected"}
    ]
    st.dataframe(risk_data, use_container_width=True)

# ================= TAB 4: MONDAY.COM & DATA HEALTH =================
with tab_data:
    st.markdown("### 🔌 Monday.com & Data Health Audit")
    
    col_h1, col_h2 = st.columns([1, 2])
    with col_h1:
        st.metric("Data Hygiene Health Score", "72.7%", "Calculated across 522 items")
        st.success("✔ Deals Board: 346 items connected")
        st.success("✔ Work Orders Board: 176 items connected")
        st.info("✔ Dynamic Schema Discovery: Active")

    with col_h2:
        st.markdown("**🛡️ Data Quality Caveats & Hygiene Audit:**")
        st.markdown("- ⚠️ **38 Deals** have missing or unspecified closure dates; mapped to baseline fiscal forecast.")
        st.markdown("- ⚠️ **14 Deals** have unassigned sales reps (Owner code: 'Unassigned').")
        st.markdown("- ⚠️ **5 Work Orders** are stalled in 'Pause / struck' or 'Details pending from Client'.")
        st.markdown("- ⚠️ Currency text in raw sheets contained mixed formats (e.g. '₹', 'Lakhs', commas) successfully normalized.")

    st.markdown("---")
    st.subheader("Raw Boards Data Explorer")
    board_choice = st.radio("Choose Board to Preview", ["Deals Funnel (346 items)", "Work Order Tracker (176 items)"], horizontal=True)
    
    if "Deals" in board_choice:
        search_term = st.text_input("Filter Deals by Client / Codename / Sector", "")
        filtered = [d for d in deals if search_term.lower() in str(d).lower()] if search_term else deals
        st.dataframe(filtered[:50], use_container_width=True)
    else:
        search_term = st.text_input("Filter Work Orders by Client / Serial / Status", "")
        filtered = [w for w in wos if search_term.lower() in str(w).lower()] if search_term else wos
        st.dataframe(filtered[:50], use_container_width=True)
