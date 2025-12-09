import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection
import time
import re
import yfinance as yf

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Bütçe Makinesi v41", page_icon="🐦", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    /* Mobilde üst ve alt boşlukları ayarla */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    
    div.kpi-card {
        background-color: white;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 5px;
    }
    div.kpi-title {
        color: #6c757d;
        font-size: 0.75rem; 
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 0;
    }
    div.kpi-value {
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
</style>
""", unsafe_allow_html=True)

# --- RENK PALETİ & SABİTLER ---
RENK_GELIR = "#28a745"
RENK_GIDER = "#dc3545"
RENK_NET = "#007bff"
RENK_ODENMEMIS = "#ffc107"
KOLONLAR = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# --- YARDIMCI FONKSİYONLAR ---
def kpi_kart_ciz(baslik, deger, renk, ikon):
    st.markdown(f"""
    <div class="kpi-card" style="border-left: 4px solid {renk};">
        <div class="kpi-title">{baslik}</div>
        <div class="kpi-value" style="color: {renk};">{ikon} {deger}</div>
    </div>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=3600) 
def piyasa_verileri_getir():
    try:
        tickers = yf.download("TRY=X EURTRY=X GC=F", period="1d", progress=False)['Close']
        dolar = tickers['TRY=X'].iloc[-1]
        euro = tickers['EURTRY=X'].iloc[-1]
        ons_altin = tickers['GC=F'].iloc[-1]
        gram_altin = (ons_altin / 31.1035) * dolar
        return dolar, euro, gram_altin
    except: return 0, 0, 0

def csv_indir(df): return df.to_csv(index=False).encode('utf-8')

# --- VERİ İŞLEMLERİ (BAĞLANTIYI GEREKTİĞİNDE AÇACAĞIZ) ---
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

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

# ==========================================
# --- UYGULAMA MANTIĞI (BLOK SİSTEMİ) ---
# ==========================================

# Oturum Durumu Kontrolü
if "giris_yapildi" not in st.session_state:
    st.session_state.giris_yapildi = False

# --- EKRAN 1: GİRİŞ EKRANI ---
if not st.session_state.giris_yapildi:
    # Eğer secrets yoksa (Lokal mod) direkt geçir
    if "genel" not in st.secrets:
        st.session_state.giris_yapildi = True
        st.rerun()
    else:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>🐦 Bütçe Makinesi</h3>", unsafe_allow_html=True)
            sifre = st.text_input("Şifre", type="password")
            if st.button("Giriş Yap", type="primary", use_container_width=True):
                if sifre == st.secrets["genel"]["sifre"]:
                    st.session_state.giris_yapildi = True
                    st.rerun()
                else:
                    st.error("Hatalı Şifre!")

