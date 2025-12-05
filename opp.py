import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection
import time
import re
import yfinance as yf

# --- 1. SAYFA VE TASARIM AYARLARI ---
st.set_page_config(page_title="Bütçe Makinesi", page_icon="🐦", layout="wide")

# --- CUSTOM CSS (GÖZE HİTAP EDEN AYARLAR) ---
st.markdown("""
    <style>
        /* Sayfa üst boşluğunu al */
        .block-container {padding-top: 1rem; padding-bottom: 1rem;}
        /* Metrik kutularını kart gibi göster */
        [data-testid="stMetric"] {
            background-color: #f9f9f9;
            border: 1px solid #e0e0e0;
            padding: 10px;
            border-radius: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        }
        /* Koyu mod desteği için metrik yazı rengi */
        @media (prefers-color-scheme: dark) {
            [data-testid="stMetric"] {
                background-color: #262730;
                border: 1px solid #464b5c;
            }
        }
    </style>
""", unsafe_allow_html=True)

# --- GÜVENLİK ---
def giris_kontrol():
    if "giris_yapildi" not in st.session_state: st.session_state.giris_yapildi = False
    if "genel" not in st.secrets: st.session_state.giris_yapildi = True; return
    if not st.session_state.giris_yapildi:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown("### 🔒 Güvenli Giriş")
            sifre = st.text_input("Şifre", type="password", label_visibility="collapsed", placeholder="Şifrenizi girin...")
            if st.button("Giriş Yap", type="primary", use_container_width=True):
                if sifre == st.secrets["genel"]["sifre"]:
                    st.session_state.giris_yapildi = True; st.rerun()
                else: st.error("Hatalı Şifre!")
        st.stop()

giris_kontrol()

# --- BAĞLANTI & SABİTLER ---
conn = st.connection("gsheets", type=GSheetsConnection)
KOLONLAR = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
RENK_PALETI = {"Gider": "#FF4B4B", "Gelir": "#00CC96", "Ödendi ✅": "#00CC96", "Ödenmedi ❌": "#EF553B"}

# --- FONKSİYONLAR ---
def verileri_cek():
    try:
        df = conn.read(worksheet="Veriler", ttl=0)
        if df.empty or "Tarih" not in df.columns: return pd.DataFrame(columns=KOLONLAR)
        df = df.dropna(how="all")
        for col in KOLONLAR:
            if col not in df.columns: df[col] = pd.NA
        return df
    except: return pd.DataFrame(columns=KOLONLAR)

