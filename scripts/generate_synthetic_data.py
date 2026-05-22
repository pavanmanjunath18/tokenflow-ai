"""
Synthetic enterprise AI telemetry generator for TokenFlow AI MVP.

Generates 4 core datasets:
  1. identity_directory.csv       — employee/department roster
  2. model_pricing.csv            — per-model token costs
  3. ai_license_inventory.csv     — seat assignments + activity
  4. api_gateway_traces.csv       — AI request-level traces (100k+ rows)

Datasets mimic real enterprise integrations but contain no real data.
The connector layer reads CSV for now; each connector has a documented
production-upgrade path to the real integration it simulates.
"""

import csv
import json
import os
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUTPUT_DIR = Path(__file__).parent.parent / "synthetic-data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── constants ────────────────────────────────────────────────────────────────

START_DATE = datetime(2024, 12, 1)
END_DATE = datetime(2025, 5, 31, 23, 59, 59)
N_EMPLOYEES = 150
N_GATEWAY_EVENTS = 120_000

DEPARTMENTS = {
    "Engineering":       {"headcount": 35, "weight": 0.30},
    "Marketing":         {"headcount": 18, "weight": 0.15},
    "Customer Support":  {"headcount": 25, "weight": 0.18},
    "Finance":           {"headcount": 12, "weight": 0.07},
    "HR":                {"headcount": 10, "weight": 0.05},
    "Product":           {"headcount": 15, "weight": 0.10},
    "Sales":             {"headcount": 20, "weight": 0.10},
    "Operations":        {"headcount": 15, "weight": 0.05},
}

ROLES_BY_DEPT = {
    "Engineering":      ["Software Engineer", "Senior Engineer", "Staff Engineer", "Engineering Manager", "DevOps Engineer", "QA Engineer"],
    "Marketing":        ["Marketing Manager", "Content Strategist", "Growth Analyst", "Brand Manager", "Marketing Coordinator"],
    "Customer Support": ["Support Agent", "Senior Support Agent", "Support Manager", "Technical Support Specialist"],
    "Finance":          ["Financial Analyst", "Senior Analyst", "Finance Manager", "Controller", "Accountant"],
    "HR":               ["HR Business Partner", "Recruiter", "HR Manager", "L&D Specialist", "Compensation Analyst"],
    "Product":          ["Product Manager", "Senior PM", "Group PM", "Product Analyst"],
    "Sales":            ["Account Executive", "Sales Manager", "SDR", "Solutions Engineer", "Enterprise AE"],
    "Operations":       ["Operations Analyst", "Operations Manager", "Program Manager", "Business Analyst"],
}

TEAMS_BY_DEPT = {
    "Engineering":      ["Platform", "Infrastructure", "Frontend", "Backend", "Data", "ML"],
    "Marketing":        ["Demand Gen", "Brand", "Content", "Growth"],
    "Customer Support": ["Tier 1", "Tier 2", "Enterprise Support"],
    "Finance":          ["FP&A", "Accounting", "Treasury"],
    "HR":               ["Talent Acquisition", "People Ops", "L&D"],
    "Product":          ["Core Product", "Platform Product", "Growth Product"],
    "Sales":            ["SMB", "Mid-Market", "Enterprise"],
    "Operations":       ["BizOps", "RevOps", "IT Ops"],
}

SSO_PROVIDERS = ["Okta", "Azure AD", "Google Workspace"]
LOCATIONS = ["San Francisco, CA", "New York, NY", "Austin, TX", "Chicago, IL", "Remote", "Boston, MA"]
EMPLOYMENT_TYPES = ["Full-time", "Contractor"]

# AI tools per department (approved)
AI_TOOLS_BY_DEPT = {
    "Engineering":      ["GitHub Copilot", "Claude Code", "OpenAI API", "Cursor"],
    "Marketing":        ["ChatGPT Plus", "Claude.ai", "Jasper", "Copy.ai"],
    "Customer Support": ["Intercom AI", "Claude.ai", "ChatGPT Plus", "Zendesk AI"],
    "Finance":          ["ChatGPT Enterprise", "Claude.ai"],
    "HR":               ["ChatGPT Enterprise", "Claude.ai"],
    "Product":          ["ChatGPT Plus", "Claude.ai", "Notion AI"],
    "Sales":            ["ChatGPT Plus", "Claude.ai", "Gong AI", "Outreach AI"],
    "Operations":       ["ChatGPT Plus", "Claude.ai", "Notion AI"],
}

