import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- VERİLƏNLƏR BAZASI AYARLARI ---
conn = sqlite3.connect('deyirman_v1.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    # Cədvəlləri yaradırıq
    c.execute('CREATE TABLE IF NOT EXISTS production (id INTEGER PRIMARY KEY, date TEXT, shift TEXT, ela INTEGER, bir INTEGER, kepek INTEGER, oboy INTEGER, yarma REAL, total_kg REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, date TEXT, customer TEXT, product TEXT, quantity REAL, price REAL, total_amount REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, name TEXT UNIQUE, phone TEXT, paid REAL DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS suppliers (id INTEGER PRIMARY KEY, name TEXT UNIQUE, phone TEXT, paid REAL DEFAULT 0)')
    c.execute('CREATE TABLE IF NOT EXISTS wheat_intake (id INTEGER PRIMARY KEY, date TEXT, supplier TEXT, quantity REAL, price REAL, total_cost REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, date TEXT, type TEXT, note TEXT, amount REAL)')
    conn.commit()

init_db()

# --- PROQRAMIN INTERFEYSİ ---
st.set_page_config(page_title="Dəyirman Proqramı", layout="wide")
st.sidebar.title("🚜 Dəyirman ERP v1.0")
menu = ["📊 Dashboard", "🏭 İstehsalat", "💰 Satış", "👥 Müştərilər", "🌾 Buğda Qəbulu", "🚛 Tədarükçülər", "💸 Xərclər"]
choice = st.sidebar.selectbox("Menyu", menu)

# --- 1. DASHBOARD (ANBAR VƏ MALİYYƏ) ---
if choice == "📊 Dashboard":
    st.header("Ümumi Vəziyyət")
    
    # Hesablamalar
    total_sales = pd.read_sql("SELECT SUM(total_amount) FROM sales", conn).iloc[0,0] or 0
    total_wheat_cost = pd.read_sql("SELECT SUM(total_cost) FROM wheat_intake", conn).iloc[0,0] or 0
    total_expenses = pd.read_sql("SELECT SUM(amount) FROM expenses", conn).iloc[0,0] or 0
    profit = total_sales - (total_wheat_cost + total_expenses)
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ümumi Gəlir", f"{total_sales:.2f} AZN")
    col2.metric("Buğda Xərci", f"{total_wheat_cost:.2f} AZN")
    col3.metric("Digər Xərclər", f"{total_expenses:.2f} AZN")
    col4.metric("XALİS MƏNFƏƏT", f"{profit:.2f} AZN", delta=f"{profit:.2f} AZN")

    st.divider()
    st.subheader("📦 Anbar Qalığı")
    # Stok hesablama məntiqi
    prod_df = pd.read_sql("SELECT SUM(ela), SUM(bir), SUM(kepek), SUM(oboy), SUM(yarma) FROM production", conn)
    sales_df = pd.read_sql("SELECT product, SUM(quantity) as qty FROM sales GROUP BY product", conn)
    
    # Sadələşdirilmiş Stok Cədvəli
    stok_data = {
        "Məhsul": ["Əla Növ (kisə)", "1-ci Növ (kisə)", "Kəpək (kisə)", "Oboy (kisə)", "Yarma (kq)"],
        "İstehsal": [prod_df.iloc[0,0] or 0, prod_df.iloc[0,1] or 0, prod_df.iloc[0,2] or 0, prod_df.iloc[0,3] or 0, prod_df.iloc[0,4] or 0],
    }
    stok_df = pd.DataFrame(stok_data)
    st.table(stok_df)

# --- 2. İSTEHSALAT ---
elif choice == "🏭 İstehsalat":
    st.header("Yeni İstehsalat Girişi")
    with st.form("prod_form"):
        col1, col2 = st.columns(2)
        date = col1.date_input("Tarix")
        shift = col2.selectbox("Smen", ["Gündüz", "Gecə"])
        
        ela = st.number_input("Əla Növ (50 kq)", min_value=0)
        bir = st.number_input("1-ci Növ (45 kq)", min_value=0)
        kepek = st.number_input("Kəpək (20 kq)", min_value=0)
        oboy = st.number_input("Oboy (30 kq)", min_value=0)
        yarma = st.number_input("Yarma (kq)", min_value=0.0)
        
        if st.form_submit_button("Yadda Saxla"):
            total_kg = (ela*50) + (bir*45) + (kepek*20) + (oboy*30) + yarma
            c.execute('INSERT INTO production (date, shift, ela, bir, kepek, oboy, yarma, total_kg) VALUES (?,?,?,?,?,?,?,?)', 
                      (str(date), shift, ela, bir, kepek, oboy, yarma, total_kg))
            conn.commit()
            st.success(f"Uğurla yazıldı! Toplam Çəki: {total_kg} kq")
            if total_kg > 0:
                st.info(f"Əla Növ Çıxımı: %{(ela*50/total_kg)*100:.1f}")

# --- 3. SATIŞ ---
elif choice == "💰 Satış":
    st.header("Yeni Satış")
    customers = [x[0] for x in c.execute('SELECT name FROM customers').fetchall()]
    with st.form("sales_form"):
        date = st.date_input("Tarix")
        customer = st.selectbox("Müştəri", customers if customers else ["Müştəri əlavə edin"])
        product = st.selectbox("Məhsul", ["Əla Növ", "1-ci Növ", "Kəpək", "Oboy", "Yarma"])
        qty = st.number_input("Miqdar (Kisə/Kq)", min_value=0.1)
        price = st.number_input("Qiymət (1 vahid üçün)", min_value=0.1)
        
        if st.form_submit_button("Satışı Tamamla"):
            total = qty * price
            c.execute('INSERT INTO sales (date, customer, product, quantity, price, total_amount) VALUES (?,?,?,?,?,?)',
                      (str(date), customer, product, qty, price, total))
            conn.commit()
            st.success(f"Satış qeydə alındı: {total} AZN")

# --- 4. MÜŞTƏRİLƏR ---
elif choice == "👥 Müştərilər":
    st.header("Müştəri İdarəetməsi")
    with st.expander("Yeni Müştəri Əlavə Et"):
        name = st.text_input("Ad Soyad / Mağaza")
        phone = st.text_input("Telefon")
        if st.button("Əlavə Et"):
            try:
                c.execute('INSERT INTO customers (name, phone) VALUES (?,?)', (name, phone))
                conn.commit()
                st.success("Müştəri bazaya düşdü.")
            except: st.error("Bu müştəri artıq var.")

    st.subheader("Borc Siyahısı")
    cust_df = pd.read_sql("SELECT name as 'Müştəri', phone as 'Telefon' FROM customers", conn)
    # Burada borc hesablaması (Hər müştərinin toplam satışı - ödənişi) gələcək
    st.dataframe(cust_df, use_container_width=True)

# --- 5. BUĞDA QƏBULU ---
elif choice == "🌾 Buğda Qəbulu":
    st.header("Tədarükçüdən Buğda Alışı")
    suppliers = [x[0] for x in c.execute('SELECT name FROM suppliers').fetchall()]
    with st.form("wheat_form"):
        date = st.date_input("Tarix")
        supplier = st.selectbox("Tədarükçü", suppliers if suppliers else ["Tədarükçü əlavə edin"])
        qty = st.number_input("Miqdar (kq)", min_value=0.0)
        price = st.number_input("1 kq Qiyməti", min_value=0.0)
        if st.form_submit_button("Qəbul Et"):
            total = qty * price
            c.execute('INSERT INTO wheat_intake (date, supplier, quantity, price, total_cost) VALUES (?,?,?,?,?)',
                      (str(date), supplier, qty, price, total))
            conn.commit()
            st.success(f"{total} AZN dəyərində buğda anbara girdi.")

# --- 6. XƏRCLƏR ---
elif choice == "💸 Xərclər":
    st.header("Digər Xərclər")
    with st.form("expense_form"):
        date = st.date_input("Tarix")
        ex_type = st.selectbox("Növ", ["Maaş", "Elektrik", "Yanacaq", "Təmir", "Digər"])
        note = st.text_input("Qeyd")
        amount = st.number_input("Məbləğ (AZN)", min_value=0.0)
        if st.form_submit_button("Xərci Yaz"):
            c.execute('INSERT INTO expenses (date, type, note, amount) VALUES (?,?,?,?)', (str(date), ex_type, note, amount))
            conn.commit()
            st.success("Xərc yadda saxlanıldı.")

# --- 7. TƏDARÜKÇÜLƏR ---
elif choice == "🚛 Tədarükçülər":
    st.header("Tədarükçü (Buğda Satanlar) Siyahısı")
    name = st.text_input("Tədarükçü Adı")
    phone = st.text_input("Telefonu")
    if st.button("Tədarükçü Əlavə Et"):
        try:
            c.execute('INSERT INTO suppliers (name, phone) VALUES (?,?)', (name, phone))
            conn.commit()
            st.success("Əlavə edildi.")
        except: st.error("Xəta baş verdi.")

st.sidebar.markdown("---")
st.sidebar.info("Dəyirman İdarəetmə Sistemi v1.0 - Hazırladı: AI Assistant")
