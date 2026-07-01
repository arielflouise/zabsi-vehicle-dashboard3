import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(page_title="Zabsi Vehicle Control", page_icon="🛻", layout="wide")

st.title("📊 ZABSI Fleet, Booking & Compliance System")
st.markdown("Sistem Log Penggunaan Kenderaan, Lokasi Projek, dan Pemantauan Tarikh Dokumen Syarikat.")

csv_file = "vehicle_data.csv"

# Load the data
if not os.path.exists(csv_file):
    st.error(f"Fail '{csv_file}' tidak dijumpai. Sila pastikan fail CSV berada di dalam folder project.")
else:
    # Read fresh data on every rerun
    df = pd.read_csv(csv_file)

    # Convert date columns to datetime objects
    df["Tarikh Mula"] = pd.to_datetime(df["Tarikh Mula"], errors='coerce')
    df["Tarikh Tamat"] = pd.to_datetime(df["Tarikh Tamat"], errors='coerce')
    df["Road Tax Expiry"] = pd.to_datetime(df["Road Tax Expiry"], errors='coerce')
    df["Insurance Expiry"] = pd.to_datetime(df["Insurance Expiry"], errors='coerce')
    df["Puspakom Expiry"] = pd.to_datetime(df["Puspakom Expiry"], errors='coerce')

    today = datetime.datetime.now()

    # --- SECTION 1: STAFF BOOKING FORM ---
    st.sidebar.header("➕ Borang Tempahan Baru (Staff Booking)")
    st.sidebar.markdown("Staff boleh masukkan tempahan perjalanan baru di sini:")

    # Create lists of unique vehicles and plates for the dropdown selection
    unique_vehicles = sorted(df["Kenderaan"].dropna().unique())
    unique_plates = sorted(df["No. Pendaftaran"].dropna().unique())

    with st.sidebar.form(key="booking_form", clear_on_submit=True):
        input_vehicle = st.selectbox("Pilih Kenderaan", unique_vehicles)
        input_plate = st.selectbox("No. Pendaftaran", unique_plates)

        # Automatically determine fuel type based on plate/vehicle selection to avoid mistakes
        matched_rows = df[df["No. Pendaftaran"] == input_plate]
        default_fuel = matched_rows["Jenis Minyak"].values[0] if not matched_rows.empty else "PETROL"
        st.caption(f"⛽ Jenis Minyak Ditetapkan: **{default_fuel}**")

        input_start = st.date_input("Tarikh Mula Perjalanan", datetime.date.today())
        input_end = st.date_input("Tarikh Tamat Perjalanan", datetime.date.today())
        input_lokasi = st.text_input("📍 Lokasi / Site")
        input_pic = st.text_input("👤 Nama PIC / Pemandu")
        input_nota = st.text_input("📝 Nota / Kegunaan (Opsional)")

        submit_button = st.form_submit_button(label="Hantar Tempahan")

    if submit_button:
        if not input_lokasi or not input_pic:
            st.sidebar.error("❌ Sila isi bahagian Lokasi dan PIC terlebih dahulu!")
        else:
            # Grab compliance dates from existing vehicle data so they don't get lost
            road_tax_val = matched_rows["Road Tax Expiry"].values[0] if not matched_rows.empty else None
            ins_val = matched_rows["Insurance Expiry"].values[0] if not matched_rows.empty else None
            puspakom_val = matched_rows["Puspakom Expiry"].values[0] if not matched_rows.empty else None

            # Format dates nicely for the CSV
            rt_str = pd.to_datetime(road_tax_val).strftime('%Y-%m-%d') if pd.notnull(road_tax_val) else ""
            ins_str = pd.to_datetime(ins_val).strftime('%Y-%m-%d') if pd.notnull(ins_val) else ""
            pk_str = pd.to_datetime(puspakom_val).strftime('%Y-%m-%d') if pd.notnull(puspakom_val) else ""

            # Create a new row row dataframe
            new_row_idx = len(df) + 1
            new_booking = pd.DataFrame([{
                "No": new_row_idx,
                "Kenderaan": input_vehicle,
                "No. Pendaftaran": input_plate,
                "Jenis Minyak": default_fuel,
                "Tarikh Mula": input_start.strftime('%Y-%m-%d'),
                "Tarikh Tamat": input_end.strftime('%Y-%m-%d'),
                "Lokasi": input_lokasi,
                "PIC": input_pic,
                "Nota / Kegunaan": input_nota,
                "Road Tax Expiry": rt_str,
                "Insurance Expiry": ins_str,
                "Puspakom Expiry": pk_str
            }])

            # Append to the CSV file directly
            new_booking.to_csv(csv_file, mode='a', header=False, index=False)
            st.success(f"✅ Tempahan untuk **{input_plate}** ke **{input_lokasi}** berjaya disimpan!")

            # Force refresh to show the new row in the data grid
            st.rerun()

    # --- SECTION 2: MASTER DATA ENGINE ---
    st.subheader("📋 Log Induk Fleet Kenderaan")
    st.dataframe(df, width="stretch")

    st.markdown("---")

    # --- SECTION 3: CRITICAL COMPLIANCE ALERTS ---
    st.subheader("🚨 Amaran Pematuhan Dokumen (Compliance Alerts)")
    master_fleet = df[
        ["Kenderaan", "No. Pendaftaran", "Road Tax Expiry", "Insurance Expiry", "Puspakom Expiry"]].drop_duplicates(
        subset=["No. Pendaftaran"])

    comp_col1, comp_col2, comp_col3 = st.columns(3)

    with comp_col1:
        st.markdown("#### 🚗 Road Tax Status")
        for _, row in master_fleet.iterrows():
            if pd.notnull(row["Road Tax Expiry"]):
                days_left = (row["Road Tax Expiry"] - today).days
                plate = row["No. Pendaftaran"]
                name = row["Kenderaan"]
                if days_left < 0:
                    st.error(
                        f"🔴 **{plate}** ({name}) \n\n **EXPIRED** ({abs(days_left)} days ago) — End: {row['Road Tax Expiry'].strftime('%d/%m/%Y')}")
                elif days_left <= 30:
                    st.warning(
                        f"🟡 **{plate}** ({name}) \n\n **Warning:** {days_left} days left! ({row['Road Tax Expiry'].strftime('%d/%m/%Y')})")
                else:
                    st.success(f"🟢 **{plate}** — Active ({days_left} days left)")

    with comp_col2:
        st.markdown("#### 🛡️ Insurance Status")
        for _, row in master_fleet.iterrows():
            if pd.notnull(row["Insurance Expiry"]):
                days_left = (row["Insurance Expiry"] - today).days
                plate = row["No. Pendaftaran"]
                if days_left < 0:
                    st.error(f"🔴 **{plate}** \n\n **EXPIRED!** ({abs(days_left)} days overdue)")
                elif days_left <= 30:
                    st.warning(f"🟡 **{plate}** \n\n Renew soon ({days_left} days left)")
                else:
                    st.success(f"🟢 **{plate}** — Covered")

    with comp_col3:
        st.markdown("#### 🚛 Puspakom (PPKM) Status")
        for _, row in master_fleet.iterrows():
            if pd.notnull(row["Puspakom Expiry"]):
                days_left = (row["Puspakom Expiry"] - today).days
                plate = row["No. Pendaftaran"]
                name = row["Kenderaan"]
                if days_left < 0:
                    st.error(f"🔴 **{plate}** ({name}) \n\n **OVERDUE** ({abs(days_left)} days)")
                elif days_left <= 30:
                    st.warning(f"🟡 **{plate}** ({name}) \n\n Inspection due in {days_left} days!")
                else:
                    st.success(f"🟢 **{plate}** — Valid")

    st.markdown("---")

    # --- SECTION 4: DAILY OPERATIONS TIMELINE ---
    st.subheader("⚡ Status Lokasi Pergerakan Projek (Hari Ini)")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🏃‍♂️ Kenderaan Aktif di Tapak Projek")
        active_count = 0
        for index, row in df.iterrows():
            if pd.notnull(row["Tarikh Mula"]) and pd.notnull(row["Tarikh Tamat"]):
                if row["Tarikh Mula"] <= today <= row["Tarikh Tamat"]:
                    st.info(f"🛻 **{row['Kenderaan']} ({row['No. Pendaftaran']})**\n\n"
                            f"📍 **Site Lokasi:** {row['Lokasi']} | 👤 **PIC:** {row['PIC']}\n\n"
                            f"⛽ **Bahan Bakar:** `{row['Jenis Minyak']}`")
                    active_count += 1
        if active_count == 0:
            st.write("Tiada pergerakan aktif dikesan untuk hari ini.")

    with col2:
        st.markdown("### ⚠️ Polisi Pengisian Minyak")
        st.warning("Sila pastikan pemandu melihat status jenis minyak sebelum mengisi.")
        st.info(
            "💡 **Tip:** Lori dan armada Navara menggunakan **DIESEL**. Kereta Saga, Bezza, Almera, BMW, serta Van menggunakan **PETROL**.")