PLAN_TYPES = {
    "GitHub Copilot":       ("Business", 19.00),
    "Claude Code":          ("Pro", 20.00),
    "OpenAI API":           ("Pay-as-you-go", 0.00),
    "Cursor":               ("Business", 40.00),
    "ChatGPT Plus":         ("Plus", 20.00),
    "ChatGPT Enterprise":   ("Enterprise", 60.00),
    "Claude.ai":            ("Pro", 20.00),
    "Jasper":               ("Business", 49.00),
    "Copy.ai":              ("Pro", 36.00),
    "Intercom AI":          ("Enterprise", 74.00),
    "Zendesk AI":           ("Suite Pro", 95.00),
    "Notion AI":            ("Plus", 10.00),
    "Gong AI":              ("Enterprise", 100.00),
    "Outreach AI":          ("Standard", 50.00),
}

# Model catalog with provider affiliation
MODELS = [
    {"provider": "Anthropic", "model": "claude-3-5-sonnet-20241022", "tier": "premium",   "input_per_1m": 3.00,  "output_per_1m": 15.00, "cached_per_1m": 0.30},
    {"provider": "Anthropic", "model": "claude-3-5-haiku-20241022",  "tier": "standard",  "input_per_1m": 0.80,  "output_per_1m": 4.00,  "cached_per_1m": 0.08},
    {"provider": "Anthropic", "model": "claude-3-opus-20240229",     "tier": "ultra",     "input_per_1m": 15.00, "output_per_1m": 75.00, "cached_per_1m": 1.50},
    {"provider": "OpenAI",    "model": "gpt-4o",                     "tier": "premium",   "input_per_1m": 2.50,  "output_per_1m": 10.00, "cached_per_1m": 1.25},
    {"provider": "OpenAI",    "model": "gpt-4o-mini",                "tier": "standard",  "input_per_1m": 0.15,  "output_per_1m": 0.60,  "cached_per_1m": 0.075},
    {"provider": "OpenAI",    "model": "o1-preview",                 "tier": "ultra",     "input_per_1m": 15.00, "output_per_1m": 60.00, "cached_per_1m": 7.50},
    {"provider": "OpenAI",    "model": "gpt-3.5-turbo",              "tier": "economy",   "input_per_1m": 0.50,  "output_per_1m": 1.50,  "cached_per_1m": 0.50},
    {"provider": "Google",    "model": "gemini-1.5-pro",             "tier": "premium",   "input_per_1m": 1.25,  "output_per_1m": 5.00,  "cached_per_1m": 0.3125},
    {"provider": "Google",    "model": "gemini-1.5-flash",           "tier": "standard",  "input_per_1m": 0.075, "output_per_1m": 0.30,  "cached_per_1m": 0.01875},
    {"provider": "Mistral",   "model": "mistral-large-2407",         "tier": "premium",   "input_per_1m": 3.00,  "output_per_1m": 9.00,  "cached_per_1m": 3.00},
    {"provider": "Mistral",   "model": "mistral-nemo",               "tier": "standard",  "input_per_1m": 0.15,  "output_per_1m": 0.15,  "cached_per_1m": 0.15},
    {"provider": "Meta",      "model": "llama-3.3-70b-instruct",     "tier": "economy",   "input_per_1m": 0.59,  "output_per_1m": 0.79,  "cached_per_1m": 0.59},
]

MODEL_BY_DEPT = {
    "Engineering":      ["claude-3-5-sonnet-20241022", "gpt-4o", "claude-3-5-haiku-20241022", "gpt-4o-mini", "claude-3-opus-20240229"],
    "Marketing":        ["gpt-4o", "claude-3-5-sonnet-20241022", "gpt-4o-mini", "gemini-1.5-pro"],
    "Customer Support": ["claude-3-5-haiku-20241022", "gpt-4o-mini", "gemini-1.5-flash", "claude-3-5-sonnet-20241022"],
    "Finance":          ["claude-3-5-sonnet-20241022", "gpt-4o", "claude-3-opus-20240229"],
    "HR":               ["claude-3-5-sonnet-20241022", "gpt-4o", "claude-3-5-haiku-20241022"],
    "Product":          ["claude-3-5-sonnet-20241022", "gpt-4o", "gemini-1.5-pro"],
    "Sales":            ["gpt-4o-mini", "claude-3-5-haiku-20241022", "gpt-4o", "claude-3-5-sonnet-20241022"],
    "Operations":       ["gpt-4o-mini", "gemini-1.5-flash", "claude-3-5-haiku-20241022"],
}

