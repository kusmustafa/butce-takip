import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
import time
import re

# --- 1. AYARLAR ---
st.set_page_config(page_title="Bütçe v48", page_icon="🐦", layout="wide")

# --- 2. RESPONSIVE CSS (HEM MOBİL HEM PC İÇİN AKILLI TASARIM) ---
st.markdown("""
<style>
    /* 1. GENEL AYARLAR (SOL MENÜYÜ GİZLE) */
    [data-testid="stSidebar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 2. DİNAMİK BOŞLUK AYARI (Media Query) */
    /* Bilgisayar (Geniş Ekran) için ayarlar */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 5rem !important;
        padding-right: 5rem !important;
    }

    /* Telefon (Dar Ekran) için ayarlar - Ekran 768px'den küçükse devreye girer */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 4rem !important; /* Çentik için boşluk */
            padding-bottom: 5rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    /* 3. AKILLI KART IZGARASI (CSS GRID) */
    /* Bu yapı, Python kolonları yerine HTML ızgarası kullanır */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr); /* Bilgisayarda 4 yan yana */
        gap: 10px; /* Kartlar arası boşluk */
        margin-bottom: 20px;
    }

    /* Telefondaysa 2 yan yana olsun */
    @media (max-width: 768px) {
        .kpi-grid {
            grid-template-columns: repeat(2, 1fr); 
        }
    }

    /* KART STİLİ */
    .kpi-card {
        background-color: white;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border: 1px solid #f0f0f0;
    }
    .kpi-title {
        color: #888;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 1.3rem; /* Mobilde taşmasın diye optimize edildi */
        font-weight: 800;
        margin: 0;
    }

    /* Piyasa Bilgisi Stili */
    .market-box {
        display: inline-flex;
        gap: 15px;
        background: #f8f9fa;
        padding: 8px 15px;
        border-radius: 20px;
        border: 1px solid #eee;
        font-size: 0.9rem;
        font-weight: 600;
        color: #444;
    }
    @media (max-width: 768px) {
        .market-box {
            font-size: 0.8rem;
            gap: 8px;
            padding: 5px 10px;
            width: 100%;
            justify-content: center;
        }
    }
</style>
""", unsafe_allow_html=True)

# --- RENKLER ---
RENK_GELIR = "#28a745"
RENK_GIDER = "#dc3545"
RENK_NET = "#007bff"
RENK_ODENMEMIS = "#ffc107"
KOLONLAR = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# --- BAĞLANTI ---
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

# --- FONKSİYONLAR ---
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
    save_df = df.copy()
    save_df["Tarih"] = save_df["Tarih"].astype(str).replace('NaT', '')
    save_df["Son Ödeme Tarihi"] = save_df["Son Ödeme Tarihi"].astype(str).replace('NaT', '')
    save_df = save_df.fillna("") 
    for col in KOLONLAR:
        if col not in save_df.columns: save_df[col] = ""
    conn.update(worksheet="Veriler", data=save_df[KOLONLAR])

def kategorileri_kaydet(conn, df): conn.update(worksheet="Kategoriler", data=df)

def tarih_olustur(yil, ay_ismi, gun):
    try: ay_index = AYLAR.index(ay_ismi) + 1
    except: ay_index = datetime.now().month
    try: h_gun = int(float(gun)); 
    except: h_gun = 1
    if h_gun <= 0: h_gun = 1
    try: return date(yil, ay_index, h_gun)
    except ValueError: return date(yil, ay_index, 28)

def son_odeme_hesapla(islem_tarihi, varsayilan_gun):
    if not varsayilan_gun or varsayilan_gun == 0: return islem_tarihi
    try:
        v_gun = int(float(varsayilan_gun))
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
# --- UYGULAMA ---
# ==========================================

if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
if "genel" not in st.secrets: st.session_state.giris_yapildi = True

