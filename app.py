import streamlit as st
import pandas as pd
import io
import base64
import time
from pathlib import Path
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

USERNAME = "admin"
PASSWORD = "ocg123"

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
div[data-testid="stDataFrame"] {border-radius:12px;overflow:hidden;}

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
    for col in ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project"]:
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
            "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project"
        ])

    df = df.copy()
    for col in ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project"]:
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
                .select("name,position,type_of_engagement,evaluation,status,project,source_file,source_path,uploaded_at")
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
    """Upload the source file and insert only staff records not already in Supabase.

    A record is considered already present when Name + Position + Project match
    case-insensitively. Duplicate rows inside the newly uploaded workbook are also skipped.
    Existing database rows are never deleted by this upload routine.
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

    # Keep the uploaded source file in Storage as an upload/version history.
    client.storage.from_("ocp-staff-files").upload(
        storage_path,
        file_bytes,
        {"content-type": content_type, "upsert": "false"}
    )

    # Read every existing staff key from Supabase. Pagination is important because
    # Supabase/PostgREST commonly returns at most 1,000 rows per request.
    existing_keys = set()
    start = 0
    page_size = 1000
    while True:
        result = (
            client.table("staff_records")
            .select("name,position,project")
            .range(start, start + page_size - 1)
            .execute()
        )
        batch = result.data or []
        for row in batch:
            existing_keys.add(_dedupe_key(
                row.get("name", ""),
                row.get("position", ""),
                row.get("project", "")
            ))
        if len(batch) < page_size:
            break
        start += page_size

    source = parsed_df[[
        "Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project"
    ]].copy()
    source = source.fillna("").astype(str)

    new_records = []
    seen_in_upload = set()
    skipped_existing = 0
    skipped_upload_duplicates = 0
    uploaded_at = pd.Timestamp.utcnow().isoformat()

    for _, row in source.iterrows():
        key = _dedupe_key(row["Name"], row["Position"], row["Project"])

        # Ignore rows without a usable employee name.
        if not key[0]:
            continue

        # Do not reinsert a staff/project combination already stored in Supabase.
        if key in existing_keys:
            skipped_existing += 1
            continue

        # Also protect against duplicate rows inside the same workbook.
        if key in seen_in_upload:
            skipped_upload_duplicates += 1
            continue

        seen_in_upload.add(key)
        new_records.append({
            "name": str(row["Name"]).strip(),
            "position": str(row["Position"]).strip(),
            "type_of_engagement": str(row["Type of Engagement"]).strip(),
            "evaluation": str(row["Evaluation"]).strip(),
            "status": str(row["Status"]).strip(),
            "project": str(row["Project"]).strip(),
            "source_file": filename,
            "source_path": storage_path,
            "uploaded_at": uploaded_at,
        })

    # Insert only genuinely new records, in safe batches.
    batch_size = 500
    for i in range(0, len(new_records), batch_size):
        client.table("staff_records").insert(new_records[i:i + batch_size]).execute()

    return {
        "storage_path": storage_path,
        "uploaded_rows": len(source),
        "added": len(new_records),
        "skipped_existing": skipped_existing,
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
            .select("id,name,position,type_of_engagement,evaluation,status,project")
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
    })


def save_staff_editor_changes(original_df, edited_df):
    """Update changed rows and insert rows added in the Admin editor."""
    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Supabase is not configured.")

    fields = ["Name", "Position", "Type of Engagement", "Evaluation", "Status", "Project"]
    db_fields = {
        "Name": "name",
        "Position": "position",
        "Type of Engagement": "type_of_engagement",
        "Evaluation": "evaluation",
        "Status": "status",
        "Project": "project",
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

    f1, f2, f3, f4 = st.columns([2.0, 1.35, 1.25, 1.7])

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

    with f2:
        selected_project = st.selectbox(
            "Project",
            ["All Projects"] + project_values,
            key="edit_filter_project",
        )

    with f3:
        selected_status = st.selectbox(
            "Status",
            ["All Status"] + status_values,
            key="edit_filter_status",
        )

    with f4:
        selected_position = st.selectbox(
            "Position",
            ["All Positions"] + position_values,
            key="edit_filter_position",
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
        f"{selected_project}::{selected_status}::{selected_position}"
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


def make_pdf(df, project, status, position, engagement, evaluation, search):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                            rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    styles = getSampleStyleSheet()
    styles["Title"].alignment = TA_CENTER
    story = [
        Paragraph("Oriental Consultants Philippines Inc.", styles["Title"]),
        Paragraph("Filtered Staff List", styles["Heading2"]), Spacer(1, 8),
        Paragraph(
            f"<b>Project:</b> {project} &nbsp; | &nbsp; <b>Status:</b> {status} &nbsp; | &nbsp; "
            f"<b>Name:</b> {search or 'All'} &nbsp; | &nbsp; <b>Position:</b> {position}<br/>"
            f"<b>Type of Engagement:</b> {engagement} &nbsp; | &nbsp; "
            f"<b>Evaluation:</b> {evaluation} &nbsp; | &nbsp; <b>Total:</b> {len(df):,}",
            styles["BodyText"]
        ), Spacer(1, 14)
    ]
    cols = ["Name", "Position", "Type of Engagement", "Evaluation", "Status"]
    data = [[Paragraph(f"<b>{c}</b>", styles["BodyText"]) for c in cols]]
    for _, r in df[cols].fillna("").iterrows():
        data.append([Paragraph(str(r[c]), styles["BodyText"]) for c in cols])
    t = Table(data, repeatRows=1, colWidths=[160, 200, 135, 105, 100])
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
    buffer.seek(0)
    return buffer.getvalue()

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
            if username == USERNAME and password == PASSWORD:
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
                                if result["added"] > 0:
                                    st.success(
                                        f"Upload complete: {result['added']:,} new staff record(s) added. "
                                        f"{result['skipped_existing']:,} existing record(s) skipped."
                                    )
                                else:
                                    st.info(
                                        f"Upload complete: no new staff records were found. "
                                        f"{result['skipped_existing']:,} existing record(s) were skipped."
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


st.caption(
    (f"Supabase file: {st.session_state.uploaded_name} · " if st.session_state.uploaded_name else "Supabase database · ")
    + f"Database records: {len(active_df):,}"
    + (f" across {active_df['Project'].nunique():,} projects." if not active_df.empty and "Project" in active_df.columns else ".")
)

st.markdown('<div class="section-title">Project Selection</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Select the project and project status you want to review.</div>', unsafe_allow_html=True)

p1, p2 = st.columns(2)
if "Project" in active_df.columns and not active_df.empty:
    projects = sorted(x for x in active_df["Project"].unique() if x and str(x).lower() != "nan")
else:
    projects = []

with p1:
    project = st.selectbox("Project", ["All Projects"] + projects)

if "Project" in active_df.columns and project != "All Projects":
    project_df = active_df[active_df["Project"] == project]
else:
    project_df = active_df.copy()

if "Status" in project_df.columns and not project_df.empty:
    statuses = sorted(x for x in project_df["Status"].unique() if x and str(x).lower() != "nan")
else:
    statuses = []

with p2:
    status = st.selectbox("Status", ["All Status"] + statuses)

filtered = project_df.copy()
if "Status" in filtered.columns and status != "All Status":
    filtered = filtered[filtered["Status"] == status]

st.markdown('<div class="section-title" style="margin-top:12px">Staff Search & Filters</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Choose any filter below. The staff list updates automatically.</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns([1.35, 1.2, 1, 1])
with c1:
    search = st.text_input("Name", placeholder="Search employee name")
with c2:
    positions = sorted(x for x in filtered["Position"].unique() if x and str(x).lower() != "nan") if "Position" in filtered.columns else []
    position = st.selectbox("Position", ["All Positions"] + positions)
with c3:
    types = sorted(x for x in filtered["Type of Engagement"].unique() if x and str(x).lower() != "nan") if "Type of Engagement" in filtered.columns else []
    engagement = st.selectbox("Type of Engagement", ["All Types"] + types)
with c4:
    evals = sorted(x for x in filtered["Evaluation"].unique() if x and str(x).lower() != "nan") if "Evaluation" in filtered.columns else []
    evaluation = st.selectbox("Evaluation", ["All Evaluations"] + evals)

if search and "Name" in filtered.columns:
    filtered = filtered[filtered["Name"].str.contains(search, case=False, na=False)]
if position != "All Positions" and "Position" in filtered.columns:
    filtered = filtered[filtered["Position"] == position]
if engagement != "All Types" and "Type of Engagement" in filtered.columns:
    filtered = filtered[filtered["Type of Engagement"] == engagement]
if evaluation != "All Evaluations" and "Evaluation" in filtered.columns:
    filtered = filtered[filtered["Evaluation"] == evaluation]

r1, r2 = st.columns([4, 1.25])
with r1:
    st.markdown(f'<div class="section-title" style="margin-top:8px">{len(filtered):,} Staff Found</div>', unsafe_allow_html=True)
with r2:
    if not filtered.empty:
        pdf = make_pdf(filtered, project, status, position, engagement, evaluation, search)
        st.download_button("Download Filtered PDF", pdf, "OCP_Filtered_Staff_List.pdf",
                           "application/pdf", use_container_width=True)

display_df = filtered[["Name", "Position", "Type of Engagement", "Evaluation", "Status"]].copy()

# Clean display values.
for col in ["Type of Engagement", "Evaluation", "Status"]:
    if col in display_df.columns:
        display_df[col] = display_df[col].fillna("").astype(str).str.strip()
        display_df.loc[display_df[col].isin(["nan", "None"]), col] = ""

# Put the most informative records first.
display_df["_has_evaluation"] = display_df["Evaluation"].ne("").astype(int) if "Evaluation" in display_df.columns else 0
display_df["_has_status"] = display_df["Status"].ne("").astype(int) if "Status" in display_df.columns else 0
display_df["_has_engagement"] = display_df["Type of Engagement"].ne("").astype(int) if "Type of Engagement" in display_df.columns else 0
display_df["_information_score"] = (
    display_df["_has_evaluation"] +
    display_df["_has_status"] +
    display_df["_has_engagement"]
)

sort_cols = ["_information_score", "_has_evaluation", "_has_status"]
sort_orders = [False, False, False]

if "Evaluation" in display_df.columns:
    sort_cols.append("Evaluation")
    sort_orders.append(False)
if "Status" in display_df.columns:
    sort_cols.append("Status")
    sort_orders.append(False)
if "Name" in display_df.columns:
    sort_cols.append("Name")
    sort_orders.append(True)

display_df = display_df.sort_values(
    by=sort_cols,
    ascending=sort_orders,
    kind="stable",
)

display_df = display_df.drop(
    columns=["_has_evaluation", "_has_status", "_has_engagement", "_information_score"]
)

# Only after sorting, show a dash for genuinely missing values.
for col in ["Type of Engagement", "Evaluation", "Status"]:
    if col in display_df.columns:
        display_df.loc[display_df[col].eq(""), col] = "—"

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=500,
    column_config={
        "Name": st.column_config.TextColumn("Name", width="medium"),
        "Position": st.column_config.TextColumn("Position", width="large"),
        "Type of Engagement": st.column_config.TextColumn("Type of Engagement", width="medium"),
        "Evaluation": st.column_config.TextColumn("Evaluation", width="medium"),
        "Status": st.column_config.TextColumn("Status", width="medium"),
    },
)