TASK_TYPES_BY_DEPT = {
    "Engineering":      ["code_generation", "code_review", "debugging", "documentation", "test_writing", "architecture_design"],
    "Marketing":        ["content_creation", "email_draft", "ad_copy", "social_media", "campaign_analysis", "blog_writing"],
    "Customer Support": ["support_response", "ticket_summarization", "knowledge_base_query", "escalation_draft"],
    "Finance":          ["financial_analysis", "report_generation", "invoice_processing", "forecast_modeling", "contract_review"],
    "HR":               ["job_description", "resume_screening", "employee_feedback", "policy_draft", "offer_letter"],
    "Product":          ["prd_writing", "user_story", "market_research", "feature_spec", "roadmap_planning"],
    "Sales":            ["email_draft", "crm_notes", "account_research", "proposal_writing", "follow_up_draft"],
    "Operations":       ["process_summary", "vendor_review", "meeting_summary", "reporting", "workflow_automation"],
}

# simple task types → flag expensive-model misuse
SIMPLE_TASK_TYPES = {"email_draft", "meeting_summary", "ticket_summarization", "social_media", "crm_notes", "follow_up_draft"}

REQUEST_TYPES = ["chat_completion", "embedding", "text_generation", "function_calling"]
STATUS_CODES  = [200, 200, 200, 200, 200, 429, 500, 503]

FIRST_NAMES = ["Aria","Blake","Cameron","Dana","Emery","Finn","Georgia","Harper","Indigo","Jordan",
               "Kai","Lena","Morgan","Noel","Olivia","Parker","Quinn","Riley","Sage","Taylor",
               "Uma","Vance","Winter","Xavier","Yasmin","Zach","Alex","Briar","Caden","Devon",
               "Ellis","Fallon","Glenn","Harlow","Ivan","Jade","Kelsey","Lane","Macy","Nash",
               "Oakley","Piper","Reese","Sloane","Tatum","Upton","Vera","Wren","Xena","Yale"]

LAST_NAMES = ["Adams","Baker","Chen","Davis","Evans","Foster","Garcia","Harris","Ivanov","Jones",
              "Kim","Lee","Miller","Nguyen","O'Brien","Patel","Quinn","Rodriguez","Smith","Taylor",
              "Upton","Vargas","Walker","Xu","Young","Zhang","Anderson","Brown","Clark","Diaz",
              "Edwards","Franklin","Green","Hall","Jackson","Johnson","Kumar","Lewis","Moore","Nelson",
              "Owen","Price","Reed","Scott","Turner","Underwood","Vance","White","Xia","York"]


# ── helpers ──────────────────────────────────────────────────────────────────

def random_date(start: datetime, end: datetime) -> datetime:
    delta = end - start
    return start + timedelta(seconds=random.randint(0, int(delta.total_seconds())))


def random_business_timestamp() -> datetime:
    """Mostly business hours Mon-Fri, with realistic off-hours tails."""
    ts = random_date(START_DATE, END_DATE)
    # 85% chance shift to business hours
    if random.random() < 0.85:
        ts = ts.replace(hour=random.randint(8, 18), minute=random.randint(0, 59))
        # ensure Mon-Fri
        while ts.weekday() >= 5:
            ts += timedelta(days=1)
    return ts


def model_pricing_lookup() -> dict:
    return {m["model"]: m for m in MODELS}


def compute_cost(model_name: str, input_tokens: int, output_tokens: int, cache_hit: bool, pricing: dict) -> float:
    info = pricing.get(model_name)
    if not info:
        return 0.0
    if cache_hit:
        cost = (input_tokens / 1_000_000) * info["cached_per_1m"] + (output_tokens / 1_000_000) * info["output_per_1m"]
    else:
        cost = (input_tokens / 1_000_000) * info["input_per_1m"] + (output_tokens / 1_000_000) * info["output_per_1m"]
    return round(cost, 6)


# ── 1. identity_directory.csv ────────────────────────────────────────────────

def generate_identity_directory() -> list[dict]:
    print("  Generating identity_directory.csv …")
    employees = []
    emp_id = 1000
    dept_list = list(DEPARTMENTS.keys())

    # Assign headcounts
    roster: list[tuple[str, int]] = []
    total = 0
    for dept, info in DEPARTMENTS.items():
        count = info["headcount"]
        total += count
        roster.append((dept, count))

    # Pad/trim to exactly N_EMPLOYEES
    while total < N_EMPLOYEES:
        roster[0] = (roster[0][0], roster[0][1] + 1)
        total += 1
    while total > N_EMPLOYEES:
        roster[-1] = (roster[-1][0], roster[-1][1] - 1)
        total -= 1

    # Manager pool (first employee per department)
    manager_ids: dict[str, str] = {}

    for dept, count in roster:
        roles = ROLES_BY_DEPT[dept]
        teams = TEAMS_BY_DEPT[dept]
        sso = random.choice(SSO_PROVIDERS)

        for i in range(count):
            eid = f"EMP{emp_id:04d}"
            name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            email_local = name.lower().replace(" ", ".").replace("'", "")
            email = f"{email_local}@acmecorp.com"
            role = roles[i % len(roles)]
            team = random.choice(teams)

            if i == 0:
                manager_ids[dept] = eid
                manager_id = ""
            else:
                manager_id = manager_ids[dept]

            start = random_date(datetime(2019, 1, 1), datetime(2024, 6, 1)).date()
            cost_center = f"CC{dept_list.index(dept) + 1:02d}0{random.randint(1,3)}"

            employees.append({
                "employee_id":      eid,
                "employee_name":    name,
                "email":            email,
                "department":       dept,
                "team":             team,
                "role":             role,
                "manager_id":       manager_id,
                "cost_center":      cost_center,
                "location":         random.choice(LOCATIONS),
                "employment_type":  random.choices(EMPLOYMENT_TYPES, weights=[90, 10])[0],
                "start_date":       str(start),
                "sso_provider":     sso,
                "status":           random.choices(["active", "inactive"], weights=[95, 5])[0],
            })
            emp_id += 1

    _write_csv(employees, OUTPUT_DIR / "identity_directory.csv")
    print(f"    → {len(employees)} employees")
    return employees


