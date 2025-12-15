import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import time
import re

# --- 1. AYARLAR ---
st.set_page_config(page_title="Bütçe v52 (Final Fix)", page_icon="🐦", layout="wide")

# --- 2. TASARIM CSS (PREMIUM & RESPONSIVE) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    [data-testid="stSidebar"], #MainMenu, footer, header {display: none;}

    .block-container {
        padding-top: 2rem !important; padding-bottom: 3rem !important;
        padding-left: 3rem !important; padding-right: 3rem !important;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-top: 4rem !important; padding-bottom: 5rem !important;
            padding-left: 1rem !important; padding-right: 1rem !important;
        }
    }

    /* BUTONLAR */
    .top-btn-container button {
        border: none !important; background-color: white !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important; color: #555 !important;
        font-weight: 600 !important; padding: 0.5rem 1rem !important;
        border-radius: 8px !important; font-size: 1rem !important; width: 100%;
    }
    .logout-btn button { color: #dc3545 !important; }

    /* HİZALAMA */
    div[data-testid="stHorizontalBlock"] > div { display: flex; align-items: center; }
    .stRadio > div, [data-testid="stNumberInput"] { margin-top: 0 !important; }

    /* KARTLAR */
    .kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 25px; }
    @media (max-width: 768px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }
    .kpi-card {
        background: white; border-radius: 16px; padding: 15px; text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05);
    }
    .kpi-title { color: #999; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; }
    .kpi-value { font-size: 1.4rem; font-weight: 800; margin: 0; }

    /* PİYASA */
    .market-box {
        display: inline-flex; gap: 15px; background: white; padding: 10px 20px;
        border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        font-size: 0.95rem; font-weight: 700; color: #444; border: 1px solid #eee;
    }
    @media (max-width: 768px) { .market-box { width: 100%; justify-content: center; font-size: 0.85rem; padding: 8px; } }
    
    /* GİRİŞLER */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 10px !important; border: 1px solid #eee !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #ff4b4b, #ff6b6b) !important;
        border: none !important; box-shadow: 0 4px 10px rgba(255, 75, 75, 0.3) !important;
        font-weight: 700 !important; padding: 0.75rem !important; color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SABİTLER ---
RENK_GELIR = "#28a745"
RENK_GIDER = "#dc3545"
RENK_NET = "#007bff"
RENK_ODENMEMIS = "#ffc107"
KOLONLAR = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# --- YARDIMCILAR ---
def guvenli_int(deger):
    try:
        if pd.isna(deger) or str(deger).strip() == "": return 0
        return int(float(deger))
    except: return 0

def get_connection():
    from streamlit_gsheets import GSheetsConnection
    return st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=3600) 
def piyasa_verileri_getir():
    try:
        import yfinance as yf
        tickers = yf.download("TRY=X EURTRY=X GC=F", period="1d", progress=False)['Close']
        dolar = tickers['TRY=X'].iloc[-1]
        euro = tickers['EURTRY=X'].iloc[-1]
        ons_altin = tickers['GC=F'].iloc[-1]
        gram_altin = (ons_altin / 31.1035) * dolar
        return dolar, euro, gram_altin
    except: return 0, 0, 0

# --- VERİ İŞLEMLERİ ---
def verileri_cek(conn):
    try:
        df = conn.read(worksheet="Veriler", ttl=0)
        if df.empty or "Tarih" not in df.columns: return pd.DataFrame(columns=KOLONLAR)
        df = df.dropna(how="all")
        for col in KOLONLAR:
            if col not in df.columns: df[col] = pd.NA
        return df
    except: return pd.DataFrame(columns=KOLONLAR)

