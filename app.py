import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import datetime

st.set_page_config(page_title="Zabsi Vehicle Control", page_icon="🛻", layout="wide")

st.title("📊 ZABSI Fleet, Booking & Compliance System")
st.markdown("Sistem Log Penggunaan Kenderaan dan Pemantauan Tarikh Dokumen Syarikat secara Live.")

# Create a connection to your live Google Sheet using the URL in your Secrets panel
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Read the data from the live sheet
    df = conn.read(ttl=5)  # ttl=5 means it checks the sheet for fresh updates every 5 seconds
except Exception as e:
    st.error("Gagal menyambung ke Google Sheets. Sila pastikan URL di bahagian Secrets adalah betul.")
    st.stop()

# Ensure standard column cleaning
df["Tarikh Mula"] = pd.to_datetime(df["Tarikh Mula"], errors='coerce')
df["Tarikh Tamat"] = pd.to_datetime(df["Tarikh Tamat"], errors='coerce')
df["Road Tax Expiry"] = pd.to_datetime(df["Road Tax Expiry"], errors='coerce')
df["Insurance Expiry"] = pd.to_datetime(df["Insurance Expiry"], errors='coerce')
df["Puspakom Expiry"] = pd.to_datetime(df["Puspakom Expiry"], errors='coerce')

today = datetime.datetime.now()

# --- SECTION 1: LIVE STAFF BOOKING FORM ---
st.sidebar.header("➕ Borang Tempahan Baru")
st.sidebar.markdown("Staff boleh masukkan tempahan perjalanan baru ke Google Sheets di sini:")

unique_vehicles = sorted(df["Kenderaan"].dropna().unique())
unique_plates = sorted(df["No. Pendaftaran"].dropna().unique())

with st.sidebar.form(key="booking_form", clear_on_submit=True):
    input_vehicle = st.selectbox("Pilih Kenderaan", unique_vehicles)
    input_plate = st.selectbox("No. Pendaftaran", unique_plates)

    matched_rows = df[df["No. Pendaftaran"] == input_plate]
    default_fuel = matched_rows["Jenis Minyak"].values[0] if not matched_rows.empty else "PETROL"
    st.caption(f"⛽ Jenis Minyak Ditetapkan: **{default_fuel}**")

    input_start = st.date_input("Tarikh Mula Perjalanan", datetime.date.today())
    input_end = st.date_input("Tarikh Tamat Perjalanan", datetime.date.today())
    input_lokasi = st.text_input("📍 Lokasi / Site")
    input_pic = st.text_input("👤 Nama PIC / Pemandu")
    input_nota = st.text_input("📝 Nota / Kegunaan (Opsional)")

    submit_button = st.form_submit_button(label="Hantar Tempahan ke Google Sheet")

if submit_button:
    if not input_lokasi or not input_pic:
        st.sidebar.error("❌ Sila isi bahagian Lokasi dan PIC terlebih dahulu!")
    else:
        road_tax_val = matched_rows["Road Tax Expiry"].values[0] if not matched_rows.empty else None
        ins_val = matched_rows["Insurance Expiry"].values[0] if not matched_rows.empty else None
        puspakom_val = matched_rows["Puspakom Expiry"].values[0] if not matched_rows.empty else None

        rt_str = pd.to_datetime(road_tax_val).strftime('%Y-%m-%d') if pd.notnull(road_tax_val) else ""
        ins_str = pd.to_datetime(ins_val).strftime('%Y-%m-%d') if pd.notnull(ins_val) else ""
        pk_str = pd.to_datetime(puspakom_val).strftime('%Y-%m-%d') if pd.notnull(puspakom_val) else ""

        new_row_idx = len(df) + 1
        new_booking = pd.DataFrame([{
            "No": int(new_row_idx),
            "Kenderaan": str(input_vehicle),
            "No. Pendaftaran": str(input_plate),
            "Jenis Minyak": str(default_fuel),
            "Tarikh Mula": input_start.strftime('%Y-%m-%d'),
            "Tarikh Tamat": input_end.strftime('%Y-%m-%d'),
            "Lokasi": str(input_lokasi).replace('"', ''),
            "PIC": str(input_pic),
            "Nota / Kegunaan": str(input_nota),
            "Road Tax Expiry": rt_str,
            "Insurance Expiry": ins_str,
            "Puspakom Expiry": pk_str
        }])

        # Combine old data and the new row, then push the whole table back to Google Sheets live
        updated_df = pd.concat([df, new_booking], ignore_index=True)
        conn.update(data=updated_df)

        st.success("✅ Berjaya disimpan terus ke Google Sheets!")
        st.rerun()

