import sqlite3
import pandas as pd
import yfinance as yf
import streamlit as st
import plotly.express as px
from datetime import datetime

# ==============================================================================
# 1. BİST GIDA HİSSE LİSTESİ VE VERİTABANI ALTYAPISI
# ==============================================================================
GIDA_HISSELERI = [
    "AEFES.IS", "AGROT.IS", "ALARK.IS", "ALTNY.IS", "ATAKP.IS", 
    "BANVT.IS", "BIGCHEFS.IS", "BIMAS.IS", "CCOLA.IS", "EKSUN.IS", 
    "ELITE.IS", "FADE.IS", "FRIGO.IS", "GOKNR.IS", "KNFRT.IS", 
    "KRSTL.IS", "LUKSK.IS", "MNDTR.IS", "OBAKR.IS", "PETUN.IS", 
    "PINAR.IS", "PNSUT.IS", "SOKM.IS", "TATGD.IS", "TUKAS.IS", "ULKER.IS"
]

def veritabani_hazirla():
    conn = sqlite3.connect('bist_gida_analiz.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS finansal_veriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT,
            hisse_kodu TEXT,
            fiyat REAL,
            fk REAL,
            pddd REAL,
            ozsermaye_karliligi REAL,
            net_kar_marji REAL,
            ceyreklik_kar_buyumesi REAL
        )
    ''')
    conn.commit()
    conn.close()

def ceyreklik_kar_buyumesi_hesapla(hisse_obj):
    try:
        quarterly_financials = hisse_obj.quarterly_financials
        if not quarterly_financials.empty and 'Net Income' in quarterly_financials.index:
            net_kar_serisi = quarterly_financials.loc['Net Income']
            if len(net_kar_serisi) >= 4:
                son_ceyrek = net_kar_serisi.iloc[0]
                gecen_yil_ayni_ceyrek = net_kar_serisi.iloc[3]
                if gecen_yil_ayni_ceyrek > 0:
                    return round(((son_ceyrek - gecen_yil_ayni_ceyrek) / gecen_yil_ayni_ceyrek) * 100, 2)
    except Exception:
        pass
    return 0.0

def verileri_bistten_guncelle():
    conn = sqlite3.connect('bist_gida_analiz.db')
    cursor = conn.cursor()
    bugun = datetime.now().strftime("%Y-%m-%d")
    
    # Eski kayıtları temizle, güncel olanı ekle
    cursor.execute("DELETE FROM finansal_veriler WHERE tarih = ?", (bugun,))
    
    for sembol in GIDA_HISSELERI:
        try:
            hisse = yf.Ticker(sembol)
            info = hisse.info
            
            fiyat = info.get('currentPrice', 0) or 0
            fk = info.get('trailingPE', 0) or 0
            pddd = info.get('priceToBook', 0) or 0
            roe = (info.get('returnOnEquity', 0) or 0) * 100
            kar_marji = (info.get('profitMargins', 0) or 0) * 100
            ceyrek_buyume = ceyreklik_kar_buyumesi_hesapla(hisse)
            
            cursor.execute('''
                INSERT INTO finansal_veriler 
                (tarih, hisse_kodu, fiyat, fk, pddd, ozsermaye_karliligi, net_kar_marji, ceyreklik_kar_buyumesi)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (bugun, sembol.replace('.IS', ''), fiyat, fk, pddd, roe, kar_marji, ceyrek_buyume))
        except Exception:
            continue
            
    conn.commit()
    conn.close()