def kategorileri_cek(conn):
    varsayilan = pd.DataFrame([{"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 1}, {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}])
    try:
        df = conn.read(worksheet="Kategoriler", ttl=0)
        if df.empty: conn.update(worksheet="Kategoriler", data=varsayilan); return varsayilan
        if "Kategori" not in df.columns: return varsayilan
        return df.dropna(how="all")
    except: return varsayilan

def verileri_kaydet(conn, df):
    # --- DÜZELTİLMİŞ VE GÜVENLİ KAYIT FONKSİYONU ---
    try:
        save_df = df.copy()
        
        # 1. Tarihleri Önce Datetime'a Zorla, Sonra String Yap
        # Bu yöntem, veri zaten string ise de, datetime ise de çalışır.
        save_df["Tarih"] = pd.to_datetime(save_df["Tarih"], errors='coerce')
        save_df["Tarih"] = save_df["Tarih"].dt.strftime('%Y-%m-%d').fillna("")
        
        save_df["Son Ödeme Tarihi"] = pd.to_datetime(save_df["Son Ödeme Tarihi"], errors='coerce')
        save_df["Son Ödeme Tarihi"] = save_df["Son Ödeme Tarihi"].dt.strftime('%Y-%m-%d').fillna("")
        
        # 2. Tutar ve Diğerleri
        save_df["Tutar"] = pd.to_numeric(save_df["Tutar"], errors='coerce').fillna(0.0)
        save_df = save_df.fillna("")
        
        # 3. Kolon Eşitleme
        for col in KOLONLAR:
            if col not in save_df.columns: save_df[col] = ""
            
        conn.update(worksheet="Veriler", data=save_df[KOLONLAR])
    except Exception as e:
        st.error(f"Kayıt Hatası: {e}")

def kategorileri_kaydet(conn, df): conn.update(worksheet="Kategoriler", data=df)

def tarih_olustur(yil, ay_ismi, gun):
    try: 
        ay_index = AYLAR.index(ay_ismi) + 1
        yil = int(yil)
    except: 
        ay_index = datetime.now().month
        yil = datetime.now().year
    
    h_gun = guvenli_int(gun)
    if h_gun <= 0: h_gun = 1
    
    try: return date(yil, ay_index, h_gun)
    except ValueError: return date(yil, ay_index, 28)

def son_odeme_hesapla(islem_tarihi, varsayilan_gun):
    v_gun = guvenli_int(varsayilan_gun)
    if v_gun == 0: return islem_tarihi
    try:
        return tarih_olustur(islem_tarihi.year, AYLAR[islem_tarihi.month-1], v_gun)
    except: return islem_tarihi

def csv_indir(df): return df.to_csv(index=False).encode('utf-8')

def etiketleri_analiz_et(df):
    etiket_verisi = []
    for _, row in df.iterrows():
        aciklama = str(row["Açıklama"]).lower()
        bulunanlar = re.findall(r"#(\w+)", aciklama)
        if bulunanlar:
            bolunmus_tutar = row["Tutar"] / len(bulunanlar)
            for etiket in bulunanlar: etiket_verisi.append({"Etiket": etiket, "Tutar": bolunmus_tutar})
    if etiket_verisi: return pd.DataFrame(etiket_verisi).groupby("Etiket")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
    else: return pd.DataFrame()

# ==========================================
# --- UYGULAMA AKIŞI ---
# ==========================================

if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
if "genel" not in st.secrets: st.session_state.giris_yapildi = True

# --- GİRİŞ ---
if not st.session_state.giris_yapildi:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #333;'>🐦 Giriş</h2>", unsafe_allow_html=True)
        with st.form("giris_formu"):
            sifre = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", type="primary", use_container_width=True):
                if sifre == st.secrets["genel"]["sifre"]:
                    st.session_state.giris_yapildi = True
                    st.rerun()
                else: st.error("Hatalı!")

# --- ANA EKRAN ---
else:
    conn = get_connection()
    df = verileri_cek(conn)
    df_kat = kategorileri_cek(conn)

    if not df.empty:
        df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
        df = df.dropna(subset=["Tarih"])
        if "Durum" in df.columns:
            df["Durum"] = df["Durum"].astype(str).str.lower().map({'true': True, 'false': False, '1.0': True, '0.0': False, '1': True, '0': False, 'nan': False}).fillna(False)
        else: df["Durum"] = False
        if "Tutar" in df.columns: df["Tutar"] = pd.to_numeric(df["Tutar"], errors='coerce').fillna(0.0)
        else: df["Tutar"] = 0.0

    # 1. ÜST BAR
    c_top_l, c_top_r = st.columns([0.65, 0.35])
    usd, eur, gram = piyasa_verileri_getir()
    
    with c_top_l:
        if usd > 0:
            st.markdown(f"""
            <div class="market-box">
                <span>💵 {usd:.2f}</span>
                <span>💶 {eur:.2f}</span>
                <span>🥇 {gram:.0f}</span>
            </div>""", unsafe_allow_html=True)
        else: st.caption("Yükleniyor...")

    with c_top_r:
        b1, b2 = st.columns(2)
        with b1: 
            st.markdown('<div class="top-btn-container">', unsafe_allow_html=True)
            if st.button("🔄 Yenile", use_container_width=True): st.cache_data.clear(); st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with b2: 
            st.markdown('<div class="top-btn-container logout-btn">', unsafe_allow_html=True)
            if st.button("⎋ Çıkış", use_container_width=True): st.session_state.giris_yapildi = False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    # 2. FİLTRELER
    c_ara, c_yil, c_ay = st.columns([0.15, 0.35, 0.50], gap="small")
    with c_ara: 
        st.write("")
        arama_modu = st.checkbox("🔍")
    
    if arama_modu:
        with c_yil: st.write("")
        with c_ay: kelime = st.text_input("Ara", label_visibility="collapsed", placeholder="Ara...")
        if kelime:
            df_filt = df[df.astype(str).apply(lambda x: x.str.contains(kelime, case=False)).any(axis=1)]
            secilen_yil = "Arama"; secilen_ay = "Arama"
        else: df_filt = df; secilen_yil = "Arama"; secilen_ay = "Arama"
    else:
        kelime = None
        yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True) if not df.empty else []
        current_year = datetime.now().year
        if current_year not in yil_list: yil_list.insert(0, current_year)
        
        with c_yil: secilen_yil = st.selectbox("Yıl", ["Tüm"] + list(yil_list), label_visibility="collapsed")
        with c_ay: 
            idx = datetime.now().month if secilen_yil == current_year else 0
            secilen_ay = st.selectbox("Ay", ["Tüm"] + AYLAR, index=idx, label_visibility="collapsed")
        
        if secilen_yil == "Tüm": df_filt = df
        else:
            df_filt = df[df["Tarih"].dt.year == secilen_yil]
            if secilen_ay != "Tüm":
                ay_no = AYLAR.index(secilen_ay) + 1
                df_filt = df_filt[df_filt["Tarih"].dt.month == ay_no]

    # 3. KOPYALAMA ARAÇLARI
    if not arama_modu and secilen_ay != "Tüm" and secilen_yil != "Tüm":
        with st.expander("🛠️ Kopyala / İndir"):
            ec1, ec2 = st.columns(2)
            with ec1: st.download_button("📥 Excel İndir", csv_indir(df), "yedek.csv", "text/csv", use_container_width=True)
            with ec2:
                if st.button("⏮️ Geçen Ayı Kopyala", use_container_width=True):
                    try:
                        hy = int(secilen_yil)
                        ha = AYLAR.index(secilen_ay) + 1
                        if ha == 1: ka = 12; ky = hy - 1
                        else: ka = ha - 1; ky = hy
                        kdf = df[(df["Tarih"].dt.year == ky) & (df["Tarih"].dt.month == ka) & (df["Tür"] == "Gider")]
                        
                        if not kdf.empty:
                            kopya = []
                            for _, r in kdf.iterrows():
                                kb = df_kat[df_kat["Kategori"] == r["Kategori"]]
                                if not kb.empty:
                                    vg = guvenli_int(kb.iloc[0]["VarsayilanGun"])
                                    yt = tarih_olustur(hy, secilen_ay, vg)
                                    yso = son_odeme_hesapla(yt, vg)
                                    kopya.append({
                                        "Tarih": pd.to_datetime(yt), "Kategori": r["Kategori"], "Tür": "Gider", 
                                        "Tutar": float(r["Tutar"]), "Son Ödeme Tarihi": yso, 
                                        "Açıklama": f"{r['Açıklama']} (Kopya)", "Durum": False
                                    })
                            if kopya:
                                yeni_df = pd.concat([df, pd.DataFrame(kopya)], ignore_index=True)
                                verileri_kaydet(conn, yeni_df)
                                st.success(f"{len(kopya)} Kayıt Kopyalandı!"); time.sleep(1); st.rerun()
                            else: st.warning("Sabit gider yok.")
                        else: st.error("Geçen ayda veri yok.")
                    except Exception as e: st.error(f"Hata: {e}")

    st.write("")

    # 4. KARTLAR
    if not df_filt.empty:
        gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
        gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
        net = gelir - gider
        bekleyen = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]["Tutar"].sum()
        
        ik = "😐"; cr = RENK_NET
        if net > 0: ik = "😃"; cr = RENK_GELIR
        elif net < 0: ik = "☹️"; cr = RENK_GIDER
        
        st.markdown(f"""
        <div class="kpi-grid">
            <div class="kpi-card" style="border-top: 4px solid {RENK_GELIR};">
                <div class="kpi-title">GELİR</div>
                <div class="kpi-value" style="color:{RENK_GELIR}">💰 {gelir:,.0f}</div>
            </div>
            <div class="kpi-card" style="border-top: 4px solid {RENK_GIDER};">
                <div class="kpi-title">GİDER</div>
                <div class="kpi-value" style="color:{RENK_GIDER}">💸 {gider:,.0f}</div>
            </div>
            <div class="kpi-card" style="border-top: 4px solid {cr};">
                <div class="kpi-title">NET</div>
                <div class="kpi-value" style="color:{cr}">{ik} {net:,.0f}</div>
            </div>
            <div class="kpi-card" style="border-top: 4px solid {RENK_ODENMEMIS};">
                <div class="kpi-title">ÖDENMEMİŞ</div>
                <div class="kpi-value" style="color:{RENK_ODENMEMIS}">⏳ {bekleyen:,.0f}</div>
            </div>
        </div>""", unsafe_allow_html=True)
    else: st.info("Kayıt yok.")

    st.write("")
    
    # 5. SEKMELER
    t1, t2, t3, t4 = st.tabs(["📝 Ekle", "📊 Grafik", "📋 Liste", "📂 Ayar"])

    with t1:
        if arama_modu: st.warning("Aramayı kapatın")
        else:
            with st.container(border=True):
                c_tur, c_kat, c_tut = st.columns([1, 1.5, 1])
                with c_tur:
                    ts = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
                with c_kat:
                    kl = df_kat[df_kat["Tur"]==ts]["Kategori"].tolist() if not df_kat.empty else []
                    ks = st.selectbox("Kat.", kl, index=None, label_visibility="collapsed", placeholder="Kategori Seç...")
                with c_tut:
                    tug = st.number_input("Tutar", step=50.0, label_visibility="collapsed", placeholder="0
