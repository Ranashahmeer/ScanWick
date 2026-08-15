"""Business intelligence analytics engine for CSV-based data analysis."""
from __future__ import annotations

import re
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# COLUMN CANDIDATES
# ---------------------------------------------------------------------------

COLUMN_CANDIDATES: dict[str, list[str]] = {
    "amount": [
        "revenue", "sales", "total_sales", "billing", "salary", "price", "value",
        "spend", "cost", "debit", "credit", "invoice_amount", "budget", "mrr", "arr",
        "adr", "total_revenue", "gross_revenue", "net_revenue", "amount",
        "total_amount", "sale_price", "transaction_amount", "charges", "fee", "rate",
        "income", "earnings", "payment_amount", "fare", "rent", "gross_sales",
        "net_sales", "proceeds", "turnover", "total_cost", "total_price",
    ],
    "profit": [
        "profit", "margin", "gain", "earnings", "ebit", "net_income", "gross_profit",
        "annual_rent", "monthly_rent", "rental_income", "budgeted_cost", "net_profit",
        "operating_profit", "gross_margin", "net_margin", "profit_margin",
        "contribution", "surplus", "return", "yield_amount", "roi", "net_revenue",
        "net_earnings", "net_gain", "income_after_tax", "operating_income",
    ],
    "qty": [
        "quantity", "qty", "units", "count", "volume", "headcount", "clicks",
        "impressions", "patients", "deliveries", "covers", "pax", "items", "pieces",
        "orders", "num_orders", "num_units", "transactions", "visits", "sessions",
        "passengers", "beds", "rooms", "loads", "shipments", "parcels", "tickets",
        "bookings",
    ],
    "category": [
        "category", "type", "segment", "department", "campaign", "product",
        "diagnosis", "room_type", "route", "phase", "meal_period", "industry",
        "sector", "division", "class", "service_type", "item_category",
        "product_category", "product_type", "channel", "medium", "source",
        "job_title", "position", "role", "specialty", "ward", "project_type",
    ],
    "subcategory": [
        "subcategory", "sub_category", "product_line", "sub_segment", "item_type",
        "sub_type", "variant", "sku_category", "brand", "model", "series",
        "product_group", "item_group", "sub_department", "sub_channel",
    ],
    "payment": [
        "payment_method", "payment_type", "tender", "booking_source", "gateway",
        "booking_channel", "payment_mode", "method", "pay_type", "instrument",
        "card_type", "transaction_type", "mode_of_payment", "pay_method",
    ],
    "date": [
        "date", "order_date", "transaction_date", "created_at", "timestamp",
        "admission_date", "check_in", "dispatch_date", "invoice_date", "sale_date",
        "purchase_date", "booking_date", "hire_date", "start_date", "entry_date",
        "report_date", "period", "datetime", "time", "check_in_date",
        "departure_date",
    ],
    "customer": [
        "customer", "client", "patient", "employee", "guest", "tenant",
        "project_name", "booking_id", "customer_name", "client_name", "account",
        "account_name", "buyer", "vendor", "supplier", "merchant", "user", "member",
        "contact", "name", "full_name", "employee_name", "staff_name", "doctor",
        "agent", "rep", "salesperson",
    ],
    "state": [
        "state", "region", "city", "location", "territory", "warehouse",
        "delivery_zone", "hub", "property_location", "area", "district", "country",
        "province", "county", "zip", "postal", "branch", "site", "store", "outlet",
        "depot", "facility", "zone", "cluster", "market", "geography",
    ],
}

# ---------------------------------------------------------------------------
# DATASET SIGNATURES
# ---------------------------------------------------------------------------

DATASET_SIGNATURES: dict[str, list[str]] = {
    "hr": ["employee", "salary", "department", "headcount", "payroll", "hire_date", "termination", "gender", "tenure", "performance"],
    "inventory": ["sku", "stock", "reorder", "supplier", "lead_time", "warehouse", "units_on_hand", "cost_price", "selling_price", "inventory"],
    "marketing": ["campaign", "impressions", "clicks", "ctr", "cpa", "roas", "spend", "conversions", "ad_spend", "channel"],
    "bank_statement": ["debit", "credit", "balance", "narration", "transaction_ref", "deposit", "withdrawal", "receipts", "dr", "cr"],
    "ecommerce": ["order_id", "cart", "fulfillment", "return_rate", "aov", "sku", "shipping", "checkout", "refund", "customer_id"],
    "sales": ["deal", "pipeline", "stage", "win", "lost", "quota", "rep", "forecast", "crm", "opportunity"],
    "real_estate": ["property", "sqm", "yield", "vacancy", "tenant", "rent", "ltv", "valuation", "occupancy", "lease"],
    "healthcare": ["patient", "diagnosis", "admission", "discharge", "bed", "ward", "icd", "treatment", "doctor", "length_of_stay"],
    "logistics": ["delivery", "route", "driver", "shipment", "sla", "on_time", "dispatch", "hub", "parcel", "carrier"],
    "hospitality": ["hotel", "room", "checkin", "checkout", "revpar", "adr", "occupancy", "booking", "amenity", "resort"],
    "construction": ["project", "contractor", "budget_variance", "spi", "cpi", "milestone", "phase", "defect", "incident", "contract_value"],
    "restaurant": ["covers", "food_cost", "labour_cost", "menu", "table", "prime_cost", "meal_period", "waste", "recipe", "kitchen"],
    "general": ["item", "product", "service", "amount", "date", "customer", "category", "total", "description", "notes"],
}

# ---------------------------------------------------------------------------
# COLUMN DETECTION
# ---------------------------------------------------------------------------


def find_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return the first df column whose name contains any candidate keyword (case-insensitive)."""
    cols_lower = {col: col.lower() for col in df.columns}
    for col, col_l in cols_lower.items():
        for kw in candidates:
            if kw.lower() in col_l:
                return col
    return None


def find_numeric_fallback(df: pd.DataFrame, exclude: Optional[list] = None) -> Optional[str]:
    """Find the best numeric column if no amount column was detected."""
    exclude = [e for e in (exclude or []) if e is not None]
    for col in df.select_dtypes(include=[np.number]).columns:
        if col in exclude:
            continue
        series = df[col].dropna()
        if len(series) == 0:
            continue
        if series.std() > 0 and series.mean() > 0:
            return col
    return None


def detect_columns(df: pd.DataFrame) -> dict:
    """Map each semantic role to a DataFrame column using keyword matching."""
    return {role: find_column(df, candidates) for role, candidates in COLUMN_CANDIDATES.items()}


def build_column_report(detected: dict) -> dict:
    """Summarise which semantic roles were found and which are missing."""
    found = [{"role": r, "column": c} for r, c in detected.items() if c is not None]
    missing = [{"role": r} for r, c in detected.items() if c is None]
    score = len(found)
    total = len(detected)
    summary = f"{score} of {total} roles detected"
    return {"found": found, "missing": missing, "summary": summary, "score": score, "total": total}


def detect_dataset_type(df: pd.DataFrame) -> str:
    """Score column headers against industry signatures and return best-matching type."""
    header_str = " ".join(c.lower() for c in df.columns)
    scores = {}
    for industry, keywords in DATASET_SIGNATURES.items():
        if industry == "general":
            continue
        scores[industry] = sum(1 for kw in keywords if kw in header_str)
    best = max(scores, key=lambda k: scores[k]) if scores else "general"
    return best if scores.get(best, 0) >= 2 else "general"


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — HR
# ---------------------------------------------------------------------------


def _analyze_hr(df: pd.DataFrame, detected: dict) -> dict:
    """Compute HR/payroll KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        category_col = detected.get("category")
        date_col = detected.get("date")
        customer_col = detected.get("customer")

        try:
            out["headcount"] = int(len(df))
        except Exception:
            pass

        if amount_col and amount_col in df.columns:
            nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
            try:
                out["total_payroll"] = round(float(nums.sum()), 2)
            except Exception:
                pass
            try:
                out["avg_salary"] = round(float(nums.mean()), 2)
            except Exception:
                pass
            try:
                out["median_salary"] = round(float(nums.median()), 2)
            except Exception:
                pass
            try:
                out["min_salary"] = round(float(nums.min()), 2)
            except Exception:
                pass
            try:
                out["max_salary"] = round(float(nums.max()), 2)
            except Exception:
                pass
            try:
                bins = [0, 30000, 60000, 100000, 150000, 200000, np.inf]
                labels = ["<30k", "30-60k", "60-100k", "100-150k", "150-200k", "200k+"]
                cut = pd.cut(nums, bins=bins, labels=labels)
                out["salary_bands"] = {str(k): int(v) for k, v in cut.value_counts().sort_index().items()}
            except Exception:
                pass

        if category_col and category_col in df.columns:
            try:
                grp = df[category_col].value_counts()
                out["dept_breakdown"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [int(v) for v in grp.values],
                    "counts": [int(v) for v in grp.values],
                }
            except Exception:
                pass

        if date_col and date_col in df.columns:
            try:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col])
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                trend = tmp.groupby("_m").size().sort_index()
                out["headcount_trend"] = {
                    "labels": [str(p) for p in trend.index],
                    "values": [int(v) for v in trend.values],
                }
            except Exception:
                pass

        # Turnover rate
        try:
            status_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["status", "employment_status"])),
                None,
            )
            if status_col:
                terminated = df[status_col].astype(str).str.lower().str.contains(
                    "terminat|left|resigned|inactive|separated", na=False
                )
                t_count = int(terminated.sum())
                a_count = int(len(df) - t_count)
                out["terminated_headcount"] = t_count
                out["active_headcount"] = a_count
                out["turnover_rate"] = round(t_count / len(df) * 100, 1) if len(df) > 0 else 0.0
        except Exception:
            pass

        # Tenure bands
        try:
            tenure_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["tenure", "years_of_service", "years_employed"])),
                None,
            )
            if tenure_col:
                ten = pd.to_numeric(df[tenure_col], errors="coerce").dropna()
                bins = [0, 0.5, 1, 2, 5, 10, np.inf]
                labels = ["<6mo", "6mo-1yr", "1-2yr", "2-5yr", "5-10yr", "10yr+"]
                cut = pd.cut(ten, bins=bins, labels=labels)
                out["tenure_bands"] = {str(k): int(v) for k, v in cut.value_counts().sort_index().items()}
                out["avg_tenure_years"] = round(float(ten.mean()), 2)
            elif date_col and date_col in df.columns:
                hire_col = next(
                    (c for c in df.columns if "hire" in c.lower() or "start_date" in c.lower()),
                    date_col,
                )
                tmp = pd.to_datetime(df[hire_col], errors="coerce").dropna()
                if len(tmp) > 0:
                    tenure_years = (pd.Timestamp.now() - tmp).dt.days / 365.25
                    bins = [0, 0.5, 1, 2, 5, 10, np.inf]
                    labels = ["<6mo", "6mo-1yr", "1-2yr", "2-5yr", "5-10yr", "10yr+"]
                    cut = pd.cut(tenure_years, bins=bins, labels=labels)
                    out["tenure_bands"] = {str(k): int(v) for k, v in cut.value_counts().sort_index().items()}
                    out["avg_tenure_years"] = round(float(tenure_years.mean()), 2)
        except Exception:
            pass

        # Payroll as pct of revenue
        try:
            if "total_payroll" in out and amount_col:
                pass  # will be computed in analyze_data if total_revenue available
        except Exception:
            pass

        # Gender pay gap
        try:
            gender_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["gender", "sex"])),
                None,
            )
            if gender_col and amount_col and amount_col in df.columns:
                tmp = df[[gender_col, amount_col]].copy()
                tmp[amount_col] = pd.to_numeric(tmp[amount_col], errors="coerce")
                male_avg = float(tmp[tmp[gender_col].astype(str).str.lower().isin(["male", "m"])][amount_col].mean() or 0)
                female_avg = float(tmp[tmp[gender_col].astype(str).str.lower().isin(["female", "f"])][amount_col].mean() or 0)
                if male_avg > 0:
                    out["gender_pay_gap_pct"] = round((male_avg - female_avg) / male_avg * 100, 1)
                out["avg_male_salary"] = round(male_avg, 2)
                out["avg_female_salary"] = round(female_avg, 2)
        except Exception:
            pass

        # Absenteeism
        try:
            absent_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["absent_days", "days_absent", "absenteeism"])),
                None,
            )
            if absent_col:
                total_absent = pd.to_numeric(df[absent_col], errors="coerce").sum()
                headcount = len(df)
                out["absenteeism_rate"] = round(float(total_absent / (headcount * 220) * 100), 1)
                out["avg_absent_days"] = round(float(total_absent / headcount), 2)
        except Exception:
            pass

        # Flight risk
        try:
            if amount_col and amount_col in df.columns:
                nums = pd.to_numeric(df[amount_col], errors="coerce")
                q25 = nums.quantile(0.25)
                low_sal = nums < q25
                if "avg_tenure_years" in out:
                    tenure_col2 = next(
                        (c for c in df.columns if "tenure" in c.lower()),
                        None,
                    )
                    if tenure_col2:
                        ten2 = pd.to_numeric(df[tenure_col2], errors="coerce").fillna(99)
                        risk = int((low_sal & (ten2 < 1)).sum())
                        out["flight_risk_count"] = risk
                        out["flight_risk_pct"] = round(risk / len(df) * 100, 1)
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — REAL ESTATE
# ---------------------------------------------------------------------------


