import streamlit as st
import pandas as pd
import io
import base64
import time
import re
from pathlib import Path
from xml.sax.saxutils import escape
import tomllib
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
        "FUNDING": "Funding",
        "FUNDING SOURCE": "Funding",
        "SECTOR": "Sector",
        "TOTAL YEAR EXPERIENCE": "Experience",
        "TOTAL YEARS EXPERIENCE": "Experience",
        "TOTAL YEARS OF EXPERIENCE": "Experience",
        "YEARS OF EXPERIENCE": "Experience",
        "EXPERIENCE": "Experience",
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
            "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience"
        ])

    df = df.copy()
    for col in ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience"]:
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
        return clean_staff(df)
    except Exception as exc:
        st.session_state.supabase_error = str(exc)
        return empty


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
            .select("id,name,position,type_of_engagement,evaluation,status,project,funding,sector,experience,source_file,source_path")
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

    source = parsed_df[[
        "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience"
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
        for db_col, source_col in [("funding", "Funding"), ("sector", "Sector"), ("experience", "Experience")]:
            new_value = str(row[source_col]).strip()
            if new_value and norm(existing.get(db_col)) != norm(new_value):
                changes[db_col] = new_value

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
            .select("id,name,position,type_of_engagement,evaluation,status,project,funding,sector,experience")
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
    })


def save_staff_editor_changes(original_df, edited_df):
    """Update changed rows and insert rows added in the Admin editor."""
    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Supabase is not configured.")

    fields = ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project", "Funding", "Sector", "Experience"]
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
            "Position",
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
            "Position": st.column_config.TextColumn("Position"),
            "Type of Engagement": st.column_config.TextColumn("Type of Engagement"),
            "Evaluation": st.column_config.TextColumn("Evaluation"),
            "Status": st.column_config.TextColumn("Status"),
            "Project": st.column_config.TextColumn("Project"),
            "Funding": st.column_config.TextColumn("Funding"),
            "Sector": st.column_config.TextColumn("Sector"),
            "Experience": st.column_config.TextColumn("Total Year Experience"),
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


def make_pdf(df, funding, position, evaluations, current_project):
    """Export only visible staff fields and applied filters."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    styles["Title"].alignment = TA_CENTER
    story = [
        Paragraph("Oriental Consultants Philippines Inc.", styles["Title"]),
        Paragraph("Filtered Personnel List", styles["Heading2"]), Spacer(1, 8),
        Paragraph(f"<b>Current Project:</b> {escape(current_project)}", styles["BodyText"]),
        Spacer(1, 5),
        Paragraph(f"<b>Funding:</b> {escape(funding)} &nbsp; | &nbsp; <b>Position:</b> {escape(position)} &nbsp; | &nbsp; "
                  f"<b>Evaluation:</b> {escape(', '.join(evaluations) or 'All')} &nbsp; | &nbsp; <b>Total:</b> {len(df):,}",
                  styles["BodyText"]), Spacer(1, 14)
    ]
    cols = ["Name", "Position", "Sector", "Funding", "Total Year Experience", "Evaluation"]
    data = [[Paragraph(f"<b>{c}</b>", styles["BodyText"]) for c in cols]]
    for _, r in df[cols].fillna("").iterrows():
        data.append([Paragraph(str(r[c]), styles["BodyText"]) for c in cols])
    t = Table(data, repeatRows=1, colWidths=[140, 170, 115, 105, 105, 125])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9EEF5")),
        ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D5DAE3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
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

active_df = fetch_staff_from_supabase()


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
            ["Upload Staff Database", "Add & Edit Staff Data"],
            horizontal=True,
            label_visibility="collapsed",
            key="admin_category"
        )

        if admin_category == "Add & Edit Staff Data":
            st.caption("Add new staff or edit existing staff information directly in Supabase for evaluation.")
            if st.button("Open Add & Edit Staff Data", type="primary", use_container_width=True):
                staff_editor_dialog()
            st.divider()
        else:
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
                                time.sleep(1.2)
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
for col in ["Name", "Position", "Sector", "Experience", "Funding", "Project", "Evaluation"]:
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


c1, c2, c3 = st.columns(3)
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
    position = st.selectbox("Position", ["All Positions"] + list(position_options),
                            help="Similar positions are grouped across spelling, capitalization, &/and, punctuation, and numbered levels. Original employee positions are preserved.")

c4, c5, c6 = st.columns(3)
with c4:
    # A zero threshold means all staff, including those with no recorded experience.
    # Higher thresholds show everyone meeting the minimum experience requirement.
    experience_min = st.slider(
        "Years of Experience",
        min_value=0,
        max_value=40,
        value=0,
        step=1,
        format="%d years",
        help="0 = all staff. Move the slider to show staff with at least the selected number of years (e.g., 15 includes 16, 19, 20 and 30).",
    )
    st.caption("All experience levels" if experience_min == 0 else f"{experience_min}+ years of experience")
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
    current_project = st.selectbox(
        "Current Project",
        ["All Projects"] + project_options,
        help="Filter staff by their current project recorded in Supabase.",
    )

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
if experience_min > 0:
    years = filtered["Experience"].map(experience_years)
    filtered = filtered[years.ge(experience_min)]
if evaluations:
    filtered = filtered[filtered["Evaluation Display"].isin(evaluations)]
if current_project != "All Projects":
    filtered = filtered[filtered["Project"].eq(current_project)]

display_df = filtered[["Name", "Position", "Sector", "Funding Display", "Experience", "Evaluation Display"]].copy()
display_df = display_df.rename(columns={
    "Funding Display": "Funding", "Experience": "Total Year Experience", "Evaluation Display": "Evaluation"
})
for col in display_df.columns:
    display_df[col] = display_df[col].replace({"": "—", "nan": "—", "None": "—"})
display_df = display_df.sort_values("Name", kind="stable")

r1, r2 = st.columns([4, 1.25])
with r1:
    st.markdown(f'<div class="section-title" style="margin-top:8px">{len(filtered):,} {"Staff Found" if show_inactive_staff else "Active Staff Found"}</div>', unsafe_allow_html=True)
    st.caption(f"Current Project: {current_project}")
with r2:
    if not filtered.empty:
        pdf = make_pdf(display_df, funding, position, evaluations, current_project)
        st.download_button("Download Filtered PDF", pdf, "OCP_Filtered_Staff_List.pdf",
                           "application/pdf", use_container_width=True)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=500,
    column_config={
        "Name": st.column_config.TextColumn("Name", width="medium"),
        "Position": st.column_config.TextColumn("Position", width="large"),
        "Sector": st.column_config.TextColumn("Sector", width="medium"),
        "Funding": st.column_config.TextColumn("Funding", width="medium"),
        "Total Year Experience": st.column_config.TextColumn("Total Year Experience", width="medium"),
        "Evaluation": st.column_config.TextColumn("Evaluation", width="medium"),
    },
)