# ── 2. model_pricing.csv ─────────────────────────────────────────────────────

def generate_model_pricing():
    print("  Generating model_pricing.csv …")
    rows = []
    for m in MODELS:
        rows.append({
            "provider":                   m["provider"],
            "model_name":                 m["model"],
            "tier":                       m["tier"],
            "input_cost_per_1m_tokens":   m["input_per_1m"],
            "output_cost_per_1m_tokens":  m["output_per_1m"],
            "cached_input_cost_per_1m_tokens": m["cached_per_1m"],
            "effective_date":             "2024-12-01",
        })
    _write_csv(rows, OUTPUT_DIR / "model_pricing.csv")
    print(f"    → {len(rows)} models")
    return rows


# ── 3. ai_license_inventory.csv ──────────────────────────────────────────────

def generate_license_inventory(employees: list[dict]) -> list[dict]:
    print("  Generating ai_license_inventory.csv …")
    rows = []
    license_id = 1

    for emp in employees:
        dept = emp["department"]
        tools = AI_TOOLS_BY_DEPT[dept]

        # Primary tool (always assigned)
        primary_tool = tools[0]
        plan, seat_cost = PLAN_TYPES[primary_tool]
        assigned = random_date(datetime(2024, 6, 1), datetime(2024, 11, 30)).date()
        last_active = random_date(datetime(2025, 1, 1), END_DATE).date()

        # Simulate inactive licenses (15% chance)
        if random.random() < 0.15:
            last_active = random_date(datetime(2024, 12, 1), datetime(2025, 1, 15)).date()
            active_days = random.randint(0, 3)
            status = "inactive"
        else:
            active_days = random.randint(10, 30)
            status = "active"

        rows.append({
            "license_id":         f"LIC{license_id:05d}",
            "employee_id":        emp["employee_id"],
            "tool_name":          primary_tool,
            "plan_type":          plan,
            "monthly_seat_cost":  seat_cost,
            "assigned_date":      str(assigned),
            "last_active_date":   str(last_active),
            "active_days_last_30": active_days,
            "license_status":     status,
            "department":         dept,
        })
        license_id += 1

        # Secondary tool (50% chance)
        if len(tools) > 1 and random.random() < 0.50:
            secondary = random.choice(tools[1:])
            plan2, cost2 = PLAN_TYPES[secondary]
            assigned2 = random_date(datetime(2024, 8, 1), datetime(2024, 12, 31)).date()
            last2 = random_date(datetime(2025, 1, 1), END_DATE).date()
            active2 = random.randint(5, 28)

            # Duplicate license anomaly (5%)
            is_dup = random.random() < 0.05

            rows.append({
                "license_id":         f"LIC{license_id:05d}",
                "employee_id":        emp["employee_id"],
                "tool_name":          primary_tool if is_dup else secondary,
                "plan_type":          plan if is_dup else plan2,
                "monthly_seat_cost":  seat_cost if is_dup else cost2,
                "assigned_date":      str(assigned2),
                "last_active_date":   str(last2),
                "active_days_last_30": active2,
                "license_status":     "active",
                "department":         dept,
            })
            license_id += 1

    _write_csv(rows, OUTPUT_DIR / "ai_license_inventory.csv")
    print(f"    → {len(rows)} license records")
    return rows


# ── 4. api_gateway_traces.csv ────────────────────────────────────────────────

