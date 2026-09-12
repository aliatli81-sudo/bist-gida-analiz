import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# Sayfa Yapılandırması (Mobil ve Masaüstü Uyumlu)
st.set_page_config(
    page_title="BİST Hisse Analiz & Sinyal", page_icon="📈", layout="wide"
)

st.title("📈 BİST Hisse Analiz & Sinyal Robotu")
st.write(
    "Temel analiz skorları ve Telegram üzerinden anlık telefon bildirim sistemi."
)

# Telegram Bildirim Fonksiyonu
def telegram_bildirim_gonder(bot_token, chat_id, mesaj):
    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mesaj, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception as e:
            st.error(f"Telegram bildirimi gönderilemedi: {e}")


# Yan Panel (Sidebar) - Bildirim Ayarları
st.sidebar.header("🔔 Telegram Bildirim Ayarları")
telegram_token = st.sidebar.text_input(
    "Telegram Bot Token", type="password", help="BotFather'dan alınan token"
)
telegram_chat_id = st.sidebar.text_input(
    "Telegram Chat ID", help="userinfobot'tan alınan ID"
)

st.sidebar.subheader("🎯 Sinyal Eşikleri")
al_esigi = st.sidebar.slider(
    "AL Sinyali için Min. Skor", min_value=60, max_value=100, value=80
)
sat_esigi = st.sidebar.slider(
    "SAT Sinyali için Max. Skor", min_value=0, max_value=60, value=40
)

# Hisse Listeleri
GIDA_HISSELERI = [
    "AEFES",
    "AKHAN",
    "ALKLC",
    "ARMGD",
    "ATAKP",
    "AVOD",
    "BALSU",
    "BANVT",
    "BESLR",
    "BIGCH",
    "BORSK",
    "BYDNR",
    "CCOLA",
    "CEMZY",
    "DARDL",
    "DMRGD",
    "DURKN",
    "ELITE",
    "EKSUN",
    "ERSU",
    "ETILR",
    "FADE",
    "FRIGO",
    "GOKNR",
    "GOLDA",
    "GUNDG",
    "KAYSE",
    "KENT",
    "KNFRT",
    "KRVGD",
    "KRSTL",
    "KTSKR",
    "MCARD",
    "MERKO",
    "MEYSU",
    "OBAMS",
    "ORCAY",
    "OYLUM",
    "OZSUB",
    "PENGD",
    "PETUN",
    "PINSU",
    "PNSUT",
    "SEGMN",
    "SELVA",
    "SOKE",
    "TABGD",
    "TATGD",
    "TBORG",
    "TUKAS",
    "ULKER",
    "ULUUN",
    "VANGD",
    "YAPRK",
    "YYLGD",
]

PERAKENDE_HISSELERI = ["BIMAS", "BIZIM", "CRFSA", "KIMMR", "MGROS", "SOKM"]


@st.cache_data(ttl=3600)
def hisse_verilerini_getir(hisse_listesi):
    veri_listesi = []

    for hisse in hisse_listesi:
        try:
            ticker = yf.Ticker(f"{hisse}.IS")
            info = ticker.info

            # Temel Göstergeler
            fk = info.get("trailingPE", None)
            pddd = info.get("priceToBook", None)
            roe = info.get("returnOnEquity", None)
            kar_buyume = info.get("earningsQuarterlyGrowth", None)
            fiyat = info.get("currentPrice", info.get("previousClose", None))

            # Skorlama Mantığı (100 üzerinden)
            skor = 50  # Başlangıç taban puanı
            if fk and 0 < fk < 10:
                skor += 15
            elif fk and 10 <= fk < 20:
                skor += 5

            if pddd and 0 < pddd < 3:
                skor += 15
            elif pddd and 3 <= pddd < 5:
                skor += 5

            if roe and roe > 0.20:
                skor += 10
            if kar_buyume and kar_buyume > 0.15:
                skor += 10

            # Sinyal Durumu
            sinyal = "NÖTR ⚖️"
            if skor >= al_esigi:
                sinyal = "AL 🚀"
            elif skor <= sat_esigi:
                sinyal = "SAT ⚠️"

            veri_listesi.append(
                {
                    "Hisse": hisse,
                    "Sinyal": sinyal,
                    "Skor (100)": skor,
                    "Fiyat (TL)": fiyat,
                    "F/K": round(fk, 2) if fk else "N/A",
                    "PD/DD": round(pddd, 2) if pddd else "N/A",
                    "Özsermaye Kâr. (%)": (
                        f"%{round(roe*100, 1)}" if roe else "N/A"
                    ),
                    "Kâr Büyümesi (%)": (
                        f"%{round(kar_buyume*100, 1)}" if kar_buyume else "N/A"
                    ),
                }
            )
        except Exception:
            continue

    df = pd.DataFrame(veri_listesi)
    if not df.empty:
        df = df.sort_values(by="Skor (100)", ascending=False).reset_index(
            drop=True
        )
        df.index = df.index + 1  # 1'den başlar
    return df


# Kategori Seçimi
kategori = st.radio(
    "Sektör Seçin:",
    ["🍎 Gıda & İçecek", "🛒 Perakende / Market"],
    horizontal=True,
)

col1, col2 = st.columns([1, 4])
with col1:
    if st.button("🔄 Verileri Güncelle"):
        st.cache_data.clear()

# Veri Getirme ve Gösterim
secili_liste = (
    GIDA_HISSELERI if kategori == "🍎 Gıda & İçecek" else PERAKENDE_HISSELERI
)
st.subheader(f"{kategori} Hisseleri ({len(secili_liste)} Hisse)")

with st.spinner("Hisse verileri analiz ediliyor..."):
    df_hisseler = hisse_verilerini_getir(secili_liste)
    st.dataframe(df_hisseler, use_container_width=True)

# Telefon Bildirimi Gönderme Butonu
with col2:
    if st.button("📲 Telefonuma Sinyal Bildirimi Gönder"):
        if not telegram_token or not telegram_chat_id:
            st.warning(
                "Lütfen sol menüden Telegram Token ve Chat ID bilgilerinizi girin!"
            )
        else:
            al_hisseleri = df_hisseler[df_hisseler["Skor (100)"] >= al_esigi]
            sat_hisseleri = df_hisseler[df_hisseler["Skor (100)"] <= sat_esigi]

            mesaj = f"📊 *BİST {kategori} Sinyal Raporu*\n\n"

            if not al_hisseleri.empty:
                mesaj += "🚀 *AL SİNYALİ VERENLER:*\n"
                for _, row in al_hisseleri.iterrows():
                    mesaj += f"• *{row['Hisse']}* - Skor: {row['Skor (100)']} (Fiyat: {row['Fiyat (TL)']} TL)\n"
                mesaj += "\n"

            if not sat_hisseleri.empty:
                mesaj += "⚠️ *SAT SİNYALİ VERENLER:*\n"
                for _, row in sat_hisseleri.iterrows():
                    mesaj += f"• *{row['Hisse']}* - Skor: {row['Skor (100)']} (Fiyat: {row['Fiyat (TL)']} TL)\n"

            if al_hisseleri.empty and sat_hisseleri.empty:
                mesaj += "Belirlediğiniz eşik değerlerinde AL veya SAT sinyali veren hisse bulunamadı."

            telegram_bildirim_gonder(telegram_token, telegram_chat_id, mesaj)
            st.success("Sinyal bildirimi Telegram hesabınıza gönderildi! 📱")