def _analyze_real_estate(df: pd.DataFrame, detected: dict) -> dict:
    """Compute real estate portfolio KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        profit_col = detected.get("profit")
        category_col = detected.get("category")
        state_col = detected.get("state")
        qty_col = detected.get("qty")

        try:
            out["property_count"] = int(len(df))
        except Exception:
            pass

        if amount_col and amount_col in df.columns:
            nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
            try:
                out["portfolio_value"] = round(float(nums.sum()), 2)
            except Exception:
                pass
            try:
                out["avg_property_price"] = round(float(nums.mean()), 2)
            except Exception:
                pass
            try:
                out["median_property_price"] = round(float(nums.median()), 2)
            except Exception:
                pass
            try:
                bins = [0, 100000, 250000, 500000, 1000000, 2000000, np.inf]
                labels = ["<100k", "100-250k", "250-500k", "500k-1M", "1-2M", "2M+"]
                cut = pd.cut(nums, bins=bins, labels=labels)
                out["price_bands"] = {str(k): int(v) for k, v in cut.value_counts().sort_index().items()}
            except Exception:
                pass

        if profit_col and profit_col in df.columns:
            try:
                rent = pd.to_numeric(df[profit_col], errors="coerce").dropna()
                total_rent = float(rent.sum())
                out["total_rent_income"] = round(total_rent, 2)
                pv = out.get("portfolio_value", 0)
                if pv and pv > 0:
                    out["yield_pct"] = round(total_rent / pv * 100, 1)
                    out["net_yield_pct"] = round(total_rent * 0.85 / pv * 100, 1)
            except Exception:
                pass

        if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(category_col)[amount_col].apply(
                    lambda x: pd.to_numeric(x, errors="coerce").sum()
                ).sort_values(ascending=False)
                out["property_type_breakdown"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [round(float(v), 2) for v in grp.values],
                }
            except Exception:
                pass

        if state_col and state_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(state_col)[amount_col].apply(
                    lambda x: pd.to_numeric(x, errors="coerce").sum()
                ).sort_values(ascending=False)
                out["location_breakdown"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [round(float(v), 2) for v in grp.values],
                }
            except Exception:
                pass

        # Vacancy rate
        try:
            vac_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["status", "vacancy", "occupied"])),
                None,
            )
            if vac_col:
                s = df[vac_col].astype(str).str.lower()
                vacant = int(s.str.contains("vacant|unoccupied|empty|available", na=False).sum())
                occupied = int(len(df) - vacant)
                out["vacant_units"] = vacant
                out["occupied_units"] = occupied
                out["vacancy_rate"] = round(vacant / len(df) * 100, 1) if len(df) > 0 else 0.0
        except Exception:
            pass

        # Price per sqm
        try:
            if qty_col and qty_col in df.columns and amount_col and amount_col in df.columns:
                sqm = pd.to_numeric(df[qty_col], errors="coerce")
                prices = pd.to_numeric(df[amount_col], errors="coerce")
                valid = (sqm > 0) & prices.notna()
                if valid.sum() > 0:
                    out["avg_price_per_sqm"] = round(float((prices[valid] / sqm[valid]).mean()), 2)
        except Exception:
            pass

        # Capital appreciation
        try:
            app_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["appreciation", "capital_growth", "growth_rate"])),
                None,
            )
            if app_col:
                app = pd.to_numeric(df[app_col], errors="coerce").dropna()
                out["avg_capital_appreciation_pct"] = round(float(app.mean()), 1)
        except Exception:
            pass

        # LTV
        try:
            ltv_col = next(
                (c for c in df.columns if any(k in c.lower() for k in ["ltv", "loan_to_value", "mortgage", "loan"])),
                None,
            )
            if ltv_col and amount_col and amount_col in df.columns:
                ltv_vals = pd.to_numeric(df[ltv_col], errors="coerce")
                prices = pd.to_numeric(df[amount_col], errors="coerce")
                if ltv_vals.mean() < 2:  # already a ratio/pct
                    ratio = ltv_vals * 100 if ltv_vals.mean() < 1.5 else ltv_vals
                else:
                    valid = prices > 0
                    ratio = (ltv_vals[valid] / prices[valid] * 100)
                out["avg_ltv_ratio"] = round(float(ratio.mean()), 1)
                out["high_ltv_count"] = int((ratio > 80).sum())
                total = len(ratio.dropna())
                out["high_ltv_pct"] = round(out["high_ltv_count"] / total * 100, 1) if total > 0 else 0.0
        except Exception:
            pass

        # Portfolio risk score
        try:
            risk = 0
            vac = out.get("vacancy_rate", 0) or 0
            ltv = out.get("avg_ltv_ratio", 0) or 0
            yld = out.get("yield_pct", 5) or 5
            if vac > 20:
                risk += 30
            elif vac > 10:
                risk += 15
            if ltv > 85:
                risk += 30
            elif ltv > 75:
                risk += 15
            if yld < 2:
                risk += 20
            elif yld < 4:
                risk += 10
            out["portfolio_risk_score"] = min(100, risk)
            out["portfolio_risk_tier"] = "High" if risk >= 50 else ("Moderate" if risk >= 25 else "Low")
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — HEALTHCARE
# ---------------------------------------------------------------------------


def _analyze_healthcare(df: pd.DataFrame, detected: dict) -> dict:
    """Compute healthcare KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        category_col = detected.get("category")
        date_col = detected.get("date")
        customer_col = detected.get("customer")
        qty_col = detected.get("qty")

        try:
            out["patient_count"] = (
                int(df[customer_col].nunique()) if customer_col and customer_col in df.columns else int(len(df))
            )
        except Exception:
            pass

        if amount_col and amount_col in df.columns:
            try:
                nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                out["total_revenue"] = round(float(nums.sum()), 2)
                pc = out.get("patient_count", 1) or 1
                out["revenue_per_patient"] = round(float(nums.sum() / pc), 2)
            except Exception:
                pass

        if category_col and category_col in df.columns:
            try:
                grp = df[category_col].value_counts().head(10)
                out["diagnosis_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [int(v) for v in grp.values]}
            except Exception:
                pass

        try:
            dept_col = next((c for c in df.columns if any(k in c.lower() for k in ["department", "dept", "ward"])), None)
            if dept_col:
                grp = df[dept_col].value_counts().head(10)
                out["dept_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [int(v) for v in grp.values]}
        except Exception:
            pass

        if date_col and date_col in df.columns:
            try:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col])
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                trend = tmp.groupby("_m").size().sort_index()
                out["patient_volume_trend"] = {"labels": [str(p) for p in trend.index], "values": [int(v) for v in trend.values]}
            except Exception:
                pass

        try:
            los_col = next((c for c in df.columns if any(k in c.lower() for k in ["length_of_stay", "los", "alos", "days_admitted"])), None)
            if los_col:
                los = pd.to_numeric(df[los_col], errors="coerce").dropna()
                out["alos_days"] = round(float(los.mean()), 1)
        except Exception:
            pass

        try:
            bed_col = next((c for c in df.columns if any(k in c.lower() for k in ["beds_available", "capacity", "total_beds"])), None)
            if bed_col and qty_col and qty_col in df.columns:
                avail = pd.to_numeric(df[bed_col], errors="coerce").sum()
                occ = pd.to_numeric(df[qty_col], errors="coerce").sum()
                if avail > 0:
                    out["bed_occupancy_rate"] = round(float(occ / avail * 100), 1)
        except Exception:
            pass

        try:
            cost_col = next((c for c in df.columns if any(k in c.lower() for k in ["cost", "expense", "charges"])), None)
            if cost_col and cost_col != amount_col:
                costs = pd.to_numeric(df[cost_col], errors="coerce").dropna()
                out["total_cost"] = round(float(costs.sum()), 2)
                pc = out.get("patient_count", 1) or 1
                out["cost_per_patient"] = round(float(costs.sum() / pc), 2)
                rev = out.get("total_revenue", 0)
                if rev and rev > 0:
                    out["operating_margin_pct"] = round((rev - float(costs.sum())) / rev * 100, 1)
        except Exception:
            pass

        try:
            payer_col = next((c for c in df.columns if any(k in c.lower() for k in ["payer", "insurance", "payer_type"])), None)
            if payer_col:
                pm = df[payer_col].value_counts().head(5)
                out["payer_mix"] = {"labels": list(pm.index.astype(str)), "values": [int(v) for v in pm.values]}
        except Exception:
            pass

        try:
            re_col = next((c for c in df.columns if any(k in c.lower() for k in ["readmission", "readmit"])), None)
            if re_col:
                re_count = df[re_col].astype(str).str.lower().isin(["yes", "true", "1"]).sum()
                pc = out.get("patient_count", 1) or 1
                out["readmission_rate"] = round(int(re_count) / pc * 100, 1)
        except Exception:
            pass

        try:
            staff_col = next((c for c in df.columns if "staff" in c.lower()), None)
            if staff_col:
                staff_count = pd.to_numeric(df[staff_col], errors="coerce").dropna().sum()
                if staff_count > 0:
                    out["patient_staff_ratio"] = round(out.get("patient_count", len(df)) / float(staff_count), 2)
        except Exception:
            pass

        try:
            comp_col = next((c for c in df.columns if "compliance" in c.lower()), None)
            if comp_col:
                comp = pd.to_numeric(df[comp_col], errors="coerce").dropna()
                val = float(comp.mean())
                out["compliance_score"] = round(val * 100 if val <= 1 else val, 1)
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — LOGISTICS
# ---------------------------------------------------------------------------