def generate_api_gateway_traces(employees: list[dict]) -> list[dict]:
    print(f"  Generating api_gateway_traces.csv ({N_GATEWAY_EVENTS:,} rows) …")
    pricing = model_pricing_lookup()

    # Build weighted employee pool
    dept_weights = [DEPARTMENTS[e["department"]]["weight"] for e in employees]

    rows = []
    trace_id = 1

    # Spike windows: simulate 3 cost anomaly weeks
    spike_windows = [
        (datetime(2025, 1, 13), datetime(2025, 1, 17)),
        (datetime(2025, 3, 3),  datetime(2025, 3, 7)),
        (datetime(2025, 4, 21), datetime(2025, 4, 25)),
    ]

    def in_spike_window(ts: datetime) -> bool:
        return any(s <= ts <= e for s, e in spike_windows)

    for _ in range(N_GATEWAY_EVENTS):
        emp = random.choices(employees, weights=dept_weights, k=1)[0]
        dept = emp["department"]
        dept_models = MODEL_BY_DEPT[dept]

        ts = random_business_timestamp()
        is_spike = in_spike_window(ts)

        # Model selection: during spike, Engineering sometimes reaches for ultra models
        if is_spike and dept == "Engineering" and random.random() < 0.30:
            model_name = random.choice(["claude-3-opus-20240229", "o1-preview"])
        else:
            weights_m = [4, 3, 2, 1, 1][:len(dept_models)]
            model_name = random.choices(dept_models, weights=weights_m, k=1)[0]

        model_info = pricing.get(model_name, {})

        task_type = random.choice(TASK_TYPES_BY_DEPT[dept])

        # Input/output token distributions by dept
        if dept == "Engineering":
            input_tokens  = int(np.random.lognormal(7.5, 0.8))   # ~1800 median
            output_tokens = int(np.random.lognormal(6.5, 0.7))
        elif dept == "Marketing":
            input_tokens  = int(np.random.lognormal(6.8, 0.7))
            output_tokens = int(np.random.lognormal(7.2, 0.8))
        elif dept == "Customer Support":
            input_tokens  = int(np.random.lognormal(6.2, 0.6))
            output_tokens = int(np.random.lognormal(6.0, 0.6))
        elif dept == "Finance":
            input_tokens  = int(np.random.lognormal(7.8, 0.9))
            output_tokens = int(np.random.lognormal(7.0, 0.7))
        else:
            input_tokens  = int(np.random.lognormal(6.9, 0.75))
            output_tokens = int(np.random.lognormal(6.5, 0.70))

        input_tokens  = max(50, min(input_tokens, 128_000))
        output_tokens = max(20, min(output_tokens, 16_000))
        total_tokens  = input_tokens + output_tokens

        cache_hit   = random.random() < 0.18
        cache_type  = random.choice(["ephemeral", "persistent"]) if cache_hit else ""
        cost        = compute_cost(model_name, input_tokens, output_tokens, cache_hit, pricing)

        # Spike multiplier
        if is_spike:
            cost *= random.uniform(1.5, 3.0)
            cost = round(cost, 6)

        latency_ms          = int(np.random.lognormal(6.5, 0.6))  # ~665ms median
        latency_ms          = max(80, min(latency_ms, 60_000))
        ttft_ms             = int(latency_ms * random.uniform(0.3, 0.7))

        status_code         = random.choices(STATUS_CODES, weights=[80,80,80,80,80,2,1,1], k=1)[0]
        fallback_used       = status_code != 200 and random.random() < 0.4
        request_allowed     = random.random() > 0.02
        blocked_reason      = "" if request_allowed else random.choice(["budget_exceeded", "policy_violation", "rate_limit"])

        # Expensive model on simple task → flag
        is_expensive_simple = (
            model_info.get("tier") in ("premium", "ultra")
            and task_type in SIMPLE_TASK_TYPES
        )

        # Tool that generated this trace
        dept_tools = AI_TOOLS_BY_DEPT[dept]
        internal_app = random.choice(dept_tools)

        rows.append({
            "trace_id":         f"TRACE{trace_id:07d}",
            "timestamp":        ts.isoformat(),
            "organization_id":  "ORG001",
            "employee_id":      emp["employee_id"],
            "department":       dept,
            "team":             emp["team"],
            "internal_app":     internal_app,
            "provider":         model_info.get("provider", "Unknown"),
            "model_name":       model_name,
            "request_type":     random.choice(REQUEST_TYPES),
            "task_type":        task_type,
            "input_tokens":     input_tokens,
            "output_tokens":    output_tokens,
            "total_tokens":     total_tokens,
            "cost_usd":         cost,
            "latency_ms":       latency_ms,
            "time_to_first_token_ms": ttft_ms,
            "status_code":      status_code,
            "cache_hit":        cache_hit,
            "cache_type":       cache_type,
            "fallback_used":    fallback_used,
            "budget_policy_id": f"POL{random.randint(1,5):02d}",
            "request_allowed":  request_allowed,
            "blocked_reason":   blocked_reason,
            "expensive_model_simple_task": is_expensive_simple,
        })
        trace_id += 1

    _write_csv(rows, OUTPUT_DIR / "api_gateway_traces.csv")
    total_cost = sum(r["cost_usd"] for r in rows)
    print(f"    → {len(rows):,} traces | total cost ${total_cost:,.2f}")
    return rows


