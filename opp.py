import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- SAYFA YAPISI (En başta olmalı) ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")

# --- CSS İLE SIKIŞTIRMA (Boşlukları Azaltma) ---
st.markdown("""
    <style>
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        div[data-testid="stMetric"] {background-color: #f0f2f6; border-radius: 10px; padding: 10px;}
    </style>
""", unsafe_allow_html=True)

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
ESKI_SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- FONKSİYONLAR ---
def sistem_baslat():
    # 1. KATEGORİ DOSYASI
    if not os.path.exists(KATEGORI_DOSYASI):
        varsayilanlar = [
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Kira", "Tur": "Gider", "VarsayilanGun": 1},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0},
        ]
        pd.DataFrame(varsayilanlar).to_csv(KATEGORI_DOSYASI, index=False)
    else:
        df = pd.read_csv(KATEGORI_DOSYASI)
        degisiklik = False
        if "VarsayilanGun" not in df.columns:
            df["VarsayilanGun"] = 0; degisiklik = True
        if "Tur" not in df.columns:
            df["Tur"] = "Gider"; degisiklik = True
        if degisiklik: df.to_csv(KATEGORI_DOSYASI, index=False)

    # 2. ESKİ SİSTEM MIGRATION
    if os.path.exists(ESKI_SABITLER_DOSYASI):
        try:
            df_eski = pd.read_csv(ESKI_SABITLER_DOSYASI)
            df_kat = pd.read_csv(KATEGORI_DOSYASI)
            for _, row in df_eski.iterrows():
                isim = row.get("Sabit Kalem"); gun = row.get("Odeme Gunu", 0)
                if isim and isim not in df_kat["Kategori"].values:
                    yeni = pd.DataFrame([{"Kategori": isim, "Tur": "Gider", "VarsayilanGun": gun}])
                    df_kat = pd.concat([df_kat, yeni], ignore_index=True)
            df_kat.to_csv(KATEGORI_DOSYASI, index=False)
            os.rename(ESKI_SABITLER_DOSYASI, "sabit_giderler_yedek.bak")
        except: pass

    # 3. VERİ DOSYASI
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])
        df.to_csv(VERI_DOSYASI, index=False)
    else:
        df = pd.read_csv(VERI_DOSYASI)
        if "Son Ödeme Tarihi" not in df.columns:
            df["Son Ödeme Tarihi"] = None; df.to_csv(VERI_DOSYASI, index=False)

def verileri_oku(yol): return pd.read_csv(yol)
def dosya_kaydet(df, yol): df.to_csv(yol, index=False)

def tarih_onerisi_hesapla(gun):
    if not gun or gun == 0: return None
    bugun = date.today()
    try: h_gun = int(gun)
    except: return None
    if not (1 <= h_gun <= 31): return None
    try: bu_ay = date(bugun.year, bugun.month, h_gun)
    except: bu_ay = date(bugun.year, bugun.month, 28)
    if bu_ay >= bugun: return bu_ay
    else:
        s_ay = bugun.month + 1 if bugun.month < 12 else 1
        yil = bugun.year if bugun.month < 12 else bugun.year + 1
        try: return date(yil, s_ay, h_gun)
        except: return date(yil, s_ay, 28)

# --- BAŞLANGIÇ ---
sistem_baslat()
try:
    df = verileri_oku(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    df_kat = verileri_oku(KATEGORI_DOSYASI)
except: df = pd.DataFrame(); df_kat = pd.DataFrame()

# --- YAN MENÜ (Gizli Kahraman) ---
with st.sidebar:
    st.header("⚙️ Ayarlar & Filtre")
    
    # FİLTRELEME
    if not df.empty:
        yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True)
        sec_yil = st.selectbox("Yıl", yil_list)
        ay_map = {i: ay for i, ay in enumerate(["Tümü", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
        sec_ay = st.selectbox("Ay", list(ay_map.keys()), format_func=lambda x: ay_map[x], index=datetime.now().month)
        
        df_filt = df[df["Tarih"].dt.year == sec_yil]
        if sec_ay != 0: df_filt = df_filt[df_filt["Tarih"].dt.month == sec_ay]; baslik = f"{ay_map[sec_ay]} {sec_yil}"
        else: baslik = f"{sec_yil} Tamamı"
    else: df_filt = df; baslik = "Veri Yok"

    st.divider()
    
    # KATEGORİ YÖNETİMİ (Sidebar'da kalsın, yer kaplamasın)
    with st.expander("Kategori Ekle/Sil"):
        y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
        y_ad = st.text_input("Adı")
        y_gun = st.number_input("Gün (Varsa)", 0, 31, 0) if y_tur == "Gider" else 0
        if st.button("Ekle/Güncelle"):
            if y_ad:
                df_kat = df_kat[df_kat["Kategori"] != y_ad]
                yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun}])
                df_kat = pd.concat([df_kat, yeni], ignore_index=True)
                dosya_kaydet(df_kat, KATEGORI_DOSYASI); st.rerun()
        
        if st.button("Seçili Kategoriyi Sil"):
            if not df_kat.empty:
                df_kat = df_kat.iloc[:-1] # Son ekleneni siler (Basitlik için)
                dosya_kaydet(df_kat, KATEGORI_DOSYASI); st.rerun()