def kategorileri_cek():
    varsayilan = pd.DataFrame([{"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 1}, {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}])
    try:
        df = conn.read(worksheet="Kategoriler", ttl=0)
        if df.empty: conn.update(worksheet="Kategoriler", data=varsayilan); return varsayilan
        if "Kategori" not in df.columns: return varsayilan
        return df.dropna(how="all")
    except: return varsayilan

def verileri_kaydet(df):
    save_df = df.copy()
    save_df["Tarih"] = save_df["Tarih"].astype(str).replace('NaT', '')
    save_df["Son Ödeme Tarihi"] = save_df["Son Ödeme Tarihi"].astype(str).replace('NaT', '')
    save_df = save_df.fillna("") 
    for col in KOLONLAR:
        if col not in save_df.columns: save_df[col] = ""
    conn.update(worksheet="Veriler", data=save_df[KOLONLAR])

def kategorileri_kaydet(df): conn.update(worksheet="Kategoriler", data=df)

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

# --- BAŞLATMA ---
df = verileri_cek()
df_kat = kategorileri_cek()

if not df.empty:
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    if "Durum" in df.columns:
        df["Durum"] = df["Durum"].astype(str).str.lower().map({'true': True, 'false': False, '1.0': True, '0.0': False, '1': True, '0': False, 'nan': False}).fillna(False)
    else: df["Durum"] = False
    if "Tutar" in df.columns: df["Tutar"] = pd.to_numeric(df["Tutar"], errors='coerce').fillna(0.0)
    else: df["Tutar"] = 0.0

# --- YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    st.markdown("### 🐦 Bütçe Makinesi")
    if st.button("🔄 Verileri Güncelle", type="primary", use_container_width=True):
        st.cache_data.clear(); st.rerun()

    # PİYASA KARTI
    with st.container(border=True):
        st.caption("💰 PİYASA (Canlı)")
        usd, eur, gram = piyasa_verileri_getir()
        if usd > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("USD", f"{usd:.2f}")
            c2.metric("EUR", f"{eur:.2f}")
            c3.metric("ALTIN", f"{gram:.0f}")
        else: st.caption("Veri yok")

    # DÖNEM FİLTRESİ
    st.markdown("---")
    arama_terimi = st.text_input("🔍 Ara...", placeholder="Migros, Tatil...")
    
    if not arama_terimi:
        secilen_yil_filtre = datetime.now().year; secilen_ay_filtre = "Yılın Tamamı"
        if not df.empty and "Tarih" in df.columns:
            yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True)
            if datetime.now().year not in yil_list: yil_list.insert(0, datetime.now().year)
            secilen_yil_filtre = st.selectbox("📅 Yıl", ["Tüm Zamanlar"] + list(yil_list))
            if secilen_yil_filtre == "Tüm Zamanlar":
                df_filt = df; baslik = "Tüm Zamanlar"; ay_no = 0
            else:
                df_filt = df[df["Tarih"].dt.year == secilen_yil_filtre]
                now = datetime.now(); varsayilan_ay = now.month if secilen_yil_filtre == now.year else 0
                secilen_ay_filtre = st.selectbox("📅 Ay", ["Yılın Tamamı"] + AYLAR, index=varsayilan_ay)
                if secilen_ay_filtre != "Yılın Tamamı":
                    ay_no = AYLAR.index(secilen_ay_filtre) + 1
                    df_filt = df_filt[df_filt["Tarih"].dt.month == ay_no]
                    baslik = f"{secilen_ay_filtre} {secilen_yil_filtre}"
                else: baslik = f"{secilen_yil_filtre} Tamamı"; ay_no = 0
        else: df_filt = df; baslik = "Veri Yok"; ay_no = 0
    else:
        mask = df.astype(str).apply(lambda x: x.str.contains(arama_terimi, case=False)).any(axis=1)
        df_filt = df[mask]
        baslik = f"🔍 Sonuç: '{arama_terimi}'"
        ay_no = 0

    # ARAÇLAR MENÜSÜ (GİZLENEBİLİR)
    with st.expander("🛠️ Araçlar & Yedek"):
        st.download_button("📥 Excel İndir", csv_indir(df), f"Yedek.csv", "text/csv", use_container_width=True)
        if not arama_terimi and secilen_ay_filtre != "Yılın Tamamı":
            if st.button("⏮️ Geçen Ayı Kopyala", use_container_width=True):
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
                    if kopya: verileri_kaydet(pd.concat([df, pd.DataFrame(kopya)], ignore_index=True)); st.success("Kopyalandı!"); time.sleep(1); st.rerun()
                    else: st.warning("Sabit gider yok.")
                else: st.error("Veri yok.")
    
    # ÇIKIŞ
    st.markdown("---")
    if st.button("🚪 Çıkış", use_container_width=True): st.session_state.giris_yapildi = False; st.rerun()

# --- ANA SAYFA ---
# ÖZET KARTLARI (METRİKLER)
if not df_filt.empty:
    gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    bekleyen = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]["Tutar"].sum()
    
    # Trend (Değişim) Hesaplama
    delta_gider = None
    if not arama_terimi and secilen_ay_filtre != "Yılın Tamamı":
        h_yil = secilen_yil_filtre; h_ay = ay_no
        p_ay = 12 if h_ay == 1 else h_ay-1; p_yil = h_yil-1 if h_ay == 1 else h_yil
        pdf = df[(df["Tarih"].dt.year == p_yil) & (df["Tarih"].dt.month == p_ay)]
        if not pdf.empty: delta_gider = gider - pdf[pdf["Tür"] == "Gider"]["Tutar"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Toplam Gelir", f"{gelir:,.0f} ₺")
    k2.metric("Toplam Gider", f"{gider:,.0f} ₺", delta=f"{delta_gider:,.0f} ₺" if delta_gider else None, delta_color="inverse")
    k3.metric("Net Durum", f"{net:,.0f} ₺", delta_color="normal" if net>0 else "inverse")
    k4.metric("Ödenmemiş", f"{bekleyen:,.0f} ₺", delta_color="inverse")
else:
    st.info("Bu dönemde henüz veri yok.")

# --- SEKME YAPISI (DAHA TEMİZ ARAYÜZ) ---
tab_giris, tab_analiz, tab_liste, tab_yonetim = st.tabs(["📝 Ekle", "📊 Analiz", "📋 Liste & Düzenle", "📂 Kategoriler"])

# 1. SEKME: VERİ GİRİŞİ (SADELEŞTİRİLMİŞ)
with tab_giris:
    if arama_terimi:
        st.warning("⚠️ Arama modundasınız. Kayıt eklemek için aramayı temizleyin.")
    else:
        # Formu bir kutu içine alalım
        with st.container(border=True):
            col_tarih, col_kategori, col_tutar = st.columns([1, 1.5, 1])
            
            # Seçimler
            current_year = datetime.now().year; current_month = datetime.now().month
            with col_tarih:
                c_y, c_m = st.columns(2)
                y_sec = c_y.selectbox("Yıl", range(current_year-1, current_year+2), index=1, label_visibility="collapsed")
                m_sec = c_m.selectbox("Ay", AYLAR, index=current_month-1, label_visibility="collapsed")
            
            # Kategori ve Tür
            with col_kategori:
                tur_sec = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
                kat_list = df_kat[df_kat["Tur"] == tur_sec]["Kategori"].tolist() if not df_kat.empty else []
                kat_sec = st.selectbox("Kategori Seç", kat_list, index=None, placeholder="Kategori...")
            
            # Tarih Hesaplama
            vg = 0
            if kat_sec and not df_kat.empty:
                r = df_kat[df_kat["Kategori"]==kat_sec]
                if not r.empty: vg = int(float(r.iloc[0]["VarsayilanGun"]))
            kt = tarih_olustur(y_sec, m_sec, vg)
            so = son_odeme_hesapla(kt, vg)

            # Tutar
            with col_tutar:
                tutar_gir = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)

            # Alt satır (Açıklama + Buton)
            col_desc, col_btn = st.columns([3, 1])
            with col_desc:
                aciklama_gir = st.text_input("Açıklama", placeholder="#etiket ekleyebilirsin")
            with col_btn:
                st.write("") # Hizalama boşluğu
                st.write("")
                if st.button("KAYDET", type="primary", use_container_width=True):
                    if kat_sec and tutar_gir > 0:
                        yeni = pd.DataFrame([{"Tarih": pd.to_datetime(kt), "Kategori": kat_sec, "Tür": tur_sec, "Tutar": float(tutar_gir), "Son Ödeme Tarihi": so, "Açıklama": aciklama_gir, "Durum": False}])
                        verileri_kaydet(pd.concat([df, yeni], ignore_index=True))
                        st.toast("✅ Kayıt Başarılı!", icon="🎉")
                        time.sleep(1); st.cache_data.clear(); st.rerun()
                    else: st.toast("⚠️ Tutar veya Kategori eksik!", icon="asd")

# 2. SEKME: GRAFİKLER (RENKLİ VE DÜZENLİ)
with tab_analiz:
    if not df_filt.empty and "Gider" in df_filt["Tür"].values:
        sg = df_filt[df_filt["Tür"]=="Gider"].copy()
        sg["Durum_Etiket"] = sg["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
        
        c_pie1, c_pie2 = st.columns(2)
        with c_pie1:
            st.markdown("##### 💳 Ödeme Durumu")
            # Renkleri sabitliyoruz
            fig1 = px.pie(sg, values="Tutar", names="Durum_Etiket", hole=0.5, 
                         color="Durum_Etiket", color_discrete_map=RENK_PALETI)
            fig1.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=True)
            st.plotly_chart(fig1, use_container_width=True)
        
        with c_pie2:
            st.markdown("##### 🛒 Nereye Gitti?")
            fig2 = px.pie(sg, values="Tutar", names="Kategori", hole=0.5)
            fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=False)
            fig2.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### 📈 Harcama Trendi")
        trend_data = sg.groupby("Tarih")["Tutar"].sum().reset_index().sort_values("Tarih")
        fig3 = px.area(trend_data, x="Tarih", y="Tutar", markers=True)
        fig3.update_layout(margin=dict(t=10, b=0, l=0, r=0), height=250, xaxis_title="", yaxis_title="")
        fig3.update_traces(line_color="#FF4B4B", fillcolor="rgba(255, 75, 75, 0.2)")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Analiz için gider kaydı bulunamadı.")

