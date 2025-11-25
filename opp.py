import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")

# --- CSS İYİLEŞTİRMELERİ ---
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

# --- DOSYALAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
ESKI_SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- YARDIMCI FONKSİYONLAR ---
def sistem_kontrol():
    # Kategori Dosyası
    if not os.path.exists(KATEGORI_DOSYASI):
        pd.DataFrame([
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}
        ]).to_csv(KATEGORI_DOSYASI, index=False)
    else:
        # Eksik sütun tamamlama
        try:
            df = pd.read_csv(KATEGORI_DOSYASI)
            degisti = False
            for col in ["Kategori", "Tur", "VarsayilanGun"]:
                if col not in df.columns:
                    df[col] = 0 if col == "VarsayilanGun" else ("Gider" if col == "Tur" else "")
                    degisti = True
            if degisti: df.to_csv(KATEGORI_DOSYASI, index=False)
        except:
            pass

    # Veri Dosyası (Sıfırdan oluştururken tarih formatını belirtiyoruz)
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])
        df.to_csv(VERI_DOSYASI, index=False)
    else:
        # Dosya var ama sütun eksikse
        try:
            df = pd.read_csv(VERI_DOSYASI)
            if "Son Ödeme Tarihi" not in df.columns:
                df["Son Ödeme Tarihi"] = None
                df.to_csv(VERI_DOSYASI, index=False)
        except:
            pass

def dosya_kaydet(df, yol):
    df.to_csv(yol, index=False)

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

# --- UYGULAMA BAŞLAT ---
sistem_kontrol()

# Verileri Yükle ve Tarihleri Formatla
try:
    df = pd.read_csv(VERI_DOSYASI)
    # Tarih sütununu datetime objesine çeviriyoruz (Hata varsa düzeltir)
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    # Tarihi bozuk olan satırları temizle
    df = df.dropna(subset=["Tarih"])
except:
    df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])

try:
    df_kat = pd.read_csv(KATEGORI_DOSYASI)
except:
    df_kat = pd.DataFrame(columns=["Kategori", "Tur", "VarsayilanGun"])

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    with st.expander("🚨 Verileri Sıfırla (Reset)"):
        if st.button("Her Şeyi Sil ve Sıfırla"):
            if os.path.exists(VERI_DOSYASI): os.remove(VERI_DOSYASI)
            if os.path.exists(KATEGORI_DOSYASI): os.remove(KATEGORI_DOSYASI)
            st.rerun()
            
    st.divider()
    st.subheader("🔍 Filtre")
    if not df.empty:
        yil_listesi = sorted(df["Tarih"].dt.year.unique(), reverse=True)
        secenekler = ["Tüm Zamanlar"] + list(yil_listesi)
        secilen_yil = st.selectbox("Dönem", secenekler)
        
        if secilen_yil == "Tüm Zamanlar":
            df_filt = df
            baslik = "Tüm Zamanlar"
        else:
            df_filt = df[df["Tarih"].dt.year == secilen_yil]
            ay_map = {i: ay for i, ay in enumerate(["Yılın Tamamı", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
            now = datetime.now()
            # Eğer seçilen yıl şimdiki yılsa şimdiki ay gelsin, değilse yılın tamamı gelsin
            idx = now.month if secilen_yil == now.year else 0
            secilen_ay_index = st.selectbox("Ay", list(ay_map.keys()), format_func=lambda x: ay_map[x], index=idx)
            
            if secilen_ay_index != 0:
                df_filt = df_filt[df_filt["Tarih"].dt.month == secilen_ay_index]
                baslik = f"{ay_map[secilen_ay_index]} {secilen_yil}"
            else:
                baslik = f"{secilen_yil} Tamamı"
    else:
        df_filt = df
        baslik = "Veri Yok"

    st.divider()
    with st.expander("Kategori Ekle", expanded=False):
        y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
        y_ad = st.text_input("Kategori Adı")
        y_gun = st.number_input("Gün", 0, 31, 0) if y_tur == "Gider" else 0
        if st.button("Ekle"):
            if y_ad:
                # Kategori zaten varsa güncelle, yoksa ekle
                df_kat = df_kat[df_kat["Kategori"] != y_ad]
                yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun}])
                df_kat = pd.concat([df_kat, yeni], ignore_index=True)
                dosya_kaydet(df_kat, KATEGORI_DOSYASI)
                st.success("Eklendi")
                st.rerun()