# ── utility ──────────────────────────────────────────────────────────────────

def _write_csv(rows: list[dict], path: Path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ── 5. browser_extension_events.csv ─────────────────────────────────────────

APPROVED_DOMAINS = {
    "chat.openai.com", "claude.ai", "github.com", "cursor.sh",
    "copilot.github.com", "notion.so", "intercom.com",
}
SHADOW_AI_DOMAINS = [
    "character.ai", "poe.com", "bard.google.com", "bing.com/chat",
    "perplexity.ai", "you.com", "phind.com",
]
TASK_TYPES_BROWSER = [
    "email_draft", "document_summary", "code_completion", "research",
    "content_creation", "form_fill", "translation", "meeting_summary",
]
BROWSERS = ["Chrome", "Firefox", "Edge", "Safari"]
PII_TYPES = ["email", "phone", "SSN", "credit_card", "address"]


def generate_browser_extension_events(employees: list[dict]) -> list[dict]:
    print("  Generating browser_extension_events.csv …")
    rows = []
    event_id = 1

    for _ in range(30_000):
        emp = random.choice(employees)
        dept = emp["department"]
        ts = random_business_timestamp()

        is_shadow = random.random() < 0.08
        domain = random.choice(SHADOW_AI_DOMAINS) if is_shadow else random.choice(list(APPROVED_DOMAINS))
        approved = not is_shadow

        contains_pii = random.random() < (0.15 if dept in ("Finance", "HR") else 0.04)
        pii_types = random.sample(PII_TYPES, k=random.randint(1, 2)) if contains_pii else []
        risk_score = round(random.uniform(0.5, 1.0) if (contains_pii or is_shadow) else random.uniform(0.0, 0.3), 2)

        if contains_pii or is_shadow:
            policy_action = random.choice(["warn", "block", "redact"])
        else:
            policy_action = "allow"

        prompt_len = random.randint(50, 2000)

        rows.append({
            "event_id":                f"BEXT{event_id:07d}",
            "timestamp":               ts.isoformat(),
            "employee_id":             emp["employee_id"],
            "department":              dept,
            "session_id":              f"SESS{random.randint(100000, 999999)}",
            "browser":                 random.choice(BROWSERS),
            "domain":                  domain,
            "task_type":               random.choice(TASK_TYPES_BROWSER),
            "prompt_length_chars":     prompt_len,
            "estimated_input_tokens":  prompt_len // 4,
            "estimated_output_tokens": random.randint(50, 800),
            "contains_pii":            contains_pii,
            "pii_types_detected":      "|".join(pii_types),
            "policy_action":           policy_action,
            "shadow_ai_flag":          is_shadow,
            "approved_tool":           approved,
            "copy_paste_detected":     random.random() < 0.25,
            "file_upload_detected":    random.random() < 0.05,
            "risk_score":              risk_score,
        })
        event_id += 1

    _write_csv(rows, OUTPUT_DIR / "browser_extension_events.csv")
    shadow_count = sum(1 for r in rows if r["shadow_ai_flag"])
    pii_count    = sum(1 for r in rows if r["contains_pii"])
    print(f"    → {len(rows):,} events | {shadow_count} shadow AI | {pii_count} PII flags")
    return rows


# ── 6. kafka_ai_telemetry.jsonl ──────────────────────────────────────────────

def generate_kafka_telemetry(employees: list[dict], traces: list[dict]) -> list[dict]:
    print("  Generating kafka_ai_telemetry.jsonl …")
    rows = []
    # Sample 20k traces and reformat as Kafka-style events
    sample = random.sample(traces, min(20_000, len(traces)))
    for t in sample:
        rows.append({
            "event_type":     "ai_request_completed",
            "trace_id":       t["trace_id"],
            "timestamp":      t["timestamp"] if isinstance(t["timestamp"], str) else t["timestamp"].isoformat(),
            "producer":       "api-gateway-v2",
            "organization_id": t.get("organization_id", "ORG001"),
            "employee_id":    t["employee_id"],
            "department":     t["department"],
            "team_id":        t.get("team", ""),
            "provider":       t["provider"],
            "model":          t["model_name"],
            "input_tokens":   t["input_tokens"],
            "output_tokens":  t["output_tokens"],
            "latency_ms":     t["latency_ms"],
            "cost_usd":       t["cost_usd"],
            "cache_hit":      t["cache_hit"],
            "policy_result":  "allowed" if t.get("request_allowed", True) else "blocked",
        })

    path = OUTPUT_DIR / "kafka_ai_telemetry.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")
    print(f"    → {len(rows):,} Kafka events")
    return rows