# --- ÜST BİLGİ KARTLARI (METRICS) ---
st.title("🐦 Kuşların Bütçe Makinesi")

if not df_filt.empty:
    gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Toplam Gelir", f"{gelir:,.0f} ₺")
    k2.metric("Toplam Gider", f"{gider:,.0f} ₺")
    k3.metric("Net Durum", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")
else:
    st.info("Bu dönem için veri yok.")

st.divider()

# --- ANA GÖVDE (İKİ KOLONLU YAPI) ---
col_sol, col_sag = st.columns([1, 1.2])

# --- SOL KOLON: VERİ GİRİŞİ ---
with col_sol:
    st.subheader("📝 Hızlı Ekle")
    with st.container(border=True): # Çerçeve içine aldık
        c_tur1, c_tur2 = st.columns(2)
        with c_tur1:
            tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
        
        kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
        secilen_kat = st.selectbox("Kategori", kat_listesi)
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)
        
        # Detaylar
        aciklama = st.text_input("Açıklama", placeholder="Opsiyonel...")
        
        # Tarih Mantığı
        varsayilan_gun = 0
        son_odeme = None
        if secilen_kat and not df_kat.empty:
            row = df_kat[df_kat["Kategori"] == secilen_kat]
            if not row.empty: varsayilan_gun = int(row.iloc[0]["VarsayilanGun"])
            
        if tur_secimi == "Gider" and varsayilan_gun > 0:
            oneri = tarih_onerisi_hesapla(varsayilan_gun)
            st.caption(f"📅 Ödeme Günü: {varsayilan_gun}")
            son_odeme = st.date_input("Son Ödeme", value=oneri)
        elif tur_secimi == "Gider":
             son_odeme = st.date_input("Son Ödeme (Opsiyonel)", value=None)

        if st.button("KAYDET", type="primary", use_container_width=True):
            if secilen_kat:
                yeni_satir = pd.DataFrame({
                    "Tarih": [date.today()], # Giriş tarihi hep bugündür
                    "Kategori": [secilen_kat],
                    "Tür": [tur_secimi],
                    "Tutar": [tutar],
                    "Son Ödeme Tarihi": [son_odeme],
                    "Açıklama": [aciklama]
                })
                df = pd.concat([df, yeni_satir], ignore_index=True)
                dosya_kaydet(df, VERI_DOSYASI)
                st.success("Kaydedildi!")
                st.rerun()
            else:
                st.error("Kategori seç!")

# --- SAĞ KOLON: ANALİZ VE LİSTE ---
with col_sag:
    # Sekmelerle alanı verimli kullanalım
    tab_grafik, tab_liste = st.tabs(["📊 Analiz", "📋 Son İşlemler"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub_df = df_filt[df_filt["Tür"] == "Gider"]
            # Grafiği küçültelim ki sığsın
            fig = px.pie(sub_df, values="Tutar", names="Kategori", hole=0.5)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig, use_container_width=True)
            
            # Altına mini bar grafik
            grp = sub_df.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False).head(5)
            st.bar_chart(grp, x="Kategori", y="Tutar", height=200)
        else:
            st.write("Grafik için veri yok.")

    with tab_liste:
        # Tabloyu KISITLI YÜKSEKLİKTE (height=400) gösteriyoruz.
        # Böylece sayfa uzamıyor, tablo içinde scroll oluyor.
        st.dataframe(
            df_filt.sort_values("Tarih", ascending=False), 
            use_container_width=True, 
            height=450, 
            hide_index=True
        )
        
        # Silme butonu listenin hemen altında
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            sil_id = st.selectbox("Silinecek", df.index, format_func=lambda x: f"{df.loc[x,'Tutar']}₺ - {df.loc[x,'Kategori']}", label_visibility="collapsed")
        with col_del2:
            if st.button("Sil"):
                df = df.drop(sil_id).reset_index(drop=True)
                dosya_kaydet(df, VERI_DOSYASI); st.rerun()
