import streamlit as st
import pandas as pd
import io
import base64
import time
import re
from pathlib import Path
from xml.sax.saxutils import escape
import tomllib
import unicodedata
import hashlib
import zipfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from datetime import datetime, timezone
from supabase import create_client, Client
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

def get_supabase_client() -> Client:
    """Initialize and return the Supabase client."""
    url, key = _read_supabase_secrets()
    if not url or not key:
        raise ValueError("Supabase URL or Key is missing from configuration/secrets.")
    return create_client(url, key)
st.set_page_config(page_title="Oriental Consultants Philippines Inc.", page_icon="OCP", layout="wide")

def _logo_data_uri():
    logo_path = Path(__file__).resolve().parent / "oc_philippines_logo.png"
    try:
        encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"
    except Exception:
        return ""

LOGO_URI = _logo_data_uri()

USERNAME = st.secrets.get("OCP_ADMIN_USERNAME", "admin")
PASSWORD = st.secrets.get("OCP_ADMIN_PASSWORD", "ocp123")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "login_loading" not in st.session_state:
    st.session_state.login_loading = False
if "uploaded_df" not in st.session_state:
    st.session_state.uploaded_df = None
if "uploaded_name" not in st.session_state:
    st.session_state.uploaded_name = None
if "supabase_ready" not in st.session_state:
    st.session_state.supabase_ready = False