# ── 7. clickhouse_ai_traces.csv ───────────────────────────────────────────────

def generate_clickhouse_traces(employees: list[dict], traces: list[dict]) -> list[dict]:
    print("  Generating clickhouse_ai_traces.csv …")
    # ClickHouse-style analytics table: aggregated per (employee, model, day)
    from collections import defaultdict

    key_fn = lambda t: (
        t["employee_id"],
        t["department"],
        t["model_name"],
        t["provider"],
        (t["timestamp"] if isinstance(t["timestamp"], str) else t["timestamp"].isoformat())[:10],
    )
    agg: dict = defaultdict(lambda: {"count": 0, "input": 0, "output": 0, "cost": 0.0, "latency_sum": 0, "cache_hits": 0})
    for t in traces:
        k = key_fn(t)
        agg[k]["count"]       += 1
        agg[k]["input"]       += t["input_tokens"]
        agg[k]["output"]      += t["output_tokens"]
        agg[k]["cost"]        += t["cost_usd"]
        agg[k]["latency_sum"] += t["latency_ms"]
        agg[k]["cache_hits"]  += int(bool(t.get("cache_hit")))

    rows = []
    trace_id = 1
    for (emp_id, dept, model, provider, day), v in agg.items():
        rows.append({
            "agg_id":          f"CH{trace_id:07d}",
            "date":            day,
            "employee_id":     emp_id,
            "department":      dept,
            "provider":        provider,
            "model_name":      model,
            "request_count":   v["count"],
            "input_tokens":    v["input"],
            "output_tokens":   v["output"],
            "total_tokens":    v["input"] + v["output"],
            "cost_usd":        round(v["cost"], 6),
            "avg_latency_ms":  round(v["latency_sum"] / v["count"]) if v["count"] else 0,
            "cache_hit_count": v["cache_hits"],
            "cache_hit_rate":  round(v["cache_hits"] / v["count"], 3) if v["count"] else 0,
        })
        trace_id += 1

    _write_csv(rows, OUTPUT_DIR / "clickhouse_ai_traces.csv")
    print(f"    → {len(rows):,} ClickHouse aggregated rows")
    return rows


# ── 8. kubernetes_gateway_logs.csv ────────────────────────────────────────────

PODS = [f"ai-gateway-{i}" for i in range(1, 7)]
NAMESPACES = ["ai-platform", "ml-infra"]
CLUSTERS   = ["prod-us-west-2", "prod-us-east-1"]


def generate_kubernetes_logs() -> list[dict]:
    print("  Generating kubernetes_gateway_logs.csv …")
    rows = []
    log_id = 1

    # One row per pod per hour
    current = START_DATE
    while current < END_DATE:
        for pod in PODS:
            cluster = CLUSTERS[0] if "west" in pod or int(pod[-1]) <= 3 else CLUSTERS[1]
            hour_of_day = current.hour
            is_peak = 9 <= hour_of_day <= 18

            req_count   = int(np.random.lognormal(5.5 if is_peak else 4.0, 0.4))
            error_count = int(req_count * random.uniform(0.005, 0.04))
            avg_lat     = int(np.random.lognormal(6.0, 0.3))
            p95_lat     = int(avg_lat * random.uniform(1.5, 3.5))
            cpu         = round(random.uniform(20, 85) if is_peak else random.uniform(5, 40), 1)
            mem_mb      = int(random.uniform(256, 1024))
            restarts    = 1 if random.random() < 0.02 else 0

            rows.append({
                "log_id":            f"K8S{log_id:08d}",
                "timestamp":         current.isoformat(),
                "cluster":           cluster,
                "namespace":         random.choice(NAMESPACES),
                "pod_name":          pod,
                "gateway_version":   "v2.4.1",
                "request_count":     req_count,
                "error_count":       error_count,
                "error_rate":        round(error_count / req_count, 4) if req_count else 0,
                "avg_latency_ms":    avg_lat,
                "p95_latency_ms":    p95_lat,
                "cpu_usage_percent": cpu,
                "memory_usage_mb":   mem_mb,
                "restart_count":     restarts,
                "status":            "degraded" if restarts or error_count / max(req_count, 1) > 0.03 else "healthy",
            })
            log_id += 1
        current += timedelta(hours=1)

    _write_csv(rows, OUTPUT_DIR / "kubernetes_gateway_logs.csv")
    print(f"    → {len(rows):,} pod-hour log entries")
    return rows