# 3. SEKME: LİSTE VE DÜZENLEME
with tab_liste:
    if not df_filt.empty:
        edt = df_filt.sort_values("Tarih", ascending=False).copy()
        edt["Tarih"] = edt["Tarih"].dt.date
        if "Son Ödeme Tarihi" in edt.columns: edt["Son Ödeme Tarihi"] = pd.to_datetime(edt["Son Ödeme Tarihi"], errors='coerce').dt.date
        
        if arama_terimi:
            st.dataframe(edt, hide_index=True, use_container_width=True)
        else:
            duzenli = st.data_editor(
                edt,
                column_config={
                    "Durum": st.column_config.CheckboxColumn("Ödendi?", default=False),
                    "Tutar": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
                    "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                    "Kategori": st.column_config.SelectboxColumn("Kategori", options=df_kat["Kategori"].unique().tolist()),
                    "Tür": st.column_config.SelectboxColumn("Tür", options=["Gider", "Gelir"]),
                },
                hide_index=True, use_container_width=True, num_rows="dynamic"
            )
            if st.button("💾 Tabloyu Kaydet", type="secondary", use_container_width=True):
                dfr = df.drop(df_filt.index); duzenli["Tarih"] = pd.to_datetime(duzenli["Tarih"])
                verileri_kaydet(pd.concat([dfr, duzenli], ignore_index=True))
                st.toast("Tablo Güncellendi!", icon="💾"); st.cache_data.clear(); time.sleep(1); st.rerun()
    else: st.write("Veri yok.")

