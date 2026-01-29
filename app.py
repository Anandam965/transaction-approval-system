import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
from reportlab.lib.styles import getSampleStyleSheet

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Transaction Approval System", layout="wide")

# ---------------- SUPABASE CONFIG ----------------
SUPABASE_URL = "https://kehrxcqhigdniadeegbk.supabase.co"
SUPABASE_KEY = "sb_publishable_6kmFJD7l9hqe2vQxxZ8iOg_sRPIDO9z"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# ---------------- SESSION ----------------
if "user" not in st.session_state:
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.page = "login"

# ---------------- DEFAULT ADMIN CHECK ----------------
admin_res = requests.get(
    SUPABASE_URL + "/rest/v1/users?role=eq.admin",
    headers=HEADERS
)

admins = admin_res.json()

if len(admins) == 0:
    admin_data = {
        "username": "admin",
        "password": "admin123",
        "role": "admin"
    }

    requests.post(
        SUPABASE_URL + "/rest/v1/users",
        headers=HEADERS,
        json=admin_data
    )

# ---------------- STATUS COLORS ----------------
def highlight_status(row):
    if row["status"] == "Pending":
        return ["background-color:#ffcccc" if c == "status" else "" for c in row.index]
    if row["status"] == "Approved":
        return ["background-color:#ccffcc" if c == "status" else "" for c in row.index]
    if row["status"] == "Rejected":
        return ["background-color:#ffd699" if c == "status" else "" for c in row.index]
    return [""] * len(row)

# ---------------- BILL DUE DATE ----------------
def calculate_due_date(tx_date):
    d = datetime.fromisoformat(tx_date)

    m = d.month
    day = d.day
    y = d.year

    if (m == 1 and day >= 14) or (m == 2 and day <= 13):
        return f"{y}-03-02"

    if (m == 2 and day >= 14) or (m == 3 and day <= 13):
        return f"{y}-04-02"

    return "Next Cycle"

# ---------------- PDF ----------------
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_pdf(username, df, due_date, total):

    filename = f"{username}_bill.pdf"

    pdf = SimpleDocTemplate(
        filename,
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        name="TitleStyle",
        fontSize=18,
        alignment=1,
        spaceAfter=15
    )

    header_style = ParagraphStyle(
        name="HeaderStyle",
        fontSize=12,
        spaceAfter=10
    )

    elements = []

    # ---------- TITLE ----------
    elements.append(Paragraph("TRANSACTION BILL REPORT", title_style))
    elements.append(Spacer(1, 10))

    # ---------- CUSTOMER INFO ----------
    elements.append(Paragraph(f"<b>Customer :</b> {username}", header_style))
    elements.append(Paragraph(f"<b>Bill Due Date :</b> {due_date}", header_style))
    elements.append(Paragraph(f"<b>Total Amount :</b> ₹ {total}", header_style))

    elements.append(Spacer(1, 15))

    # ---------- TABLE ----------
    table_data = []

    headers = ["Card", "Date", "Amount", "Purpose", "Status"]
    table_data.append(headers)

    for _, row in df.iterrows():
        table_data.append([
            row["card_name"],
            row["trans_date"][:10],
            f"₹ {row['amount']}",
            row["purpose"],
            row["status"]
        ])

    table = Table(table_data, colWidths=[70, 90, 70, 160, 70])

    table.setStyle([

        # Header style
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),

        # Alignment
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("ALIGN", (2,1), (2,-1), "RIGHT"),

        # Fonts
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),

        # Grid
        ("GRID", (0,0), (-1,-1), 1, colors.black),

        # Padding
        ("BOTTOMPADDING", (0,0), (-1,0), 10),
        ("TOPPADDING", (0,0), (-1,0), 10),
    ])

    elements.append(table)

    elements.append(Spacer(1, 20))

    # ---------- FOOTER ----------
    elements.append(
        Paragraph(
            "<i>This is a system generated bill. No signature required.</i>",
            styles["Italic"]
        )
    )

    pdf.build(elements)

    return filename