# --- ÜST BİLGİ ---
st.title("🐦 Kuşların Bütçe Makinesi")
st.caption(f"Rapor: **{baslik}**")

if not df_filt.empty:
    gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    k1, k2, k3 = st.columns(3)
    k1.metric("Gelir", f"{gelir:,.0f} ₺")
    k2.metric("Gider", f"{gider:,.0f} ₺")
    k3.metric("Net", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")
else:
    st.info("Kayıt yok.")

st.divider()

# --- ANA GÖVDE ---
col_sol, col_sag = st.columns([1, 1.3])

with col_sol:
    st.subheader("📝 Veri Girişi")
    with st.container(border=True):
        # 1. TARİH SEÇİMİ
        giris_tarihi = st.date_input("İşlem Tarihi", date.today())
        
        # 2. SEÇİMLER
        c_tur1, c_tur2 = st.columns(2)
        with c_tur1:
            tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
        
        kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
        secilen_kat = st.selectbox("Kategori", kat_listesi, index=None, placeholder="Seçiniz...")
        
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)
        aciklama = st.text_input("Açıklama")
        
        # 3. DETAYLAR
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
             son_odeme = st.date_input("Son Ödeme", value=None)

        # 4. KAYDETME BUTONU (DÜZELTİLDİ)
        if st.button("KAYDET", type="primary", use_container_width=True):
            if secilen_kat is None:
                st.error("⚠️ Lütfen bir kategori seçin!")
            elif tutar == 0:
                st.warning("⚠️ Tutar 0 girildi, emin misiniz?")
                # Tutar 0 olsa da kaydeder ama uyarır
            
            if secilen_kat:
                try:
                    # Yeni satırı oluştur
                    yeni_satir = pd.DataFrame({
                        "Tarih": [pd.to_datetime(giris_tarihi)], # Formatı zorla
                        "Kategori": [secilen_kat],
                        "Tür": [tur_secimi],
                        "Tutar": [float(tutar)],
                        "Son Ödeme Tarihi": [son_odeme],
                        "Açıklama": [aciklama]
                    })
                    
                    # Ana tablo ile birleştir
                    df = pd.concat([df, yeni_satir], ignore_index=True)
                    
                    # Dosyaya kaydet
                    dosya_kaydet(df, VERI_DOSYASI)
                    st.success(f"✅ {secilen_kat} - {tutar} TL eklendi!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")

with col_sag:
    tab_grafik, tab_liste = st.tabs(["📊 Analiz", "📋 Liste"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub_df = df_filt[df_filt["Tür"] == "Gider"]
            fig = px.pie(sub_df, values="Tutar", names="Kategori", hole=0.5)
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=220)
            st.plotly_chart(fig, use_container_width=True)
            
            grp = sub_df.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False).head(5)
            st.bar_chart(grp, x="Kategori", y="Tutar", height=200)

    with tab_liste:
        # Görsel Tablo (Tarih formatı düzgün görünsün diye kopya alıyoruz)
        gosterim_df = df_filt.sort_values("Tarih", ascending=False).copy()
        gosterim_df["Tarih"] = gosterim_df["Tarih"].dt.strftime('%d.%m.%Y') # Gün.Ay.Yıl formatı
        
        st.dataframe(gosterim_df, use_container_width=True, height=450, hide_index=True)
        
        # Silme
        if not df_filt.empty:
            sil_id = st.selectbox("Silinecek Kayıt", df_filt.index, 
                                 format_func=lambda x: f"{df.loc[x,'Tarih'].strftime('%d.%m')} - {df.loc[x,'Tutar']}TL - {df.loc[x,'Kategori']}",
                                 label_visibility="collapsed")
            if st.button("Sil"):
                df = df.drop(sil_id).reset_index(drop=True)
                dosya_kaydet(df, VERI_DOSYASI)
                st.rerun()
