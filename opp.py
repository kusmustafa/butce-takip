import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")

# --- CSS ---
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

# --- DOSYA İSİMLERİ ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
ESKI_SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- GÜVENLİ VERİ YÖNETİMİ ---
def verileri_kontrol_et_ve_yukle():
    """Dosyaları ve sütunları kontrol eder, eksikse onarır."""
    
    # 1. KATEGORİ DOSYASI KONTROLÜ
    gerekli_kat_sutunlar = ["Kategori", "Tur", "VarsayilanGun"]
    if not os.path.exists(KATEGORI_DOSYASI):
        varsayilanlar = [
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Kira", "Tur": "Gider", "VarsayilanGun": 1},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0},
        ]
        pd.DataFrame(varsayilanlar).to_csv(KATEGORI_DOSYASI, index=False)
    else:
        # Dosya var ama sütunlar eksik mi?
        try:
            df = pd.read_csv(KATEGORI_DOSYASI)
            kaydet = False
            for col in gerekli_kat_sutunlar:
                if col not in df.columns:
                    if col == "VarsayilanGun": df[col] = 0
                    if col == "Tur": df[col] = "Gider"
                    kaydet = True
            if kaydet: df.to_csv(KATEGORI_DOSYASI, index=False)
        except:
            # Dosya bozuksa yeniden oluştur
            pd.DataFrame(columns=gerekli_kat_sutunlar).to_csv(KATEGORI_DOSYASI, index=False)

    # 2. ESKİ SİSTEMDEN GEÇİŞ (Varsa Temizle)
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

    # 3. ANA VERİ DOSYASI KONTROLÜ (En Kritik Yer)
    gerekli_veri_sutunlar = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"]
    
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=gerekli_veri_sutunlar)
        df.to_csv(VERI_DOSYASI, index=False)
        return df
    else:
        try:
            df = pd.read_csv(VERI_DOSYASI)
            # Sütun isimleri uyuşuyor mu?
            mevcut_sutunlar = df.columns.tolist()
            eksik_var_mi = False
            
            # Kritik sütun kontrolü
            if "Tür" not in mevcut_sutunlar: 
                # Belki eski dosyada 'Tur' yazıyordur veya hiç yoktur
                if "Tur" in mevcut_sutunlar:
                    df.rename(columns={"Tur": "Tür"}, inplace=True)
                else:
                    df["Tür"] = "Gider" # Varsayılan ata
                eksik_var_mi = True
                
            if "Son Ödeme Tarihi" not in mevcut_sutunlar:
                df["Son Ödeme Tarihi"] = None
                eksik_var_mi = True

            # Eğer kritik hata varsa dosyayı güncelle
            if eksik_var_mi:
                df.to_csv(VERI_DOSYASI, index=False)
                
            return df
        except Exception as e:
            # Dosya okunamayacak kadar bozuksa boş dön
            return pd.DataFrame(columns=gerekli_veri_sutunlar)

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
df = verileri_kontrol_et_ve_yukle()
try:
    df_kat = pd.read_csv(KATEGORI_DOSYASI)
except:
    df_kat = pd.DataFrame(columns=["Kategori", "Tur", "VarsayilanGun"])

# Tarih formatını güvenli çevirme
if not df.empty and "Tarih" in df.columns:
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce') # Hatalı tarihleri NaT yapar
    df = df.dropna(subset=["Tarih"]) # Tarihi bozuk olanları listeden çıkarır (Çökmemesi için)

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    # ACİL DURUM BUTONU
    with st.expander("🚨 Sorun Giderici (Hata Varsa)"):
        st.warning("Eğer 'KeyError' alıyorsanız buna basın. Verileri sıfırlar.")
        if st.button("Tüm Verileri Sıfırla ve Onar"):
            if os.path.exists(VERI_DOSYASI): os.remove(VERI_DOSYASI)
            if os.path.exists(KATEGORI_DOSYASI): os.remove(KATEGORI_DOSYASI)
            st.success("Sıfırlandı. Sayfayı yenileyin.")
            st.rerun()

    st.divider()
    
    # FİLTRELEME
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
            default_index = datetime.now().month
            secilen_ay_index = st.selectbox("Ay", list(ay_map.keys()), format_func=lambda x: ay_map[x], index=default_index)
            
            if secilen_ay_index != 0:
                df_filt = df_filt[df_filt["Tarih"].dt.month == secilen_ay_index]
                baslik = f"{ay_map[secilen_ay_index]} {secilen_yil}"
            else:
                baslik = f"{secilen_yil} Tamamı"
    else:
        df_filt = df
        baslik = "Veri Yok"

    st.divider()
    with st.expander("Kategori Ekle"):
        y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
        y_ad = st.text_input("Kategori Adı")
        y_gun = st.number_input("Gün", 0, 31, 0) if y_tur == "Gider" else 0
        if st.button("Ekle"):
            if y_ad:
                df_kat = df_kat[df_kat["Kategori"] != y_ad]
                yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun}])
                df_kat = pd.concat([df_kat, yeni], ignore_index=True)
                dosya_kaydet(df_kat, KATEGORI_DOSYASI); st.rerun()

