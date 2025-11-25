import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- 1. SAYFA AYARLARI (EN BAŞTA) ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")

# --- 2. CSS TASARIM İYİLEŞTİRMELERİ ---
st.markdown("""
    <style>
        .block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
        div[data-testid="stMetric"] {
            background-color: #ffffff; 
            border: 1px solid #e6e6e6;
            border-radius: 10px; 
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    </style>
""", unsafe_allow_html=True)

# --- 3. DOSYA AYARLARI ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
ESKI_SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- 4. SİSTEM FONKSİYONLARI ---
def sistem_baslat():
    # Kategori Dosyası Kontrolü
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
        if "VarsayilanGun" not in df.columns: df["VarsayilanGun"] = 0; degisiklik = True
        if "Tur" not in df.columns: df["Tur"] = "Gider"; degisiklik = True
        if degisiklik: df.to_csv(KATEGORI_DOSYASI, index=False)

    # Eski Sistemden Geçiş
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

    # Veri Dosyası Kontrolü
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

# --- UYGULAMA BAŞLANGICI ---
sistem_baslat()
try:
    df = verileri_oku(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    df_kat = verileri_oku(KATEGORI_DOSYASI)
except: df = pd.DataFrame(); df_kat = pd.DataFrame()

# --- 5. YAN MENÜ (FİLTRE MEKANİZMASI) ---
with st.sidebar:
    st.header("🔍 Filtreleme")
    
    if not df.empty:
        # Yılları al ve başına "Tüm Zamanlar" ekle
        yil_listesi = sorted(df["Tarih"].dt.year.unique(), reverse=True)
        secenekler = ["Tüm Zamanlar"] + list(yil_listesi)
        
        secilen_yil = st.selectbox("Dönem / Yıl", secenekler)
        
        # Filtreleme Mantığı
        if secilen_yil == "Tüm Zamanlar":
            df_filt = df
            baslik = "Tüm Zamanlar"
            # Tüm zamanlar seçiliyse Ay seçimi gizlenir
        else:
            # Yıl seçildiyse, o yılı filtrele
            df_filt = df[df["Tarih"].dt.year == secilen_yil]
            
            # Ay Seçimi
            ay_map = {i: ay for i, ay in enumerate(["Yılın Tamamı", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
            
            # Şimdiki ay varsayılan olsun
            default_index = datetime.now().month
            secilen_ay_index = st.selectbox("Ay", list(ay_map.keys()), format_func=lambda x: ay_map[x], index=default_index)
            
            if secilen_ay_index != 0: # 0 = Yılın Tamamı
                df_filt = df_filt[df_filt["Tarih"].dt.month == secilen_ay_index]
                baslik = f"{ay_map[secilen_ay_index]} {secilen_yil}"
            else:
                baslik = f"{secilen_yil} Tamamı"
    else:
        df_filt = df
        baslik = "Veri Yok"

    st.divider()
    
    # KATEGORİ EKLEME (Sidebar'da)
    with st.expander("Kategori Ekle/Sil"):
        y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
        y_ad = st.text_input("Adı", placeholder="Örn: Su Faturası")
        y_gun = st.number_input("Otomatik Gün (Varsa)", 0, 31, 0) if y_tur == "Gider" else 0
        
        if st.button("Kaydet/Güncelle"):
            if y_ad:
                df_kat = df_kat[df_kat["Kategori"] != y_ad]
                yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun}])
                df_kat = pd.concat([df_kat, yeni], ignore_index=True)
                dosya_kaydet(df_kat, KATEGORI_DOSYASI); st.rerun()
        
        if st.button("Son Ekleneni Sil"):
            if not df_kat.empty:
                df_kat = df_kat.iloc[:-1]
                dosya_kaydet(df_kat, KATEGORI_DOSYASI); st.rerun()

# --- 6. ÜST BİLGİ KARTLARI (METRICS) ---
st.title(f"🐦 Kuşların Bütçe Makinesi")
st.caption(f"Gösterilen Dönem: **{baslik}**")

# Hesaplamalar tamamen df_filt (Filtrelenmiş Veri) üzerinden yapılır
if not df_filt.empty:
    gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Gelir", f"{gelir:,.0f} ₺")
    k2.metric("Gider", f"{gider:,.0f} ₺")
    k3.metric("Net Durum", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")
else:
    st.info("Bu tarih aralığında kayıt bulunamadı.")

st.divider()

# --- 7. ANA GÖVDE (Split View) ---
col_sol, col_sag = st.columns([1, 1.3])

# SOL: Veri Girişi (Hep sabit kalır, filtreden etkilenmez)
with col_sol:
    st.subheader("📝 Hızlı Ekle")
    with st.container(border=True):
        c_tur1, c_tur2 = st.columns(2)
        with c_tur1:
            tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
        
        kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
        secilen_kat = st.selectbox("Kategori", kat_listesi)
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)
        aciklama = st.text_input("Açıklama", placeholder="Opsiyonel...")
        
        # Tarih ve Gün Mantığı
        varsayilan_gun = 0
        son_odeme = None
        if secilen_kat and not df_kat.empty:
            row = df_kat[df_kat["Kategori"] == secilen_kat]
            if not row.empty: varsayilan_gun = int(row.iloc[0]["VarsayilanGun"])
            
        if tur_secimi == "Gider" and varsayilan_gun > 0:
            oneri = tarih_onerisi_hesapla(varsayilan_gun)
            st.caption(f"📅 Sabit Gün: {varsayilan_gun}")
            son_odeme = st.date_input("Son Ödeme", value=oneri)
        elif tur_secimi == "Gider":
             son_odeme = st.date_input("Son Ödeme (Opsiyonel)", value=None)

        if st.button("KAYDET", type="primary", use_container_width=True):
            if secilen_kat:
                yeni_satir = pd.DataFrame({
                    "Tarih": [date.today()], # Giriş hep bugüne yapılır
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
                st.error("Kategori seçiniz.")

# SAĞ: Analiz ve Liste (Filtreden etkilenir)
with col_sag:
    tab_grafik, tab_liste = st.tabs(["📊 Analiz", "📋 Kayıt Listesi"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub_df = df_filt[df_filt["Tür"] == "Gider"]
            
            # Pasta Grafik
            fig = px.pie(sub_df, values="Tutar", names="Kategori", hole=0.5)
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=220)
            st.plotly_chart(fig, use_container_width=True)
            
            # Bar Grafik
            grp = sub_df.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False).head(5)
            st.bar_chart(grp, x="Kategori", y="Tutar", height=200)
        else:
            st.caption("Grafik oluşturulacak gider verisi yok.")

    with tab_liste:
        st.dataframe(
            df_filt.sort_values("Tarih", ascending=False), 
            use_container_width=True, 
            height=450, 
            hide_index=True
        )
        
        # Silme Bölümü
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            # Silme listesi sadece filtrelenenleri değil, tüm veriyi kapsamalı ki karışıklık olmasın
            # Veya sadece ekrandakileri silmek daha güvenli olabilir. Şimdilik sadece filtrelenenleri sildirelim.
            sil_id = st.selectbox("Silinecek", df_filt.index, format_func=lambda x: f"{df.loc[x,'Tutar']}₺ - {df.loc[x,'Kategori']}", label_visibility="collapsed")
        with col_del2:
            if st.button("Sil"):
                df = df.drop(sil_id).reset_index(drop=True)
                dosya_kaydet(df, VERI_DOSYASI); st.rerun()