# ── 9. productivity_metrics.csv ───────────────────────────────────────────────

def generate_productivity_metrics(employees: list[dict]) -> list[dict]:
    print("  Generating productivity_metrics.csv …")
    rows = []
    metric_id = 1

    for emp in employees:
        dept = emp["department"]
        # One record per 2-week period over 6 months → ~13 periods
        period_start = START_DATE.date()
        for _ in range(13):
            period_end = period_start + timedelta(days=13)

            rows.append({
                "metric_id":                  f"PROD{metric_id:06d}",
                "employee_id":                emp["employee_id"],
                "department":                 dept,
                "source_system":              {
                    "Engineering":      "GitHub",
                    "Marketing":        "HubSpot",
                    "Customer Support": "Zendesk",
                    "Finance":          "Salesforce",
                    "HR":               "Workday",
                    "Product":          "Jira",
                    "Sales":            "Salesforce",
                    "Operations":       "Jira",
                }.get(dept, "Internal"),
                "period_start":               str(period_start),
                "period_end":                 str(period_end),
                "tickets_closed":             random.randint(0, 30) if dept == "Customer Support" else 0,
                "prs_merged":                 random.randint(0, 12) if dept == "Engineering" else 0,
                "commits_count":              random.randint(0, 50) if dept == "Engineering" else 0,
                "support_resolution_hours":   round(random.uniform(1, 48), 1) if dept == "Customer Support" else 0,
                "sales_opportunities_created": random.randint(0, 20) if dept == "Sales" else 0,
                "ai_assisted_work_items":     random.randint(0, 15),
                "quality_score":              round(random.uniform(0.6, 1.0), 2),
            })
            metric_id += 1
            period_start = period_end + timedelta(days=1)

    _write_csv(rows, OUTPUT_DIR / "productivity_metrics.csv")
    print(f"    → {len(rows):,} productivity records")
    return rows


# ── manifest ─────────────────────────────────────────────────────────────────

def write_manifest(employees, models, licenses, traces, browser, kafka, clickhouse, k8s, productivity):
    manifest = {
        "generated_at": datetime.now().isoformat() + "Z",
        "seed": SEED,
        "period": {"start": START_DATE.isoformat(), "end": END_DATE.isoformat()},
        "files": {
            "identity_directory.csv":      {"rows": len(employees),    "phase": 1},
            "model_pricing.csv":           {"rows": len(models),       "phase": 1},
            "ai_license_inventory.csv":    {"rows": len(licenses),     "phase": 1},
            "api_gateway_traces.csv":      {"rows": len(traces),       "phase": 1},
            "browser_extension_events.csv": {"rows": len(browser),     "phase": 2},
            "kafka_ai_telemetry.jsonl":    {"rows": len(kafka),        "phase": 2},
            "clickhouse_ai_traces.csv":    {"rows": len(clickhouse),   "phase": 2},
            "kubernetes_gateway_logs.csv": {"rows": len(k8s),          "phase": 2},
            "productivity_metrics.csv":    {"rows": len(productivity), "phase": 2},
        },
        "summary": {
            "employees":     len(employees),
            "departments":   len(DEPARTMENTS),
            "models":        len(models),
            "gateway_events": len(traces),
            "total_cost_usd": round(sum(r["cost_usd"] for r in traces), 2),
        },
    }
    with open(OUTPUT_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("  Wrote manifest.json")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("TokenFlow AI — Synthetic Data Generator (Phase 1 + 2)")
    print(f"Output directory: {OUTPUT_DIR.resolve()}\n")

    employees    = generate_identity_directory()
    models       = generate_model_pricing()
    licenses     = generate_license_inventory(employees)
    traces       = generate_api_gateway_traces(employees)

    browser      = generate_browser_extension_events(employees)
    kafka        = generate_kafka_telemetry(employees, traces)
    clickhouse   = generate_clickhouse_traces(employees, traces)
    k8s          = generate_kubernetes_logs()
    productivity = generate_productivity_metrics(employees)

    write_manifest(employees, models, licenses, traces, browser, kafka, clickhouse, k8s, productivity)

    print("\nDone. Summary:")
    print(f"  Employees        : {len(employees)}")
    print(f"  Gateway traces   : {len(traces):,}")
    print(f"  Browser events   : {len(browser):,}")
    print(f"  Kafka events     : {len(kafka):,}")
    print(f"  ClickHouse rows  : {len(clickhouse):,}")
    print(f"  K8s log entries  : {len(k8s):,}")
    print(f"  Productivity recs: {len(productivity):,}")
    print(f"  Total AI cost    : ${sum(r['cost_usd'] for r in traces):,.2f}")


if __name__ == "__main__":
    main()