# ==============================================================================
# 2. YAPAY ZEKA SKORLAMA VE ANALİZ MOTORU
# ==============================================================================
def verileri_yukle_ve_skorla():
    conn = sqlite3.connect('bist_gida_analiz.db')
    query = '''
        SELECT hisse_kodu, fiyat, fk, pddd, ozsermaye_karliligi, net_kar_marji, ceyreklik_kar_buyumesi
        FROM finansal_veriler
        WHERE tarih = (SELECT MAX(tarih) FROM finansal_veriler)
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        return df

    def ai_skor_hesapla(row):
        skor = 0
        # F/K Çarpan Değerlemesi (Max 25 Puan)
        if 0 < row['fk'] <= 10: skor += 25
        elif 10 < row['fk'] <= 18: skor += 15
        
        # PD/DD Çarpan Değerlemesi (Max 25 Puan)
        if 0 < row['pddd'] <= 2.5: skor += 25
        elif 2.5 < row['pddd'] <= 5: skor += 15
        
        # Özsermaye Kârlılığı (Max 20 Puan)
        if row['ozsermaye_karliligi'] >= 30: skor += 20
        elif row['ozsermaye_karliligi'] >= 15: skor += 10
        
        # Net Kâr Marjı (Max 15 Puan)
        if row['net_kar_marji'] >= 12: skor += 15
        elif row['net_kar_marji'] >= 6: skor += 8
        
        # Çeyreklik Kâr Büyümesi (Max 15 Puan)
        if row['ceyreklik_kar_buyumesi'] >= 20: skor += 15
        elif row['ceyreklik_kar_buyumesi'] > 0: skor += 8
        
        return skor

    df['AI_Skoru'] = df.apply(ai_skor_hesapla, axis=1)
    return df.sort_values(by='AI_Skoru', ascending=False)

# ==============================================================================
# 3. STREAMLIT WEB ARAYÜZÜ (DASHBOARD)
# ==============================================================================
st.set_page_config(page_title="BİST Gıda AI Robotu", page_icon="🤖", layout="wide")

veritabani_hazirla()

st.title("🤖 BİST Gıda Sektörü Yapay Zeka Analiz Robotu")
st.caption("Borsa İstanbul Gıda Şirketlerinin Otomatik Kârlılık, Çarpan ve Bilanço Sıralaması")

# Üst Menü - Veri Güncelleme Butonu
col_btn, col_txt = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Borsa Verilerini Güncelle"):
        with st.spinner("BİST Gıda Hisseleri Taranıyor..."):
            verileri_bistten_guncelle()
            st.success("Veriler Başarıyla Güncellendi!")
            st.rerun()

df = verileri_yukle_ve_skorla()

if df.empty:
    st.info("Henüz veritabanında kayıt yok. Lütfen yukarıdaki **'Borsa Verilerini Güncelle'** butonuna basarak taramayı başlatın.")
else:
    # Metrikler
    top_hisse = df.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("En Yüksek AI Skorlu Hisse", top_hisse['hisse_kodu'], f"{top_hisse['AI_Skoru']} Puan")
    m2.metric("En Yüksek Özsermaye Kârlılığı", df.loc[df['ozsermaye_karliligi'].idxmax()]['hisse_kodu'], f"%{df['ozsermaye_karliligi'].max():.1f}")
    m3.metric("En Yüksek Çeyreklik Kâr Büyümesi", df.loc[df['ceyreklik_kar_buyumesi'].idxmax()]['hisse_kodu'], f"%{df['ceyreklik_kar_buyumesi'].max():.1f}")
    m4.metric("Analiz Edilen Şirket", len(df))

    st.divider()

    # Grafik ve Top 5
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("📊 Şirketlerin Yapay Zeka Skor Grafiği")
        fig = px.bar(
            df, x='hisse_kodu', y='AI_Skoru', color='ozsermaye_karliligi',
            labels={'hisse_kodu': 'Hisse', 'AI_Skoru': 'AI Skoru (100 Üzerinden)', 'ozsermaye_karliligi': 'Özsermaye Kâr (%)'},
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.subheader("🎯 En Potansiyelli Top 5 Gıda Hissesi")
        top5 = df[['hisse_kodu', 'fiyat', 'AI_Skoru']].head(5)
        top5.columns = ['Hisse', 'Fiyat (TL)', 'AI Skor']
        st.dataframe(top5, hide_index=True, use_container_width=True)

    st.divider()

    # Detaylı Tablo
    st.subheader("📋 Detaylı Bilanço ve Kârlılık Tablosu")
    st.dataframe(
        df,
        column_config={
            "hisse_kodu": "Hisse Kodu",
            "fiyat": st.column_config.NumberColumn("Fiyat", format="%.2f ₺"),
            "fk": st.column_config.NumberColumn("F/K", format="%.2f"),
            "pddd": st.column_config.NumberColumn("PD/DD", format="%.2f"),
            "ozsermaye_karliligi": st.column_config.NumberColumn("Özsermaye Kârlılığı", format="%% %.2f"),
            "net_kar_marji": st.column_config.NumberColumn("Net Kâr Marjı", format="%% %.2f"),
            "ceyreklik_kar_buyumesi": st.column_config.NumberColumn("Çeyreklik Kâr Büyümesi", format="%% %.2f"),
            "AI_Skoru": st.column_config.ProgressColumn("AI Sağlamlık Skoru", format="%d", min_value=0, max_value=100),
        },
        hide_index=True,
        use_container_width=True
    )

