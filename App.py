import time
import pandas as pd
import requests
import streamlit as st
import yfinance as yf

# Sayfa Yapılandırması
st.set_page_config(
    page_title="BİST Canlı Sinyal Robotu", page_icon="📈", layout="wide"
)

st.title("📈 BİST Otomatik Sinyal & Bildirim Robotu")
st.write(
    "Hisseleri otomatik tarar, ekrandaki tabloyu günceller ve sinyalleri Telegram'a gönderir."
)


# Telegram Bildirim Fonksiyonu
def telegram_bildirim_gonder(bot_token, chat_id, mesaj):
    if bot_token and chat_id:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": mesaj, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=5)
            return True
        except Exception as e:
            st.error(f"Telegram bildirimi gönderilemedi: {e}")
            return False
    return False


# Sidebar - Telegram ve Sinyal Ayarları
st.sidebar.header("🔔 Telegram Bildirim Ayarları")
telegram_token = st.sidebar.text_input(
    "Telegram Bot Token", type="password", help="BotFather token adresi"
)
telegram_chat_id = st.sidebar.text_input(
    "Telegram Chat ID", help="userinfobot ID adresi"
)

st.sidebar.subheader("🎯 Sinyal Eşikleri")
al_esigi = st.sidebar.slider(
    "AL Sinyali için Min. Skor", min_value=60, max_value=100, value=80
)
sat_esigi = st.sidebar.slider(
    "SAT Sinyali için Max. Skor", min_value=0, max_value=60, value=40
)

st.sidebar.subheader("🤖 Otomasyon Ayarları")
otomatik_mod = st.sidebar.checkbox("🚀 OTOMATİK TARAMAYI BAŞLAT")
taramasuresi = st.sidebar.number_input(
    "Tarama Sıklığı (Dakika)", min_value=1, max_value=60, value=5
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


def hisse_verilerini_getir(hisse_listesi):
    veri_listesi = []

    for hisse in hisse_listesi:
        try:
            ticker = yf.Ticker(f"{hisse}.IS")
            info = ticker.info

            fk = info.get("trailingPE", None)
            pddd = info.get("priceToBook", None)
            roe = info.get("returnOnEquity", None)
            kar_buyume = info.get("earningsQuarterlyGrowth", None)
            fiyat = info.get("currentPrice", info.get("previousClose", None))

            # Skorlama
            skor = 50
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
        df.index = df.index + 1
    return df


def tarama_yap_ve_ekrana_bas(hisse_listesi):
    df = hisse_verilerini_getir(hisse_listesi)

    if not df.empty:
        # Tabloyu ekranda göster
        st.dataframe(df, use_container_width=True)

        # Telegram Bildirimi İçin Sinyalleri Kontrol Et
        al_hisseleri = df[df["Skor (100)"] >= al_esigi]
        sat_hisseleri = df[df["Skor (100)"] <= sat_esigi]

        if (
            not al_hisseleri.empty or not sat_hisseleri.empty
        ) and telegram_token:
            mesaj = "🤖 *OTOMATİK SİNYAL BİLDİRİMİ*\n\n"

            if not al_hisseleri.empty:
                mesaj += "🚀 *AL SİNYALİ VERENLER:*\n"
                for _, row in al_hisseleri.iterrows():
                    mesaj += f"• *{row['Hisse']}* - Skor: {row['Skor (100)']} ({row['Fiyat (TL)']} TL)\n"
                mesaj += "\n"

            if not sat_hisseleri.empty:
                mesaj += "⚠️ *SAT SİNYALİ VERENLER:*\n"
                for _, row in sat_hisseleri.iterrows():
                    mesaj += f"• *{row['Hisse']}* - Skor: {row['Skor (100)']} ({row['Fiyat (TL)']} TL)\n"

            telegram_bildirim_gonder(telegram_token, telegram_chat_id, mesaj)


# Sektör Seçimi (Her İki Modda da Görünür)
kategori = st.radio(
    "Sektör Seçin:", ["🍎 Gıda & İçecek", "🛒 Perakende / Market"], horizontal=True
)
secili_liste = (
    GIDA_HISSELERI if kategori == "🍎 Gıda & İçecek" else PERAKENDE_HISSELERI
)

# Çalışma Mantığı
if otomatik_mod:
    if not telegram_token or not telegram_chat_id:
        st.error(
            "Otomatik bildirim alabilmek için lütfen sol menüden Telegram Token ve Chat ID girin!"
        )
    else:
        st.success(
            f"🟢 Otomatik tarama aktif! Sistem her {taramasuresi} dakikada bir tabloyu güncelleyip sinyalleri Telegram'a atacak."
        )

    canli_bilgi = st.empty()
    tablo_alani = st.empty()

    while True:
        with canli_bilgi.container():
            st.info(
                f"Son tarama zamanı: {time.strftime('%H:%M:%S')} - Bir sonraki otomatik tarama bekleniyor..."
            )
        with tablo_alani.container():
            tarama_yap_ve_ekrana_bas(secili_liste)

        if not otomatik_mod:
            break

        time.sleep(taramasuresi * 60)
        st.rerun()

else:
    with st.spinner("Veriler yükleniyor..."):
        tarama_yap_ve_ekrana_bas(secili_liste)
