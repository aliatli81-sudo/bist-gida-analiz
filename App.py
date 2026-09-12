import pandas as pd
import streamlit as st
import yfinance as yf

# Sayfa Yapılandırması (Mobil ve Masaüstü Uyumlu)
st.set_page_config(
    page_title="BİST Hisse Analiz", page_icon="📈", layout="wide"
)

st.title("📈 BİST Hisse Analiz Robotu")
st.write("Sektörel bazda hisselerin temel analiz skorları ve rasyoları")

# Ekran görüntülerinizdeki tüm gıda & içecek hisseleri
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

# Perakende & Market Hisseleri
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

            veri_listesi.append(
                {
                    "Hisse": hisse,
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
        # Skora göre büyükten küçüğe sıralar
        df = df.sort_values(by="Skor (100)", ascending=False).reset_index(
            drop=True
        )
        # Sıra numarasını 0 yerine 1'den başlatır
        df.index = df.index + 1
    return df


# Kategori Seçimi
kategori = st.radio(
    "Sektör Seçin:",
    ["🍎 Gıda & İçecek", "🛒 Perakende / Market"],
    horizontal=True,
)

if st.button("🔄 Verileri Güncelle"):
    st.cache_data.clear()

# Tablo Gösterimi
if kategori == "🍎 Gıda & İçecek":
    st.subheader(f"Gıda & İçecek Hisseleri ({len(GIDA_HISSELERI)} Hisse)")
    with st.spinner("Veriler çekiliyor..."):
        df_gida = hisse_verilerini_getir(GIDA_HISSELERI)
        st.dataframe(df_gida, use_container_width=True)

else:
    st.subheader(f"Perakende & Market Hisseleri ({len(PERAKENDE_HISSELERI)} Hisse)")
    with st.spinner("Veriler çekiliyor..."):
        df_perakende = hisse_verilerini_getir(PERAKENDE_HISSELERI)
        st.dataframe(df_perakende, use_container_width=True)