# --- GİRİŞ EKRANI ---
if not st.session_state.giris_yapildi:
    st.markdown("<br><br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center; color: #555;'>🐦 Giriş</h2>", unsafe_allow_html=True)
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

    # Veri Tipi Düzeltme
    if not df.empty:
        df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
        df = df.dropna(subset=["Tarih"])
        if "Durum" in df.columns:
            df["Durum"] = df["Durum"].astype(str).str.lower().map({'true': True, 'false': False, '1.0': True, '0.0': False, '1': True, '0': False, 'nan': False}).fillna(False)
        else: df["Durum"] = False
        if "Tutar" in df.columns: df["Tutar"] = pd.to_numeric(df["Tutar"], errors='coerce').fillna(0.0)
        else: df["Tutar"] = 0.0

    # 1. ÜST BAR (Piyasa + Yenile + Çıkış)
    # Mobilde alt alta, PC'de yan yana olacak şekilde
    col_top_left, col_top_right = st.columns([0.7, 0.3])
    
    usd, eur, gram = piyasa_verileri_getir()
    
    with col_top_left:
        # PİYASA KUTUSU
        if usd > 0:
            st.markdown(f"""
            <div class="market-box">
                <span>💵 {usd:.2f}</span>
                <span>💶 {eur:.2f}</span>
                <span>🥇 {gram:.0f}</span>
            </div>
            """, unsafe_allow_html=True)
        else: st.caption("Yükleniyor...")

    with col_top_right:
        # BUTONLAR
        b1, b2 = st.columns(2)
        with b1: 
            if st.button("🔄", help="Yenile"): st.cache_data.clear(); st.rerun()
        with b2: 
            if st.button("🚪", help="Çıkış"): st.session_state.giris_yapildi = False; st.rerun()

    st.markdown("---")

    # 2. BAŞLIK VE FİLTRELER
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
        if datetime.now().year not in yil_list: yil_list.insert(0, datetime.now().year)
        
        with c_yil: secilen_yil = st.selectbox("Yıl", ["Tüm"] + list(yil_list), label_visibility="collapsed")
        with c_ay: 
            idx = datetime.now().month if secilen_yil == datetime.now().year else 0
            secilen_ay = st.selectbox("Ay", ["Tüm"] + AYLAR, index=idx, label_visibility="collapsed")
        
        if secilen_yil == "Tüm": df_filt = df
        else:
            df_filt = df[df["Tarih"].dt.year == secilen_yil]
            if secilen_ay != "Tüm":
                ay_no = AYLAR.index(secilen_ay) + 1
                df_filt = df_filt[df_filt["Tarih"].dt.month == ay_no]

    # Ek Araçlar
    if not arama_modu and secilen_ay != "Tüm" and secilen_yil != "Tüm":
        with st.expander("🛠️ Kopyala / İndir"):
            ec1, ec2 = st.columns(2)
            with ec1: st.download_button("📥 Excel", csv_indir(df), "yedek.csv", "text/csv", use_container_width=True)
            with ec2:
                if st.button("⏮️ Kopyala", use_container_width=True):
                    hy = secilen_yil; ha = AYLAR.index(secilen_ay) + 1
                    if ha == 1: ka = 12; ky = hy - 1
                    else: ka = ha - 1; ky = hy
                    kdf = df[(df["Tarih"].dt.year == ky) & (df["Tarih"].dt.month == ka) & (df["Tür"] == "Gider")]
                    if not kdf.empty:
                        kopya = []
                        for _, r in kdf.iterrows():
                            kb = df_kat[df_kat["Kategori"] == r["Kategori"]]
                            if not kb.empty and int(float(kb.iloc[0]["VarsayilanGun"])) > 0:
                                vg = int(float(kb.iloc[0]["VarsayilanGun"]))
                                yt = tarih_olustur(hy, secilen_ay, vg)
                                kopya.append({"Tarih": pd.to_datetime(yt), "Kategori": r["Kategori"], "Tür": "Gider", "Tutar": r["Tutar"], "Son Ödeme Tarihi": son_odeme_hesapla(yt, vg), "Açıklama": f"{r['Açıklama']} (Kopya)", "Durum": False})
                        if kopya: verileri_kaydet(conn, pd.concat([df, pd.DataFrame(kopya)], ignore_index=True)); st.success("Tamam"); time.sleep(1); st.rerun()
                        else: st.warning("Sabit yok")
                    else: st.error("Veri yok")

    st.write("")

    # 3. KARTLAR (CSS GRID İLE OTOMATİK DÜZEN)
    if not df_filt.empty:
        gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
        gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
        net = gelir - gider
        bekleyen = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]["Tutar"].sum()
        
        ik = "😐"; cr = RENK_NET
        if net > 0: ik = "😃"; cr = RENK_GELIR
        elif net < 0: ik = "☹️"; cr = RENK_GIDER
        
        # HTML GRID YAPISI (BİLGİSAYARDA 4, TELEFONDA 2 KOLON)
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
        </div>
        """, unsafe_allow_html=True)
    else: st.info("Kayıt yok.")

    st.write("")
    
    # 4. SEKMELER
    t1, t2, t3, t4 = st.tabs(["📝 Ekle", "📊 Grafik", "📋 Liste", "📂 Ayar"])

    with t1:
        if arama_modu: st.warning("Aramayı kapatın")
        else:
            with st.container(border=True):
                c_k, c_t = st.columns([1.5, 1])
                with c_k:
                    ts = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
                    kl = df_kat[df_kat["Tur"]==ts]["Kategori"].tolist() if not df_kat.empty else []
                    ks = st.selectbox("Kat.", kl, index=None, label_visibility="collapsed", placeholder="Seç...")
                with c_t:
                    st.write("")
                    tug = st.number_input("Tutar", step=50.0, label_visibility="collapsed", placeholder="0.00 ₺")
                ac = st.text_input("Not", placeholder="#etiket")
                if st.button("KAYDET", type="primary", use_container_width=True):
                    if secilen_yil == "Tüm" or secilen_ay == "Tüm": st.error("Yıl/Ay Seç")
                    elif ks and tug > 0:
                        vg = 0
                        if not df_kat.empty:
                            r = df_kat[df_kat["Kategori"]==ks]
                            if not r.empty: vg = int(float(r.iloc[0]["VarsayilanGun"]))
                        kt = tarih_olustur(secilen_yil, secilen_ay, vg)
                        yeni = pd.DataFrame([{"Tarih": pd.to_datetime(kt), "Kategori": ks, "Tür": ts, "Tutar": float(tug), "Son Ödeme Tarihi": son_odeme_hesapla(kt, vg), "Açıklama": ac, "Durum": False}])
                        verileri_kaydet(conn, pd.concat([df, yeni], ignore_index=True)); st.success("Ok"); time.sleep(0.5); st.rerun()
                    else: st.warning("Eksik")

    with t2:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sg = df_filt[df_filt["Tür"]=="Gider"].copy()
            sg["D"] = sg["Durum"].map({True:"Ödendi", False:"Bekliyor"})
            c_g1, c_g2 = st.columns(2)
            with c_g1: st.caption("Durum"); st.plotly_chart(px.pie(sg, values="Tutar", names="D", hole=0.5, color="D", color_discrete_map={"Ödendi":RENK_GELIR, "Bekliyor":RENK_GIDER}).update_layout(margin=dict(t=0,b=0,l=0,r=0), height=180, showlegend=False), use_container_width=True)
            with c_g2: st.caption("Kategori"); st.plotly_chart(px.pie(sg, values="Tutar", names="Kategori", hole=0.5).update_layout(margin=dict(t=0,b=0,l=0,r=0), height=180, showlegend=False), use_container_width=True)
            edf = etiketleri_analiz_et(sg)
            if not edf.empty: st.caption("Etiketler"); st.plotly_chart(px.bar(edf, x="Etiket", y="Tutar").update_layout(height=200, showlegend=False), use_container_width=True)
        else: st.info("Veri yok")

    with t3:
        if not df_filt.empty:
            edt = df_filt.sort_values("Tarih", ascending=False).copy()
            edt["Tarih"] = edt["Tarih"].dt.date
            if "Son Ödeme Tarihi" in edt.columns: edt["Son Ödeme Tarihi"] = pd.to_datetime(edt["Son Ödeme Tarihi"], errors='coerce').dt.date
            if arama_modu: st.dataframe(edt, hide_index=True, use_container_width=True)
            else:
                duz = st.data_editor(edt, column_config={"Durum": st.column_config.CheckboxColumn(default=False), "Tutar": st.column_config.NumberColumn(format="%.0f"), "Kategori": st.column_config.SelectboxColumn(options=df_kat["Kategori"].unique().tolist()), "Tür": st.column_config.SelectboxColumn(options=["Gider", "Gelir"])}, hide_index=True, use_container_width=True, num_rows="dynamic")
                if st.button("💾 Kaydet", use_container_width=True):
                    dfr = df.drop(df_filt.index); duz["Tarih"] = pd.to_datetime(duz["Tarih"])
                    verileri_kaydet(conn, pd.concat([dfr, duz], ignore_index=True)); st.success("Ok"); st.rerun()
        else: st.write("Boş")

    with t4:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("ke"):
                kt = st.radio("T", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
                ka = st.text_input("Ad", label_visibility="collapsed", placeholder="Yeni Kategori")
                kg = st.number_input("Gün", 0, 31, 0, label_visibility="collapsed")
                if st.form_submit_button("Ekle"):
                    gk = conn.read(worksheet="Kategoriler", ttl=0) if not df_kat.empty else df_kat
                    if ka and ka not in gk["Kategori"].values:
                        kategorileri_kaydet(conn, pd.concat([gk, pd.DataFrame([{"Kategori": ka, "Tur": kt, "VarsayilanGun": kg}])], ignore_index=True)); st.success("Ok"); st.rerun()
        with c2:
            if not df_kat.empty:
                sk = st.selectbox("Sil", df_kat["Kategori"].tolist(), label_visibility="collapsed")
                if st.button("Sil", type="primary", use_container_width=True):
                    if sk in df["Kategori"].values: st.error("Dolu!")
                    else: kategorileri_kaydet(conn, df_kat[df_kat["Kategori"]!=sk]); st.success("Ok"); st.rerun()