# ---------------- AUTH ----------------
def login(username, password):

    url = SUPABASE_URL + "/rest/v1/users"
    query = f"?username=eq.{username}&password=eq.{password}"

    res = requests.get(url + query, headers=HEADERS)
    data = res.json()

    if len(data) > 0:
        return data[0]["role"]
    else:
        return None


def signup_request(username, password):

    data = {
        "username": username,
        "password": password
    }

    res = requests.post(
        SUPABASE_URL + "/rest/v1/pending_users",
        headers=HEADERS,
        json=data
    )

    return res.status_code == 201

# ---------------- LOGIN PAGE ----------------
def login_page():
    st.title("🔐 Login")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)

    if col1.button("Login"):
        role = login(u, p)

        if role:
            st.session_state.user = u
            st.session_state.role = role
            st.rerun()
        else:
            st.error("Invalid OR Waiting For Admin Approval")

    if col2.button("New User? Register"):
        st.session_state.page = "signup"
        st.rerun()

# ---------------- SIGNUP ----------------
def signup_page():
    st.title("📝 Registration Request")

    u = st.text_input("Username")
    p = st.text_input("Password", type="password")

    if st.button("Submit For Admin Approval"):
        if signup_request(u, p):
            st.success("Registration Sent For Admin Approval")
            st.session_state.page = "login"
            st.rerun()
        else:
            st.error("Already Exists")

    if st.button("Back To Login"):
        st.session_state.page = "login"
        st.rerun()

# ---------------- CUSTOMER DASHBOARD ----------------
def customer_page():
    st.title("👤 Customer Dashboard")

    with st.form("tx_form"):

        card = st.selectbox("Card Name", ["Rupay", "Master", "Other"])
        amt = st.number_input("Amount", min_value=0.0)
        pur = st.text_area("Purpose")

        if st.form_submit_button("Submit Transaction"):

            data = {
                "card_name": card,
                "username": st.session_state.user,
                "trans_date": datetime.now().isoformat(),
                "amount": amt,
                "purpose": pur,
                "status": "Pending"
            }

            requests.post(
                SUPABASE_URL + "/rest/v1/transactions",
                headers=HEADERS,
                json=data
            )

            st.success("Transaction Sent For Approval")

    res = requests.get(
        SUPABASE_URL + "/rest/v1/transactions?username=eq."+st.session_state.user+"&status=eq.Approved",
        headers=HEADERS
    )

    df = pd.DataFrame(res.json())

    if not df.empty:

        df["due_date"] = df["trans_date"].apply(calculate_due_date)

        st.subheader("Approved Transactions")
        st.dataframe(df.style.apply(highlight_status, axis=1))

        total = df["amount"].sum()
        due = df["due_date"].iloc[0]

        st.success(f"Total Bill Amount : ₹ {total}")
        st.warning(f"Bill Due Date : {due}")

        st.subheader("Spending Graph")
        st.bar_chart(df.set_index("trans_date")["amount"])

        if st.button("Download Bill PDF"):
            pdf = generate_pdf(st.session_state.user, df, due, total)

            with open(pdf, "rb") as f:
                st.download_button("Download PDF", f, file_name=pdf)

    else:
        st.info("No Approved Transactions Yet")