def _analyze_logistics(df: pd.DataFrame, detected: dict) -> dict:
    """Compute logistics and delivery KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        category_col = detected.get("category")
        state_col = detected.get("state")
        date_col = detected.get("date")
        qty_col = detected.get("qty")

        out["total_deliveries"] = int(len(df))

        if amount_col and amount_col in df.columns:
            try:
                nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                out["total_revenue"] = round(float(nums.sum()), 2)
                out["cost_per_delivery"] = round(float(nums.mean()), 2)
            except Exception:
                pass

        try:
            ot_col = next((c for c in df.columns if any(k in c.lower() for k in ["on_time", "ontime", "status"])), None)
            if ot_col:
                s = df[ot_col].astype(str).str.lower()
                on_time = s.isin(["true", "1", "yes", "on_time", "on time", "delivered_on_time"]).sum()
                out["on_time_rate"] = round(int(on_time) / len(df) * 100, 1)
        except Exception:
            pass

        if category_col and category_col in df.columns:
            try:
                grp = df[category_col].value_counts().head(10)
                out["route_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [int(v) for v in grp.values]}
            except Exception:
                pass

        if state_col and state_col in df.columns:
            try:
                grp = df[state_col].value_counts().head(10)
                out["zone_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [int(v) for v in grp.values]}
            except Exception:
                pass

        if date_col and date_col in df.columns:
            try:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col])
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                trend = tmp.groupby("_m").size().sort_index()
                out["delivery_volume_trend"] = {"labels": [str(p) for p in trend.index], "values": [int(v) for v in trend.values]}
            except Exception:
                pass

        try:
            att_col = next((c for c in df.columns if any(k in c.lower() for k in ["attempt", "delivery_attempt"])), None)
            if att_col:
                atts = pd.to_numeric(df[att_col], errors="coerce").dropna()
                out["fadr"] = round(float((atts == 1).sum() / len(atts) * 100), 1)
                out["avg_delivery_attempts"] = round(float(atts.mean()), 2)
        except Exception:
            pass

        try:
            ret_col = next((c for c in df.columns if any(k in c.lower() for k in ["return", "damage", "returned"])), None)
            status_col = next((c for c in df.columns if "status" in c.lower()), None)
            if ret_col:
                ret_count = int(df[ret_col].astype(str).str.lower().str.contains("return|damage", na=False).sum())
            elif status_col:
                ret_count = int(df[status_col].astype(str).str.lower().str.contains("return|damage", na=False).sum())
            else:
                ret_count = 0
            out["return_damage_count"] = ret_count
            out["return_damage_rate"] = round(ret_count / len(df) * 100, 1)
        except Exception:
            pass

        try:
            dist_col = next((c for c in df.columns if any(k in c.lower() for k in ["distance", "km", "miles"])), None)
            if dist_col and amount_col and amount_col in df.columns:
                dist = pd.to_numeric(df[dist_col], errors="coerce").dropna()
                costs = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                total_dist = float(dist.sum())
                out["total_distance_km"] = round(total_dist, 2)
                if total_dist > 0:
                    out["cost_per_km"] = round(float(costs.sum() / total_dist), 2)
        except Exception:
            pass

        try:
            wt_col = next((c for c in df.columns if any(k in c.lower() for k in ["weight", "kg", "mass"])), None)
            if wt_col and amount_col and amount_col in df.columns:
                wt = pd.to_numeric(df[wt_col], errors="coerce").sum()
                costs = pd.to_numeric(df[amount_col], errors="coerce").sum()
                if wt > 0:
                    out["cost_per_kg"] = round(float(costs / wt), 2)
        except Exception:
            pass

        try:
            sla_col = next((c for c in df.columns if "sla" in c.lower()), None)
            if sla_col:
                breached = int(df[sla_col].astype(str).str.lower().str.contains("breach|fail|late|miss", na=False).sum())
                out["sla_breach_rate"] = round(breached / len(df) * 100, 1)
        except Exception:
            pass

        try:
            ot_col2 = next((c for c in df.columns if "on_time" in c.lower()), None)
            ret_col2 = next((c for c in df.columns if "return" in c.lower() or "damage" in c.lower()), None)
            if ot_col2 and ret_col2:
                on_time_mask = df[ot_col2].astype(str).str.lower().isin(["true", "1", "yes", "on_time"])
                no_damage_mask = ~df[ret_col2].astype(str).str.lower().str.contains("return|damage", na=False)
                out["perfect_order_rate"] = round(float((on_time_mask & no_damage_mask).sum() / len(df) * 100), 1)
        except Exception:
            pass

        try:
            carrier_col = next((c for c in df.columns if any(k in c.lower() for k in ["carrier", "courier", "provider"])), None)
            if carrier_col:
                ot_col3 = next((c for c in df.columns if "on_time" in c.lower()), None)
                scorecard = []
                for name, grp_df in df.groupby(carrier_col):
                    entry: dict = {"carrier": str(name), "deliveries": int(len(grp_df))}
                    if ot_col3:
                        try:
                            ot = grp_df[ot_col3].astype(str).str.lower().isin(["true", "1", "yes", "on_time"]).mean()
                            entry["on_time_rate"] = round(float(ot * 100), 1)
                        except Exception:
                            pass
                    scorecard.append(entry)
                scorecard.sort(key=lambda x: x.get("on_time_rate", 0), reverse=True)
                out["carrier_scorecard"] = scorecard[:10]
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — HOSPITALITY
# ---------------------------------------------------------------------------


def _analyze_hospitality(df: pd.DataFrame, detected: dict) -> dict:
    """Compute hospitality and hotel KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        category_col = detected.get("category")
        payment_col = detected.get("payment")
        date_col = detected.get("date")
        qty_col = detected.get("qty")

        out["total_bookings"] = int(len(df))

        if amount_col and amount_col in df.columns:
            try:
                nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                out["total_revenue"] = round(float(nums.sum()), 2)
                out["adr"] = round(float(nums.mean()), 2)
            except Exception:
                pass

        try:
            occ_col = next((c for c in df.columns if any(k in c.lower() for k in ["rooms_available", "capacity", "total_rooms"])), None)
            if occ_col and qty_col and qty_col in df.columns:
                avail = pd.to_numeric(df[occ_col], errors="coerce").sum()
                occ = pd.to_numeric(df[qty_col], errors="coerce").sum()
                if avail > 0:
                    out["occupancy_rate"] = round(float(occ / avail * 100), 1)
            elif qty_col and qty_col in df.columns:
                occ = pd.to_numeric(df[qty_col], errors="coerce").sum()
                if occ > 0:
                    out["occupancy_rate"] = min(100.0, round(float(occ / len(df) * 100), 1))
        except Exception:
            pass

        try:
            adr = out.get("adr", 0)
            occ_rate = out.get("occupancy_rate", 0)
            if adr and occ_rate:
                out["revpar"] = round(adr * (occ_rate / 100), 2)
        except Exception:
            pass

        if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(category_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False)
                cnt = df.groupby(category_col).size()
                out["room_type_breakdown"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [round(float(v), 2) for v in grp.values],
                    "counts": [int(cnt.get(k, 0)) for k in grp.index],
                }
            except Exception:
                pass

        if payment_col and payment_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(payment_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False)
                out["booking_source_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
            except Exception:
                pass

        try:
            cancel_col = next((c for c in df.columns if "cancel" in c.lower() or "status" in c.lower()), None)
            if cancel_col:
                cancelled = df[cancel_col].astype(str).str.lower().str.contains("cancel", na=False).sum()
                out["cancelled_bookings"] = int(cancelled)
                out["cancellation_rate"] = round(int(cancelled) / len(df) * 100, 1)
        except Exception:
            pass

        try:
            los_col = next((c for c in df.columns if any(k in c.lower() for k in ["nights", "length_of_stay", "los", "duration"])), None)
            if los_col:
                los = pd.to_numeric(df[los_col], errors="coerce").dropna()
                out["avg_los"] = round(float(los.mean()), 1)
        except Exception:
            pass

        try:
            lt_col = next((c for c in df.columns if "lead_time" in c.lower()), None)
            if lt_col:
                lt = pd.to_numeric(df[lt_col], errors="coerce").dropna()
                out["avg_lead_time_days"] = round(float(lt.mean()), 1)
        except Exception:
            pass

        try:
            if payment_col and payment_col in df.columns and amount_col and amount_col in df.columns:
                ota_kw = ["booking.com", "expedia", "airbnb", "ota", "agoda", "hotels.com", "online"]
                src = df[payment_col].astype(str).str.lower()
                ota_mask = src.str.contains("|".join(ota_kw), na=False)
                nums = pd.to_numeric(df[amount_col], errors="coerce")
                ota_rev = float(nums[ota_mask].sum())
                total_rev = out.get("total_revenue", float(nums.sum()))
                if total_rev > 0:
                    out["ota_revenue_pct"] = round(ota_rev / total_rev * 100, 1)
                    out["direct_revenue_pct"] = round(100 - out["ota_revenue_pct"], 1)
        except Exception:
            pass

        try:
            gop_col = next((c for c in df.columns if any(k in c.lower() for k in ["gop", "gross_operating_profit"])), None)
            if gop_col:
                gop = pd.to_numeric(df[gop_col], errors="coerce").dropna()
                total_gop = float(gop.sum())
                out["goppar"] = round(total_gop / max(len(df), 1), 2)
                rev = out.get("total_revenue", 0)
                if rev and rev > 0:
                    out["gop_pct"] = round(total_gop / rev * 100, 1)
        except Exception:
            pass

        try:
            if date_col and date_col in df.columns and amount_col and amount_col in df.columns:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col])
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                monthly = tmp.groupby("_m")[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_index()
                if len(monthly) > 1:
                    cv = float(monthly.std() / monthly.mean() * 100) if monthly.mean() != 0 else 0
                    out["seasonality_score"] = round(cv, 1)
                out["monthly_trend"] = {"labels": [str(p) for p in monthly.index], "values": [round(float(v), 2) for v in monthly.values]}
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — CONSTRUCTION
# ---------------------------------------------------------------------------


def _analyze_construction(df: pd.DataFrame, detected: dict) -> dict:
    """Compute construction project KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        category_col = detected.get("category")
        state_col = detected.get("state")

        out["project_count"] = int(len(df))

        if amount_col and amount_col in df.columns:
            try:
                nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                out["total_contract_value"] = round(float(nums.sum()), 2)
                out["avg_project_value"] = round(float(nums.mean()), 2)
            except Exception:
                pass

        try:
            actual_col = next((c for c in df.columns if "actual_cost" in c.lower() or ("actual" in c.lower() and "cost" in c.lower())), None)
            budget_col = next((c for c in df.columns if any(k in c.lower() for k in ["budgeted_cost", "planned_cost", "budget"])), None)
            if actual_col and budget_col:
                actual = pd.to_numeric(df[actual_col], errors="coerce")
                budget = pd.to_numeric(df[budget_col], errors="coerce")
                valid = (budget > 0) & actual.notna() & budget.notna()
                variance = (actual[valid] - budget[valid]) / budget[valid] * 100
                out["budget_variance_pct"] = round(float(variance.mean()), 1)
                out["over_budget_count"] = int((variance > 10).sum())
                out["on_budget_count"] = int((variance <= 10).sum())
        except Exception:
            pass

        if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(category_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
                cnt = df.groupby(category_col).size()
                out["project_stage_breakdown"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [round(float(v), 2) for v in grp.values],
                    "counts": [int(cnt.get(k, 0)) for k in grp.index],
                }
            except Exception:
                pass

        if state_col and state_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(state_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
                out["site_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
            except Exception:
                pass

        try:
            if amount_col and amount_col in df.columns:
                cost_col = next((c for c in df.columns if "cost" in c.lower() and c != amount_col), None)
                if cost_col:
                    costs = pd.to_numeric(df[cost_col], errors="coerce")
                    vals = pd.to_numeric(df[amount_col], errors="coerce")
                    valid = (vals > 0) & costs.notna()
                    margins = (vals[valid] - costs[valid]) / vals[valid] * 100
                    out["contract_margin_pct"] = round(float(margins.mean()), 1)
        except Exception:
            pass

        try:
            spi_col = next((c for c in df.columns if any(k in c.lower() for k in ["spi", "schedule_performance"])), None)
            if spi_col:
                spi = pd.to_numeric(df[spi_col], errors="coerce").dropna()
                avg_spi = float(spi.mean())
                out["avg_spi"] = round(avg_spi, 2)
                out["spi_status"] = (
                    "On Schedule" if avg_spi >= 1.0 else
                    "Slightly Behind" if avg_spi >= 0.9 else
                    "Behind Schedule" if avg_spi >= 0.75 else "Critical"
                )
        except Exception:
            pass

        try:
            pay_col = next((c for c in df.columns if any(k in c.lower() for k in ["payment_status", "overdue"])), None)
            if pay_col:
                overdue = int(df[pay_col].astype(str).str.lower().str.contains("overdue|unpaid|late", na=False).sum())
                out["overdue_payments"] = overdue
                out["overdue_payment_pct"] = round(overdue / len(df) * 100, 1)
        except Exception:
            pass

        try:
            cpi_col = next((c for c in df.columns if any(k in c.lower() for k in ["cpi", "cost_performance"])), None)
            if cpi_col:
                cpi_vals = pd.to_numeric(df[cpi_col], errors="coerce").dropna()
                avg_cpi = float(cpi_vals.mean())
                out["cpi"] = round(avg_cpi, 2)
                out["cpi_status"] = (
                    "Under Budget" if avg_cpi >= 1.0 else
                    "Slightly Over" if avg_cpi >= 0.9 else
                    "Over Budget" if avg_cpi >= 0.75 else "Critical"
                )
        except Exception:
            pass

        try:
            def_col = next((c for c in df.columns if any(k in c.lower() for k in ["defect", "snag", "punch"])), None)
            if def_col:
                defects = pd.to_numeric(df[def_col], errors="coerce").dropna()
                out["total_defects"] = int(defects.sum())
                out["avg_defects_per_project"] = round(float(defects.mean()), 2)
        except Exception:
            pass

        try:
            inc_col = next((c for c in df.columns if any(k in c.lower() for k in ["incident", "safety", "accident"])), None)
            if inc_col:
                incs = pd.to_numeric(df[inc_col], errors="coerce").dropna()
                out["total_incidents"] = int(incs.sum())
                out["incident_rate"] = round(float(incs.mean()), 2)
        except Exception:
            pass

        try:
            risk = 0
            bv = abs(out.get("budget_variance_pct", 0) or 0)
            spi_v = out.get("avg_spi", 1.0) or 1.0
            cpi_v = out.get("cpi", 1.0) or 1.0
            inc = out.get("total_incidents", 0) or 0
            if bv > 20: risk += 30
            elif bv > 10: risk += 15
            if spi_v < 0.75: risk += 25
            elif spi_v < 0.9: risk += 12
            if cpi_v < 0.75: risk += 25
            elif cpi_v < 0.9: risk += 12
            if inc > 5: risk += 20
            elif inc > 2: risk += 10
            out["project_risk_score"] = min(100, risk)
            out["project_risk_tier"] = "Critical" if risk >= 75 else ("High" if risk >= 50 else ("Moderate" if risk >= 25 else "Low"))
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — MARKETING
# ---------------------------------------------------------------------------


def _analyze_marketing(df: pd.DataFrame, detected: dict) -> dict:
    """Compute marketing campaign KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        profit_col = detected.get("profit")
        category_col = detected.get("category")
        payment_col = detected.get("payment")
        qty_col = detected.get("qty")

        if amount_col and amount_col in df.columns:
            try:
                out["total_spend"] = round(float(pd.to_numeric(df[amount_col], errors="coerce").dropna().sum()), 2)
            except Exception:
                pass

        try:
            conv_col = next((c for c in df.columns if any(k in c.lower() for k in ["conversions", "leads", "converted"])), None)
            if conv_col:
                convs = int(pd.to_numeric(df[conv_col], errors="coerce").dropna().sum())
                out["total_conversions"] = convs
                spend = out.get("total_spend", 0)
                if spend and convs > 0:
                    out["avg_cpa"] = round(spend / convs, 2)
        except Exception:
            pass

        if profit_col and profit_col in df.columns:
            try:
                rev = pd.to_numeric(df[profit_col], errors="coerce").dropna()
                total_rev = float(rev.sum())
                out["total_revenue"] = round(total_rev, 2)
                spend = out.get("total_spend", 0)
                if spend and spend > 0:
                    out["avg_roas"] = round(total_rev / spend, 2)
                    out["campaign_roi_pct"] = round((total_rev - spend) / spend * 100, 1)
            except Exception:
                pass

        if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(category_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False)
                out["campaign_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
            except Exception:
                pass

        if payment_col and payment_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(payment_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False)
                out["channel_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
                spend = out.get("total_spend", 0)
                if spend and len(grp) > 0:
                    out["top_channel_pct"] = round(float(grp.iloc[0] / spend * 100), 1)
            except Exception:
                pass

        try:
            click_col = next((c for c in df.columns if "click" in c.lower()), None) or qty_col
            imp_col = next((c for c in df.columns if "impression" in c.lower()), None)
            if click_col and click_col in df.columns:
                out["total_clicks"] = int(pd.to_numeric(df[click_col], errors="coerce").dropna().sum())
            if imp_col and imp_col in df.columns:
                out["total_impressions"] = int(pd.to_numeric(df[imp_col], errors="coerce").dropna().sum())
                if "total_clicks" in out and out["total_impressions"] > 0:
                    out["avg_ctr"] = round(out["total_clicks"] / out["total_impressions"] * 100, 2)
            convs = out.get("total_conversions", 0)
            clicks = out.get("total_clicks", 0)
            if convs and clicks and clicks > 0:
                out["conversion_rate"] = round(convs / clicks * 100, 2)
        except Exception:
            pass

        try:
            nc_col = next((c for c in df.columns if "new_customer" in c.lower()), None)
            if nc_col:
                nc = int(pd.to_numeric(df[nc_col], errors="coerce").dropna().sum())
                out["total_new_customers"] = nc
                spend = out.get("total_spend", 0)
                if spend and nc > 0:
                    out["cac"] = round(spend / nc, 2)
        except Exception:
            pass

        try:
            ltv_col = next((c for c in df.columns if any(k in c.lower() for k in ["ltv", "customer_value", "lifetime_value"])), None)
            if ltv_col:
                ltv_val = round(float(pd.to_numeric(df[ltv_col], errors="coerce").dropna().mean()), 2)
                out["ltv"] = ltv_val
                cac = out.get("cac", 0)
                if cac and cac > 0:
                    ratio = round(ltv_val / cac, 2)
                    out["cac_ltv_ratio"] = ratio
                    out["cac_ltv_status"] = "Excellent" if ratio >= 3 else ("Good" if ratio >= 1 else "Poor")
        except Exception:
            pass

        try:
            roi = out.get("campaign_roi_pct", 0) or 0
            roas = out.get("avg_roas", 0) or 0
            out["budget_efficiency_score"] = min(100, round((roi / 100) * (roas / 4) * 100, 1)) if roas else 0
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — BANK STATEMENT
# ---------------------------------------------------------------------------


def _analyze_bank_statement(df: pd.DataFrame, detected: dict) -> dict:
    """Compute bank statement cash flow and credit KPIs."""
    try:
        out: dict = {}
        date_col = detected.get("date")
        customer_col = detected.get("customer")
        payment_col = detected.get("payment")
        cols_lower = {c: c.lower() for c in df.columns}

        # --- Normalise into credit/debit series ---
        _credit_series: pd.Series = pd.Series(dtype=float)
        _debit_series: pd.Series = pd.Series(dtype=float)

        def _find_col(*keywords: str) -> Optional[str]:
            for col, col_l in cols_lower.items():
                if any(kw in col_l for kw in keywords):
                    return col
            return None

        credit_col = _find_col("credit", "credits", "inflow", "receipt", "deposit", "cr")
        debit_col = _find_col("debit", "debits", "outflow", "withdrawal", "expense", "dr", "payment")
        type_col = _find_col("type", "drcr", "dr_cr", "indicator", "transaction_type")
        amount_col = detected.get("amount")
        balance_col = _find_col("balance", "closing_balance", "running_balance")

        # Case A: separate credit + debit columns
        if credit_col and debit_col and credit_col != debit_col:
            _credit_series = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
            _debit_series = pd.to_numeric(df[debit_col], errors="coerce").fillna(0).abs()
        # Case B: type indicator + amount
        elif type_col and amount_col and amount_col in df.columns:
            amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
            t = df[type_col].astype(str).str.lower()
            cr_mask = t.isin(["credit", "cr", "deposit", "in", "receipt", "positive", "c"])
            _credit_series = amounts.where(cr_mask, 0)
            _debit_series = amounts.where(~cr_mask, 0).abs()
        # Case C: signed single amount
        elif amount_col and amount_col in df.columns:
            amounts = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
            _credit_series = amounts.where(amounts > 0, 0)
            _debit_series = amounts.where(amounts < 0, 0).abs()
        # Case D: only credit column
        elif credit_col and not debit_col:
            _credit_series = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
            _debit_series = pd.Series(0.0, index=df.index)
        # Case E: only debit column
        elif debit_col and not credit_col:
            _debit_series = pd.to_numeric(df[debit_col], errors="coerce").fillna(0).abs()
            _credit_series = pd.Series(0.0, index=df.index)
        else:
            return {"error": "Unable to detect credit/debit columns in bank statement"}

        # --- Core metrics ---
        try:
            out["total_inflows"] = round(float(_credit_series.sum()), 2)
            out["total_outflows"] = round(float(_debit_series.sum()), 2)
            out["net_position"] = round(out["total_inflows"] - out["total_outflows"], 2)
            out["total_transactions"] = int(len(df))
            out["credit_transactions"] = int((_credit_series > 0).sum())
            out["debit_transactions"] = int((_debit_series > 0).sum())
        except Exception:
            pass

        if balance_col:
            try:
                bal = pd.to_numeric(df[balance_col], errors="coerce").dropna()
                out["avg_balance"] = round(float(bal.mean()), 2)
                out["min_balance"] = round(float(bal.min()), 2)
                out["max_balance"] = round(float(bal.max()), 2)
            except Exception:
                pass

        # --- Top payees / income sources ---
        try:
            narr_col = _find_col("narration", "description", "payee", "remarks", "particulars", "memo")
            ref_col = narr_col or customer_col
            if ref_col and ref_col in df.columns:
                tmp = df.copy()
                tmp["_cr"] = _credit_series.values
                tmp["_dr"] = _debit_series.values
                payee_dr = tmp.groupby(ref_col)["_dr"].sum().sort_values(ascending=False).head(5)
                payee_cr = tmp.groupby(ref_col)["_cr"].sum().sort_values(ascending=False).head(5)
                out["top_payees"] = {"labels": list(payee_dr.index.astype(str)), "values": [round(float(v), 2) for v in payee_dr.values]}
                out["top_income_sources"] = {"labels": list(payee_cr.index.astype(str)), "values": [round(float(v), 2) for v in payee_cr.values]}
                total_out = out.get("total_outflows", 0)
                total_in = out.get("total_inflows", 0)
                if total_out > 0 and len(payee_dr) > 0:
                    out["top_payee_pct"] = round(float(payee_dr.iloc[0]) / total_out * 100, 1)
                if total_in > 0 and len(payee_cr) > 0:
                    out["top_income_source_pct"] = round(float(payee_cr.iloc[0]) / total_in * 100, 1)
        except Exception:
            pass

        # --- Monthly cashflow ---
        if date_col and date_col in df.columns:
            try:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col]).copy()
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                tmp["_cr"] = _credit_series.reindex(tmp.index).fillna(0).values
                tmp["_dr"] = _debit_series.reindex(tmp.index).fillna(0).values
                monthly_cr = tmp.groupby("_m")["_cr"].sum().sort_index()
                monthly_dr = tmp.groupby("_m")["_dr"].sum().sort_index()
                monthly_net = monthly_cr - monthly_dr
                labels = [str(p) for p in monthly_cr.index]
                out["monthly_cashflow"] = {
                    "labels": labels,
                    "inflows": [round(float(v), 2) for v in monthly_cr.values],
                    "outflows": [round(float(v), 2) for v in monthly_dr.values],
                    "net": [round(float(v), 2) for v in monthly_net.values],
                }
                # Overdraft months (net < 0)
                out["overdraft_months"] = int((monthly_net < 0).sum())
                # ABM
                net_vals = monthly_net.values
                out["abm_3m"] = round(float(net_vals[-3:].mean()), 2) if len(net_vals) >= 3 else round(float(net_vals.mean()), 2)
                out["abm_6m"] = round(float(net_vals[-6:].mean()), 2) if len(net_vals) >= 6 else round(float(net_vals.mean()), 2)
                out["abm_12m"] = round(float(net_vals.mean()), 2)
                # Income stability (CV-inverted)
                cr_vals = monthly_cr.values
                if cr_vals.mean() != 0:
                    cv = cr_vals.std() / cr_vals.mean() * 100
                    out["income_stability_score"] = round(max(0, min(100, 100 - cv)), 1)
                else:
                    out["income_stability_score"] = 0.0
                # Cash buffer months
                avg_monthly_out = float(monthly_dr.mean())
                if avg_monthly_out > 0 and "avg_balance" in out:
                    out["cash_buffer_months"] = round(out["avg_balance"] / avg_monthly_out, 1)
                # Running balance
                out["running_balance"] = {
                    "labels": labels,
                    "values": [round(float(v), 2) for v in monthly_net.cumsum().values],
                }
            except Exception:
                pass

        # Recurring / variable payments
        try:
            ref_col2 = _find_col("narration", "description", "payee", "remarks", "particulars") or customer_col
            if ref_col2 and ref_col2 in df.columns:
                freq = df[ref_col2].value_counts()
                out["recurring_payments"] = list(freq[freq >= 3].index.astype(str))
                out["variable_payments"] = list(freq[freq < 3].index.astype(str)[:20])
        except Exception:
            pass

        # Expense by payment mode
        try:
            if payment_col and payment_col in df.columns:
                tmp2 = df.copy()
                tmp2["_dr"] = _debit_series.values
                grp = tmp2.groupby(payment_col)["_dr"].sum().sort_values(ascending=False)
                out["expense_by_mode"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
                out["payment_mode_counts"] = {str(k): int(v) for k, v in df[payment_col].value_counts().items()}
        except Exception:
            pass

        # --- Fraud detection (Premium) ---
        try:
            fraud_flags: list[str] = []
            dr_vals = _debit_series[_debit_series > 0]

            # Rule 1: Round number clustering
            try:
                round_pct = float((dr_vals % 1000 == 0).sum() / max(len(dr_vals), 1) * 100)
                if round_pct > 30:
                    fraud_flags.append(f"Round number clustering: {round_pct:.1f}% of debits are multiples of 1000")
            except Exception:
                pass

            # Rule 2: Rapid in-out
            try:
                if "monthly_cashflow" in out:
                    inflows = out["monthly_cashflow"]["inflows"]
                    outflows = out["monthly_cashflow"]["outflows"]
                    if len(inflows) > 1:
                        avg_in = sum(inflows) / len(inflows)
                        avg_out = sum(outflows) / len(outflows)
                        rapid = sum(1 for i, o in zip(inflows, outflows) if i > 2 * avg_in and o > 2 * avg_out)
                        if rapid > 0:
                            fraud_flags.append(f"Rapid in-out detected in {rapid} month(s)")
            except Exception:
                pass

            # Rule 3: Statistical outliers
            try:
                if len(dr_vals) > 5:
                    mean_dr = float(dr_vals.mean())
                    std_dr = float(dr_vals.std())
                    outliers = dr_vals[dr_vals > mean_dr + 3 * std_dr]
                    if len(outliers) > 0:
                        fraud_flags.append(f"{len(outliers)} statistically anomalous debit(s) above ${mean_dr + 3*std_dr:,.2f}")
            except Exception:
                pass

            # Rule 4: Duplicate transactions
            try:
                if date_col and date_col in df.columns:
                    tmp3 = df.copy()
                    tmp3["_dr"] = _debit_series.values
                    tmp3["_date"] = pd.to_datetime(tmp3[date_col], errors="coerce").dt.date
                    dups = tmp3.duplicated(subset=["_dr", "_date"], keep=False) & (tmp3["_dr"] > 0)
                    if dups.sum() > 0:
                        fraud_flags.append(f"{int(dups.sum())} duplicate transaction(s) — same amount and date")
            except Exception:
                pass

            # Rule 5: Near-zero balance
            try:
                if balance_col:
                    bal_vals = pd.to_numeric(df[balance_col], errors="coerce").dropna()
                    near_zero = int((bal_vals < 100).sum())
                    if near_zero > 0:
                        fraud_flags.append(f"Balance fell below $100 on {near_zero} occasion(s)")
            except Exception:
                pass

            out["fraud_anomaly_flags"] = fraud_flags
            out["fraud_risk_score"] = min(100, len(fraud_flags) * 20)
        except Exception:
            pass

        # --- Credit risk (Premium) ---
        try:
            ref_col3 = _find_col("narration", "description", "payee", "remarks") or customer_col
            credit_risk: dict = {}
            if ref_col3 and ref_col3 in df.columns:
                bank_kw = ["loan", "mortgage", "credit", "finance", "lend", "repayment"]
                s = df[ref_col3].astype(str).str.lower()
                bank_mask = s.str.contains("|".join(bank_kw), na=False)
                tmp4 = df.copy()
                tmp4["_dr"] = _debit_series.values
                bank_dr = float(tmp4["_dr"][bank_mask].sum())
                total_in = out.get("total_inflows", 1) or 1
                credit_risk["debt_obligation_ratio"] = round(bank_dr / total_in * 100, 1)
            else:
                credit_risk["debt_obligation_ratio"] = 0.0

            abm3 = out.get("abm_3m", 0) or 0
            abm12 = out.get("abm_12m", 0) or 0
            credit_risk["abm_trend"] = round(abm3 - abm12, 2)

            stab = out.get("income_stability_score", 50) or 50
            credit_risk["income_regularity"] = "Regular" if stab >= 70 else ("Moderate" if stab >= 40 else "Irregular")

            # Risk factors
            factors = 0
            if out.get("overdraft_months", 0) > 1: factors += 1
            if out.get("fraud_risk_score", 0) > 20: factors += 1
            if stab < 40: factors += 1
            if credit_risk["debt_obligation_ratio"] > 40: factors += 1
            if out.get("net_position", 0) < 0: factors += 1
            if credit_risk["abm_trend"] < 0: factors += 1
            credit_risk["risk_factors_count"] = factors
            credit_risk["risk_tier"] = (
                "Very High" if factors >= 5 else
                "High" if factors >= 3 else
                "Moderate" if factors >= 2 else "Low"
            )
            out["credit_risk"] = credit_risk
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — SALES
# ---------------------------------------------------------------------------


def _analyze_sales(df: pd.DataFrame, detected: dict) -> dict:
    """Compute sales and CRM KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        profit_col = detected.get("profit")
        category_col = detected.get("category")
        customer_col = detected.get("customer")
        date_col = detected.get("date")
        payment_col = detected.get("payment")

        if amount_col and amount_col in df.columns:
            try:
                nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                out["total_sales_value"] = round(float(nums.sum()), 2)
                out["avg_deal_value"] = round(float(nums.mean()), 2)
                out["median_deal_value"] = round(float(nums.median()), 2)
                out["largest_deal"] = round(float(nums.max()), 2)
            except Exception:
                pass

        try:
            rep_kw = ["rep", "salesperson", "agent", "owner", "account_manager"]
            rep_col = next((c for c in df.columns if any(k in c.lower() for k in rep_kw)), None)
            if rep_col and amount_col and amount_col in df.columns:
                grp = df.groupby(rep_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False).head(10)
                out["rep_performance"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
        except Exception:
            pass

        if customer_col and customer_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(customer_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False).head(5)
                out["top_customers_sales"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
                total = out.get("total_sales_value", 0)
                if total and len(grp) > 0:
                    out["customer_concentration_pct"] = round(float(grp.iloc[0]) / total * 100, 1)
            except Exception:
                pass

        try:
            disc_col = next((c for c in df.columns if "discount" in c.lower()), None)
            if disc_col:
                disc = pd.to_numeric(df[disc_col], errors="coerce").dropna()
                mean_disc = float(disc.mean())
                out["avg_discount_rate"] = round(mean_disc * 100 if mean_disc <= 1 else mean_disc, 1)
        except Exception:
            pass

        if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(category_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False)
                out["sales_by_category"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
            except Exception:
                pass

        try:
            stage_col = next((c for c in df.columns if "stage" in c.lower()), None) or payment_col
            if stage_col and stage_col in df.columns and amount_col and amount_col in df.columns:
                grp = df.groupby(stage_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
                cnt = df.groupby(stage_col).size()
                out["pipeline_by_stage"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [round(float(v), 2) for v in grp.values],
                    "counts": [int(cnt.get(k, 0)) for k in grp.index],
                }
        except Exception:
            pass

        try:
            outcome_col = next((c for c in df.columns if any(k in c.lower() for k in ["outcome", "result", "status", "win_loss", "stage", "deal_stage"])), None)
            if outcome_col:
                s = df[outcome_col].astype(str).str.lower()
                won = int(s.str.contains("won|win|closed_won|closed won|closed", na=False).sum())
                lost = int(s.str.contains("lost|lose|closed_lost|closed lost", na=False).sum())
                total_decided = won + lost
                if total_decided > 0:
                    out["win_rate"] = round(won / total_decided * 100, 1)
                    out["lost_rate"] = round(lost / total_decided * 100, 1)
                if amount_col and amount_col in df.columns:
                    lost_mask = s.str.contains("lost|lose|closed_lost", na=False)
                    out["lost_revenue"] = round(float(pd.to_numeric(df.loc[lost_mask, amount_col], errors="coerce").sum()), 2)
        except Exception:
            pass

        try:
            cycle_col = next((c for c in df.columns if any(k in c.lower() for k in ["days_to_close", "cycle_days", "sales_cycle"])), None)
            if cycle_col:
                out["avg_sales_cycle_days"] = round(float(pd.to_numeric(df[cycle_col], errors="coerce").dropna().mean()), 1)
        except Exception:
            pass

        try:
            quota_col = next((c for c in df.columns if "quota" in c.lower()), None)
            att_col = next((c for c in df.columns if "attainment" in c.lower()), None)
            if quota_col and amount_col and amount_col in df.columns:
                quota = pd.to_numeric(df[quota_col], errors="coerce")
                actual = pd.to_numeric(df[amount_col], errors="coerce")
                valid = quota > 0
                att = actual[valid] / quota[valid] * 100
                out["avg_quota_attainment"] = round(float(att.mean()), 1)
                out["above_quota_pct"] = round(float((att >= 100).sum() / len(att) * 100), 1)
            elif att_col:
                att = pd.to_numeric(df[att_col], errors="coerce").dropna()
                out["avg_quota_attainment"] = round(float(att.mean()), 1)
        except Exception:
            pass

        if date_col and date_col in df.columns and amount_col and amount_col in df.columns:
            try:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col])
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                monthly = tmp.groupby("_m")[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_index()
                out["monthly_trend"] = {"labels": [str(p) for p in monthly.index], "values": [round(float(v), 2) for v in monthly.values]}
            except Exception:
                pass

        try:
            pipe_col = next((c for c in df.columns if "pipeline_value" in c.lower()), None)
            q_col = next((c for c in df.columns if "quota" in c.lower()), None)
            if pipe_col and q_col:
                pipe = pd.to_numeric(df[pipe_col], errors="coerce").sum()
                quota = pd.to_numeric(df[q_col], errors="coerce").sum()
                if quota > 0:
                    ratio = round(float(pipe / quota), 2)
                    out["pipeline_coverage_ratio"] = ratio
                    out["pipeline_status"] = "Strong" if ratio >= 3 else ("Adequate" if ratio >= 1.5 else "Weak")
        except Exception:
            pass

        try:
            if date_col and date_col in df.columns and customer_col and customer_col in df.columns:
                tmp2 = df.copy()
                tmp2[date_col] = pd.to_datetime(tmp2[date_col], errors="coerce")
                tmp2 = tmp2.dropna(subset=[date_col])
                cutoff = tmp2[date_col].max() - pd.Timedelta(days=90)
                recent = tmp2[tmp2[date_col] >= cutoff][customer_col].unique()
                all_customers = tmp2[customer_col].unique()
                at_risk = [c for c in all_customers if c not in recent]
                out["churn_risk_count"] = len(at_risk)
                total_c = len(all_customers)
                out["churn_risk_pct"] = round(len(at_risk) / total_c * 100, 1) if total_c > 0 else 0.0
                if amount_col and amount_col in df.columns:
                    risk_rev = float(tmp2[tmp2[customer_col].isin(at_risk)][amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce")).sum())
                    out["churn_risk_revenue"] = round(risk_rev, 2)
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — INVENTORY
# ---------------------------------------------------------------------------


def _analyze_inventory(df: pd.DataFrame, detected: dict) -> dict:
    """Compute inventory management KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        qty_col = detected.get("qty")
        category_col = detected.get("category")
        customer_col = detected.get("customer")

        try:
            sku_col = next((c for c in df.columns if "sku" in c.lower()), None)
            out["total_skus"] = int(df[sku_col].nunique()) if sku_col else int(len(df))
        except Exception:
            pass

        if amount_col and amount_col in df.columns:
            try:
                prices = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
                if qty_col and qty_col in df.columns:
                    qtys = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
                    out["total_stock_value"] = round(float((prices * qtys).sum()), 2)
                else:
                    out["total_stock_value"] = round(float(prices.sum()), 2)
                out["avg_unit_cost"] = round(float(prices[prices > 0].mean()), 2)
            except Exception:
                pass

        try:
            cogs_col = next((c for c in df.columns if any(k in c.lower() for k in ["cogs", "cost_of_goods", "cost_of_sales"])), None)
            stock_val = out.get("total_stock_value", 0)
            if cogs_col and stock_val and stock_val > 0:
                cogs = float(pd.to_numeric(df[cogs_col], errors="coerce").dropna().sum())
                out["inventory_turnover"] = round(cogs / stock_val, 2)
                out["days_inventory_outstanding"] = round(365 / max(out["inventory_turnover"], 0.01), 1)
            else:
                out["inventory_turnover"] = 4.0
                out["days_inventory_outstanding"] = round(365 / 4.0, 1)
        except Exception:
            pass

        try:
            reorder_col = next((c for c in df.columns if "reorder" in c.lower() or "reorder_point" in c.lower()), None)
            if reorder_col and qty_col and qty_col in df.columns:
                reorder = pd.to_numeric(df[reorder_col], errors="coerce").fillna(0)
                qty = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
                stockout_mask = qty <= reorder
                out["stockout_risk_count"] = int(stockout_mask.sum())
                sku_col2 = next((c for c in df.columns if "sku" in c.lower() or "product" in c.lower()), category_col)
                if sku_col2 and sku_col2 in df.columns:
                    out["reorder_alerts"] = list(df.loc[stockout_mask, sku_col2].astype(str).head(20))
        except Exception:
            pass

        try:
            last_sold_col = next((c for c in df.columns if any(k in c.lower() for k in ["last_sold", "last_sale", "days_since"])), None)
            if last_sold_col:
                days = pd.to_numeric(df[last_sold_col], errors="coerce").dropna()
                out["dead_stock_count"] = int((days > 180).sum())
            elif qty_col and qty_col in df.columns:
                qty = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
                out["dead_stock_count"] = int((qty > 0).sum())
        except Exception:
            pass

        try:
            if amount_col and amount_col in df.columns:
                prices = pd.to_numeric(df[amount_col], errors="coerce").fillna(0)
                if qty_col and qty_col in df.columns:
                    qtys = pd.to_numeric(df[qty_col], errors="coerce").fillna(0)
                    stock_values = prices * qtys
                else:
                    stock_values = prices
                total_val = stock_values.sum()
                if total_val > 0:
                    sorted_vals = stock_values.sort_values(ascending=False)
                    cumsum = sorted_vals.cumsum()
                    a_mask = cumsum <= total_val * 0.80
                    b_mask = (cumsum > total_val * 0.80) & (cumsum <= total_val * 0.95)
                    c_mask = cumsum > total_val * 0.95
                    out["abc_classification"] = {
                        "A_count": int(a_mask.sum()),
                        "B_count": int(b_mask.sum()),
                        "C_count": int(c_mask.sum()),
                        "A_value": round(float(sorted_vals[a_mask].sum()), 2),
                        "B_value": round(float(sorted_vals[b_mask].sum()), 2),
                        "C_value": round(float(sorted_vals[c_mask].sum()), 2),
                    }
        except Exception:
            pass

        try:
            sup_col = customer_col or next((c for c in df.columns if "supplier" in c.lower()), None)
            if sup_col and sup_col in df.columns and amount_col and amount_col in df.columns:
                grp = df.groupby(sup_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False).head(10)
                out["supplier_breakdown"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
        except Exception:
            pass

        try:
            fill_col = next((c for c in df.columns if "fill_rate" in c.lower()), None)
            ord_col = next((c for c in df.columns if "qty_ordered" in c.lower() or "ordered" in c.lower()), None)
            ful_col = next((c for c in df.columns if "qty_fulfilled" in c.lower() or "fulfilled" in c.lower()), None)
            if fill_col:
                fill = pd.to_numeric(df[fill_col], errors="coerce").dropna()
                mean_fill = float(fill.mean())
                out["avg_fill_rate"] = round(mean_fill * 100 if mean_fill <= 1 else mean_fill, 1)
            elif ord_col and ful_col:
                ordered = pd.to_numeric(df[ord_col], errors="coerce").fillna(0)
                fulfilled = pd.to_numeric(df[ful_col], errors="coerce").fillna(0)
                valid = ordered > 0
                out["avg_fill_rate"] = round(float((fulfilled[valid] / ordered[valid]).mean() * 100), 1)
        except Exception:
            pass

        try:
            lt_col = next((c for c in df.columns if "lead_time" in c.lower()), None)
            if lt_col:
                lt = pd.to_numeric(df[lt_col], errors="coerce").dropna()
                out["avg_lead_time_days"] = round(float(lt.mean()), 1)
                out["lead_time_std_days"] = round(float(lt.std()), 1)
                out["lead_time_variance_score"] = round(float(lt.std() / lt.mean() * 100) if lt.mean() > 0 else 0, 1)
        except Exception:
            pass

        try:
            gm_col = next((c for c in df.columns if "gross_margin" in c.lower() or "gm" == c.lower()), None)
            stock_val = out.get("total_stock_value", 0)
            if gm_col and stock_val and stock_val > 0:
                gm = float(pd.to_numeric(df[gm_col], errors="coerce").dropna().sum())
                gmroi = round(gm / stock_val, 2)
                out["gmroi"] = gmroi
                out["gmroi_status"] = "Excellent" if gmroi >= 3 else ("Good" if gmroi >= 2 else ("Fair" if gmroi >= 1 else "Poor"))
        except Exception:
            pass

        try:
            shrink_col = next((c for c in df.columns if any(k in c.lower() for k in ["shrinkage", "shrink", "loss", "lost"])), None)
            if shrink_col and amount_col and amount_col in df.columns:
                shrink = pd.to_numeric(df[shrink_col], errors="coerce").dropna()
                shrink_val = float(shrink.sum())
                stock_val = out.get("total_stock_value", 0)
                out["shrinkage_value"] = round(shrink_val, 2)
                if stock_val and stock_val > 0:
                    out["shrinkage_rate"] = round(shrink_val / stock_val * 100, 1)
        except Exception:
            pass

        try:
            reorder_col2 = next((c for c in df.columns if "reorder" in c.lower()), None)
            total_skus = out.get("total_skus", len(df))
            if reorder_col2 and total_skus > 0:
                has_reorder = pd.to_numeric(df[reorder_col2], errors="coerce").notna().sum()
                out["reorder_optimisation_score"] = round(float(has_reorder / total_skus * 100), 1)
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — RESTAURANT
# ---------------------------------------------------------------------------


def _analyze_restaurant(df: pd.DataFrame, detected: dict) -> dict:
    """Compute restaurant and F&B KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        category_col = detected.get("category")
        qty_col = detected.get("qty")
        profit_col = detected.get("profit")
        date_col = detected.get("date")
        customer_col = detected.get("customer")

        if amount_col and amount_col in df.columns:
            try:
                nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                out["total_revenue"] = round(float(nums.sum()), 2)
            except Exception:
                pass

        try:
            if qty_col and qty_col in df.columns:
                qty = pd.to_numeric(df[qty_col], errors="coerce").dropna()
                out["total_covers"] = int(qty.sum())
            else:
                out["total_covers"] = int(len(df))
            total_covers = out["total_covers"]
            total_rev = out.get("total_revenue", 0)
            if total_covers and total_covers > 0 and total_rev:
                out["revenue_per_cover"] = round(total_rev / total_covers, 2)
        except Exception:
            pass

        if profit_col and profit_col in df.columns:
            try:
                food_cost = pd.to_numeric(df[profit_col], errors="coerce").dropna()
                out["total_food_cost"] = round(float(food_cost.sum()), 2)
                total_rev = out.get("total_revenue", 0)
                if total_rev and total_rev > 0:
                    out["food_cost_pct"] = round(float(food_cost.sum()) / total_rev * 100, 1)
            except Exception:
                pass

        try:
            period_col = next((c for c in df.columns if "meal_period" in c.lower() or "period" in c.lower()), None)
            use_col = period_col or category_col
            if use_col and use_col in df.columns and amount_col and amount_col in df.columns:
                grp = df.groupby(use_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False)
                cnt = df.groupby(use_col).size()
                out["meal_period_breakdown"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [round(float(v), 2) for v in grp.values],
                    "counts": [int(cnt.get(k, 0)) for k in grp.index],
                }
        except Exception:
            pass

        try:
            table_col = next((c for c in df.columns if "table" in c.lower()), None) or customer_col
            if table_col and table_col in df.columns:
                num_tables = df[table_col].nunique()
                if num_tables > 0:
                    out["table_turnover_rate"] = round(len(df) / num_tables, 2)
        except Exception:
            pass

        # Menu engineering (Star/Plow Horse/Puzzle/Dog)
        try:
            if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
                item_rev = df.groupby(category_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum())
                item_cnt = df.groupby(category_col).size()
                median_rev = item_rev.median()
                median_cnt = item_cnt.median()
                stars, plow_horses, puzzles, dogs = [], [], [], []
                for item in item_rev.index:
                    rev = item_rev[item]
                    cnt = item_cnt[item]
                    if rev >= median_rev and cnt >= median_cnt:
                        stars.append(str(item))
                    elif rev >= median_rev and cnt < median_cnt:
                        plow_horses.append(str(item))
                    elif rev < median_rev and cnt >= median_cnt:
                        puzzles.append(str(item))
                    else:
                        dogs.append(str(item))
                out["menu_engineering"] = {"stars": stars, "plow_horses": plow_horses, "puzzles": puzzles, "dogs": dogs}
                grp_top = item_rev.sort_values(ascending=False).head(10)
                out["top_menu_items"] = {"labels": list(grp_top.index.astype(str)), "values": [round(float(v), 2) for v in grp_top.values]}
        except Exception:
            pass

        if date_col and date_col in df.columns and amount_col and amount_col in df.columns:
            try:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col])
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                monthly = tmp.groupby("_m")[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_index()
                out["monthly_trend"] = {"labels": [str(p) for p in monthly.index], "values": [round(float(v), 2) for v in monthly.values]}
            except Exception:
                pass

        try:
            labour_col = next((c for c in df.columns if any(k in c.lower() for k in ["labour_cost", "labor_cost", "staff_cost", "wages"])), None)
            if labour_col:
                lc = pd.to_numeric(df[labour_col], errors="coerce").dropna()
                out["total_labour_cost"] = round(float(lc.sum()), 2)
                total_rev = out.get("total_revenue", 0)
                if total_rev and total_rev > 0:
                    out["labour_cost_pct"] = round(float(lc.sum()) / total_rev * 100, 1)
        except Exception:
            pass

        try:
            fc = out.get("total_food_cost", 0) or 0
            lc = out.get("total_labour_cost", 0) or 0
            pc = fc + lc
            out["prime_cost"] = round(pc, 2)
            total_rev = out.get("total_revenue", 0)
            if total_rev and total_rev > 0:
                pct = pc / total_rev * 100
                out["prime_cost_pct"] = round(pct, 1)
                out["prime_cost_status"] = (
                    "Excellent" if pct < 55 else
                    "Good" if pct < 65 else
                    "Fair" if pct < 75 else "Poor"
                )
        except Exception:
            pass

        try:
            if date_col and date_col in df.columns and amount_col and amount_col in df.columns:
                tmp2 = df.copy()
                tmp2[date_col] = pd.to_datetime(tmp2[date_col], errors="coerce")
                tmp2 = tmp2.dropna(subset=[date_col])
                tmp2["_m"] = tmp2[date_col].dt.to_period("M")
                avg_check = tmp2.groupby("_m")[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").mean()).sort_index()
                out["avg_check_trend"] = {"labels": [str(p) for p in avg_check.index], "values": [round(float(v), 2) for v in avg_check.values]}
        except Exception:
            pass

        try:
            waste_col = next((c for c in df.columns if any(k in c.lower() for k in ["waste", "waste_cost"])), None)
            if waste_col:
                waste = pd.to_numeric(df[waste_col], errors="coerce").dropna()
                out["total_waste"] = round(float(waste.sum()), 2)
                total_rev = out.get("total_revenue", 0)
                if total_rev and total_rev > 0:
                    out["waste_pct"] = round(float(waste.sum()) / total_rev * 100, 1)
        except Exception:
            pass

        try:
            if profit_col and profit_col in df.columns and category_col and category_col in df.columns:
                grp_gp = df.groupby(category_col)[profit_col].apply(lambda x: pd.to_numeric(x, errors="coerce").mean()).sort_values(ascending=False).head(10)
                out["top_gp_dishes"] = {"labels": list(grp_gp.index.astype(str)), "values": [round(float(v), 2) for v in grp_gp.values]}
        except Exception:
            pass

        try:
            me = out.get("menu_engineering", {})
            stars = len(me.get("stars", []))
            plow = len(me.get("plow_horses", []))
            total_items = sum(len(v) for v in me.values()) if me else 1
            if total_items > 0:
                out["menu_profitability_score"] = round((stars + plow) / total_items * 100, 1)
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZER — ECOMMERCE
# ---------------------------------------------------------------------------


def _analyze_ecommerce(df: pd.DataFrame, detected: dict) -> dict:
    """Compute e-commerce KPIs."""
    try:
        out: dict = {}
        amount_col = detected.get("amount")
        category_col = detected.get("category")
        customer_col = detected.get("customer")
        state_col = detected.get("state")
        date_col = detected.get("date")
        qty_col = detected.get("qty")
        profit_col = detected.get("profit")

        out["total_orders"] = int(len(df))

        if amount_col and amount_col in df.columns:
            try:
                nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
                out["total_revenue"] = round(float(nums.sum()), 2)
                out["avg_order_value"] = round(float(nums.mean()), 2)
            except Exception:
                pass

        try:
            if customer_col and customer_col in df.columns:
                total_cust = int(df[customer_col].nunique())
                out["total_customers"] = total_cust
                repeat_mask = df.groupby(customer_col)[customer_col].transform("count") > 1
                repeat_count = int(df[customer_col][repeat_mask].nunique())
                out["repeat_customers"] = repeat_count
                out["repeat_purchase_rate"] = round(repeat_count / total_cust * 100, 1) if total_cust > 0 else 0.0
                total_rev = out.get("total_revenue", 0)
                if total_rev and total_cust > 0:
                    out["avg_customer_ltv"] = round(total_rev / total_cust, 2)
            else:
                out["total_customers"] = int(len(df))
        except Exception:
            pass

        try:
            ret_col = next((c for c in df.columns if any(k in c.lower() for k in ["returned", "return_status", "refund", "return"])), None)
            if ret_col:
                ret_count = int(df[ret_col].astype(str).str.lower().str.contains("return|refund|yes|true|1", na=False).sum())
                out["return_count"] = ret_count
                out["return_rate"] = round(ret_count / len(df) * 100, 1)
        except Exception:
            pass

        if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(category_col).agg(
                    revenue=(amount_col, lambda x: pd.to_numeric(x, errors="coerce").sum()),
                    orders=(amount_col, "count"),
                ).sort_values("revenue", ascending=False).head(10)
                out["top_skus"] = {
                    "labels": list(grp.index.astype(str)),
                    "values": [round(float(v), 2) for v in grp["revenue"].values],
                    "counts": [int(v) for v in grp["orders"].values],
                }
            except Exception:
                pass

        if state_col and state_col in df.columns and amount_col and amount_col in df.columns:
            try:
                grp = df.groupby(state_col)[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_values(ascending=False)
                out["revenue_by_region"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
            except Exception:
                pass

        try:
            ful_col = next((c for c in df.columns if any(k in c.lower() for k in ["fulfillment_days", "days_to_ship", "shipping_days"])), None)
            if ful_col:
                out["avg_fulfillment_days"] = round(float(pd.to_numeric(df[ful_col], errors="coerce").dropna().mean()), 1)
        except Exception:
            pass

        try:
            late_col = next((c for c in df.columns if any(k in c.lower() for k in ["late", "delayed"])), None)
            ot_col = next((c for c in df.columns if "on_time" in c.lower()), None)
            if late_col:
                late = int(df[late_col].astype(str).str.lower().isin(["true", "1", "yes", "late"]).sum())
                out["late_shipment_rate"] = round(late / len(df) * 100, 1)
            elif ot_col:
                not_ot = int(~df[ot_col].astype(str).str.lower().isin(["true", "1", "yes", "on_time"]).sum())
                out["late_shipment_rate"] = round(not_ot / len(df) * 100, 1)
        except Exception:
            pass

        if date_col and date_col in df.columns and amount_col and amount_col in df.columns:
            try:
                tmp = df.copy()
                tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
                tmp = tmp.dropna(subset=[date_col])
                tmp["_m"] = tmp[date_col].dt.to_period("M")
                monthly = tmp.groupby("_m")[amount_col].apply(lambda x: pd.to_numeric(x, errors="coerce").sum()).sort_index()
                out["monthly_trend"] = {"labels": [str(p) for p in monthly.index], "values": [round(float(v), 2) for v in monthly.values]}
            except Exception:
                pass

        try:
            if profit_col and profit_col in df.columns and category_col and category_col in df.columns:
                grp = df.groupby(category_col)[profit_col].apply(lambda x: pd.to_numeric(x, errors="coerce").mean()).sort_values(ascending=False)
                out["margin_by_sku"] = {"labels": list(grp.index.astype(str)), "values": [round(float(v), 2) for v in grp.values]}
        except Exception:
            pass

        try:
            cart_col = next((c for c in df.columns if any(k in c.lower() for k in ["cart_status", "abandoned", "cart"])), None)
            if cart_col:
                abandoned = int(df[cart_col].astype(str).str.lower().str.contains("abandon|cart", na=False).sum())
                out["cart_abandonment_rate"] = round(abandoned / len(df) * 100, 1)
            else:
                out["cart_abandonment_rate"] = 65.0  # industry default
        except Exception:
            pass

        try:
            vis_col = next((c for c in df.columns if any(k in c.lower() for k in ["visitors", "sessions", "traffic"])), None)
            if vis_col:
                visitors = int(pd.to_numeric(df[vis_col], errors="coerce").dropna().sum())
                out["total_visitors"] = visitors
                total_rev = out.get("total_revenue", 0)
                if total_rev and visitors > 0:
                    out["revenue_per_visitor"] = round(total_rev / visitors, 2)
        except Exception:
            pass

        try:
            cac_col = next((c for c in df.columns if any(k in c.lower() for k in ["cac", "acquisition_cost"])), None)
            ltv_col = next((c for c in df.columns if "ltv" in c.lower() and c != cac_col), None)
            if cac_col:
                out["avg_cac"] = round(float(pd.to_numeric(df[cac_col], errors="coerce").dropna().mean()), 2)
            if ltv_col:
                out["avg_ltv"] = round(float(pd.to_numeric(df[ltv_col], errors="coerce").dropna().mean()), 2)
            if "avg_cac" in out and "avg_ltv" in out and out["avg_cac"] > 0:
                ratio = round(out["avg_ltv"] / out["avg_cac"], 2)
                out["cac_ltv_ratio"] = ratio
                out["cac_ltv_status"] = "Excellent" if ratio >= 3 else ("Good" if ratio >= 2 else ("Fair" if ratio >= 1 else "Poor"))
        except Exception:
            pass

        try:
            cohort_col = next((c for c in df.columns if any(k in c.lower() for k in ["cohort", "first_purchase", "acquisition_date"])), None)
            if cohort_col and customer_col and customer_col in df.columns and date_col and date_col in df.columns:
                tmp2 = df.copy()
                tmp2[date_col] = pd.to_datetime(tmp2[date_col], errors="coerce")
                tmp2[cohort_col] = pd.to_datetime(tmp2[cohort_col], errors="coerce")
                tmp2 = tmp2.dropna(subset=[date_col, cohort_col])
                tmp2["months_since"] = ((tmp2[date_col].dt.year - tmp2[cohort_col].dt.year) * 12 + (tmp2[date_col].dt.month - tmp2[cohort_col].dt.month))
                cohort_size = tmp2[tmp2["months_since"] == 0][customer_col].nunique()
                m1 = tmp2[tmp2["months_since"] == 1][customer_col].nunique()
                if cohort_size > 0:
                    out["cohort_m1_retention"] = round(m1 / cohort_size * 100, 1)
        except Exception:
            pass

        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# INDUSTRY ANALYZERS DISPATCH TABLE
# ---------------------------------------------------------------------------

_INDUSTRY_ANALYZERS: dict = {
    "hr": _analyze_hr,
    "real_estate": _analyze_real_estate,
    "healthcare": _analyze_healthcare,
    "logistics": _analyze_logistics,
    "hospitality": _analyze_hospitality,
    "construction": _analyze_construction,
    "marketing": _analyze_marketing,
    "bank_statement": _analyze_bank_statement,
    "sales": _analyze_sales,
    "inventory": _analyze_inventory,
    "restaurant": _analyze_restaurant,
    "ecommerce": _analyze_ecommerce,
    "general": lambda df, detected: {},
}


# ---------------------------------------------------------------------------
# DATA QUALITY ENGINE
# ---------------------------------------------------------------------------


def compute_data_quality(df: pd.DataFrame, detected: dict) -> dict:
    """Run 6 data quality checks and return a scored report."""
    checks = []
    total_pts = 0
    amount_col = detected.get("amount")
    date_col = detected.get("date")

    # Check 1 — Missing Values (20 pts)
    try:
        null_pcts = {c: round(df[c].isna().mean() * 100, 1) for c in df.columns}
        bad_cols = [(c, p) for c, p in null_pcts.items() if p > 5]
        if len(bad_cols) == 0:
            checks.append({"label": "Missing Values", "status": "pass", "message": "No significant missing values"})
            total_pts += 20
        elif len(bad_cols) <= 2:
            detail = ", ".join(f"{c} ({p}%)" for c, p in bad_cols)
            checks.append({"label": "Missing Values", "status": "warn", "message": f"Missing data in: {detail}"})
            total_pts += 10
        else:
            detail = ", ".join(f"{c} ({p}%)" for c, p in bad_cols)
            checks.append({"label": "Missing Values", "status": "fail", "message": f"High missing data in {len(bad_cols)} columns: {detail}"})
    except Exception:
        checks.append({"label": "Missing Values", "status": "warn", "message": "Could not check missing values"})
        total_pts += 10

    # Check 2 — Duplicate Rows (15 pts)
    try:
        dup_count = int(df.duplicated().sum())
        dup_pct = round(dup_count / max(len(df), 1) * 100, 1)
        if dup_count == 0:
            checks.append({"label": "Duplicate Rows", "status": "pass", "message": "No duplicate rows"})
            total_pts += 15
        elif dup_pct < 2:
            checks.append({"label": "Duplicate Rows", "status": "warn", "message": f"{dup_count} duplicate rows found ({dup_pct}%)"})
            total_pts += 8
        else:
            checks.append({"label": "Duplicate Rows", "status": "fail", "message": f"{dup_count} duplicate rows ({dup_pct}%) — recommend de-duplication"})
    except Exception:
        checks.append({"label": "Duplicate Rows", "status": "warn", "message": "Could not check duplicates"})
        total_pts += 8

    # Check 3 — Revenue Column (20 pts)
    try:
        if not amount_col or amount_col not in df.columns:
            checks.append({"label": "Revenue Column", "status": "warn", "message": "No revenue/amount column detected"})
            total_pts += 10
        else:
            col_str = df[amount_col].astype(str)
            has_currency = col_str.str.contains(r"[$£€₦]", regex=True, na=False).any()
            has_negatives = (pd.to_numeric(df[amount_col], errors="coerce") < 0).any()
            issues = []
            if has_currency:
                issues.append("currency symbols present")
            if has_negatives:
                issues.append("negative values present")
            if not issues:
                checks.append({"label": "Revenue Column", "status": "pass", "message": "Revenue column looks clean"})
                total_pts += 20
            else:
                checks.append({"label": "Revenue Column", "status": "warn", "message": f"Revenue column issues: {', '.join(issues)}"})
                total_pts += 8
    except Exception:
        checks.append({"label": "Revenue Column", "status": "warn", "message": "Could not inspect revenue column"})
        total_pts += 8

    # Check 4 — Date Parsing (15 pts)
    try:
        if not date_col or date_col not in df.columns:
            checks.append({"label": "Date Parsing", "status": "warn", "message": "No date column detected"})
            total_pts += 8
        else:
            parsed = pd.to_datetime(df[date_col], errors="coerce")
            bad_count = int(parsed.isna().sum())
            bad_pct = round(bad_count / max(len(df), 1) * 100, 1)
            if bad_count == 0:
                date_range = f"{parsed.min().date()} to {parsed.max().date()}"
                checks.append({"label": "Date Parsing", "status": "pass", "message": f"All dates valid — range: {date_range}"})
                total_pts += 15
            elif bad_pct < 5:
                checks.append({"label": "Date Parsing", "status": "warn", "message": f"{bad_count} unparseable dates ({bad_pct}%)"})
                total_pts += 8
            else:
                checks.append({"label": "Date Parsing", "status": "fail", "message": f"{bad_count} unparseable dates ({bad_pct}%) — check date format"})
    except Exception:
        checks.append({"label": "Date Parsing", "status": "warn", "message": "Could not parse date column"})
        total_pts += 8

    # Check 5 — Revenue Outliers (15 pts)
    try:
        if not amount_col or amount_col not in df.columns:
            checks.append({"label": "Revenue Outliers", "status": "pass", "message": "No amount column to check"})
            total_pts += 10
        else:
            nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
            if len(nums) < 10:
                checks.append({"label": "Revenue Outliers", "status": "pass", "message": "Too few rows to detect outliers"})
                total_pts += 10
            else:
                threshold = nums.mean() + 3 * nums.std()
                outliers = int((nums > threshold).sum())
                if outliers == 0:
                    checks.append({"label": "Revenue Outliers", "status": "pass", "message": "No statistical outliers detected"})
                    total_pts += 15
                else:
                    checks.append({"label": "Revenue Outliers", "status": "warn", "message": f"{outliers} outlier value(s) above ${threshold:,.2f} — please verify"})
                    total_pts += 8
    except Exception:
        checks.append({"label": "Revenue Outliers", "status": "warn", "message": "Could not check outliers"})
        total_pts += 8

    # Check 6 — Column Coverage (15 pts)
    try:
        detected_count = sum(1 for v in detected.values() if v is not None)
        total_roles = len(detected)
        pct = detected_count / total_roles if total_roles > 0 else 0
        if pct >= 0.80:
            checks.append({"label": "Column Coverage", "status": "pass", "message": f"{detected_count}/{total_roles} semantic roles detected"})
            total_pts += 15
        elif pct >= 0.55:
            checks.append({"label": "Column Coverage", "status": "warn", "message": f"Only {detected_count}/{total_roles} roles detected — some insights may be limited"})
            total_pts += 8
        else:
            checks.append({"label": "Column Coverage", "status": "fail", "message": f"Low coverage: {detected_count}/{total_roles} roles detected"})
    except Exception:
        checks.append({"label": "Column Coverage", "status": "warn", "message": "Could not compute column coverage"})
        total_pts += 8

    score = min(100, round(total_pts))
    grade_map = [("Excellent", 85), ("Good", 65), ("Fair", 45)]
    grade = "Poor"
    for g, threshold in grade_map:
        if score >= threshold:
            grade = g
            break

    passed = sum(1 for c in checks if c["status"] == "pass")
    warned = sum(1 for c in checks if c["status"] == "warn")
    failed = sum(1 for c in checks if c["status"] == "fail")

    return {
        "score": score,
        "grade": grade,
        "checks": checks,
        "passed": passed,
        "warned": warned,
        "failed": failed,
        "total_rows": int(len(df)),
        "total_cols": int(len(df.columns)),
        "summary": f"{passed} passed · {warned} warnings · {failed} issues",
    }


# ---------------------------------------------------------------------------
# HEALTH SCORING HELPERS
# ---------------------------------------------------------------------------


def _grade(score: int) -> str:
    """Convert numeric score to letter grade."""
    if score >= 80: return "A"
    if score >= 65: return "B"
    if score >= 50: return "C"
    if score >= 35: return "D"
    return "F"


def _trend_score(monthly_key: str, insights: dict) -> tuple:
    """Score revenue/volume trend using last 3 months of monthly data."""
    try:
        data = insights.get(monthly_key, {})
        vals = data.get("values", []) if isinstance(data, dict) else []
        if len(vals) < 3:
            return (10, 25, "N/A", "Insufficient data")
        v = [float(x) for x in vals[-3:]]
        if v[0] == 0:
            return (10, 25, "N/A", "Insufficient base")
        change = (v[2] - v[0]) / abs(v[0]) * 100
        if change >= 15: return (25, 25, f"+{change:.1f}%", "Strong growth")
        if change >= 5:  return (18, 25, f"+{change:.1f}%", "Growing trend")
        if change >= -5: return (12, 25, f"{change:.1f}%", "Flat trend")
        if change >= -15: return (6, 25, f"{change:.1f}%", "Declining")
        return (0, 25, f"{change:.1f}%", "Steep decline")
    except Exception:
        return (10, 25, "N/A", "Insufficient data")


# ---------------------------------------------------------------------------
# HEALTH SCORERS — ONE PER INDUSTRY
# ---------------------------------------------------------------------------


def _health_hr(insights: dict) -> dict:
    """Compute HR health score."""
    components = []
    score = 0
    try:
        s, m, v, msg = _trend_score("headcount_trend", insights)
        score += s; components.append({"name": "Headcount Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Headcount Trend", "score": 0, "max": 25, "value": "N/A", "message": "No data"})
    try:
        med = insights.get("median_salary", 0) or 0
        avg = insights.get("avg_salary", 1) or 1
        ratio = med / avg if avg else 0
        if ratio >= 0.9: s, msg = 20, "Excellent equity"
        elif ratio >= 0.75: s, msg = 14, "Good equity"
        elif ratio >= 0.6: s, msg = 8, "Moderate inequality"
        else: s, msg = 3, "High inequality"
        score += s; components.append({"name": "Salary Equity", "score": s, "max": 20, "value": f"{ratio:.2f}", "message": msg})
    except Exception:
        components.append({"name": "Salary Equity", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        tr = insights.get("turnover_rate")
        if tr is None: raise ValueError
        if tr <= 10: s, msg = 20, "Excellent retention"
        elif tr <= 20: s, msg = 14, "Good retention"
        elif tr <= 30: s, msg = 8, "High turnover"
        else: s, msg = 2, "Critical turnover"
        score += s; components.append({"name": "Staff Retention", "score": s, "max": 20, "value": f"{tr:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Staff Retention", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        db = insights.get("dept_breakdown", {})
        vals = db.get("values", []) if isinstance(db, dict) else []
        total = sum(vals)
        top_pct = (max(vals) / total * 100) if total > 0 and vals else 50
        if top_pct <= 35: s, msg = 20, "Well balanced"
        elif top_pct <= 55: s, msg = 14, "Fairly balanced"
        elif top_pct <= 70: s, msg = 8, "Some concentration"
        else: s, msg = 3, "High concentration"
        score += s; components.append({"name": "Dept Balance", "score": s, "max": 20, "value": f"{top_pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Dept Balance", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        gap = insights.get("gender_pay_gap_pct")
        if gap is None: raise ValueError
        if gap <= 5: s, msg = 10, "Excellent pay equity"
        elif gap <= 10: s, msg = 7, "Good pay equity"
        elif gap <= 20: s, msg = 4, "Notable gap"
        else: s, msg = 1, "Significant gap"
        score += s; components.append({"name": "Pay Equity", "score": s, "max": 10, "value": f"{gap:.1f}%", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Pay Equity", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_real_estate(insights: dict) -> dict:
    """Compute real estate health score."""
    components = []
    score = 0
    try:
        yld = insights.get("yield_pct", 0) or 0
        if yld >= 8: s, msg = 25, "Excellent yield"
        elif yld >= 6: s, msg = 18, "Good yield"
        elif yld >= 4: s, msg = 11, "Moderate yield"
        elif yld >= 2: s, msg = 5, "Low yield"
        else: s, msg = 1, "Very low yield"
        score += s; components.append({"name": "Gross Yield", "score": s, "max": 25, "value": f"{yld:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Gross Yield", "score": 5, "max": 25, "value": "N/A", "message": "No data"})
    try:
        vac = insights.get("vacancy_rate")
        if vac is None: raise ValueError
        if vac <= 5: s, msg = 25, "Very low vacancy"
        elif vac <= 10: s, msg = 18, "Low vacancy"
        elif vac <= 20: s, msg = 10, "Moderate vacancy"
        else: s, msg = 3, "High vacancy"
        score += s; components.append({"name": "Vacancy Rate", "score": s, "max": 25, "value": f"{vac:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Vacancy Rate", "score": 12, "max": 25, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Value Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Value Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        pb = insights.get("property_type_breakdown", {})
        vals = pb.get("values", []) if isinstance(pb, dict) else []
        total = sum(vals)
        top_pct = (max(vals) / total * 100) if total > 0 and vals else 50
        if top_pct <= 40: s, msg = 15, "Well diversified"
        elif top_pct <= 60: s, msg = 10, "Moderate diversity"
        elif top_pct <= 80: s, msg = 6, "Low diversity"
        else: s, msg = 2, "Concentrated"
        score += s; components.append({"name": "Portfolio Diversity", "score": s, "max": 15, "value": f"{top_pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Portfolio Diversity", "score": 6, "max": 15, "value": "N/A", "message": "No data"})
    try:
        ltv = insights.get("avg_ltv_ratio")
        if ltv is None: raise ValueError
        if ltv <= 60: s, msg = 10, "Conservative LTV"
        elif ltv <= 75: s, msg = 7, "Moderate LTV"
        elif ltv <= 85: s, msg = 4, "High LTV"
        else: s, msg = 1, "Very high LTV"
        score += s; components.append({"name": "LTV Ratio", "score": s, "max": 10, "value": f"{ltv:.1f}%", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "LTV Ratio", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_healthcare(insights: dict) -> dict:
    """Compute healthcare health score."""
    components = []
    score = 0
    try:
        s, m, v, msg = _trend_score("patient_volume_trend", insights)
        score += s; components.append({"name": "Patient Volume Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Patient Volume Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        rpp = insights.get("revenue_per_patient", 0) or 0
        if rpp >= 600: s, msg = 20, "High revenue per patient"
        elif rpp >= 400: s, msg = 14, "Good revenue per patient"
        elif rpp >= 200: s, msg = 8, "Moderate"
        elif rpp > 0: s, msg = 4, "Low revenue per patient"
        else: s, msg = 8, "No data"
        score += s; components.append({"name": "Revenue per Patient", "score": s, "max": 20, "value": f"${rpp:,.0f}", "message": msg})
    except Exception:
        components.append({"name": "Revenue per Patient", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        occ = insights.get("bed_occupancy_rate")
        if occ is None: raise ValueError
        if 75 <= occ <= 85: s, msg = 20, "Optimal occupancy"
        elif occ <= 90: s, msg = 14, "Good occupancy"
        elif occ < 75: s, msg = 10, "Under-utilised"
        else: s, msg = 5, "Over capacity"
        score += s; components.append({"name": "Bed Occupancy", "score": s, "max": 20, "value": f"{occ:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Bed Occupancy", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        alos = insights.get("alos_days")
        if alos is None: raise ValueError
        if alos <= 4: s, msg = 20, "Short stay — efficient"
        elif alos <= 7: s, msg = 14, "Moderate stay"
        elif alos <= 10: s, msg = 8, "Long stay"
        else: s, msg = 3, "Very long stay"
        score += s; components.append({"name": "Avg Length of Stay", "score": s, "max": 20, "value": f"{alos:.1f} days", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Avg Length of Stay", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        rr = insights.get("readmission_rate")
        if rr is None: raise ValueError
        if rr <= 5: s, msg = 10, "Excellent"
        elif rr <= 10: s, msg = 7, "Good"
        elif rr <= 15: s, msg = 4, "Needs improvement"
        else: s, msg = 1, "High readmission"
        score += s; components.append({"name": "Readmission Rate", "score": s, "max": 10, "value": f"{rr:.1f}%", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Readmission Rate", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_logistics(insights: dict) -> dict:
    """Compute logistics health score."""
    components = []
    score = 0
    try:
        otr = insights.get("on_time_rate", 0) or 0
        if otr >= 95: s, msg = 25, "Excellent on-time rate"
        elif otr >= 90: s, msg = 18, "Good on-time rate"
        elif otr >= 80: s, msg = 10, "Moderate — needs improvement"
        elif otr >= 70: s, msg = 5, "Low on-time rate"
        else: s, msg = 1, "Critical — high delays"
        score += s; components.append({"name": "On-Time Rate", "score": s, "max": 25, "value": f"{otr:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "On-Time Rate", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        fadr = insights.get("fadr")
        if fadr is None: raise ValueError
        if fadr >= 90: s, msg = 20, "Excellent first-attempt rate"
        elif fadr >= 80: s, msg = 14, "Good"
        elif fadr >= 70: s, msg = 8, "Needs improvement"
        else: s, msg = 3, "High re-delivery cost"
        score += s; components.append({"name": "First Attempt Rate", "score": s, "max": 20, "value": f"{fadr:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "First Attempt Rate", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        rdr = insights.get("return_damage_rate", 0) or 0
        if rdr <= 2: s, msg = 20, "Very low returns"
        elif rdr <= 5: s, msg = 14, "Low returns"
        elif rdr <= 10: s, msg = 8, "Moderate returns"
        else: s, msg = 2, "High return/damage rate"
        score += s; components.append({"name": "Return/Damage Rate", "score": s, "max": 20, "value": f"{rdr:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Return/Damage Rate", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        s, m, v, msg = _trend_score("delivery_volume_trend", insights)
        score += s; components.append({"name": "Volume Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Volume Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        por = insights.get("perfect_order_rate")
        if por is None: raise ValueError
        if por >= 95: s, msg = 10, "Excellent"
        elif por >= 85: s, msg = 7, "Good"
        elif por >= 75: s, msg = 4, "Moderate"
        else: s, msg = 1, "Low perfect order rate"
        score += s; components.append({"name": "Perfect Order Rate", "score": s, "max": 10, "value": f"{por:.1f}%", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Perfect Order Rate", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_hospitality(insights: dict) -> dict:
    """Compute hospitality health score."""
    components = []
    score = 0
    try:
        occ = insights.get("occupancy_rate", 0) or 0
        if occ >= 85: s, msg = 25, "Excellent occupancy"
        elif occ >= 70: s, msg = 18, "Good occupancy"
        elif occ >= 55: s, msg = 10, "Moderate occupancy"
        elif occ >= 40: s, msg = 5, "Low occupancy"
        else: s, msg = 1, "Very low occupancy"
        score += s; components.append({"name": "Occupancy Rate", "score": s, "max": 25, "value": f"{occ:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Occupancy Rate", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        revpar = insights.get("revpar")
        if revpar:
            s = min(20, round(revpar / 10))
            msg = f"RevPAR: ${revpar:,.2f}"
        elif insights.get("adr"):
            s, msg = 10, "Only ADR available"
        else:
            s, msg = 8, "No RevPAR data"
        score += s; components.append({"name": "RevPAR", "score": s, "max": 20, "value": f"${revpar:,.2f}" if revpar else "N/A", "message": msg})
    except Exception:
        components.append({"name": "RevPAR", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        cr = insights.get("cancellation_rate")
        if cr is None: raise ValueError
        if cr <= 10: s, msg = 20, "Low cancellation"
        elif cr <= 20: s, msg = 14, "Moderate cancellation"
        elif cr <= 30: s, msg = 8, "High cancellation"
        else: s, msg = 3, "Very high cancellation"
        score += s; components.append({"name": "Cancellation Rate", "score": s, "max": 20, "value": f"{cr:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Cancellation Rate", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Revenue Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Revenue Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        gop_pct = insights.get("gop_pct")
        if gop_pct is None: raise ValueError
        if gop_pct >= 30: s, msg = 10, "Strong GOP"
        elif gop_pct >= 20: s, msg = 7, "Good GOP"
        elif gop_pct >= 10: s, msg = 4, "Moderate GOP"
        else: s, msg = 1, "Low GOP"
        score += s; components.append({"name": "GOPPAR", "score": s, "max": 10, "value": f"{gop_pct:.1f}%", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "GOPPAR", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_construction(insights: dict) -> dict:
    """Compute construction health score."""
    components = []
    score = 0
    try:
        on_b = insights.get("on_budget_count", 0) or 0
        total = insights.get("project_count", 1) or 1
        pct = on_b / total * 100
        if pct >= 80: s, msg = 25, "Strong budget control"
        elif pct >= 65: s, msg = 18, "Good budget control"
        elif pct >= 50: s, msg = 10, "Moderate overruns"
        else: s, msg = 3, "High budget overruns"
        score += s; components.append({"name": "Budget Performance", "score": s, "max": 25, "value": f"{pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Budget Performance", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        spi = insights.get("avg_spi")
        if spi is None: raise ValueError
        if spi >= 1.0: s, msg = 20, "On schedule"
        elif spi >= 0.9: s, msg = 14, "Slightly behind"
        elif spi >= 0.75: s, msg = 8, "Behind schedule"
        else: s, msg = 2, "Critical delays"
        score += s; components.append({"name": "Schedule Performance (SPI)", "score": s, "max": 20, "value": f"{spi:.2f}", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Schedule Performance (SPI)", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        cpi = insights.get("cpi")
        if cpi is None: raise ValueError
        if cpi >= 1.0: s, msg = 20, "Under budget"
        elif cpi >= 0.9: s, msg = 14, "Slightly over"
        elif cpi >= 0.75: s, msg = 8, "Over budget"
        else: s, msg = 2, "Severely over budget"
        score += s; components.append({"name": "Cost Performance (CPI)", "score": s, "max": 20, "value": f"{cpi:.2f}", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Cost Performance (CPI)", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Pipeline Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Pipeline Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        inc = insights.get("total_incidents", 0) or 0
        if inc == 0: s, msg = 10, "No incidents recorded"
        elif inc <= 2: s, msg = 6, "Minor incidents"
        else: s, msg = 2, "Safety concerns"
        score += s; components.append({"name": "Safety Record", "score": s, "max": 10, "value": str(inc), "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Safety Record", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_marketing(insights: dict) -> dict:
    """Compute marketing health score."""
    components = []
    score = 0
    try:
        roas = insights.get("avg_roas", 0) or 0
        if roas >= 6: s, msg = 25, "Excellent ROAS"
        elif roas >= 4: s, msg = 18, "Good ROAS"
        elif roas >= 2: s, msg = 10, "Moderate ROAS"
        elif roas >= 1: s, msg = 5, "Break-even ROAS"
        else: s, msg = 0, "Losing money"
        score += s; components.append({"name": "ROAS", "score": s, "max": 25, "value": f"{roas:.2f}x", "message": msg})
    except Exception:
        components.append({"name": "ROAS", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        ctr = insights.get("avg_ctr")
        if ctr is None: raise ValueError
        if ctr >= 3: s, msg = 20, "Excellent CTR"
        elif ctr >= 2: s, msg = 14, "Good CTR"
        elif ctr >= 1: s, msg = 8, "Moderate CTR"
        else: s, msg = 3, "Low CTR"
        score += s; components.append({"name": "Click-Through Rate", "score": s, "max": 20, "value": f"{ctr:.2f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Click-Through Rate", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Spend Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Spend Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        top_ch = insights.get("top_channel_pct", 50) or 50
        if top_ch <= 40: s, msg = 15, "Well diversified"
        elif top_ch <= 60: s, msg = 10, "Moderate diversity"
        elif top_ch <= 80: s, msg = 6, "Low diversity"
        else: s, msg = 2, "Single channel risk"
        score += s; components.append({"name": "Channel Diversity", "score": s, "max": 15, "value": f"{top_ch:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Channel Diversity", "score": 6, "max": 15, "value": "N/A", "message": "No data"})
    try:
        ratio = insights.get("cac_ltv_ratio")
        if ratio is None: raise ValueError
        if ratio >= 3: s, msg = 10, "Excellent CAC:LTV"
        elif ratio >= 1: s, msg = 7, "Good CAC:LTV"
        else: s, msg = 2, "Poor CAC:LTV"
        score += s; components.append({"name": "CAC:LTV Ratio", "score": s, "max": 10, "value": f"{ratio:.2f}x", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "CAC:LTV Ratio", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_bank_statement(insights: dict) -> dict:
    """Compute bank statement health score."""
    components = []
    score = 0
    try:
        mcf = insights.get("monthly_cashflow", {})
        net_vals = mcf.get("net", []) if isinstance(mcf, dict) else []
        if len(net_vals) >= 3:
            v = [float(x) for x in net_vals]
            mean_v = sum(v) / len(v)
            if mean_v != 0:
                slope_pct = (v[-1] - v[0]) / abs(mean_v) * 100
                if slope_pct >= 10: s, msg = 20, "Strong positive cashflow trend"
                elif slope_pct >= 2: s, msg = 15, "Growing cashflow"
                elif slope_pct >= -2: s, msg = 10, "Stable cashflow"
                elif slope_pct >= -10: s, msg = 5, "Declining cashflow"
                else: s, msg = 0, "Negative cashflow trend"
            else:
                s, msg = 10, "Flat cashflow"
        else:
            s, msg = 10, "Insufficient data"
        score += s; components.append({"name": "Cash Flow Trend", "score": s, "max": 20, "value": "See chart", "message": msg})
    except Exception:
        components.append({"name": "Cash Flow Trend", "score": 10, "max": 20, "value": "N/A", "message": "No data"})
    try:
        inflows = insights.get("total_inflows", 0) or 0
        net = insights.get("net_position", 0) or 0
        if inflows > 0:
            savings_rate = net / inflows * 100
            if savings_rate >= 30: s, msg = 20, "Excellent savings rate"
            elif savings_rate >= 15: s, msg = 15, "Good savings"
            elif savings_rate >= 5: s, msg = 10, "Moderate savings"
            elif savings_rate >= 0: s, msg = 4, "Breaking even"
            else: s, msg = 0, "Spending more than earning"
        else:
            s, msg = 5, "No inflow data"
            savings_rate = 0
        score += s; components.append({"name": "Net Position", "score": s, "max": 20, "value": f"{savings_rate:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Net Position", "score": 5, "max": 20, "value": "N/A", "message": "No data"})
    try:
        buf = insights.get("cash_buffer_months")
        if buf is not None:
            if buf >= 6: s, msg = 20, "Strong liquidity buffer"
            elif buf >= 3: s, msg = 15, "Good buffer"
            elif buf >= 1: s, msg = 8, "Thin buffer"
            elif buf >= 0: s, msg = 3, "Very thin buffer"
            else: s, msg = 0, "No buffer"
            score += s; components.append({"name": "Liquidity Buffer", "score": s, "max": 20, "value": f"{buf:.1f} months", "message": msg})
        else:
            od = insights.get("overdraft_months", 0) or 0
            if od == 0: s, msg = 15, "No overdraft months"
            elif od <= 1: s, msg = 8, "Occasional overdraft"
            else: s, msg = 3, "Frequent overdraft"
            score += s; components.append({"name": "Liquidity Buffer", "score": s, "max": 20, "value": f"{od} overdraft months", "message": msg})
    except Exception:
        components.append({"name": "Liquidity Buffer", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        stab = insights.get("income_stability_score")
        if stab is None: raise ValueError
        if stab >= 75: s, msg = 20, "Very stable income"
        elif stab >= 55: s, msg = 15, "Stable income"
        elif stab >= 35: s, msg = 8, "Moderate stability"
        else: s, msg = 3, "Volatile income"
        score += s; components.append({"name": "Income Stability", "score": s, "max": 20, "value": f"{stab:.1f}", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Income Stability", "score": 8, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        top_pct = insights.get("top_payee_pct", 0) or 0
        if top_pct <= 15: s, msg = 10, "Diversified expenses"
        elif top_pct <= 30: s, msg = 7, "Moderate concentration"
        elif top_pct <= 50: s, msg = 4, "High concentration"
        else: s, msg = 1, "Very concentrated expenses"
        score += s; components.append({"name": "Expense Concentration", "score": s, "max": 10, "value": f"{top_pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Expense Concentration", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    try:
        frs = insights.get("fraud_risk_score", 0) or 0
        if frs == 0: s, msg = 10, "No fraud signals"
        elif frs <= 20: s, msg = 7, "Low fraud risk"
        elif frs <= 40: s, msg = 4, "Moderate fraud risk"
        else: s, msg = 1, "High fraud risk"
        score += s; components.append({"name": "Fraud Risk", "score": s, "max": 10, "value": str(frs), "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Fraud Risk", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_sales(insights: dict) -> dict:
    """Compute sales health score."""
    components = []
    score = 0
    try:
        pm = insights.get("profit_margin", 0) or 0
        if pm >= 25: s, msg = 20, "Excellent margin"
        elif pm >= 15: s, msg = 14, "Good margin"
        elif pm >= 8: s, msg = 8, "Moderate margin"
        elif pm >= 0: s, msg = 3, "Thin margin"
        else: s, msg = 0, "Negative margin"
        score += s; components.append({"name": "Profit Margin", "score": s, "max": 20, "value": f"{pm:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Profit Margin", "score": 5, "max": 20, "value": "N/A", "message": "No data"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Revenue Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Revenue Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        wr = insights.get("win_rate")
        if wr is None: raise ValueError
        if wr >= 40: s, msg = 20, "High win rate"
        elif wr >= 25: s, msg = 14, "Good win rate"
        elif wr >= 15: s, msg = 8, "Moderate win rate"
        else: s, msg = 3, "Low win rate"
        score += s; components.append({"name": "Win Rate", "score": s, "max": 20, "value": f"{wr:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Win Rate", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        top_pct = insights.get("customer_concentration_pct", 50) or 50
        if top_pct <= 20: s, msg = 15, "Well diversified"
        elif top_pct <= 35: s, msg = 10, "Moderate concentration"
        elif top_pct <= 50: s, msg = 6, "High concentration"
        else: s, msg = 2, "Very concentrated"
        score += s; components.append({"name": "Customer Diversity", "score": s, "max": 15, "value": f"{top_pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Customer Diversity", "score": 6, "max": 15, "value": "N/A", "message": "No data"})
    try:
        cr_pct = insights.get("churn_risk_pct")
        if cr_pct is None: raise ValueError
        if cr_pct <= 5: s, msg = 10, "Low churn risk"
        elif cr_pct <= 15: s, msg = 7, "Moderate churn risk"
        elif cr_pct <= 30: s, msg = 4, "High churn risk"
        else: s, msg = 1, "Critical churn risk"
        score += s; components.append({"name": "Churn Risk Score", "score": s, "max": 10, "value": f"{cr_pct:.1f}%", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Churn Risk Score", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_inventory(insights: dict) -> dict:
    """Compute inventory health score."""
    components = []
    score = 0
    try:
        it = insights.get("inventory_turnover", 0) or 0
        if it >= 8: s, msg = 25, "Excellent turnover"
        elif it >= 5: s, msg = 18, "Good turnover"
        elif it >= 3: s, msg = 10, "Moderate turnover"
        elif it >= 1: s, msg = 5, "Slow turnover"
        else: s, msg = 1, "Very slow turnover"
        score += s; components.append({"name": "Inventory Turnover", "score": s, "max": 25, "value": f"{it:.2f}x", "message": msg})
    except Exception:
        components.append({"name": "Inventory Turnover", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        total_skus = insights.get("total_skus", 1) or 1
        stockout = insights.get("stockout_risk_count", 0) or 0
        pct = stockout / total_skus * 100
        if pct == 0: s, msg = 20, "No stockout risk"
        elif pct <= 5: s, msg = 14, "Low stockout risk"
        elif pct <= 15: s, msg = 8, "Moderate stockout risk"
        elif pct <= 30: s, msg = 3, "High stockout risk"
        else: s, msg = 0, "Critical stockout risk"
        score += s; components.append({"name": "Stockout Risk", "score": s, "max": 20, "value": f"{pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Stockout Risk", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        total_skus = insights.get("total_skus", 1) or 1
        dead = insights.get("dead_stock_count", 0) or 0
        pct = dead / total_skus * 100
        if pct == 0: s, msg = 20, "No dead stock"
        elif pct <= 5: s, msg = 14, "Low dead stock"
        elif pct <= 15: s, msg = 8, "Moderate dead stock"
        elif pct <= 30: s, msg = 3, "High dead stock"
        else: s, msg = 0, "Critical dead stock issue"
        score += s; components.append({"name": "Dead Stock", "score": s, "max": 20, "value": f"{pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Dead Stock", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        fr = insights.get("avg_fill_rate")
        if fr is None: raise ValueError
        if fr >= 98: s, msg = 15, "Excellent fill rate"
        elif fr >= 95: s, msg = 11, "Good fill rate"
        elif fr >= 90: s, msg = 7, "Moderate fill rate"
        else: s, msg = 2, "Low fill rate"
        score += s; components.append({"name": "Fill Rate", "score": s, "max": 15, "value": f"{fr:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Fill Rate", "score": 7, "max": 15, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        gmroi = insights.get("gmroi")
        if gmroi is None: raise ValueError
        if gmroi >= 3: s, msg = 10, "Excellent GMROI"
        elif gmroi >= 2: s, msg = 7, "Good GMROI"
        elif gmroi >= 1: s, msg = 4, "Fair GMROI"
        else: s, msg = 1, "Poor GMROI"
        score += s; components.append({"name": "GMROI", "score": s, "max": 10, "value": f"{gmroi:.2f}x", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "GMROI", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_restaurant(insights: dict) -> dict:
    """Compute restaurant health score."""
    components = []
    score = 0
    try:
        fc = insights.get("food_cost_pct", 0) or 0
        if fc <= 28: s, msg = 25, "Excellent food cost"
        elif fc <= 32: s, msg = 18, "Good food cost"
        elif fc <= 35: s, msg = 12, "Moderate food cost"
        elif fc <= 40: s, msg = 6, "High food cost"
        else: s, msg = 1, "Critical food cost"
        score += s; components.append({"name": "Food Cost %", "score": s, "max": 25, "value": f"{fc:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Food Cost %", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        pc = insights.get("prime_cost_pct")
        if pc is None: raise ValueError
        if pc < 55: s, msg = 20, "Excellent prime cost"
        elif pc < 65: s, msg = 14, "Good prime cost"
        elif pc < 75: s, msg = 8, "High prime cost"
        else: s, msg = 2, "Critical prime cost"
        score += s; components.append({"name": "Prime Cost %", "score": s, "max": 20, "value": f"{pc:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Prime Cost %", "score": 10, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Revenue Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Revenue Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        rpc = insights.get("revenue_per_cover", 0) or 0
        if rpc > 0: s, msg = 15, f"${rpc:.2f} per cover"
        else: s, msg = 8, "No cover data"
        score += s; components.append({"name": "Revenue per Cover", "score": s, "max": 15, "value": f"${rpc:.2f}", "message": msg})
    except Exception:
        components.append({"name": "Revenue per Cover", "score": 8, "max": 15, "value": "N/A", "message": "No data"})
    try:
        mps = insights.get("menu_profitability_score")
        if mps is None: raise ValueError
        if mps >= 60: s, msg = 10, "Strong menu profitability"
        elif mps >= 40: s, msg = 7, "Good menu profitability"
        else: s, msg = 3, "Needs menu optimisation"
        score += s; components.append({"name": "Menu Profitability", "score": s, "max": 10, "value": f"{mps:.1f}%", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "Menu Profitability", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_ecommerce(insights: dict) -> dict:
    """Compute e-commerce health score."""
    components = []
    score = 0
    try:
        rpr = insights.get("repeat_purchase_rate", 0) or 0
        if rpr >= 40: s, msg = 25, "Excellent repeat rate"
        elif rpr >= 25: s, msg = 18, "Good repeat rate"
        elif rpr >= 15: s, msg = 10, "Moderate repeat rate"
        elif rpr >= 5: s, msg = 5, "Low repeat rate"
        else: s, msg = 1, "Very low repeat rate"
        score += s; components.append({"name": "Repeat Purchase Rate", "score": s, "max": 25, "value": f"{rpr:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Repeat Purchase Rate", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        ret = insights.get("return_rate", 0) or 0
        if ret <= 3: s, msg = 20, "Very low return rate"
        elif ret <= 8: s, msg = 14, "Low return rate"
        elif ret <= 15: s, msg = 8, "Moderate return rate"
        elif ret <= 25: s, msg = 3, "High return rate"
        else: s, msg = 0, "Critical return rate"
        score += s; components.append({"name": "Return Rate", "score": s, "max": 20, "value": f"{ret:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Return Rate", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Revenue Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Revenue Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        car = insights.get("cart_abandonment_rate", 65) or 65
        if car <= 50: s, msg = 20, "Low abandonment"
        elif car <= 65: s, msg = 14, "Moderate abandonment"
        elif car <= 75: s, msg = 8, "High abandonment"
        else: s, msg = 3, "Very high abandonment"
        score += s; components.append({"name": "Cart Abandonment", "score": s, "max": 20, "value": f"{car:.1f}%", "message": msg, "_requires": "basic"})
    except Exception:
        components.append({"name": "Cart Abandonment", "score": 8, "max": 20, "value": "N/A", "message": "No data", "_requires": "basic"})
    try:
        ratio = insights.get("cac_ltv_ratio")
        if ratio is None: raise ValueError
        if ratio >= 3: s, msg = 10, "Excellent CAC:LTV"
        elif ratio >= 1: s, msg = 7, "Good CAC:LTV"
        else: s, msg = 2, "Poor CAC:LTV"
        score += s; components.append({"name": "CAC:LTV Ratio", "score": s, "max": 10, "value": f"{ratio:.2f}x", "message": msg, "_requires": "premium"})
    except Exception:
        components.append({"name": "CAC:LTV Ratio", "score": 5, "max": 10, "value": "N/A", "message": "No data", "_requires": "premium"})
    try:
        dq = insights.get("data_quality", {}).get("score", 50) or 50
        s = round(dq / 100 * 10)
        score += s; components.append({"name": "Data Quality", "score": s, "max": 10, "value": str(dq), "message": f"DQ score: {dq}"})
    except Exception:
        components.append({"name": "Data Quality", "score": 5, "max": 10, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def _health_general(insights: dict) -> dict:
    """Compute general (fallback) health score."""
    components = []
    score = 0
    try:
        pm = insights.get("profit_margin", 0) or 0
        if pm >= 25: s, msg = 30, "Excellent margin"
        elif pm >= 15: s, msg = 22, "Good margin"
        elif pm >= 8: s, msg = 14, "Moderate margin"
        elif pm >= 0: s, msg = 6, "Thin margin"
        else: s, msg = 0, "Negative margin"
        score += s; components.append({"name": "Profit Margin", "score": s, "max": 30, "value": f"{pm:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Profit Margin", "score": 10, "max": 30, "value": "N/A", "message": "No data"})
    try:
        s, m, v, msg = _trend_score("monthly_trend", insights)
        score += s; components.append({"name": "Revenue Trend", "score": s, "max": m, "value": v, "message": msg})
    except Exception:
        components.append({"name": "Revenue Trend", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        tc = insights.get("top_customers", {})
        vals = tc.get("values", []) if isinstance(tc, dict) else []
        total_rev = insights.get("total_revenue", 0) or 0
        top_pct = (vals[0] / total_rev * 100) if vals and total_rev > 0 else 50
        if top_pct <= 20: s, msg = 25, "Well diversified"
        elif top_pct <= 35: s, msg = 18, "Moderate concentration"
        elif top_pct <= 50: s, msg = 10, "High concentration"
        else: s, msg = 4, "Very concentrated"
        score += s; components.append({"name": "Customer Diversity", "score": s, "max": 25, "value": f"{top_pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Customer Diversity", "score": 10, "max": 25, "value": "N/A", "message": "No data"})
    try:
        cr = insights.get("category_revenue", {})
        vals = cr.get("values", []) if isinstance(cr, dict) else []
        total = sum(vals)
        top_pct = (vals[0] / total * 100) if vals and total > 0 else 50
        if top_pct <= 40: s, msg = 20, "Balanced category mix"
        elif top_pct <= 60: s, msg = 14, "Moderate mix"
        elif top_pct <= 80: s, msg = 8, "Concentrated"
        else: s, msg = 3, "Single category"
        score += s; components.append({"name": "Category Mix", "score": s, "max": 20, "value": f"{top_pct:.1f}%", "message": msg})
    except Exception:
        components.append({"name": "Category Mix", "score": 8, "max": 20, "value": "N/A", "message": "No data"})
    score = min(100, score)
    return {"score": score, "max": 100, "grade": _grade(score), "components": components}


def compute_health_score(insights: dict, dataset_type: str) -> dict:
    """Dispatch to the industry health scorer and return grade with components."""
    _health_dispatch = {
        "hr": _health_hr,
        "real_estate": _health_real_estate,
        "healthcare": _health_healthcare,
        "logistics": _health_logistics,
        "hospitality": _health_hospitality,
        "construction": _health_construction,
        "marketing": _health_marketing,
        "bank_statement": _health_bank_statement,
        "sales": _health_sales,
        "inventory": _health_inventory,
        "restaurant": _health_restaurant,
        "ecommerce": _health_ecommerce,
        "general": _health_general,
    }
    try:
        fn = _health_dispatch.get(dataset_type, _health_general)
        return fn(insights)
    except Exception:
        return {"score": 50, "max": 100, "grade": "C", "components": []}


# ---------------------------------------------------------------------------
# HIGH VALUE ORDER PREDICTOR
# ---------------------------------------------------------------------------


def run_high_value_predictor(df: pd.DataFrame, detected: dict) -> dict:
    """Predict high-value orders using logistic regression via pure NumPy gradient descent."""
    try:
        amount_col = detected.get("amount")
        if not amount_col or amount_col not in df.columns:
            return {"error": "No amount column available for prediction"}
        if len(df) < 20:
            return {"error": f"Insufficient data: need at least 20 rows, got {len(df)}"}

        amounts = pd.to_numeric(df[amount_col], errors="coerce").dropna()
        if len(amounts) < 20:
            return {"error": "Insufficient numeric amount data"}

        df_clean = df.loc[amounts.index].copy()
        threshold = float(amounts.median())
        y = (amounts >= threshold).astype(float).values

        features = []
        feature_names = []

        cat_col = detected.get("category")
        if cat_col and cat_col in df_clean.columns:
            try:
                codes = df_clean[cat_col].astype("category").cat.codes.astype(float).values
                features.append(codes)
                feature_names.append(("category", cat_col))
            except Exception:
                pass

        pay_col = detected.get("payment")
        if pay_col and pay_col in df_clean.columns:
            try:
                codes = df_clean[pay_col].astype("category").cat.codes.astype(float).values
                features.append(codes)
                feature_names.append(("payment", pay_col))
            except Exception:
                pass

        qty_col = detected.get("qty")
        if qty_col and qty_col in df_clean.columns:
            try:
                vals = pd.to_numeric(df_clean[qty_col], errors="coerce").fillna(0).values
                features.append(vals)
                feature_names.append(("quantity", qty_col))
            except Exception:
                pass

        if not features:
            return {"error": "No suitable features available for prediction"}

        X = np.column_stack(features)
        means = X.mean(axis=0)
        stds = X.std(axis=0)
        stds[stds == 0] = 1
        X = (X - means) / stds
        X = np.hstack([np.ones((X.shape[0], 1)), X])

        theta = np.zeros(X.shape[1])
        lr = 0.1
        n = len(y)
        for _ in range(300):
            z = np.clip(X @ theta, -500, 500)
            h = 1 / (1 + np.exp(-z))
            grad = X.T @ (h - y) / n
            theta -= lr * grad

        z_final = np.clip(X @ theta, -500, 500)
        h_final = 1 / (1 + np.exp(-z_final))
        preds = (h_final >= 0.5).astype(float)
        accuracy = float(np.mean(preds == y) * 100)
        high_value_count = int(y.sum())
        high_value_pct = round(high_value_count / n * 100, 1)

        drivers = []
        coefficients = theta[1:]
        for i, (feat_type, col_name) in enumerate(feature_names):
            coef = float(coefficients[i])
            if abs(coef) < 0.05:
                continue
            strength = "strongly predicts" if abs(coef) > 0.4 else "moderately predicts"
            direction = "high-value" if coef > 0 else "lower-value"
            plain = f"{col_name} ({feat_type}) {strength} {direction} orders"
            drivers.append({"factor": col_name, "direction": direction, "strength": round(abs(coef), 3), "plain": plain})

        drivers.sort(key=lambda x: x["strength"], reverse=True)

        if drivers:
            headline = f"Model is {accuracy:.0f}% accurate. {drivers[0]['plain']}."
        else:
            headline = f"Model is {accuracy:.0f}% accurate. No strong individual predictors found."

        return {
            "threshold": round(threshold, 2),
            "threshold_label": f"${threshold:,.2f}",
            "accuracy": round(accuracy, 1),
            "model_confidence": f"{accuracy:.0f}% accurate",
            "n_samples": n,
            "high_value_count": high_value_count,
            "high_value_pct": high_value_pct,
            "drivers": drivers,
            "headline": headline,
        }
    except Exception as e:
        return {"error": f"Predictor failed: {str(e)}"}


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------


def analyze_data(
    df: pd.DataFrame,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    industry_override: Optional[str] = None,
) -> dict:
    """Run the full analytics pipeline on a DataFrame and return the insights dict."""
    df = df.copy()
    df.columns = df.columns.str.strip()
    insights: dict = {}
    insights["total_rows"] = int(len(df))
    insights["columns"] = list(df.columns)

    detected = detect_columns(df)
    insights["column_report"] = build_column_report(detected)

    date_col = detected.get("date")
    if date_col and date_col in df.columns:
        try:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            if date_from:
                df = df[df[date_col] >= pd.to_datetime(date_from)]
            if date_to:
                df = df[df[date_col] <= pd.to_datetime(date_to)]
            insights["total_rows"] = int(len(df))
        except Exception:
            pass

    if date_col and date_col in df.columns:
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if len(dates) > 0:
                insights["date_range"] = {
                    "from": str(dates.min().date()),
                    "to": str(dates.max().date()),
                    "days": int((dates.max() - dates.min()).days),
                }
            else:
                insights["date_range"] = None
        except Exception:
            insights["date_range"] = None
    else:
        insights["date_range"] = None

    valid_types = set(_INDUSTRY_ANALYZERS.keys())
    if industry_override and industry_override in valid_types:
        dataset_type = industry_override
    else:
        dataset_type = detect_dataset_type(df)
    insights["dataset_type"] = dataset_type

    amount_col = detected.get("amount")
    insights["amount_fallback"] = False
    if not amount_col or amount_col not in df.columns:
        fallback = find_numeric_fallback(df, exclude=[v for v in detected.values() if v])
        if fallback:
            detected["amount"] = fallback
            insights["amount_fallback"] = True
            amount_col = fallback

    if amount_col and amount_col in df.columns and dataset_type != "bank_statement":
        try:
            nums = pd.to_numeric(df[amount_col], errors="coerce").dropna()
            insights["total_revenue"] = round(float(nums.sum()), 2)
            insights["avg_order_value"] = round(float(nums.mean()), 2)
            insights["max_order"] = round(float(nums.max()), 2)
            insights["min_order"] = round(float(nums.min()), 2)
        except Exception:
            pass

    profit_col = detected.get("profit")
    if profit_col and profit_col in df.columns:
        try:
            profits = pd.to_numeric(df[profit_col], errors="coerce").dropna()
            insights["total_profit"] = round(float(profits.sum()), 2)
            total_rev = insights.get("total_revenue", 0)
            if total_rev and total_rev != 0:
                insights["profit_margin"] = round(float(profits.sum() / total_rev * 100), 1)
        except Exception:
            pass

    category_col = detected.get("category")
    if category_col and category_col in df.columns and amount_col and amount_col in df.columns:
        try:
            cat_rev = df.groupby(category_col)[amount_col].apply(
                lambda x: pd.to_numeric(x, errors="coerce").sum()
            ).sort_values(ascending=False)
            insights["category_revenue"] = {
                "labels": list(cat_rev.index.astype(str)),
                "values": [round(float(v), 2) for v in cat_rev.values],
            }
        except Exception:
            pass

    sub_col = detected.get("subcategory")
    if sub_col and sub_col in df.columns and amount_col and amount_col in df.columns:
        try:
            sub_rev = df.groupby(sub_col)[amount_col].apply(
                lambda x: pd.to_numeric(x, errors="coerce").sum()
            ).sort_values(ascending=False).head(8)
            insights["subcategory_revenue"] = {
                "labels": list(sub_rev.index.astype(str)),
                "values": [round(float(v), 2) for v in sub_rev.values],
            }
        except Exception:
            pass

    payment_col = detected.get("payment")
    if payment_col and payment_col in df.columns:
        try:
            pm = df[payment_col].value_counts().head(10)
            insights["payment_methods"] = {
                "labels": list(pm.index.astype(str)),
                "values": [int(v) for v in pm.values],
            }
        except Exception:
            pass

    customer_col = detected.get("customer")
    if customer_col and customer_col in df.columns and amount_col and amount_col in df.columns:
        try:
            top_cust = df.groupby(customer_col)[amount_col].apply(
                lambda x: pd.to_numeric(x, errors="coerce").sum()
            ).sort_values(ascending=False).head(5)
            insights["top_customers"] = {
                "labels": list(top_cust.index.astype(str)),
                "values": [round(float(v), 2) for v in top_cust.values],
            }
        except Exception:
            pass

    state_col = detected.get("state")
    if state_col and state_col in df.columns and amount_col and amount_col in df.columns:
        try:
            state_rev = df.groupby(state_col)[amount_col].apply(
                lambda x: pd.to_numeric(x, errors="coerce").sum()
            ).sort_values(ascending=False).head(10)
            insights["sales_by_state"] = {
                "labels": list(state_rev.index.astype(str)),
                "values": [round(float(v), 2) for v in state_rev.values],
            }
        except Exception:
            pass

    if date_col and date_col in df.columns and amount_col and amount_col in df.columns:
        try:
            tmp = df.copy()
            tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
            tmp = tmp.dropna(subset=[date_col])
            tmp["_month"] = tmp[date_col].dt.to_period("M")
            monthly = tmp.groupby("_month")[amount_col].apply(
                lambda x: pd.to_numeric(x, errors="coerce").sum()
            ).sort_index()
            insights["monthly_trend"] = {
                "labels": [str(p) for p in monthly.index],
                "values": [round(float(v), 2) for v in monthly.values],
            }
        except Exception:
            pass

    qty_col = detected.get("qty")
    if qty_col and qty_col in df.columns and category_col and category_col in df.columns:
        try:
            qty_cat = df.groupby(category_col)[qty_col].apply(
                lambda x: pd.to_numeric(x, errors="coerce").sum()
            ).sort_values(ascending=False)
            insights["quantity_by_category"] = {
                "labels": list(qty_cat.index.astype(str)),
                "values": [round(float(v), 2) for v in qty_cat.values],
            }
        except Exception:
            pass

    try:
        analyzer_fn = _INDUSTRY_ANALYZERS.get(dataset_type, _INDUSTRY_ANALYZERS["general"])
        industry_insights = analyzer_fn(df, detected)
        insights.update(industry_insights)
    except Exception:
        pass

    try:
        insights["data_quality"] = compute_data_quality(df, detected)
    except Exception:
        insights["data_quality"] = {
            "score": 50, "grade": "Fair", "checks": [],
            "passed": 0, "warned": 0, "failed": 0, "summary": "Quality check failed",
        }

    try:
        insights["health_score"] = compute_health_score(insights, dataset_type)
    except Exception:
        insights["health_score"] = {"score": 50, "max": 100, "grade": "C", "components": []}

    try:
        insights["high_value_predictor"] = run_high_value_predictor(df, detected)
    except Exception:
        insights["high_value_predictor"] = {"error": "Predictor unavailable"}

    return insights


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

__all__ = [
    "COLUMN_CANDIDATES",
    "DATASET_SIGNATURES",
    "detect_columns",
    "detect_dataset_type",
    "build_column_report",
    "analyze_data",
    "compute_data_quality",
    "compute_health_score",
    "run_high_value_predictor",
    "find_column",
    "find_numeric_fallback",
]