st.markdown("""
<style>
html, body, [class*="css"] {font-family: Inter, Arial, sans-serif;}
.stApp {background:#f4f7fb;}
.block-container {padding-top:2.2rem; padding-bottom:3rem; max-width:1700px;}

.portal-header {
    background:#fff;
    border:1px solid #dfe6ee;
    border-radius:20px;
    padding:26px 28px;
    box-shadow:0 6px 20px rgba(20,45,75,.04);
    margin-bottom:22px;
}
.header-left {display:flex;align-items:center;gap:17px;}
.ocp-square {
    width:58px;height:58px;border-radius:15px;background:#124d7d;color:#fff;
    display:flex;align-items:center;justify-content:center;font-weight:800;
    font-size:19px;letter-spacing:.5px;
}
.header-title {font-size:23px;font-weight:800;color:#092e50;line-height:1.15;}
.header-sub {font-size:15px;color:#68788a;margin-top:8px;}
.portal-pill {
    display:inline-block;background:#eef7ff;border:1px solid #d4e6f5;color:#0c4a78;
    border-radius:999px;padding:12px 18px;font-weight:700;font-size:14px;
}
.section-title {font-size:20px;font-weight:800;color:#092e50;margin-top:14px;}
.section-sub {color:#68788a;font-size:14px;margin-top:5px;margin-bottom:14px;}
.signed-in {color:#77808d;font-size:15px;margin:7px 0 24px 0;}

div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
div[data-testid="stTextInput"] [data-baseweb="input"] {
    background:#f0f3f7;border-color:#e5eaf0;border-radius:10px;min-height:49px;
}
.stButton > button, .stDownloadButton > button {
    min-height:48px;border-radius:10px;font-weight:700;
}
div[data-testid="stDataFrame"] {border-radius:14px;overflow:hidden;border:1px solid #e3e9f0;background:#fff;}

/* Compact, aligned inline experience controls; no dropdown. */
.experience-filter-heading {font-size:14px;color:#092e50;margin:0 0 6px;line-height:1.4;}
div[data-testid="stCheckbox"] label {font-size:13px !important;}
div[data-testid="stCheckbox"] {margin:0 !important;}
div[data-testid="stSlider"] {padding-top:0 !important;}
/* Experience popover: override Admin popover styles ONLY in this filter. */
/* Match the Evaluation multiselect's neutral-gray surface, without affecting Admin. */
.st-key-experience_filter_panel div[data-testid="stPopover"] > button {
    background:#f0f2f6 !important;
    color:#17243a !important;
    border:1px solid transparent !important;
    min-height:48px !important;
    height:48px !important;
    border-radius:10px !important;
    padding:0 10px !important;
    font-size:13px !important;
    font-weight:400 !important;
    box-shadow:none !important;
    justify-content:space-between !important;
    white-space:nowrap !important;
}
.st-key-experience_filter_panel div[data-testid="stPopover"] > button:hover {
    background:#e9edf3 !important;
    border-color:transparent !important;
}
.st-key-experience_filter_panel div[data-testid="stCheckbox"] label {
    font-size:13px !important;
    white-space:nowrap;
}
/* Give only the experience settings popover a comfortable, responsive width. */
div[data-baseweb="popover"]:has(.ocp-experience-popover-marker) {
    width: min(420px, calc(100vw - 32px)) !important;
    max-width: calc(100vw - 32px) !important;
}
div[data-testid="stPopoverBody"]:has(.ocp-experience-popover-marker) {
    width: min(420px, calc(100vw - 32px)) !important;
    min-width: min(360px, calc(100vw - 32px)) !important;
    max-width: calc(100vw - 32px) !important;
    box-sizing: border-box !important;
    padding: 18px 20px !important;
    overflow: visible !important;
}
div[data-testid="stPopoverBody"]:has(.ocp-experience-popover-marker) div[data-testid="stSlider"] {
    width: 100% !important;
}
/* Modern responsive evaluation guide */
.eval-guide {
    background:#ffffff;
    border:1px solid #dfe6ee;
    border-radius:14px;
    padding:14px 16px;
    margin:8px 0 14px 0;
    box-shadow:0 4px 14px rgba(20,45,75,.035);
}
.eval-guide-head {
    display:flex;align-items:center;justify-content:space-between;gap:12px;
    margin-bottom:10px;
}
.eval-guide-title {font-size:14px;font-weight:800;color:#092e50;}
.eval-guide-note {font-size:12px;color:#7b8794;}
.eval-guide-grid {
    display:grid;
    grid-template-columns:repeat(5,minmax(120px,1fr));
    gap:8px;
}
.eval-chip {
    background:#f7f9fc;
    border:1px solid #e6ebf1;
    border-radius:10px;
    padding:9px 11px;
    min-width:0;
}
.eval-chip-label {font-size:12px;font-weight:700;color:#24384b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.eval-chip-score {font-size:13px;font-weight:800;color:#0c4a78;margin-top:3px;}

/* Responsive dashboard */
@media (max-width: 900px) {
    .block-container {padding-left:1rem !important;padding-right:1rem !important;padding-top:1rem !important;}
    .ocp-portal-header {padding:18px;gap:14px;align-items:flex-start;}
    .ocp-header-title {font-size:19px;}
    .ocp-header-subtitle {font-size:13px;margin-top:5px;}
    .ocp-portal-pill {font-size:12px;padding:9px 12px;}
    .eval-guide-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
}
@media (max-width: 600px) {
    .ocp-portal-header {flex-direction:column;}
    .ocp-portal-pill {width:100%;text-align:center;box-sizing:border-box;}
    .section-title {font-size:17px;}
    .section-sub {font-size:13px;}
    .eval-guide-head {align-items:flex-start;flex-direction:column;gap:3px;}
    .eval-guide-grid {grid-template-columns:1fr;}
    .eval-chip {padding:8px 10px;}
    div[data-testid="stDataFrame"] {overflow-x:auto;}
}

/* Login */
.login-wrap {max-width:500px;margin:5vh auto 18px;text-align:center;}
.login-logo {
    width:66px;height:66px;border-radius:16px;background:#124d7d;color:white;
    margin:0 auto 14px;display:flex;align-items:center;justify-content:center;
    font-weight:800;font-size:20px;
}
.login-title {font-size:27px;font-weight:800;color:#092e50;}
.login-sub {color:#68788a;margin-top:5px;}
div[data-testid="stForm"] {
    max-width:500px;margin:0 auto;background:#fff;border:1px solid #e0e7ef;
    border-radius:17px;padding:26px 28px;box-shadow:0 10px 30px rgba(20,45,75,.07);
}

/* Dialog */
div[role="dialog"] {border-radius:18px;}

/* Transparent Streamlit top navigation/header */
[data-testid="stHeader"] {
    background: transparent !important;
}
[data-testid="stToolbar"] {
    background: transparent !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}

/* Single OCP portal header card */
.ocp-portal-header {
    background:#ffffff;
    border:1px solid #dfe6ee;
    border-radius:20px;
    padding:26px 28px;
    box-shadow:0 6px 20px rgba(20,45,75,.04);
    margin-bottom:22px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:24px;
}
.ocp-header-left {
    display:flex;
    align-items:center;
    gap:17px;
}
.ocp-header-logo {
    width:58px;
    height:58px;
    border-radius:15px;
    background:#124d7d;
    color:#ffffff;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:18px;
    font-weight:800;
    letter-spacing:.4px;
    flex:0 0 auto;
}
.ocp-header-title {
    color:#092e50;
    font-size:23px;
    font-weight:800;
    line-height:1.15;
}
.ocp-header-subtitle {
    color:#68788a;
    font-size:15px;
    margin-top:8px;
}
.ocp-portal-pill {
    background:#eef7ff;
    border:1px solid #d4e6f5;
    color:#0c4a78;
    border-radius:999px;
    padding:13px 19px;
    font-weight:700;
    font-size:14px;
    white-space:nowrap;
}
.login-loading {
    max-width:480px;
    margin:18vh auto 0;
    text-align:center;
}
.login-loading-logo {
    width:72px;
    height:72px;
    border-radius:18px;
    margin:0 auto 18px;
    background:#124d7d;
    color:#fff;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:20px;
    font-weight:800;
    box-shadow:0 10px 25px rgba(18,77,125,.18);
}
.login-loading-title {
    font-size:25px;
    font-weight:800;
    color:#092e50;
}
.login-loading-text {
    color:#68788a;
    margin-top:7px;
    font-size:15px;
}
@media(max-width:700px){
    .ocp-portal-header{align-items:flex-start;flex-direction:column;}
    .ocp-portal-pill{align-self:flex-start;}
}

/* Compact portal spacing */
.block-container {
    padding-top: 1.05rem !important;
    padding-bottom: 1.6rem !important;
}
.ocp-portal-header {
    padding: 18px 22px !important;
    margin-bottom: 10px !important;
    border-radius: 16px !important;
}
.ocp-header-logo {
    width: 50px !important;
    height: 50px !important;
    border-radius: 13px !important;
}
.ocp-header-title {font-size:20px !important;}
.ocp-header-subtitle {margin-top:5px !important;font-size:13px !important;}
.ocp-portal-pill {padding:10px 16px !important;font-size:12px !important;}
.signed-in {
    margin: 2px 0 5px 0 !important;
    font-size: 13px !important;
}
.section-title {
    margin-top: 8px !important;
    font-size: 18px !important;
}
.section-sub {
    margin-top: 2px !important;
    margin-bottom: 7px !important;
    font-size: 13px !important;
}
div[data-testid="stVerticalBlock"] {gap:.55rem;}
div[data-testid="stSelectbox"], div[data-testid="stTextInput"] {margin-bottom:0 !important;}
.stButton > button, .stDownloadButton > button {
    min-height: 42px !important;
}
div[data-testid="stDataFrame"] {margin-top:2px !important;}

/* Modern floating login loading modal */
.login-modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 999998;
    background: rgba(238, 243, 249, .70);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
}
.login-modal-card {
    position: fixed;
    z-index: 999999;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: min(390px, calc(100vw - 40px));
    background: rgba(255,255,255,.96);
    border: 1px solid rgba(216,225,235,.95);
    border-radius: 22px;
    padding: 30px 30px 28px;
    text-align: center;
    box-shadow: 0 24px 70px rgba(20, 45, 75, .18);
}
.login-modal-mark {
    width: 58px;
    height: 58px;
    margin: 0 auto 17px;
    border-radius: 16px;
    background: #124d7d;
    color: #fff;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: .4px;
    box-shadow: 0 9px 22px rgba(18,77,125,.18);
}
.login-modal-spinner {
    width: 34px;
    height: 34px;
    margin: 0 auto 16px;
    border: 3px solid #dbe8f2;
    border-top-color: #17649c;
    border-radius: 50%;
    animation: ocpSpin .8s linear infinite;
}
@keyframes ocpSpin {
    to { transform: rotate(360deg); }
}
.login-modal-title {
    color: #092e50;
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 5px;
}
.login-modal-text {
    color: #718096;
    font-size: 13px;
}

/* ===== CLASSIC LAYOUT RESTORED ===== */
.classic-ocp-header{
    width:100%;
    box-sizing:border-box;
    background:#ffffff;
    border:1px solid #dfe6ee;
    border-radius:20px;
    padding:18px 28px;
    min-height:112px;
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:24px;
    box-shadow:0 6px 20px rgba(20,45,75,.04);
    margin-bottom:14px;
}
.classic-ocp-brand{
    display:flex;
    align-items:center;
    gap:17px;
}
.classic-ocp-logo{
    width:58px;
    height:58px;
    flex:0 0 58px;
    border-radius:15px;
    background:#124d7d;
    color:#fff;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size:18px;
    font-weight:800;
}
.classic-ocp-title{
    color:#092e50;
    font-size:22px;
    font-weight:800;
    line-height:1.15;
}
.classic-ocp-subtitle{
    color:#68788a;
    font-size:14px;
    margin-top:7px;
}
.classic-portal-pill{
    min-width:205px;
    min-height:42px;
    box-sizing:border-box;
    border-radius:999px;
    border:1px solid #d4e6f5;
    background:#eef7ff;
    color:#0c4a78;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:9px 18px;
    font-size:12px;
    font-weight:700;
    white-space:nowrap;
}

/* Admin replaces the old dark-blue Log Out button */
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]){
    position:static !important;
    height:auto !important;
    min-height:auto !important;
    margin:0 0 8px 0 !important;
    padding:0 !important;
    overflow:visible !important;
}
div[data-testid="stHorizontalBlock"]:has(div[data-testid="stPopover"]) > div:last-child{
    position:static !important;
    width:auto !important;
    right:auto !important;
    bottom:auto !important;
}
div[data-testid="stPopover"]{
    display:block !important;
    width:100% !important;
}
div[data-testid="stPopover"] > button{
    position:static !important;
    opacity:1 !important;
    visibility:visible !important;
    width:100% !important;
    min-height:54px !important;
    height:54px !important;
    border-radius:12px !important;
    border:1px solid #124d7d !important;
    background:#124d7d !important;
    color:#ffffff !important;
    font-size:14px !important;
    font-weight:700 !important;
    box-shadow:none !important;
}
div[data-testid="stPopover"] > button:hover{
    background:#0d416c !important;
    border-color:#0d416c !important;
}
div[data-testid="stPopoverBody"]{
    background:#ffffff !important;
    border:1px solid #dfe6ee !important;
    border-radius:14px !important;
    box-shadow:0 16px 38px rgba(20,45,75,.16) !important;
    padding:8px !important;
}
div[data-testid="stPopoverBody"] .stButton > button{
    width:100% !important;
    min-height:42px !important;
    border-radius:9px !important;
    font-weight:600 !important;
}

/* Hide only obsolete experimental header elements. */
.ocp-admin-pill,
.ocp-restored-admin-visual,
.final-header,
.modern-brand,
.ocp-clean-brand{
    display:none !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# FILE UPLOAD / STAFF DATABASE
# ============================================================

def parse_contract_date(value):
    """Return YYYY-MM-DD for Supabase DATE; leave empty cells unset."""
    if value is None or str(value).strip().lower() in ("", "nan", "none", "nat"):
        return None
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        return parsed.date().isoformat() if not pd.isna(parsed) else None
    except (ValueError, TypeError, OverflowError):
        return None


def normalize_columns(df):
    """Normalize common column names from OCP Excel/CSV files."""
    df = df.copy()
    aliases = {
        "NAME": "Name",
        "EMPLOYEE NAME": "Name",
        "FULL NAME": "Name",
        "PERSONNEL NAME": "Name",
        "POSITION": "Position",
        "DESIGNATION": "Position",
        "JOB TITLE": "Position",
        "TYPE OF ENGAGEMENT": "Type of Engagement",
        "ENGAGEMENT": "Type of Engagement",
        "EMPLOYMENT TYPE": "Type of Engagement",
        "EVALUATION": "Evaluation",
        "RATING": "Evaluation",
        "PERFORMANCE": "Evaluation",
        "STATUS": "Status",
        "PROJECT": "Project",
        "PROJECT NAME": "Project",
        "CURRENT PROJECT": "Project",
        "ELIGIBILITY": "Eligibility",
        "PROFESSIONAL ELIGIBILITY": "Eligibility",
        "FUNDING": "Funding",
        "FUNDING SOURCE": "Funding",
        "SECTOR": "Sector",
        "TOTAL YEAR EXPERIENCE": "Experience",
        "TOTAL YEARS EXPERIENCE": "Experience",
        "TOTAL YEARS OF EXPERIENCE": "Experience",
        "YEARS OF EXPERIENCE": "Experience",
        "EXPERIENCE": "Experience",
        "OVERSEAS": "Overseas Experience",
        "OVERSEAS EXPERIENCE": "Overseas Experience",
        "OVERSEAS YEARS": "Overseas Experience",
        "END OF CONTRACT": "End of Contract",
        "CONTRACT END DATE": "End of Contract",
        "CONTRACT EXPIRY": "End of Contract",
    }
    renamed = {}
    for col in df.columns:
        key = str(col).strip().upper()
        if key in aliases:
            renamed[col] = aliases[key]
    df = df.rename(columns=renamed)
    return df


def enrich_staff_fields(df):
    """Fill common engagement/evaluation fields when source files use alternate columns."""
    df = df.copy()
    for col in ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience"]:
        if col not in df.columns:
            df[col] = ""

    engagement_candidates = [
        c for c in df.columns
        if c != "Type of Engagement" and (
            "ENGAGEMENT" in str(c).upper()
            or "EMPLOYMENT TYPE" in str(c).upper()
            or "CONTRACT TYPE" in str(c).upper()
        )
    ]
    evaluation_candidates = [
        c for c in df.columns
        if c != "Evaluation" and (
            "EVALUATION" in str(c).upper()
            or "RATING" in str(c).upper()
            or "PERFORMANCE" in str(c).upper()
        )
    ]

    for c in engagement_candidates:
        vals = df[c].fillna("").astype(str).str.strip()
        blank = df["Type of Engagement"].fillna("").astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[blank & vals.ne("") & vals.ne("nan"), "Type of Engagement"] = vals

    for c in evaluation_candidates:
        vals = df[c].fillna("").astype(str).str.strip()
        blank = df["Evaluation"].fillna("").astype(str).str.strip().isin(["", "nan", "None"])
        df.loc[blank & vals.ne("") & vals.ne("nan"), "Evaluation"] = vals

    return df


def find_header(raw):
    """Find the header row in an OCP worksheet."""
    for i in range(min(len(raw), 25)):
        vals = [str(v).strip().upper() for v in raw.iloc[i].tolist() if pd.notna(v)]
        joined = " | ".join(vals)
        if "NAME" in joined and ("POSITION" in joined or "DESIGNATION" in joined):
            return i
    return 0


def load_upload(uploaded):
    """Read CSV, XLSX, or legacy XLS files, including all Excel worksheets."""
    suffix = Path(uploaded.name).suffix.lower()

    if suffix == ".csv":
        uploaded.seek(0)
        try:
            df = pd.read_csv(uploaded)
        except UnicodeDecodeError:
            uploaded.seek(0)
            df = pd.read_csv(uploaded, encoding="latin-1")
        df = enrich_staff_fields(normalize_columns(df))
        if "Project" not in df.columns:
            df["Project"] = Path(uploaded.name).stem
        return df

    if suffix not in {".xlsx", ".xls"}:
        raise ValueError("Unsupported file format. Please upload .xlsx, .xls, or .csv.")

    frames = []
    uploaded.seek(0)
    engine = "xlrd" if suffix == ".xls" else "openpyxl"
    xls = pd.ExcelFile(uploaded, engine=engine)

    for sheet in xls.sheet_names:
        try:
            uploaded.seek(0)
            raw = pd.read_excel(uploaded, sheet_name=sheet, header=None)
            header_row = find_header(raw)
            uploaded.seek(0)
            df = pd.read_excel(uploaded, sheet_name=sheet, header=header_row)
            df = normalize_columns(df)
            df = enrich_staff_fields(df)

            if "Project" not in df.columns or df["Project"].fillna("").astype(str).str.strip().eq("").all():
                df["Project"] = sheet.strip()

            df = df.dropna(how="all")
            frames.append(df)
        except Exception:
            continue

    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()


def clean_staff(df):
    """Normalize staff fields while preserving meaningful rows."""
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience", "Overseas Experience", "End of Contract", "Eligibility"
        ])

    df = df.copy()
    for col in ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience", "Overseas Experience", "End of Contract", "Eligibility"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
        df.loc[df[col].str.lower().isin(["nan", "none"]), col] = ""

    useful = (df["Name"] != "") | (df["Position"] != "")
    return df[useful].copy()


def _read_supabase_secrets():
    """Read Supabase credentials from Streamlit secrets.

    Supported formats:
      [supabase]
      url = "..."
      secret_key = "sb_secret_..."

    and the existing project format:
      [connections.postgres]
      url = "..."
      secret_key = "sb_secret_..."

    A legacy JWT `key` is also accepted, but `secret_key` is preferred.
    """
    try:
        # Preferred format
        if "supabase" in st.secrets:
            cfg = st.secrets["supabase"]
            url = cfg.get("url") or cfg.get("URL")
            key = cfg.get("secret_key") or cfg.get("key")
            if url and key:
                return str(url).strip(), str(key).strip()

        # Support the user's existing [connections.postgres] section.
        if "connections" in st.secrets and "postgres" in st.secrets["connections"]:
            cfg = st.secrets["connections"]["postgres"]
            url = cfg.get("url")
            key = cfg.get("secret_key") or cfg.get("key")
            if url and key:
                return str(url).strip(), str(key).strip()

        # Flat environment-style secrets
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_SECRET_KEY") or st.secrets.get("SUPABASE_KEY")
        if url and key:
            return str(url).strip(), str(key).strip()
    except Exception:
        pass

    return None, None

def fetch_staff_from_supabase():
    """Load the staff records currently stored in Supabase."""
    empty = pd.DataFrame(columns=[
        "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project",
        "Source File", "Source Path", "Uploaded At"
    ])
    client = get_supabase_client()
    if client is None:
        return empty

    try:
        rows = []
        start = 0
        page_size = 1000
        while True:
            result = (
                client.table("staff_records")
                .select("name,position,type_of_engagement,evaluation,status,project,funding,sector,experience,source_file,source_path,uploaded_at")
                .range(start, start + page_size - 1)
                .execute()
            )
            batch = result.data or []
            rows.extend(batch)
            if len(batch) < page_size:
                break
            start += page_size

        if not rows:
            return empty

        df = pd.DataFrame(rows).rename(columns={
            "name": "Name",
            "position": "Position",
            "type_of_engagement": "Type of Engagement",
            "evaluation": "Evaluation",
            "status": "Status",
            "project": "Project",
            "funding": "Funding",
            "sector": "Sector",
            "experience": "Experience",
            "source_file": "Source File",
            "source_path": "Source Path",
            "uploaded_at": "Uploaded At",
        })
        # Overseas experience is optional in older Supabase schemas.
        try:
            overseas_rows = []
            offset = 0
            while True:
                page = (client.table("staff_records")
                        .select("name,position,project,overseas_experience")
                        .range(offset, offset + 999).execute()).data or []
                overseas_rows.extend(page)
                if len(page) < 1000:
                    break
                offset += 1000
            overseas_map = {
                _dedupe_key(r.get("name"), r.get("position"), r.get("project")): r.get("overseas_experience")
                for r in overseas_rows
            }
            df["Overseas Experience"] = df.apply(
                lambda r: overseas_map.get(_dedupe_key(r.get("Name"), r.get("Position"), r.get("Project")), ""), axis=1)
        except Exception:
            df["Overseas Experience"] = ""
        # Optional date column: older Supabase schemas may not have it yet.
        try:
            contract_rows = []
            offset = 0
            while True:
                page = (client.table("staff_records")
                        .select("name,position,project,end_of_contract")
                        .range(offset, offset + 999).execute()).data or []
                contract_rows.extend(page)
                if len(page) < 1000:
                    break
                offset += 1000
            contract_map = {
                _dedupe_key(r.get("name"), r.get("position"), r.get("project")): r.get("end_of_contract")
                for r in contract_rows
            }
            df["End of Contract"] = df.apply(
                lambda r: contract_map.get(_dedupe_key(r.get("Name"), r.get("Position"), r.get("Project"))) or "", axis=1)
        except Exception:
            df["End of Contract"] = ""
        # Eligibility is optional for older databases; keep the table usable until SQL is run.
        try:
            eligibility_rows = []
            offset = 0
            while True:
                page = (client.table("staff_records")
                        .select("name,position,project,eligibility")
                        .range(offset, offset + 999).execute()).data or []
                eligibility_rows.extend(page)
                if len(page) < 1000:
                    break
                offset += 1000
            eligibility_map = {
                _dedupe_key(r.get("name"), r.get("position"), r.get("project")): r.get("eligibility")
                for r in eligibility_rows
            }
            df["Eligibility"] = df.apply(
                lambda r: eligibility_map.get(_dedupe_key(r.get("Name"), r.get("Position"), r.get("Project"))) or "", axis=1)
        except Exception:
            df["Eligibility"] = ""
        return clean_staff(df)
    except Exception as exc:
        st.session_state.supabase_error = str(exc)
        return empty


# --- Private CV storage / employee-name matching ---
CV_BUCKET = "employee-cvs"

def cv_name_key(value):
    """Match 'Juan Dela Cruz.pdf' with 'DELA CRUZ, Juan' (case-insensitive).
    Assumes comma-formatted employee names use LAST, FIRST. Ambiguous matches are skipped.
    """
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = re.sub(r"\.(?:pdf|docx|doc)$", "", value, flags=re.I).strip()
    if "," in value:
        last, first = value.split(",", 1)
        value = first + " " + last
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value.casefold())
    return " ".join(sorted(value.split()))

def cv_clean_filename(filename):
    """Extract a staff name from CV files with codes and role annotations."""
    name = re.sub(r"\.(?:pdf|docx|doc)$", "", str(filename or ""), flags=re.I).strip()
    # Examples: B173 - NAME, BR1 - NAME, B 424 - NAME
    name = re.sub(r"^\s*[A-Za-z]{1,10}\s*[-_ ]?\s*\d+\s*[-–—_:]\s*", "", name)
    # Role annotation e.g. NAME - (CC18 - Inspector), NAME (B057 - Engineer)
    name = re.sub(r"\s*[-–—]?\s*\([^)]*\)\s*$", "", name)
    # Remove any trailing role following an explicit dash after the name.
    if "," in name:
        name = re.split(r"\s+[-–—]\s+", name, maxsplit=1)[0]
    return name.strip(" ._-–—")


def cv_filename_key(filename):
    return cv_name_key(cv_clean_filename(filename))


def cv_tokens(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", value.casefold())


def cv_filename_identity(filename):
    name = cv_clean_filename(filename)
    if "," not in name:
        return None
    last, given = name.split(",", 1)
    return cv_tokens(last), cv_tokens(given)


def cv_match_candidates(filename, index):
    """Conservative matching: exact or unique surname + full first name.

    Missing middle initials are allowed; conflicting supplied middle names
    are not. Ambiguous employees must be reviewed manually.
    """
    exact = index.get(cv_filename_key(filename), [])
    if exact:
        return exact

    identity = cv_filename_identity(filename)
    cleaned = cv_clean_filename(filename)
    matches = []
    seen = set()
    for rows in index.values():
        for row in rows:
            raw_staff = str(row.get("name") or "")
            if "," not in raw_staff:
                continue
            db_last_raw, db_given_raw = raw_staff.split(",", 1)
            db_last, db_given = cv_tokens(db_last_raw), cv_tokens(db_given_raw)
            if not db_last or not db_given:
                continue
            if identity:
                last, given = identity
                if last != db_last or not given or len(given[0]) < 2:
                    continue
                if given[0] != db_given[0]:
                    continue
                extras = given[1:]
            else:
                tokens = cv_tokens(cleaned)
                if len(tokens) < 2 or tokens[0] != db_given[0]:
                    continue
                if tokens[-len(db_last):] != db_last:
                    continue
                extras = tokens[1:len(tokens) - len(db_last)]
            # Additional names/initials in the CV must match the database.
            # An omitted middle name is acceptable only for a unique candidate.
            db_extra = db_given[1:]
            if any(not any(t == d or (len(t) == 1 and d.startswith(t))
                           for d in db_extra) for t in extras):
                continue
            rid = str(row.get("id"))
            if rid not in seen:
                seen.add(rid)
                matches.append(row)
    return matches


def cv_staff_index(client):
    rows = []
    offset = 0
    while True:
        batch = (client.table("staff_records").select("id,name")
                 .range(offset, offset + 999).execute()).data or []
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    by_name = {}
    for row in rows:
        key = cv_name_key(row.get("name"))
        if key:
            by_name.setdefault(key, []).append(row)
    return by_name

def cv_upload_batch(files):
    client = get_supabase_client()
    index = cv_staff_index(client)
    matched, unmatched, failed = [], [], []
    for f in files:
        extension = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        allowed_types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "doc": "application/msword",
        }
        if extension not in allowed_types:
            failed.append(f"{f.name}: only PDF, DOCX, and DOC files are supported")
            continue
        data = f.getvalue()
        if extension == "pdf" and not data.startswith(b"%PDF-"):
            failed.append(f"{f.name}: invalid PDF")
            continue
        if extension == "docx":
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as document:
                    if "word/document.xml" not in document.namelist():
                        raise ValueError("missing Word document content")
            except (zipfile.BadZipFile, ValueError):
                failed.append(f"{f.name}: invalid DOCX")
                continue
        if extension == "doc" and not data.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
            failed.append(f"{f.name}: invalid legacy Word document")
            continue
        candidates = cv_match_candidates(f.name, index)
        if len(candidates) != 1:
            unmatched.append(f"{f.name}: {'no match' if not candidates else 'ambiguous employee name'}")
            continue
        staff = candidates[0]
        staff_id = str(staff["id"])
        digest = hashlib.sha256(data).hexdigest()[:16]
        path = f"{staff_id}/{digest}.{extension}"
        try:
            client.storage.from_(CV_BUCKET).upload(
                path, data, {"content-type": allowed_types[extension], "upsert": "true"}
            )
            old = (client.table("staff_cvs").select("storage_path")
                   .eq("staff_record_id", staff_id).execute()).data or []
            client.table("staff_cvs").upsert({
                "staff_record_id": staff["id"], "employee_name": staff["name"],
                "original_filename": f.name, "storage_path": path,
                "file_size": len(data), "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }, on_conflict="staff_record_id").execute()
            matched.append(f"{f.name} → {staff['name']}")
            # Do not delete previous object until metadata is committed.
            for prev in old:
                if prev.get("storage_path") and prev["storage_path"] != path:
                    try:
                        client.storage.from_(CV_BUCKET).remove([prev["storage_path"]])
                    except Exception:
                        pass
        except Exception as exc:
            failed.append(f"{f.name}: {exc}")
    if matched:
        cv_metadata_for_names.clear()
        cv_signed_link.clear()
        st.session_state.pop("cv_once_metadata", None)
        st.session_state.pop("cv_once_urls", None)
    return matched, unmatched, failed

@st.cache_data(show_spinner=False)
def cv_metadata_for_names(names):
    """Return one CV per exact normalized employee name, without public URLs."""
    client = get_supabase_client()
    desired = {cv_name_key(n) for n in names}
    results = {}
    offset = 0
    while True:
        batch = (client.table("staff_cvs")
                 .select("employee_name,original_filename,storage_path")
                 .range(offset, offset + 999).execute()).data or []
        for item in batch:
            key = cv_name_key(item.get("employee_name"))
            if key in desired:
                results[key] = item
        if len(batch) < 1000:
            break
        offset += 1000
    return results

@st.cache_data(show_spinner=False, max_entries=2000)
def cv_signed_link(path):
    client = get_supabase_client()
    response = client.storage.from_(CV_BUCKET).create_signed_url(path, 86400)
    return response.get("signedURL") or response.get("signedUrl") or ""

def cv_zip_export(pdf_bytes, staff_names, metadata):
    client = get_supabase_client()
    output = io.BytesIO()
    included, missing = [], []
    used = set()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Filtered_Personnel_List.pdf", pdf_bytes)
        for name in dict.fromkeys(staff_names):
            entry = metadata.get(cv_name_key(name))
            if not entry:
                missing.append(name)
                continue
            try:
                blob = client.storage.from_(CV_BUCKET).download(entry["storage_path"])
                safe = re.sub(r"[^\w .()-]", "_", str(name)).strip()[:100] or "Employee"
                extension = str(entry.get("original_filename") or entry.get("storage_path") or "").rsplit(".", 1)[-1].lower()
                if extension not in {"pdf", "docx", "doc"}:
                    extension = "pdf"
                filename = f"Employee_CVs/{safe}.{extension}"
                if filename in used:
                    continue
                used.add(filename)
                z.writestr(filename, blob)
                included.append(name)
            except Exception:
                missing.append(name)
        z.writestr("CV_Export_Summary.txt", "Included CVs: " + str(len(included)) +
                   "\nMissing or unavailable CVs: " + str(len(missing)) +
                   "\n\n" + "\n".join(missing))
    return output.getvalue(), included, missing

@st.cache_resource(show_spinner=False)
def _cv_job_registry():
    # Shared between Streamlit reruns; each session only receives its own random job ID.
    return {"lock": threading.Lock(), "jobs": {}}


def _run_cv_export_job(job_id, url, key, pdf_bytes, names, metadata):
    registry = _cv_job_registry()
    unique_names = list(dict.fromkeys(names))
    included, missing, downloaded = [], [], []
    try:
        tasks = [(name, metadata.get(cv_name_key(name))) for name in unique_names]
        available = [(name, entry) for name, entry in tasks if entry]
        missing.extend(name for name, entry in tasks if not entry)
        with registry["lock"]:
            registry["jobs"][job_id]["total"] = len(available)
            registry["jobs"][job_id]["missing"] = len(missing)

        def fetch(item):
            name, entry = item
            # Client is created inside the worker thread, not shared with Streamlit UI.
            client = create_client(url, key)
            blob = client.storage.from_(CV_BUCKET).download(entry["storage_path"])
            return name, entry, blob

        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(fetch, item): item[0] for item in available}
            for future in as_completed(futures):
                try:
                    downloaded.append(future.result())
                    included.append(futures[future])
                except Exception:
                    missing.append(futures[future])
                with registry["lock"]:
                    job = registry["jobs"].get(job_id)
                    if job is None:
                        return
                    job["completed"] += 1
                    job["included"] = len(included)
                    job["missing"] = len(missing)

        output = io.BytesIO()
        used = set()
        with zipfile.ZipFile(output, "w", zipfile.ZIP_STORED) as archive:
            archive.writestr("Filtered_Personnel_List.pdf", pdf_bytes)
            for name, entry, blob in downloaded:
                safe = re.sub(r"[^\w .()-]", "_", str(name)).strip()[:100] or "Employee"
                extension = str(entry.get("original_filename") or entry.get("storage_path") or "").rsplit(".", 1)[-1].lower()
                if extension not in {"pdf", "docx", "doc"}:
                    extension = "pdf"
                filename = f"Employee_CVs/{safe}.{extension}"
                if filename in used:
                    continue
                used.add(filename)
                archive.writestr(filename, blob)
            archive.writestr("CV_Export_Summary.txt", f"Included CVs: {len(included)}\nMissing or unavailable CVs: {len(missing)}\n\n" + "\n".join(missing))
        with registry["lock"]:
            job = registry["jobs"].get(job_id)
            if job is not None:
                job.update(status="ready", data=output.getvalue(), completed=len(available))
    except Exception as exc:
        with registry["lock"]:
            job = registry["jobs"].get(job_id)
            if job is not None:
                job.update(status="error", error=str(exc))


def _dismiss_cv_job():
    job_id = st.session_state.pop("cv_background_job_id", None)
    if job_id:
        registry = _cv_job_registry()
        with registry["lock"]:
            registry["jobs"].pop(job_id, None)


@st.fragment(run_every="1s")
def show_cv_export_status():
    job_id = st.session_state.get("cv_background_job_id")
    if not job_id:
        return
    registry = _cv_job_registry()
    with registry["lock"]:
        job = dict(registry["jobs"].get(job_id, {}))
    if not job:
        return
    st.markdown("**CV Extraction Status**")
    status = job.get("status")
    if status == "running":
        total = job.get("total", 0)
        completed = job.get("completed", 0)
        percent = completed / total if total else 0
        st.progress(percent, text=f"CV Extraction in Progress — {completed}/{total} CVs ({percent:.0%})")
    elif status == "ready":
        st.success(f"CV Export Ready — {job.get('included', 0)} CV(s) included, {job.get('missing', 0)} missing.")
        st.download_button(
            "Download Completed CV ZIP", data=job["data"],
            file_name=job["filename"], mime="application/zip",
            on_click=_dismiss_cv_job, use_container_width=True,
            key=f"download_background_{job_id}",
        )
    elif status == "error":
        st.error("CV extraction failed: " + job.get("error", "Unknown error"))
        if st.button("Dismiss CV Export Status", key=f"dismiss_{job_id}"):
            _dismiss_cv_job()
            st.rerun()


def _dedupe_key(name, position, project):
    """Build a case-insensitive key used to identify the same staff/project record."""
    def norm(value):
        if value is None or pd.isna(value):
            return ""
        return " ".join(str(value).strip().lower().split())
    return (norm(name), norm(position), norm(project))


def upload_staff_to_supabase(uploaded, parsed_df):
    """Synchronize an uploaded staff file with Supabase.

    Matching key: Name + Position + Project (case-insensitive, whitespace-normalized).

    - New key -> INSERT
    - Existing key with changed engagement/evaluation/status -> UPDATE
    - Existing key with no changes -> SKIP
    - Duplicate key inside the same upload -> SKIP

    The uploaded source file is also stored in Supabase Storage as version history.
    """
    client = get_supabase_client()
    if client is None:
        raise RuntimeError(
            "Supabase is not configured. Check .streamlit/secrets.toml and make sure "
            "it contains your Supabase URL and Key."
        )

    filename = Path(uploaded.name).name
    file_bytes = uploaded.getvalue()
    safe_name = filename.replace(" ", "_")
    timestamp = pd.Timestamp.utcnow().strftime("%Y%m%d_%H%M%S")
    storage_path = f"staff/{timestamp}_{safe_name}"

    suffix = Path(filename).suffix.lower()
    if suffix == ".csv":
        content_type = "text/csv"
    elif suffix == ".xls":
        content_type = "application/vnd.ms-excel"
    else:
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Keep the source file as upload/version history.
    client.storage.from_("ocp-staff-files").upload(
        storage_path,
        file_bytes,
        {"content-type": content_type, "upsert": "false"}
    )

    # Load all current records. Pagination avoids the common 1,000-row API limit.
    existing_lookup = {}
    start = 0
    page_size = 1000
    while True:
        result = (
            client.table("staff_records")
            .select("id,name,position,type_of_engagement,evaluation,status,project,funding,sector,experience,end_of_contract,eligibility,source_file,source_path")
            .range(start, start + page_size - 1)
            .execute()
        )
        batch = result.data or []
        for record in batch:
            key = _dedupe_key(
                record.get("name", ""),
                record.get("position", ""),
                record.get("project", "")
            )
            if key[0]:
                existing_lookup[key] = record
        if len(batch) < page_size:
            break
        start += page_size

    if "Eligibility" not in parsed_df.columns:
        parsed_df["Eligibility"] = ""

    source = parsed_df[[
        "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience", "Overseas Experience", "End of Contract", "Eligibility"
    ]].copy()
    source = source.fillna("").astype(str)

    def norm(value):
        if value is None or pd.isna(value):
            return ""
        return " ".join(str(value).strip().lower().split())

    inserted = 0
    updated = 0
    unchanged = 0
    skipped_upload_duplicates = 0
    seen_in_upload = set()
    uploaded_at = pd.Timestamp.utcnow().isoformat()
    new_records = []

    for _, row in source.iterrows():
        name = str(row["Name"]).strip()
        position = str(row["Position"]).strip()
        engagement = str(row["Type of Engagement"]).strip()
        evaluation = str(row["Evaluation"]).strip()
        status = str(row["Status"]).strip()
        project = str(row["Project"]).strip()

        key = _dedupe_key(name, position, project)
        if not key[0]:
            continue

        # Prevent duplicate rows inside the same workbook/upload.
        if key in seen_in_upload:
            skipped_upload_duplicates += 1
            continue
        seen_in_upload.add(key)

        existing = existing_lookup.get(key)

        if existing is None:
            new_records.append({
                "name": name,
                "position": position,
                "type_of_engagement": engagement,
                "evaluation": evaluation,
                "status": status,
                "project": project,
                "funding": str(row["Funding"]).strip(),
                "sector": str(row["Sector"]).strip(),
                "experience": str(row["Experience"]).strip(),
                "overseas_experience": (float(row["Overseas Experience"]) if str(row["Overseas Experience"]).strip() not in ("", "nan", "None") else None),
                "end_of_contract": parse_contract_date(row["End of Contract"]),
                "eligibility": str(row["Eligibility"]).strip(),
                "source_file": filename,
                "source_path": storage_path,
                "uploaded_at": uploaded_at,
            })
            continue

        # Existing employee/project: compare fields that are allowed to change.
        changes = {}
        if norm(existing.get("type_of_engagement")) != norm(engagement):
            changes["type_of_engagement"] = engagement
        if norm(existing.get("evaluation")) != norm(evaluation):
            changes["evaluation"] = evaluation
        if norm(existing.get("status")) != norm(status):
            changes["status"] = status
        for db_col, source_col in [("funding", "Funding"), ("sector", "Sector"), ("experience", "Experience"), ("eligibility", "Eligibility")]:
            new_value = str(row[source_col]).strip()
            if new_value and norm(existing.get(db_col)) != norm(new_value):
                changes[db_col] = new_value

        # The Excel column is named "Overseas"; normalize_columns maps it to
        # "Overseas Experience". Preserve existing values when the cell is blank.
        overseas_value = str(row["Overseas Experience"]).strip()
        if overseas_value and overseas_value.lower() not in ("nan", "none"):
            try:
                parsed_overseas = float(overseas_value)
                old_overseas = existing.get("overseas_experience")
                if old_overseas is None or float(old_overseas) != parsed_overseas:
                    changes["overseas_experience"] = parsed_overseas
            except (TypeError, ValueError):
                pass

        contract_date = parse_contract_date(row["End of Contract"])
        if contract_date and str(existing.get("end_of_contract") or "")[:10] != contract_date:
            changes["end_of_contract"] = contract_date

        if changes:
            # Record where the latest values came from.
            changes["source_file"] = filename
            changes["source_path"] = storage_path
            changes["uploaded_at"] = uploaded_at

            (
                client.table("staff_records")
                .update(changes)
                .eq("id", existing["id"])
                .execute()
            )
            existing.update(changes)
            updated += 1
        else:
            unchanged += 1

    # Insert genuinely new records in batches.
    batch_size = 500
    for i in range(0, len(new_records), batch_size):
        batch = new_records[i:i + batch_size]
        result = client.table("staff_records").insert(batch).execute()
        inserted += len(batch)

        # Keep the in-memory lookup current during this upload.
        for record in (result.data or []):
            key = _dedupe_key(
                record.get("name", ""),
                record.get("position", ""),
                record.get("project", "")
            )
            if key[0]:
                existing_lookup[key] = record

    return {
        "storage_path": storage_path,
        "uploaded_rows": len(source),
        "added": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "skipped_existing": unchanged,  # backward-compatible key
        "skipped_upload_duplicates": skipped_upload_duplicates,
    }

def fetch_staff_for_editor():
    """Load editable staff rows including the database ID."""
    client = get_supabase_client()
    if client is None:
        return pd.DataFrame(columns=["id", "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project"])

    rows = []
    start = 0
    page_size = 1000
    while True:
        result = (
            client.table("staff_records")
            .select("id,name,position,type_of_engagement,evaluation,status,project,funding,sector,experience,eligibility")
            .order("id")
            .range(start, start + page_size - 1)
            .execute()
        )
        batch = result.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size

    if not rows:
        return pd.DataFrame(columns=["id", "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project"])

    return pd.DataFrame(rows).rename(columns={
        "name": "Name",
        "position": "Position",
        "type_of_engagement": "Type of Engagement",
        "evaluation": "Evaluation",
        "status": "Status",
        "project": "Project",
        "funding": "Funding",
        "sector": "Sector",
        "experience": "Experience",
        "eligibility": "Eligibility",
    })


def save_staff_editor_changes(original_df, edited_df):
    """Update changed rows and insert rows added in the Admin editor."""
    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Supabase is not configured.")

    fields = ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience", "Eligibility"]
    db_fields = {
        "Name": "name",
        "Position": "position",
        "Type of Engagement": "type_of_engagement",
        "Evaluation": "evaluation",
        "Status": "status",
        "Project": "project",
        "Funding": "funding",
        "Sector": "sector",
        "Experience": "experience",
        "Eligibility": "eligibility",
    }

    def clean(v):
        if v is None or pd.isna(v):
            return ""
        return str(v).strip()

    original_by_id = {}
    if original_df is not None and not original_df.empty:
        for _, row in original_df.iterrows():
            if pd.notna(row.get("id")):
                original_by_id[int(row["id"])] = {f: clean(row.get(f, "")) for f in fields}

    updated = 0
    added = 0
    seen_new = set()

    for _, row in edited_df.iterrows():
        values = {f: clean(row.get(f, "")) for f in fields}
        if not values["Name"] and not values["Position"]:
            continue

        row_id = row.get("id")
        payload = {db_fields[f]: values[f] for f in fields}

        if pd.notna(row_id) and str(row_id).strip() not in ("", "nan", "None"):
            rid = int(float(row_id))
            if original_by_id.get(rid) != values:
                client.table("staff_records").update(payload).eq("id", rid).execute()
                updated += 1
        else:
            key = _dedupe_key(values["Name"], values["Position"], values["Project"])
            if key in seen_new:
                continue
            seen_new.add(key)

            exists = (
                client.table("staff_records")
                .select("id")
                .ilike("name", values["Name"])
                .ilike("position", values["Position"])
                .ilike("project", values["Project"])
                .limit(1)
                .execute()
            )
            if exists.data:
                continue

            payload.update({
                "source_file": "Admin manual entry",
                "source_path": "",
                "uploaded_at": pd.Timestamp.utcnow().isoformat(),
            })
            client.table("staff_records").insert(payload).execute()
            added += 1

    return {"updated": updated, "added": added}


@st.dialog("Add & Edit Staff Data", width="large")
def staff_editor_dialog():
    st.caption("Search or filter staff first, then edit the exact record you need. Changes are saved directly to Supabase.")
    try:
        original = fetch_staff_for_editor()
    except Exception as exc:
        st.error(f"Unable to load staff records: {exc}")
        return

    if original.empty:
        st.info("No staff records are available to edit.")
        return

    # ---------------------------------------------------------
    # SEARCH & FILTERS
    # ---------------------------------------------------------
    st.markdown("#### Search & Filter")

    f1, f4, f5 = st.columns([2.0, 1.5, 1.7])

    with f1:
        search_name = st.text_input(
            "Search Name",
            placeholder="Search employee name...",
            key="edit_search_name",
        )

    project_values = sorted(
        x for x in original["Project"].fillna("").astype(str).str.strip().unique().tolist()
        if x
    )
    status_values = sorted(
        x for x in original["Status"].fillna("").astype(str).str.strip().unique().tolist()
        if x
    )
    position_values = sorted(
        x for x in original["Position"].fillna("").astype(str).str.strip().unique().tolist()
        if x
    )
    evaluation_values = sorted(
        x for x in original["Evaluation"].fillna("").astype(str).str.strip().unique().tolist()
        if x
    )

    selected_project = "All Projects"
    selected_status = "All Status"

    with f4:
        selected_position = st.selectbox(
            "Current Position",
            ["All Positions"] + position_values,
            key="edit_filter_position",
        )

    with f5:
        selected_evaluation = st.multiselect(
            "Evaluation",
            ["Exceptional", "Exceed Requirements"],
            key="edit_filter_evaluation",
        )

    filtered = original.copy()

    if search_name.strip():
        filtered = filtered[
            filtered["Name"].fillna("").astype(str).str.contains(
                search_name.strip(), case=False, na=False, regex=False
            )
        ]

    if selected_project != "All Projects":
        filtered = filtered[
            filtered["Project"].fillna("").astype(str).str.strip() == selected_project
        ]

    if selected_status != "All Status":
        filtered = filtered[
            filtered["Status"].fillna("").astype(str).str.strip() == selected_status
        ]

    if selected_position != "All Positions":
        filtered = filtered[
            filtered["Position"].fillna("").astype(str).str.strip() == selected_position
        ]

    if selected_evaluation:
        filtered = filtered[filtered["Evaluation"].map(normalize_evaluation).isin(selected_evaluation)]

    st.caption(f"Showing {len(filtered):,} of {len(original):,} staff records")

    if filtered.empty:
        st.warning("No staff records match the current search and filters.")
        return

    editor_source = filtered.copy()
    if "id" not in editor_source.columns:
        editor_source.insert(0, "id", pd.NA)

    # The editor key changes with the active filters so Streamlit always shows
    # the correct filtered rows instead of retaining rows from a previous filter.
    editor_key = (
        f"admin_staff_editor::{search_name.strip().lower()}::"
        f"{selected_project}::{selected_status}::{selected_position}::{selected_evaluation}"
    )

    edited = st.data_editor(
        editor_source,
        key=editor_key,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        disabled=["id"],
        column_config={
            "id": st.column_config.NumberColumn("ID", help="Supabase record ID", width="small"),
            "Name": st.column_config.TextColumn("Name", required=True),
            "Position": st.column_config.TextColumn("Current Position"),
            "Type of Engagement": st.column_config.TextColumn("Type of Engagement"),
            "Evaluation": st.column_config.TextColumn("Evaluation"),
            "Status": st.column_config.TextColumn("Status"),
            "Project": st.column_config.TextColumn("Project"),
            "Funding": st.column_config.TextColumn("Funding"),
            "Sector": st.column_config.TextColumn("Sector"),
            "Experience": st.column_config.TextColumn("Total Year Experience"),
            "Eligibility": st.column_config.TextColumn("Eligibility"),
        },
        height=520,
    )

    st.caption(
        "Edit the filtered records above, or use the blank row at the bottom to add a candidate. "
        "Only the records currently shown are evaluated when you save."
    )

    if st.button("Save Staff Changes", type="primary", use_container_width=True):
        try:
            with st.spinner("Saving changes to Supabase..."):
                # Pass only the filtered originals. Hidden records are never overwritten.
                result = save_staff_editor_changes(filtered, edited)
            if result["added"] == 0 and result["updated"] == 0:
                st.info("No changes were detected.")
            else:
                st.success(
                    f"Saved successfully: {result['added']:,} new record(s) added and "
                    f"{result['updated']:,} record(s) updated."
                )
                time.sleep(1.0)
                st.rerun()
        except Exception as exc:
            st.error(f"Unable to save changes: {exc}")


def project_grouped_rows(df):
    """Sort projects alphabetically, then sort employees by name within each project."""
    result = df.copy()
    result["Current Project"] = result["Current Project"].fillna("—").astype(str).str.strip()
    result.loc[result["Current Project"].isin(["", "nan", "None"]), "Current Project"] = "—"
    result["_project_sort"] = result["Current Project"].map(str.casefold)
    result["_name_sort"] = result["Name"].fillna("").astype(str).map(str.casefold)
    result = result.sort_values(["_project_sort", "_name_sort"], kind="stable")
    return [(project, group.drop(columns=["_project_sort", "_name_sort"]))
            for project, group in result.groupby("Current Project", sort=False)]


def make_pdf(df, funding, position, evaluations, current_project, group_by_project=True):
    """Export filtered staff in a single PDF, separated and sorted by current project."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    styles["Title"].alignment = TA_CENTER
    story = [
        Paragraph("Oriental Consultants Philippines Inc.", styles["Title"]),
        Paragraph("Personnel List by Current Project" if group_by_project else "Personnel List", styles["Heading2"]), Spacer(1, 8),
        Paragraph(f"<b>Selected Project(s):</b> {escape(str(current_project))}", styles["BodyText"]),
        Spacer(1, 5),
        Paragraph(f"<b>Funding:</b> {escape(str(funding))} &nbsp; | &nbsp; <b>Current Position:</b> {escape(str(position))} &nbsp; | &nbsp; "
                  f"<b>Evaluation:</b> {escape(', '.join(evaluations) or 'All')} &nbsp; | &nbsp; <b>Total:</b> {len(df):,}",
                  styles["BodyText"]), Spacer(1, 12)
    ]
    cols = ["Name", "Current Position", "Current Project", "Eligibility", "Sector", "Funding", "Total Year Experience", "Overseas Experience", "Evaluation", "End of Contract"]
    widths = [86, 94, 64, 75, 57, 44, 59, 59, 76, 69]
    if group_by_project:
        pdf_groups = project_grouped_rows(df)
    else:
        pdf_groups = [(None, df.sort_values("Name", kind="stable"))]
    for project, group in pdf_groups:
        if project is not None:
            story.append(Paragraph(f"{escape(project)} — {len(group):,} employee(s)", styles["Heading3"]))
            story.append(Spacer(1, 5))
        data = [[Paragraph(f"<b>{escape(c)}</b>", styles["BodyText"]) for c in cols]]
        for _, record in group.iterrows():
            data.append([Paragraph(escape(str(record.get(c, "") if pd.notna(record.get(c, "")) else "")), styles["BodyText"]) for c in cols])
        table = Table(data, repeatRows=1, colWidths=widths, hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF5")),
            ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D5DAE3")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([table, Spacer(1, 14)])
    doc.build(story)
    return buffer.getvalue()


def normalize_evaluation(value):
    value = str(value or "").strip()
    if value.casefold() in {"excellent", "exceptional"}:
        return "Exceptional"
    if value.casefold() in {"exceed requirements", "exceeds requirements"}:
        return "Exceed Requirements"
    return value

# Login loading transition shown as a floating modal over the login page
if st.session_state.login_loading and not st.session_state.logged_in:
    # Keep the login page visually present behind the modal.
    st.markdown(f"""
    <div class="login-wrap">
      <img src="{LOGO_URI}" alt="OC Philippines" style="width:110px;height:110px;object-fit:contain;margin-bottom:8px;" />
      <div class="login-title">Oriental Consultants Philippines Inc.</div>
      <div class="login-sub">Employee Database Monitoring</div>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_loading_background"):
        st.text_input("Username", value="admin", disabled=True)
        st.text_input("Password", value="••••••••", disabled=True)
        st.form_submit_button("Log In", use_container_width=True, disabled=True)

    st.markdown(f"""
    <div class="login-modal-backdrop"></div>
    <div class="login-modal-card">
        <img src="{LOGO_URI}" alt="OC Philippines" style="width:74px;height:74px;object-fit:contain;margin:0 auto 8px;display:block;" />
        <div class="login-modal-spinner"></div>
        <div class="login-modal-title">Signing you in...</div>
        <div class="login-modal-text">Preparing your Personnel Selection Portal</div>
    </div>
    """, unsafe_allow_html=True)

    time.sleep(1.15)
    st.session_state.logged_in = True
    st.session_state.login_loading = False
    st.rerun()

# Login
if not st.session_state.logged_in:
    st.markdown(f"""
    <div class="login-wrap">
      <img src="{LOGO_URI}" alt="OC Philippines" style="width:110px;height:110px;object-fit:contain;margin-bottom:8px;" />
      <div class="login-title">Oriental Consultants Philippines Inc.</div>
      <div class="login-sub">Employee Database Monitoring</div>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
        go = st.form_submit_button("Log In", type="primary", use_container_width=True)
        if go:
            if PASSWORD and username == USERNAME and password == PASSWORD:
                st.session_state.login_loading = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")
    st.stop()



# ============================================================
# CURRENT STAFF DATABASE - LOADED FROM SUPABASE
# ============================================================

if "personnel_once_df" not in st.session_state:
    with st.spinner("Loading personnel records for this session..."):
        st.session_state["personnel_once_df"] = fetch_staff_from_supabase()
active_df = st.session_state["personnel_once_df"].copy()


# Classic OCP header layout
st.markdown(f"""
<div class="classic-ocp-header">
    <div class="classic-ocp-brand">
        <div class="classic-ocp-logo" style="background:transparent;padding:0;display:flex;align-items:center;justify-content:center;">
            <img src="{LOGO_URI}" alt="OC Philippines" style="width:68px;height:68px;object-fit:contain;" />
        </div>
        <div>
            <div class="classic-ocp-title">Oriental Consultants Philippines Inc.</div>
            <div class="classic-ocp-subtitle">Employee Database Monitoring</div>
        </div>
    </div>
    <div class="classic-portal-pill">Personnel Selection Portal</div>
</div>
""", unsafe_allow_html=True)

# Admin menu - upload staff file and logout.
_admin_space, _admin_col = st.columns([5, 1])
with _admin_col:
    with st.popover("Admin  ▾", use_container_width=True):
        st.markdown("**Staff Database**")
        admin_category = st.radio(
            "Admin Category",
            ["Upload Staff Database", "Add & Edit Staff Data", "Upload & Manage CVs"],
            horizontal=True,
            label_visibility="collapsed",
            key="admin_category"
        )

        if admin_category == "Upload & Manage CVs":
            st.caption("Upload multiple PDF or Word CVs (.pdf, .docx, .doc). Names are matched to staff records; ambiguous matches are skipped.")
            cv_files = st.file_uploader("Upload employee CVs", type=["pdf", "docx", "doc"],
                                        accept_multiple_files=True, key="cv_upload")
            if cv_files and st.button("Save CVs to Supabase", use_container_width=True, type="primary"):
                with st.spinner("Matching and uploading CVs..."):
                    try:
                        matched, unmatched, failed = cv_upload_batch(cv_files)
                        st.success(f"{len(matched)} matched CV(s) uploaded.")
                        st.info(f"Processed {len(matched) + len(unmatched) + len(failed)} file(s): "
                                f"{len(matched)} uploaded, {len(unmatched)} unmatched/ambiguous, "
                                f"{len(failed)} upload error(s).")
                        if unmatched:
                            st.warning(f"{len(unmatched)} CV(s) need review. Showing the first 15 below.")
                            st.text("\n".join(unmatched[:15]))
                        if failed:
                            st.error(f"{len(failed)} upload error(s). Showing the first 15 below.")
                            st.text("\n".join(failed[:15]))
                        if unmatched or failed:
                            import csv
                            report = io.StringIO()
                            writer = csv.writer(report)
                            writer.writerow(["Status", "Filename / details"])
                            writer.writerows(("Unmatched or ambiguous", v) for v in unmatched)
                            writer.writerows(("Upload failed", v) for v in failed)
                            st.session_state["cv_import_issues_csv"] = report.getvalue().encode("utf-8-sig")
                        else:
                            st.session_state.pop("cv_import_issues_csv", None)
                    except Exception as exc:
                        st.error(f"CV upload failed: {exc}. Check SQL setup and private Storage bucket.")
            if st.session_state.get("cv_import_issues_csv"):
                st.download_button("Download all unmatched / failed CVs (CSV)",
                    st.session_state["cv_import_issues_csv"],
                    file_name="OCP_CV_Import_Issues.csv", mime="text/csv",
                    use_container_width=True)
            st.divider()
        if admin_category == "Add & Edit Staff Data":
            st.caption("Add new staff or edit existing staff information directly in Supabase for evaluation.")
            if st.button("Open Add & Edit Staff Data", type="primary", use_container_width=True):
                staff_editor_dialog()
            st.divider()
        elif admin_category == "Upload Staff Database":
            st.caption("Upload an Excel or CSV file to Supabase. Existing staff are skipped and only new records are added.")

        uploaded = None
        if admin_category == "Upload Staff Database":
            uploaded = st.file_uploader(
            "Upload Staff Database",
            type=["xlsx", "xls", "csv"],
            key="staff_database_upload",
            help="The original file is stored in Supabase Storage and its records are saved in the Supabase database."
        )

        if uploaded is not None:
            try:
                preview = clean_staff(load_upload(uploaded))
                if preview.empty:
                    st.error("No usable staff records were found in this file.")
                else:
                    st.info(f"Ready to upload: {uploaded.name}")
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Records", f"{len(preview):,}")
                    m2.metric("Projects", f"{preview['Project'].replace('', pd.NA).dropna().nunique():,}")
                    m3.metric("Statuses", f"{preview['Status'].replace('', pd.NA).dropna().nunique():,}")

                    if st.button("Upload File to Supabase", type="primary", use_container_width=True):
                        with st.spinner("Uploading file and saving records to Supabase..."):
                            try:
                                result = upload_staff_to_supabase(uploaded, preview)
                                st.session_state.uploaded_name = uploaded.name
                                st.session_state.uploaded_df = None
                                st.success(
                                    f"Database synchronized successfully — "
                                    f"{result['added']:,} new record(s) added, "
                                    f"{result['updated']:,} existing record(s) updated, and "
                                    f"{result['unchanged']:,} unchanged record(s) skipped."
                                )
                                if result["skipped_upload_duplicates"]:
                                    st.caption(
                                        f"{result['skipped_upload_duplicates']:,} duplicate row(s) inside the uploaded file were also skipped."
                                    )
                                st.session_state.pop("personnel_once_df", None)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Supabase upload failed: {e}")
            except Exception as e:
                st.error(f"Unable to read file: {e}")

        if st.session_state.uploaded_name:
            st.divider()
            st.caption(f"Latest uploaded file: **{st.session_state.uploaded_name}**")

        st.divider()
        if st.button("Log Out", key="classic_logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.login_loading = False
            st.rerun()

if active_df.empty:
    st.info("No staff records are stored in Supabase. Open **Admin ▾** and upload an Excel or CSV file.")


filtered = active_df.copy()
for col in ["Name", "Position", "Sector", "Experience", "Overseas Experience", "Funding", "Project", "Evaluation", "Status", "End of Contract", "Eligibility"]:
    if col not in filtered.columns:
        filtered[col] = ""
    filtered[col] = filtered[col].fillna("").astype(str).str.strip()

# Funding is a separate database field. When it has not been populated yet,
# show legacy Project values as a temporary fallback, without modifying them.
filtered["Funding Display"] = filtered["Funding"].where(
    filtered["Funding"].ne(""), filtered["Project"]
)
filtered["Evaluation Display"] = filtered["Evaluation"].map(normalize_evaluation)

def position_family(value):
    """Normalize spelling, punctuation and grades for *filtering only*."""
    value = re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    if value in {"", "nan", "none", "null", "—"}:
        return ""
    value = re.sub(r"\s*&\s*", " and ", value)
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    corrections = {
        "adminstrator": "administrator", "administrater": "administrator",
        "administator": "administrator", "adminitrator": "administrator",
        "asistant": "assistant", "assitant": "assistant",
        "assisstant": "assistant", "assistent": "assistant",
        "adminstrative": "administrative", "administrativ": "administrative",
        "coordiantor": "coordinator", "coodinator": "coordinator",
        "compilationn": "compilation", "captian": "captain",
        "enginer": "engineer", "engneer": "engineer",
        "mananger": "manager", "manger": "manager",
        "architecht": "architect", "architech": "architect",
        "acountant": "accountant", "accoutant": "accountant",
    }
    value = " ".join(corrections.get(w, w) for w in value.split())
    value = re.sub(r"\s+(?:level|grade)\s*\d+\s*$", "", value)
    value = re.sub(r"\s+\d+\s*$", "", value)
    value = re.sub(r"\s+for\s+(?:cp\s*\d+|project\b).*$", "", value)
    value = re.sub(r"^(bim captain)\s+(?:revit|autocad).*$", r"\1", value)
    return value.strip()


def position_label(key):
    acronyms = {"bim", "cad", "mep", "qa", "qc", "it", "hr", "gis", "hse", "hvac"}
    return " ".join(w.upper() if w in acronyms else w.capitalize() for w in key.split())


def build_position_groups(position_values):
    """Deduplicate across the entire staff dataset, not just a typed example.

    Conservative fuzzy matching fixes near-identical typos, but does not
    collapse distinct roles such as BIM Electrical vs BIM Mechanical.
    """
    from difflib import SequenceMatcher
    keys = sorted({position_family(v) for v in position_values if position_family(v)},
                  key=lambda k: (len(k), k))
    parent = {k: k for k in keys}

    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    # Restrict fuzzy matches to similar word counts and matching key terms.
    # Avoid generic substring matching, which merges unrelated occupations.
    for i, left in enumerate(keys):
        lw = left.split()
        for right in keys[i + 1:]:
            rw = right.split()
            if abs(len(left) - len(right)) > 3 or len(lw) != len(rw):
                continue
            if lw[0][0] != rw[0][0]:
                continue
            if len(lw) > 1 and lw[-1] != rw[-1] and SequenceMatcher(None, lw[-1], rw[-1]).ratio() < .88:
                continue
            similarity = SequenceMatcher(None, left, right).ratio()
            if similarity >= .94:
                parent[root(right)] = root(left)

    groups = {}
    for key in keys:
        groups.setdefault(root(key), []).append(key)
    canonical = {}
    for variants in groups.values():
        # Favor cleanest/shortest spelling for the visible label.
        chosen = sorted(variants, key=lambda v: (len(v), v))[0]
        for v in variants:
            canonical[v] = chosen
    return canonical


def experience_years(value):
    """Read numeric Excel/Supabase values, including '15 years' or '20+'."""
    match = re.search(r"\d+(?:\.\d+)?", str(value or ""))
    return float(match.group()) if match else None


# Limit the visible dropdown list height without limiting searchable choices.
st.markdown("""
<style>
/* Match the Sector selector to Funding and Position (same soft-gray field). */
div[data-testid="stSelectbox"].st-key-sector_dropdown [data-baseweb="select"] > div,
.st-key-sector_dropdown div[data-baseweb="select"] > div {
    background-color:#f0f3f7 !important;
    border:1px solid #e5eaf0 !important;
    border-radius:10px !important;
    min-height:49px !important;
    box-shadow:none !important;
}
.st-key-sector_dropdown div[data-baseweb="select"] > div:hover {
    background-color:#edf1f6 !important;
    border-color:#dce3ec !important;
}
.st-key-sector_dropdown div[data-baseweb="select"] input,
.st-key-sector_dropdown div[data-baseweb="select"] [data-testid="stMarkdownContainer"] {
    text-align:left !important;
}
/* Streamlit selectbox menu: compact, scrollable list */
div[data-baseweb="popover"] div[data-baseweb="menu"] {
    max-height: 220px !important;
    overflow-y: auto !important;
}
</style>
""", unsafe_allow_html=True)

position_group_map = build_position_groups(filtered["Position"].unique())
filtered["Position Group"] = filtered["Position"].map(
    lambda v: position_group_map.get(position_family(v), "")
)

def sector_parts(value):
    """Interpret existing Sector text as Main > Child; no schema change."""
    return [part.strip() for part in str(value or "").split(">") if part.strip()]


def sector_matches(value, selected):
    """Parent includes descendants; child matches its exact hierarchical path."""
    if not selected:
        return True
    parts = sector_parts(value)
    selected_parts = sector_parts(selected)
    return [p.casefold() for p in parts[:len(selected_parts)]] == [p.casefold() for p in selected_parts]


# Target Position is computed from the existing Position field; no database migration.
# Keep the matching rules explicit so they can be refined for OCP job titles.
import re as _target_re

TARGET_POSITION_CATEGORIES = [
    "Structure",
    "Quality Assurance / Quality Control",
    "QS (Quantity Surveyor)",
    "BIM",
    "Accounting",
]

def target_position_matches(position_text, target):
    if not target or target == "All Target Positions":
        return True
    name = _target_re.sub(r"[^a-z0-9]+", " ", str(position_text or "").casefold()).strip()
    def contains(pattern):
        return bool(_target_re.search(pattern, name))
    if target == "Structure":
        return contains(r"\b(structur(?:e|al|es)|bridge|viaduct|seismic|foundation|geotechnical|geotech|steel design|concrete design)\b")
    if target == "Quality Assurance / Quality Control":
        return contains(r"\b(qa|qc|qa qc|quality assurance|quality control|quality engineer|quality inspector|material(?:s)? engineer|material(?:s)? inspector|inspection engineer)\b")
    if target == "QS (Quantity Surveyor)":
        return contains(r"\b(qs|quantity survey(?:or|ing)|cost engineer|cost estimator|estimat(?:or|ing)|bill of quantities|boq|commercial engineer)\b")
    if target == "BIM":
        return contains(r"\b(bim|building information model(?:ing|ling)?|revit|bim modeler|bim modeller|bim coordinator|bim manager)\b")
    if target == "Accounting":
        return contains(r"\b(account(?:ant|ants|ing|s)?|bookkeep(?:er|ing)|finance|financial|payroll|auditor|audit|taxation|tax|treasury|billing|accounts payable|accounts receivable)\b")
    return False

c1, c2, c3, c_target = st.columns([1.0, 1.05, 1.05, 1.3], gap="small")
with c1:
    funding_options = sorted(x for x in filtered["Funding Display"].unique() if x)
    funding = st.selectbox("Funding", ["All Funding"] + funding_options)
with c2:
    # One expandable sector control, populated dynamically from Supabase data.
    # Supports values like "Railway > Civil Structural" without a new column.
    sector_paths = {}
    for raw_sector in filtered["Sector"].unique():
        parts = sector_parts(raw_sector)
        if parts and parts[0].casefold() not in {"nan", "none", "—"}:
            main = parts[0]
            entry = sector_paths.setdefault(main.casefold(), {"name": main, "children": {}})
            if len(parts) > 1:
                full_path = " > ".join(parts)
                entry["children"].setdefault(full_path.casefold(), full_path)

    # Native selectbox preserves the original three-column filter layout.
    # Selecting a main sector opens its related categories in this SAME dropdown.
    if "selected_sector_path" not in st.session_state:
        st.session_state.selected_sector_path = ""
    if "sector_expanded_main" not in st.session_state:
        st.session_state.sector_expanded_main = ""

    expanded_main = st.session_state.sector_expanded_main
    options = ["All Sectors"]
    if expanded_main and expanded_main.casefold() in sector_paths:
        group = sector_paths[expanded_main.casefold()]
        main_name = group["name"]
        options += ["← All main sectors", main_name]
        options += sorted(group["children"].values(), key=str.casefold)
    else:
        st.session_state.sector_expanded_main = ""
        options += [v["name"] for v in sorted(sector_paths.values(), key=lambda g: g["name"].casefold())]

    selected_path = st.session_state.selected_sector_path
    current_option = selected_path if selected_path in options else "All Sectors"
    def on_sector_change():
        choice = st.session_state.sector_dropdown
        if choice == "← All main sectors":
            st.session_state.sector_expanded_main = ""
            st.session_state.selected_sector_path = ""
        elif choice == "All Sectors":
            st.session_state.sector_expanded_main = ""
            st.session_state.selected_sector_path = ""
        elif choice.casefold() in sector_paths:
            st.session_state.sector_expanded_main = choice
            st.session_state.selected_sector_path = choice
        else:
            st.session_state.selected_sector_path = choice

    # When the option list changes, sync the widget key before constructing it.
    if st.session_state.get("sector_dropdown") not in options:
        st.session_state.sector_dropdown = current_option
    sector = st.session_state.selected_sector_path
    st.selectbox(
        "Sector", options, key="sector_dropdown", on_change=on_sector_change,
        help="Select a main sector to reveal its categories. Select a full path to filter that category; selecting the main sector includes all related categories.",
    )
    sector = st.session_state.selected_sector_path

with c3:
    position_keys = sorted((x for x in filtered["Position Group"].unique() if x), key=str.casefold)
    position_options = {position_label(key): key for key in position_keys}
    position = st.selectbox("Current Position", ["All Positions"] + list(position_options),
                            help="Similar positions are grouped across spelling, capitalization, &/and, punctuation, and numbered levels. Original employee positions are preserved.")

with c_target:
    target_positions = st.multiselect(
        "Target Position",
        TARGET_POSITION_CATEGORIES,
        default=[],
        placeholder="All Target Positions",
        help="Select one or more target categories. Matching any selected category includes the employee. Leave empty to show all positions.",
        key="target_position_filter",
    )

c4, c5, c6 = st.columns(3)
with c4:
    st.markdown("<div class='experience-filter-heading'>Years of Experience</div>", unsafe_allow_html=True)
    # All controls share one compact row. Sliders render in a floating popover,
    # so toggling either option never increases the filter row height.
    with st.container(key="experience_filter_panel"):
        settings_col, total_col, overseas_col = st.columns([1.45, 1.1, 1.25], gap="small", vertical_alignment="center")
        with settings_col:
            with st.popover("Years of Experience", use_container_width=True):
                st.markdown("<span class='ocp-experience-popover-marker'></span>", unsafe_allow_html=True)
                st.markdown("**Experience requirements**")
                if st.session_state.get("filter_total_exp", False):
                    st.slider("Total Experience", 0, 40, 0, 1, key="experience_total_min")
                if st.session_state.get("filter_overseas_exp", False):
                    st.slider("Overseas Experience", 0, 40, 0, 1, key="experience_overseas_min")
                if not (st.session_state.get("filter_total_exp", False) or st.session_state.get("filter_overseas_exp", False)):
                    st.caption("Select Total or Overseas Experience to enable its slider.")
        with total_col:
            filter_total = st.checkbox("Total Experience", value=False, key="filter_total_exp")
        with overseas_col:
            filter_overseas = st.checkbox("Overseas Experience", value=False, key="filter_overseas_exp")
    experience_min = st.session_state.get("experience_total_min", 0) if filter_total else 0
    overseas_min = st.session_state.get("experience_overseas_min", 0) if filter_overseas else 0

with c5:
    evaluations = st.multiselect(
        "Evaluation",
        options=["Exceptional", "Exceed Requirements"],
        default=[],
        help="Select either or both categories. Leave empty to show all evaluations.",
    )

with c6:
    # Read current projects from the existing Supabase `project` field.
    # Empty project values are omitted from the dropdown.
    project_options = sorted(
        (x for x in filtered["Project"].unique() if x and x != "—"),
        key=str.casefold,
    )
    selected_projects = st.multiselect(
        "Current Project",
        options=project_options,
        default=[],
        placeholder="All Projects",
        help="Select one or more projects. Leave empty to show all projects.",
        key="current_project_multiselect",
    )
    current_project = ", ".join(selected_projects) if selected_projects else "All Projects"

# Default to active staff only. The toggle includes inactive/other-status
# records without changing any stored Supabase status values.
show_inactive_staff = st.toggle(
    "Show inactive staff",
    value=False,
    help="Turn ON to include inactive staff and employees with other statuses in the results. Turn OFF to show Active staff only (default). This does not change any employee status in Supabase.",
    key="show_inactive_staff",
)
if not show_inactive_staff:
    filtered = filtered[
        filtered["Status"].fillna("").astype(str).str.strip().str.casefold().eq("active")
    ]

if funding != "All Funding":
    filtered = filtered[filtered["Funding Display"].eq(funding)]
if sector:
    filtered = filtered[filtered["Sector"].map(lambda value: sector_matches(value, sector))]
if position != "All Positions":
    filtered = filtered[filtered["Position Group"].eq(position_options[position])]
if target_positions:
    filtered = filtered[
        filtered["Position"].map(
            lambda value: any(target_position_matches(value, target) for target in target_positions)
        )
    ]
if experience_min > 0:
    years = filtered["Experience"].map(experience_years)
    filtered = filtered[years.ge(experience_min)]
if filter_overseas and overseas_min > 0:
    overseas_years = filtered["Overseas Experience"].map(experience_years)
    filtered = filtered[overseas_years.ge(overseas_min)]
if evaluations:
    filtered = filtered[filtered["Evaluation Display"].isin(evaluations)]
if selected_projects:
    filtered = filtered[filtered["Project"].isin(selected_projects)]

display_df = filtered[["Name", "Position", "Project", "Eligibility", "Sector", "Funding Display", "Experience", "Overseas Experience", "Evaluation Display", "End of Contract"]].copy()
display_df = display_df.rename(columns={
    "Project": "Current Project", "Funding Display": "Funding", "Experience": "Total Year Experience", "Evaluation Display": "Evaluation"
})
for col in display_df.columns:
    display_df[col] = display_df[col].replace({"": "—", "nan": "—", "None": "—"})
# Format dates for display/export only; Supabase continues storing ISO DATE values.
def format_contract_date(value):
    if value is None or str(value).strip().lower() in ("", "—", "nan", "none", "nat"):
        return "—"
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return "—"
    return f"{parsed.strftime('%B')} {parsed.day}, {parsed.year}"


display_df["End of Contract"] = display_df["End of Contract"].map(format_contract_date)
def format_personnel_name(value):
    """Uppercase surname, title-case given names; preserve missing names."""
    import re
    if pd.isna(value) or not str(value).strip() or str(value).strip() == "—":
        return "—"
    name = re.sub(r"\s+", " ", str(value)).strip()
    if "," not in name:
        return name.title()
    surname, given = name.split(",", 1)
    return f"{surname.strip().upper()}, {given.strip().title()}" if given.strip() else surname.strip().upper()


display_df["Name"] = display_df["Name"].map(format_personnel_name)

display_df = display_df.rename(columns={"Position": "Current Position"})
display_df = display_df.sort_values("Name", kind="stable")

r1, r2 = st.columns([4, 1.25])
with r1:
    st.markdown(f'<div class="section-title" style="margin-top:8px">{len(filtered):,} {"Staff Found" if show_inactive_staff else "Active Staff Found"}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div style="display:flex;align-items:center;gap:7px;margin-top:2px;color:#8a8e98;font-size:0.83rem;">'
        f'<span>Current Project: {escape(str(current_project))}</span>'
        '<span title="Click a blue employee name to open the matching CV. Names without uploaded CVs remain plain text." '
        'aria-label="CV viewing help" style="display:inline-flex;align-items:center;justify-content:center;'
        'width:15px;height:15px;border:1px solid #8a8e98;border-radius:50%;font-size:11px;'
        'font-weight:600;cursor:help;">?</span></div>',
        unsafe_allow_html=True,
    )
with r2:
    if not filtered.empty:
        pdf = make_pdf(display_df, funding, position, evaluations, current_project)
        if st.button("Download Filtered PDF", use_container_width=True, key="export_filtered_staff"):
            st.session_state["open_cv_export"] = True

@st.dialog("Export Filtered Personnel", width="large")
def cv_export_dialog():
    # The project selector applies only to printing/exporting, not the main table filters.
    all_rows = display_df.reset_index(drop=True).copy()
    all_groups = project_grouped_rows(all_rows)
    project_names = [project for project, _ in all_groups]
    selected_export_projects = st.multiselect(
        "Select projects to print / download",
        options=project_names,
        default=[],
        placeholder="All Projects (no project grouping)",
        key="cv_export_project_choices",
        help="Select two or more projects. Leave empty to include all filtered employees in one alphabetical table without project sections.",
    )
    all_projects_mode = not selected_export_projects
    if all_projects_mode:
        export_rows = all_rows.copy()
        st.caption("All Projects · no project grouping · employees sorted alphabetically")
    else:
        export_rows = all_rows[all_rows["Current Project"].isin(selected_export_projects)].copy()
        st.caption(f"{len(selected_export_projects)} project(s) selected")
    export_rows = export_rows.sort_values("Name", kind="stable").reset_index(drop=True)
    st.write(f"**{len(export_rows):,} employee(s) selected**")

    if all_projects_mode:
        # All Projects is a single ungrouped alphabetical table.
        st.dataframe(
            export_rows,
            use_container_width=True,
            hide_index=True,
            height=min(560, max(110, 35 * (len(export_rows) + 1))),
        )
    else:
        # Multiple selected projects are previewed in separate project sections.
        for project_name, project_staff in project_grouped_rows(export_rows):
            st.markdown(f"**{project_name} — {len(project_staff):,} employee(s)**")
            st.dataframe(
                project_staff.reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
                height=min(560, max(110, 35 * (len(project_staff) + 1))),
            )

    # CV metadata is only needed if the user opts into a ZIP; it is never shown as a column.
    metadata = {}
    cv_lookup_error = None
    try:
        metadata = cv_metadata_for_names(export_rows["Name"].tolist())
    except Exception as exc:
        cv_lookup_error = str(exc)
    available_count = sum(cv_name_key(name) in metadata for name in export_rows["Name"])
    if cv_lookup_error:
        st.warning("CV availability could not be checked. The personnel PDF can still be downloaded.")
    include_cvs = st.checkbox(
        "Include matching employee CVs (ZIP)",
        value=False,
        disabled=bool(cv_lookup_error) or available_count == 0,
        key="export_include_matching_cvs",
    )

    export_label = "All Projects" if all_projects_mode else ", ".join(selected_export_projects)
    pdf_bytes = make_pdf(
        export_rows, funding, position, evaluations,
        export_label, group_by_project=not all_projects_mode,
    )
    safe_project = "All_Projects" if all_projects_mode else "_".join(
        re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") for name in selected_export_projects
    )[:110]
    if not include_cvs:
        st.download_button(
            "Download Personnel PDF", pdf_bytes, f"OCP_Personnel_{safe_project}.pdf",
            mime="application/pdf", use_container_width=True,
        )
    else:
        active_id = st.session_state.get("cv_background_job_id")
        registry = _cv_job_registry()
        with registry["lock"]:
            active_job = registry["jobs"].get(active_id, {}) if active_id else {}
        if active_job.get("status") in {"running", "ready"}:
            st.info("CV export is being prepared or is ready. Check the CV Extraction Status below the export button.")
        elif st.button("Prepare ZIP with CVs", use_container_width=True):
            try:
                url, key = _read_supabase_secrets()
                if not url or not key:
                    raise ValueError("Supabase configuration is missing")
                job_id = uuid.uuid4().hex
                filename = f"OCP_Personnel_{safe_project}_CVs.zip"
                with registry["lock"]:
                    registry["jobs"][job_id] = {
                        "status": "running", "total": 0, "completed": 0,
                        "included": 0, "missing": 0, "filename": filename,
                    }
                st.session_state["cv_background_job_id"] = job_id
                worker = threading.Thread(
                    target=_run_cv_export_job,
                    args=(job_id, url, key, pdf_bytes, export_rows["Name"].tolist(), dict(metadata)),
                    daemon=True,
                )
                worker.start()
                st.info("CV extraction started. You can close this modal and monitor progress below the export button.")
            except Exception as exc:
                st.error(f"Unable to start CV extraction: {exc}")

if st.session_state.pop("open_cv_export", False):
    st.session_state.pop("cv_export_zip", None)
    cv_export_dialog()

# Status stays on the main page, directly below Download Filtered PDF.
show_cv_export_status()

# Display the employee name as the CV link, without a separate CV column.
# Render an HTML table so linked and unlinked names can share the same column.
from html import escape as html_escape

table_df = display_df.copy()
# Fetch CV metadata and signed links only once per Streamlit user session.
# Filters reuse this snapshot; uploading CVs invalidates it explicitly.
if "cv_once_metadata" not in st.session_state:
    with st.spinner("Loading CV links for this session..."):
        try:
            all_names = tuple(sorted(set(active_df["Name"].dropna().astype(str))))
            st.session_state["cv_once_metadata"] = cv_metadata_for_names(all_names)
        except Exception:
            st.session_state["cv_once_metadata"] = {}
if "cv_once_urls" not in st.session_state:
    with st.spinner("Preparing CV links once..."):
        links = {}
        for key, item in st.session_state["cv_once_metadata"].items():
            try:
                links[key] = cv_signed_link(item["storage_path"])
            except Exception:
                continue
        st.session_state["cv_once_urls"] = links
cv_urls = st.session_state["cv_once_urls"]

# Compact widths preserve all personnel columns on a standard desktop screen.
column_widths = {
    "Name": "16%", "Current Position": "16%", "Current Project": "8%",
    "Eligibility": "10%", "Sector": "8%", "Funding": "6%", "Total Year Experience": "9%",
    "Overseas Experience": "9%", "Evaluation": "10%", "End of Contract": "8%",
}
visible_cols = list(table_df.columns)
headers = "".join(
    f'<th style="width:{column_widths.get(c, "auto")}">{html_escape(str(c))}</th>'
    for c in visible_cols
)
rows_html = []
for _, record in table_df.iterrows():
    cells = []
    for col in visible_cols:
        value = record[col]
        label = "—" if pd.isna(value) or str(value).strip() == "" else str(value)
        content = html_escape(label)
        if col == "Name":
            url = cv_urls.get(cv_name_key(label), "")
            if url and url.startswith(("https://", "http://")):
                content = (
                    f'<a href="{html_escape(url, quote=True)}" target="_blank" '
                    f'rel="noopener noreferrer" title="Open CV for {html_escape(label, quote=True)}">'
                    f'{content} <span aria-hidden="true">↗</span></a>'
                )
        cells.append(f"<td>{content}</td>")
    rows_html.append("<tr>" + "".join(cells) + "</tr>")

st.markdown(
    """<style>
    .ocp-staff-scroll {max-height:565px;overflow-y:auto;overflow-x:auto;border:1px solid #dfe6ee;border-radius:12px;background:white;}
    .ocp-staff-table {width:100%;table-layout:fixed;border-collapse:collapse;font-family:Inter,Arial,sans-serif;font-size:12px;color:#26344c;}
    .ocp-staff-table th {position:sticky;top:0;background:#f7f9fc;z-index:1;color:#728198;font-weight:500;text-align:left;}
    .ocp-staff-table td,.ocp-staff-table th {padding:10px 7px;border-bottom:1px solid #e4e9ef;vertical-align:middle;overflow-wrap:anywhere;}
    .ocp-staff-table a {color:#1163bd;text-decoration:none;font-weight:500;}
    .ocp-staff-table a:hover {text-decoration:underline;}
    .ocp-staff-table tr:hover td {background:#f7faff;}
    </style>"""
    + '<div class="ocp-staff-scroll"><table class="ocp-staff-table"><thead><tr>'
    + headers + '</tr></thead><tbody>' + "".join(rows_html)
    + '</tbody></table></div>',
    unsafe_allow_html=True,
)