# --- EKRAN 2: ANA UYGULAMA (Sadece giriş yapıldıysa çalışır) ---
else:
    # Bağlantıyı ve Verileri Burada Başlatıyoruz
    conn = get_connection()
    df = verileri_cek(conn)
    df_kat = kategorileri_cek(conn)

    # Veri Tipi Düzeltmeleri
    if not df.empty:
        df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
        df = df.dropna(subset=["Tarih"])
        if "Durum" in df.columns:
            df["Durum"] = df["Durum"].astype(str).str.lower().map({'true': True, 'false': False, '1.0': True, '0.0': False, '1': True, '0': False, 'nan': False}).fillna(False)
        else: df["Durum"] = False
        if "Tutar" in df.columns: df["Tutar"] = pd.to_numeric(df["Tutar"], errors='coerce').fillna(0.0)
        else: df["Tutar"] = 0.0

    # --- ÜST BAŞLIK & YENİLEME ---
    col_header, col_refresh = st.columns([0.80, 0.20], gap="small")
    with col_header: st.markdown("### 🐦 Bütçe Makinesi")
    with col_refresh:
        if st.button("🔄", help="Yenile", use_container_width=True):
            st.cache_data.clear(); st.rerun()

    # --- ANA EKRAN KONTROLLERİ ---
    c_arama_btn, c_yil_ana, c_ay_ana = st.columns([0.15, 0.35, 0.50], gap="small")
    with c_arama_btn:
        arama_aktif = st.checkbox("🔍", help="Arama Modunu Aç")

    if arama_aktif:
        with c_yil_ana: st.write("") 
        with c_ay_ana: arama_terimi = st.text_input("Kelime Ara...", label_visibility="collapsed", placeholder="Migros...")
        if arama_terimi:
            mask = df.astype(str).apply(lambda x: x.str.contains(arama_terimi, case=False)).any(axis=1)
            df_filt = df[mask]; baslik = f"🔍 '{arama_terimi}'"; ay_no = 0; secilen_ay_filtre = "Arama"
        else: df_filt = df; baslik = "Tüm Kayıtlar"; ay_no = 0; secilen_ay_filtre = "Yılın Tamamı"
    else:
        arama_terimi = None
        if not df.empty and "Tarih" in df.columns:
            yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True)
            if datetime.now().year not in yil_list: yil_list.insert(0, datetime.now().year)
            with c_yil_ana: secilen_yil_filtre = st.selectbox("Yıl", ["Tüm Zamanlar"] + list(yil_list), label_visibility="collapsed")
            with c_ay_ana:
                now = datetime.now(); varsayilan_ay = now.month if secilen_yil_filtre == now.year else 0
                secilen_ay_filtre = st.selectbox("Ay", ["Yılın Tamamı"] + AYLAR, index=varsayilan_ay, label_visibility="collapsed")
            if secilen_yil_filtre == "Tüm Zamanlar": df_filt = df; baslik = "Tüm Zamanlar"; ay_no = 0
            else:
                df_filt = df[df["Tarih"].dt.year == secilen_yil_filtre]
                if secilen_ay_filtre != "Yılın Tamamı":
                    ay_no = AYLAR.index(secilen_ay_filtre) + 1
                    df_filt = df_filt[df_filt["Tarih"].dt.month == ay_no]; baslik = f"{secilen_ay_filtre} {secilen_yil_filtre}"
                else: baslik = f"{secilen_yil_filtre} Tamamı"; ay_no = 0
        else: df_filt = df; baslik = "Veri Yok"; ay_no = 0

    # --- EK ARAÇLAR (KOPYALA) ---
    if not arama_aktif and secilen_ay_filtre != "Yılın Tamamı" and secilen_yil_filtre != "Tüm Zamanlar":
        with st.expander("🛠️ İşlemler"):
            c_kopya, c_indir = st.columns(2)
            with c_indir: st.download_button("📥 Excel", csv_indir(df), f"Yedek.csv", "text/csv", use_container_width=True)
            with c_kopya:
                if st.button("⏮️ Ayı Kopyala", use_container_width=True):
                    hy = secilen_yil_filtre; ha = ay_no
                    if ha == 1: ka = 12; ky = hy - 1
                    else: ka = ha - 1; ky = hy
                    kdf = df[(df["Tarih"].dt.year == ky) & (df["Tarih"].dt.month == ka) & (df["Tür"] == "Gider")]
                    if not kdf.empty:
                        kopya = []
                        for _, row in kdf.iterrows():
                            kb = df_kat[df_kat["Kategori"] == row["Kategori"]]
                            if not kb.empty and int(float(kb.iloc[0]["VarsayilanGun"])) > 0:
                                vg = int(float(kb.iloc[0]["VarsayilanGun"]))
                                yt = tarih_olustur(hy, secilen_ay_filtre, vg)
                                yso = son_odeme_hesapla(yt, vg)
                                kopya.append({"Tarih": pd.to_datetime(yt), "Kategori": row["Kategori"], "Tür": "Gider", "Tutar": row["Tutar"], "Son Ödeme Tarihi": yso, "Açıklama": f"{row['Açıklama']} (Kopya)", "Durum": False})
                        if kopya: verileri_kaydet(conn, pd.concat([df, pd.DataFrame(kopya)], ignore_index=True)); st.success("Tamam"); time.sleep(1); st.rerun()
                        else: st.warning("Sabit yok.")
                    else: st.error("Veri yok.")

    st.write("") 

    # --- KPI KARTLARI ---
    if not df_filt.empty:
        gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
        gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
        net = gelir - gider
        bekleyen = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]["Tutar"].sum()
        if net > 0: net_ikon = "😃"; net_renk = RENK_GELIR
        elif net < 0: net_ikon = "☹️"; net_renk = RENK_GIDER
        else: net_ikon = "😐"; net_renk = RENK_NET
        
        row1_c1, row1_c2 = st.columns(2)
        with row1_c1: kpi_kart_ciz("GELİR", f"{gelir:,.0f} ₺", RENK_GELIR, "💰")
        with row1_c2: kpi_kart_ciz("GİDER", f"{gider:,.0f} ₺", RENK_GIDER, "💸")
        row2_c1, row2_c2 = st.columns(2)
        with row2_c1: kpi_kart_ciz("NET", f"{net:,.0f} ₺", net_renk, net_ikon)
        with row2_c2: kpi_kart_ciz("ÖDENMEMİŞ", f"{bekleyen:,.0f} ₺", RENK_ODENMEMIS, "⏳")
    else: st.info("Kayıt yok.")

    # --- SEKMELER ---
    st.write("")
    tab_giris, tab_analiz, tab_liste, tab_yonetim = st.tabs(["📝 Ekle", "📊 Grafik", "📋 Kayıt", "📂 Ayar"])

    with tab_giris:
        if arama_terimi: st.warning("Aramayı kapatın.")
        else:
            with st.container(border=True):
                c_gir1, c_gir2 = st.columns([1.5, 1])
                with c_gir1:
                    tur_sec = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
                    kat_list = df_kat[df_kat["Tur"] == tur_sec]["Kategori"].tolist() if not df_kat.empty else []
                    kat_sec = st.selectbox("Kategori", kat_list, index=None, placeholder="Kategori...", label_visibility="collapsed")
                with c_gir2:
                    st.write("") 
                    tutar_gir = st.number_input("Tutar", min_value=0.0, step=50.0, label_visibility="collapsed", placeholder="0.00 ₺")
                aciklama_gir = st.text_input("Açıklama", placeholder="#etiket (Opsiyonel)")
                if st.button("KAYDET", type="primary", use_container_width=True):
                    if secilen_yil_filtre == "Tüm Zamanlar" or secilen_ay_filtre == "Yılın Tamamı": st.error("Yıl/Ay Seç!")
                    elif kat_sec and tutar_gir > 0:
                        vg = 0
                        if not df_kat.empty:
                            r = df_kat[df_kat["Kategori"]==kat_sec]
                            if not r.empty: vg = int(float(r.iloc[0]["VarsayilanGun"]))
                        kt = tarih_olustur(secilen_yil_filtre, secilen_ay_filtre, vg)
                        so = son_odeme_hesapla(kt, vg)
                        yeni = pd.DataFrame([{"Tarih": pd.to_datetime(kt), "Kategori": kat_sec, "Tür": tur_sec, "Tutar": float(tutar_gir), "Son Ödeme Tarihi": so, "Açıklama": aciklama_gir, "Durum": False}])
                        verileri_kaydet(conn, pd.concat([df, yeni], ignore_index=True))
                        st.toast("✅ Kaydedildi!"); time.sleep(0.5); st.cache_data.clear(); st.rerun()
                    else: st.warning("Eksik bilgi!")

    with tab_analiz:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sg = df_filt[df_filt["Tür"]=="Gider"].copy()
            sg["Durum_Etiket"] = sg["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Durum")
                fig1 = px.pie(sg, values="Tutar", names="Durum_Etiket", hole=0.5, color="Durum_Etiket", color_discrete_map={"Ödendi ✅": RENK_GELIR, "Ödenmedi ❌": RENK_GIDER})
                fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200, showlegend=False); st.plotly_chart(fig1, use_container_width=True)
            with c2:
                st.caption("Kategori")
                fig2 = px.pie(sg, values="Tutar", names="Kategori", hole=0.5)
                fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200, showlegend=False); st.plotly_chart(fig2, use_container_width=True)
        else: st.info("Veri yok.")

    with tab_liste:
        col_list_baslik, col_list_btn = st.columns([0.8, 0.2])
        with col_list_baslik: st.caption("Kayıtlar")
        with col_list_btn: st.download_button("📥", csv_indir(df), f"Yedek.csv", "text/csv", use_container_width=True)
        if not df_filt.empty:
            edt = df_filt.sort_values("Tarih", ascending=False).copy()
            edt["Tarih"] = edt["Tarih"].dt.date
            if "Son Ödeme Tarihi" in edt.columns: edt["Son Ödeme Tarihi"] = pd.to_datetime(edt["Son Ödeme Tarihi"], errors='coerce').dt.date
            if arama_terimi: st.dataframe(edt, hide_index=True, use_container_width=True)
            else:
                duzenli = st.data_editor(edt, column_config={"Durum": st.column_config.CheckboxColumn(default=False), "Tutar": st.column_config.NumberColumn(format="%.2f ₺"), "Kategori": st.column_config.SelectboxColumn(options=df_kat["Kategori"].unique().tolist()), "Tür": st.column_config.SelectboxColumn(options=["Gider", "Gelir"])}, hide_index=True, use_container_width=True, num_rows="dynamic")
                if st.button("💾 Kaydet", use_container_width=True):
                    dfr = df.drop(df_filt.index); duzenli["Tarih"] = pd.to_datetime(duzenli["Tarih"])
                    verileri_kaydet(conn, pd.concat([dfr, duzenli], ignore_index=True)); st.success("Güncellendi"); st.cache_data.clear(); st.rerun()
        else: st.write("Veri yok.")

    with tab_yonetim:
        c_ekle, c_duzenle = st.columns(2)
        with c_ekle:
            with st.form("kat_ekle"):
                kt = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
                ka = st.text_input("Yeni Kategori")
                kg = st.number_input("Varsayılan Gün", 0, 31, 0)
                if st.form_submit_button("Ekle"):
                    gk = conn.read(worksheet="Kategoriler", ttl=0) if not df_kat.empty else df_kat
                    if ka and ka not in gk["Kategori"].values:
                        kategorileri_kaydet(conn, pd.concat([gk, pd.DataFrame([{"Kategori": ka, "Tur": kt, "VarsayilanGun": kg}])], ignore_index=True)); st.success("Eklendi!"); st.rerun()
        with c_duzenle:
            if not df_kat.empty:
                sel_k = st.selectbox("Düzenle", df_kat["Kategori"].tolist())
                row_k = df_kat[df_kat["Kategori"] == sel_k].iloc[0]
                new_ad = st.text_input("Ad", value=row_k['Kategori'])
                new_tur = st.selectbox("Tür", ["Gider", "Gelir"], index=0 if row_k['Tur']=="Gider" else 1)
                new_gun = st.number_input("Gün", 0, 31, int(float(row_k['VarsayilanGun'])))
                c_upd, c_del = st.columns(2)
                if c_upd.button("Güncelle"):
                    df_kat.loc[df_kat["Kategori"]==sel_k, ["Kategori","Tur","VarsayilanGun"]] = [new_ad, new_tur, new_gun]
                    kategorileri_kaydet(conn, df_kat)
                    if sel_k != new_ad and not df.empty: df.loc[df["Kategori"]==sel_k, "Kategori"] = new_ad; verileri_kaydet(conn, df)
                    st.success("Oldu!"); st.rerun()
                if c_del.button("Sil"):
                    if sel_k in df["Kategori"].values: st.error("Kullanımda!")
                    else: kategorileri_kaydet(conn, df_kat[df_kat["Kategori"]!=sel_k]); st.success("Silindi"); st.rerun()

    # --- SIDEBAR (Sadece Piyasa & Çıkış) ---
    with st.sidebar:
        st.caption("Piyasa (Canlı)")
        usd, eur, gram = piyasa_verileri_getir()
        if usd > 0:
            st.write(f"💵 **USD:** {usd:.2f} ₺")
            st.write(f"💶 **EUR:** {eur:.2f} ₺")
            st.write(f"🥇 **ALTIN:** {gram:.0f} ₺")
        st.markdown("---")
        if st.button("🚪 Çıkış", use_container_width=True): st.session_state.giris_yapildi = False; st.rerun()