# 4. SEKME: KATEGORİLER
with tab_yonetim:
    c_ekle, c_duzenle = st.columns(2)
    with c_ekle:
        st.markdown("###### ➕ Yeni Kategori")
        with st.form("kat_ekle"):
            kt = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, key="kt_radio")
            ka = st.text_input("Ad")
            kg = st.number_input("Varsayılan Gün", 0, 31, 0)
            if st.form_submit_button("Ekle"):
                gk = conn.read(worksheet="Kategoriler", ttl=0) if not df_kat.empty else df_kat
                if ka not in gk["Kategori"].values:
                    kategorileri_kaydet(pd.concat([gk, pd.DataFrame([{"Kategori": ka, "Tur": kt, "VarsayilanGun": kg}])], ignore_index=True))
                    st.success("Eklendi!"); st.rerun()
                else: st.warning("Mevcut.")
    
    with c_duzenle:
        st.markdown("###### ✏️ Düzenle / Sil")
        if not df_kat.empty:
            sel_k = st.selectbox("Seç", df_kat["Kategori"].tolist(), label_visibility="collapsed")
            row_k = df_kat[df_kat["Kategori"] == sel_k].iloc[0]
            
            with st.container(border=True):
                new_ad = st.text_input("Ad", value=row_k['Kategori'])
                new_tur = st.selectbox("Tür", ["Gider", "Gelir"], index=0 if row_k['Tur']=="Gider" else 1)
                new_gun = st.number_input("Gün", 0, 31, int(float(row_k['VarsayilanGun'])))
                
                b1, b2 = st.columns(2)
                if b1.button("Güncelle", use_container_width=True):
                    df_kat.loc[df_kat["Kategori"]==sel_k, ["Kategori","Tur","VarsayilanGun"]] = [new_ad, new_tur, new_gun]
                    kategorileri_kaydet(df_kat)
                    if sel_k != new_ad and not df.empty: 
                        df.loc[df["Kategori"]==sel_k, "Kategori"] = new_ad; verileri_kaydet(df)
                    st.toast("Güncellendi"); st.rerun()
                
                if b2.button("Sil", use_container_width=True):
                    if sel_k in df["Kategori"].values: st.error("Kullanımda!")
                    else: kategorileri_kaydet(df_kat[df_kat["Kategori"]!=sel_k]); st.success("Silindi"); st.rerun()