# --- ÜST KARTLAR ---
st.title("🐦 Kuşların Bütçe Makinesi")
st.caption(f"Rapor: **{baslik}**")

try:
    if not df_filt.empty:
        # KeyError buradaydı, artık güvenli
        gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
        gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
        net = gelir - gider
        
        k1, k2, k3 = st.columns(3)
        k1.metric("Gelir", f"{gelir:,.0f} ₺")
        k2.metric("Gider", f"{gider:,.0f} ₺")
        k3.metric("Net", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")
    else:
        st.info("Kayıt yok.")
except Exception as e:
    st.error(f"Bir hata oluştu: {e}. Lütfen sol menüden 'Sorun Giderici'yi kullanın.")

st.divider()

# --- GÖVDE ---
col_sol, col_sag = st.columns([1, 1.3])

with col_sol:
    st.subheader("📝 İşlem")
    with st.container(border=True):
        c_tur1, c_tur2 = st.columns(2)
        with c_tur1:
            tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
        
        kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
        secilen_kat = st.selectbox("Kategori", kat_listesi)
        tutar = st.number_input("Tutar", min_value=0.0, step=50.0)
        aciklama = st.text_input("Açıklama")
        
        varsayilan_gun = 0
        son_odeme = None
        if secilen_kat and not df_kat.empty:
            row = df_kat[df_kat["Kategori"] == secilen_kat]
            if not row.empty: varsayilan_gun = int(row.iloc[0]["VarsayilanGun"])
            
        if tur_secimi == "Gider" and varsayilan_gun > 0:
            oneri = tarih_onerisi_hesapla(varsayilan_gun)
            st.caption(f"📅 Gün: {varsayilan_gun}")
            son_odeme = st.date_input("Son Ödeme", value=oneri)
        elif tur_secimi == "Gider":
             son_odeme = st.date_input("Son Ödeme", value=None)

        if st.button("KAYDET", type="primary", use_container_width=True):
            if secilen_kat:
                yeni_satir = pd.DataFrame({
                    "Tarih": [date.today()],
                    "Kategori": [secilen_kat],
                    "Tür": [tur_secimi],
                    "Tutar": [tutar],
                    "Son Ödeme Tarihi": [son_odeme],
                    "Açıklama": [aciklama]
                })
                # Sütun sırasını garantiye al
                yeni_satir = yeni_satir[["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"]]
                
                df = pd.concat([df, yeni_satir], ignore_index=True)
                dosya_kaydet(df, VERI_DOSYASI)
                st.success("Kaydedildi!")
                st.rerun()
            else:
                st.error("Kategori seçiniz.")

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
        st.dataframe(df_filt.sort_values("Tarih", ascending=False), use_container_width=True, height=450, hide_index=True)
        
        c_del1, c_del2 = st.columns([3, 1])
        with c_del1:
            # Silme işlemi için ID güvenliği
            try:
                sil_id = st.selectbox("Silinecek", df_filt.index, format_func=lambda x: f"{df.loc[x,'Tutar']}₺ - {df.loc[x,'Kategori']}", label_visibility="collapsed")
            except:
                sil_id = None
        with c_del2:
            if st.button("Sil") and sil_id is not None:
                df = df.drop(sil_id).reset_index(drop=True)
                dosya_kaydet(df, VERI_DOSYASI); st.rerun()