# ---------------- ADMIN DASHBOARD ----------------
def admin_page():
    st.title("🛠 Admin Control Panel")

    tab1, tab2, tab3, tab4 = st.tabs([
    "User Approvals",
    "Transaction Approvals",
    "User Management",
    "Analytics"
    ])
    # -------- USER APPROVAL --------
    with tab1:

        res = requests.get(
            SUPABASE_URL + "/rest/v1/pending_users",
            headers=HEADERS
        )

        df = pd.DataFrame(res.json())

        if df.empty:
            st.info("No Pending Users")
        else:
            for _, row in df.iterrows():
                with st.expander(row["username"]):

                    if st.button("Approve", key=f"a{row['id']}"):

                        user_data = {
                            "username": row["username"],
                            "password": row["password"],
                            "role": "customer"
                        }

                        requests.post(
                            SUPABASE_URL + "/rest/v1/users",
                            headers=HEADERS,
                            json=user_data
                        )

                        requests.delete(
                            SUPABASE_URL + "/rest/v1/pending_users?id=eq."+str(row["id"]),
                            headers=HEADERS
                        )

                        st.success("User Approved")
                        st.rerun()

                    if st.button("Reject", key=f"r{row['id']}"):

                        requests.delete(
                            SUPABASE_URL + "/rest/v1/pending_users?id=eq."+str(row["id"]),
                            headers=HEADERS
                        )

                        st.warning("User Rejected")
                        st.rerun()

    # -------- TRANSACTION APPROVAL --------
    with tab2:

        res = requests.get(
            SUPABASE_URL + "/rest/v1/transactions?status=eq.Pending",
            headers=HEADERS
        )

        df = pd.DataFrame(res.json())

        if df.empty:
            st.info("No Pending Transactions")
        else:
            for _, row in df.iterrows():
                with st.expander(f"{row['username']} | ₹{row['amount']}"):

                    new_amt = st.number_input("Edit Amount", value=row["amount"])
                    new_pur = st.text_input("Edit Purpose", value=row["purpose"])

                    if st.button("Approve", key=f"txa{row['id']}"):

                        requests.patch(
                            SUPABASE_URL + "/rest/v1/transactions?id=eq."+str(row["id"]),
                            headers=HEADERS,
                            json={
                                "amount": new_amt,
                                "purpose": new_pur,
                                "status": "Approved"
                            }
                        )

                        st.success("Transaction Approved")
                        st.rerun()

                    if st.button("Reject", key=f"txr{row['id']}"):

                        requests.patch(
                            SUPABASE_URL + "/rest/v1/transactions?id=eq."+str(row["id"]),
                            headers=HEADERS,
                            json={"status": "Rejected"}
                        )

                        st.warning("Transaction Rejected")
                        st.rerun()

    # -------- ANALYTICS --------
    # -------- USER MANAGEMENT --------
    with tab3:

        st.subheader("Edit / Delete Users")

        res = requests.get(
            SUPABASE_URL + "/rest/v1/users",
            headers=HEADERS
        )

        df = pd.DataFrame(res.json())

        if df.empty:
            st.info("No Users Found")
        else:

            for _, row in df.iterrows():

                with st.expander(f"{row['username']} ({row['role']})"):

                    new_username = st.text_input(
                        "Username",
                        value=row["username"],
                        key=f"u{row['id']}"
                    )

                    new_password = st.text_input(
                        "Password",
                        value=row["password"],
                        type="password",
                        key=f"p{row['id']}"
                    )

                    new_role = st.selectbox(
                        "Role",
                        ["customer", "admin"],
                        index=0 if row["role"] == "customer" else 1,
                        key=f"r{row['id']}"
                    )

                    col1, col2 = st.columns(2)

                    # UPDATE USER
                    if col1.button("Update", key=f"up{row['id']}"):

                        requests.patch(
                            SUPABASE_URL + "/rest/v1/users?id=eq."+str(row["id"]),
                            headers=HEADERS,
                            json={
                                "username": new_username,
                                "password": new_password,
                                "role": new_role
                            }
                        )

                        st.success("User Updated Successfully")
                        st.rerun()

                    # DELETE USER
                    if col2.button("Delete", key=f"del{row['id']}"):

                        if row["role"] == "admin":
                            st.error("Admin account cannot be deleted")
                        else:

                            requests.delete(
                                SUPABASE_URL + "/rest/v1/users?id=eq."+str(row["id"]),
                                headers=HEADERS
                            )

                            st.warning("User Deleted")
                            st.rerun()

# ---------------- LOGOUT ----------------
def logout():
    st.session_state.user = None
    st.session_state.role = None
    st.session_state.page = "login"
    st.rerun()

# ---------------- MAIN ----------------
if st.session_state.user is None:

    if st.session_state.page == "login":
        login_page()
    else:
        signup_page()

else:

    st.sidebar.success(f"Logged in : {st.session_state.user}")

    if st.sidebar.button("Logout"):
        logout()

    if st.session_state.role == "admin":
        admin_page()
    else:
        customer_page()