# --- SECTION 2: LIVE MASTER DATA VIEW ---
st.subheader("📋 Log Induk Fleet Kenderaan (Live dari Google Sheets)")
st.dataframe(df, width="stretch")

st.markdown("---")

# --- SECTION 3: COMPLIANCE ALERTS ---
st.subheader("🚨 Amaran Pematuhan Dokumen")
master_fleet = df[
    ["Kenderaan", "No. Pendaftaran", "Road Tax Expiry", "Insurance Expiry", "Puspakom Expiry"]].drop_duplicates(
    subset=["No. Pendaftaran"])

comp_col1, comp_col2, comp_col3 = st.columns(3)
with comp_col1:
    st.markdown("#### 🚗 Road Tax Status")
    for _, row in master_fleet.iterrows():
        if pd.notnull(row["Road Tax Expiry"]):
            days_left = (row["Road Tax Expiry"] - today).days
            if days_left < 0:
                st.error(f"🔴 **{row['No. Pendaftaran']}** \n\n EXPIRED ({abs(days_left)} days ago)")
            elif days_left <= 30:
                st.warning(f"🟡 **{row['No. Pendaftaran']}** \n\n Warning: {days_left} days left!")
            else:
                st.success(f"🟢 **{row['No. Pendaftaran']}** — {days_left} days left")

with comp_col2:
    st.markdown("#### 🛡️ Insurance Status")
    for _, row in master_fleet.iterrows():
        if pd.notnull(row["Insurance Expiry"]):
            days_left = (row["Insurance Expiry"] - today).days
            if days_left < 0:
                st.error(f"🔴 **{row['No. Pendaftaran']}** \n\n EXPIRED!")
            elif days_left <= 30:
                st.warning(f"🟡 **{row['No. Pendaftaran']}** \n\n Renew soon ({days_left} days left)")
            else:
                st.success(f"🟢 **{row['No. Pendaftaran']}** — Covered")

with comp_col3:
    st.markdown("#### 🚛 Puspakom Status")
    for _, row in master_fleet.iterrows():
        if pd.notnull(row["Puspakom Expiry"]):
            days_left = (row["Puspakom Expiry"] - today).days
            if days_left < 0:
                st.error(f"🔴 **{row['No. Pendaftaran']}** \n\n OVERDUE")
            elif days_left <= 30:
                st.warning(f"🟡 **{row['No. Pendaftaran']}** \n\n Due in {days_left} days!")
            else:
                st.success(f"🟢 **{row['No. Pendaftaran']}** — Valid")

st.markdown("---")

# --- SECTION 4: TODAY'S MOVEMENTS ---
st.subheader("⚡ Status Lokasi Pergerakan Projek (Hari Ini)")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏃‍♂️ Kenderaan Aktif di Tapak Projek")
    active_count = 0
    for index, row in df.iterrows():
        if pd.notnull(row["Tarikh Mula"]) and pd.notnull(row["Tarikh Tamat"]):
            if row["Tarikh Mula"] <= today <= row["Tarikh Tamat"]:
                st.info(
                    f"🛻 **{row['Kenderaan']} ({row['No. Pendaftaran']})**\n\n📍 **Site:** {row['Lokasi']} | 👤 **PIC:** {row['PIC']}")
                active_count += 1
    if active_count == 0:
        st.write("Tiada pergerakan aktif dikesan untuk hari ini.")

with col2:
    st.markdown("### ⚠️ Polisi Pengisian Minyak")
    st.warning("Sila pastikan pemandu melihat status jenis minyak sebelum mengisi.")