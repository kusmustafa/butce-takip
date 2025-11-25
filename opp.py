import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
ESKI_SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- YARDIMCI FONKSİYONLAR ---
def sistem_baslat():
    """Dosya yapılarını kontrol eder ve eksikleri tamamlar."""
    
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
            df["VarsayilanGun"] = 0
            degisiklik = True
        if "Tur" not in df.columns:
            df["Tur"] = "Gider"
            degisiklik = True
        
        if degisiklik:
            df.to_csv(KATEGORI_DOSYASI, index=False)

    # 2. ESKİ SİSTEMDEN GEÇİŞ (Varsa)
    if os.path.exists(ESKI_SABITLER_DOSYASI):
        try:
            df_eski = pd.read_csv(ESKI_SABITLER_DOSYASI)
            df_kat = pd.read_csv(KATEGORI_DOSYASI)
            for _, row in df_eski.iterrows():
                isim = row.get("Sabit Kalem")
                gun = row.get("Odeme Gunu", 0)
                if isim and isim not in df_kat["Kategori"].values:
                    yeni = pd.DataFrame([{"Kategori": isim, "Tur": "Gider", "VarsayilanGun": gun}])
                    df_kat = pd.concat([df_kat, yeni], ignore_index=True)
            df_kat.to_csv(KATEGORI_DOSYASI, index=False)
            os.rename(ESKI_SABITLER_DOSYASI, "sabit_giderler_yedek.bak")
        except:
            pass

    # 3. VERİ DOSYASI
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])
        df.to_csv(VERI_DOSYASI, index=False)
    else:
        df = pd.read_csv(VERI_DOSYASI)
        if "Son Ödeme Tarihi" not in df.columns:
            df["Son Ödeme Tarihi"] = None
            df.to_csv(VERI_DOSYASI, index=False)

def verileri_oku(yol):
    return pd.read_csv(yol)

def dosya_kaydet(df, yol):
    df.to_csv(yol, index=False)

def tarih_onerisi_hesapla(gun):
    """Verilen gün için en yakın mantıklı ödeme tarihini bulur."""
    if gun is None or gun == 0:
        return None
        
    bugun = date.today()
    try:
        hedef_gun = int(gun)
    except:
        return None
        
    if not (1 <= hedef_gun <= 31):
        return None

    # Bu ayın tarihi
    try:
        bu_ay = date(bugun.year, bugun.month, hedef_gun)
    except ValueError:
        bu_ay = date(bugun.year, bugun.month, 28) # Şubat vb. için koruma

    if bu_ay >= bugun:
        return bu_ay
    else:
        # Tarih geçmiş, bir sonraki aya at
        sonraki_ay = bugun.month + 1 if bugun.month < 12 else 1
        yil = bugun.year if bugun.month < 12 else bugun.year + 1
        try:
            return date(yil, sonraki_ay, hedef_gun)
        except ValueError:
            return date(yil, sonraki_ay, 28)

# --- UYGULAMA ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")
sistem_baslat()

st.title("🐦 Kuşların Bütçe Makinesi")

# Verileri Yükle
try:
    df = verileri_oku(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    df_kat = verileri_oku(KATEGORI_DOSYASI)
except:
    df = pd.DataFrame()
    df_kat = pd.DataFrame()

# --- YAN MENÜ: AYARLAR ---
st.sidebar.header("⚙️ Ayarlar")

with st.sidebar.expander("Kategori Ekle / Düzenle", expanded=True):
    st.write("Yeni Kategori:")
    # 1. Tür Seçimi
    yeni_tur = st.radio("Tür Seçiniz", ["Gider", "Gelir"], horizontal=True)
    yeni_ad = st.text_input("Kategori Adı", placeholder="Örn: Doğalgaz")
    
    # 2. Gün Seçimi (Sadece Gider için aktif ama zorunlu değil)
    yeni_gun = 0
    if yeni_tur == "Gider":
        st.caption("Otomatik Tarih Önerisi (Opsiyonel)")
        yeni_gun = st.number_input("Ayın hangi günü?", min_value=0, max_value=31, value=0, help="0 bırakırsanız tarih önerilmez.")
    
    if st.button("Listeye Ekle / Güncelle"):
        if yeni_ad:
            # Önce varsa eskini silelim (Güncelleme mantığı)
            df_kat = df_kat[df_kat["Kategori"] != yeni_ad]
            
            yeni_veri = pd.DataFrame([{
                "Kategori": yeni_ad, 
                "Tur": yeni_tur, 
                "VarsayilanGun": yeni_gun
            }])
            df_kat = pd.concat([df_kat, yeni_veri], ignore_index=True)
            dosya_kaydet(df_kat, KATEGORI_DOSYASI)
            st.success(f"✅ {yeni_ad} eklendi/güncellendi!")
            st.rerun()

    st.divider()
    silinecek = st.selectbox("Kategori Sil", ["Seçiniz"] + df_kat["Kategori"].tolist())
    if st.button("Sil") and silinecek != "Seçiniz":
        df_kat = df_kat[df_kat["Kategori"] != silinecek]
        dosya_kaydet(df_kat, KATEGORI_DOSYASI)
        st.rerun()

# --- YAN MENÜ: FİLTRE ---
st.sidebar.divider()
st.sidebar.header("🔍 Dönem")
if not df.empty:
    yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True)
    sec_yil = st.sidebar.selectbox("Yıl", yil_list)
    
    ay_map = {i: ay for i, ay in enumerate(["Tümü", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
    sec_ay = st.sidebar.selectbox("Ay", list(ay_map.keys()), format_func=lambda x: ay_map[x], index=datetime.now().month)
    
    df_filt = df[df["Tarih"].dt.year == sec_yil]
    if sec_ay != 0:
        df_filt = df_filt[df_filt["Tarih"].dt.month == sec_ay]
        baslik = f"{ay_map[sec_ay]} {sec_yil}"
    else:
        baslik = f"{sec_yil} Tamamı"
else:
    df_filt = df
    baslik = "Veri Yok"

# --- ANA EKRAN: GİRİŞ ---
st.subheader("📝 İşlem Girişi")

c1, c2, c3, c4 = st.columns([1, 1.5, 1, 1])

with c1:
    tur_secimi = st.radio("İşlem Türü", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")

# Kategori listesini türe göre süz
if not df_kat.empty:
    kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist()
else:
    kat_listesi = []

with c2:
    secilen_kat = st.selectbox("Kategori", kat_listesi)

with c3:
    tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0, label_visibility="collapsed")

with c4:
    st.write("")
    st.write("")
    kaydet = st.button("KAYDET 💾", type="primary", use_container_width=True)

# DETAYLAR (Dinamik Tarih)
aciklama = ""
son_odeme = None
islem_tarih = date.today()

# Seçilen kategorinin günü var mı bak
varsayilan_gun = 0
if secilen_kat and not df_kat.empty:
    row = df_kat[df_kat["Kategori"] == secilen_kat]
    if not row.empty:
        varsayilan_gun = int(row.iloc[0]["VarsayilanGun"])

# Expander varsayılan olarak kapalı, ancak Gider seçiliyse her türlü açılabilir
with st.expander("Detaylar & Tarih Ayarları", expanded=(tur_secimi=="Gider")):
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        islem_tarih = st.date_input("İşlem Tarihi", date.today())
        aciklama = st.text_input("Açıklama", placeholder="Notunuz...")
    
    with col_d2:
        if tur_secimi == "Gider":
            if varsayilan_gun > 0:
                # Kategoriye özel gün VARSA -> Hesapla ve Getir
                oneri = tarih_onerisi_hesapla(varsayilan_gun)
                st.info(f"📅 Sabit Gün: Ayın {varsayilan_gun}'i")
                son_odeme = st.date_input("Son Ödeme Tarihi", value=oneri)
            else:
                # Kategoriye özel gün YOKSA -> Boş Getir (User seçsin)
                st.caption("Sabit ödeme günü yok.")
                son_odeme = st.date_input("Son Ödeme Tarihi (Seçiniz)", value=None)
        else:
            st.info("Gelir için son ödeme tarihi yoktur.")

if kaydet:
    if not secilen_kat:
        st.error("Kategori seçmelisiniz.")
    else:
        yeni_satir = pd.DataFrame({
            "Tarih": [islem_tarih],
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

# --- RAPORLAR ---
st.divider()
st.header(f"📊 Rapor: {baslik}")

if not df_filt.empty:
    gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Gelir", f"{gelir:,.0f} ₺")
    m2.metric("Gider", f"{gider:,.0f} ₺")
    m3.metric("Kalan", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")
    
    tabs = st.tabs(["Pasta", "Harcama Detay", "Liste"])
    
    with tabs[0]:
        # Hangi tür baskınsa veya genel gider
        sub_df = df_filt[df_filt["Tür"] == "Gider"]
        if not sub_df.empty:
            fig = px.pie(sub_df, values="Tutar", names="Kategori", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Gider yok.")

    with tabs[1]:
        # Kategori bazlı bar grafik
        if not sub_df.empty:
            grp = sub_df.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
            st.bar_chart(grp, x="Kategori", y="Tutar")

    with tabs[2]:
        st.dataframe(df_filt.sort_values("Tarih", ascending=False), use_container_width=True)
        
        st.write("---")
        sil_id = st.selectbox("Silinecek Kayıt", df.index, 
                             format_func=lambda x: f"{df.loc[x,'Tarih'].strftime('%Y-%m-%d')} - {df.loc[x,'Kategori']} - {df.loc[x,'Tutar']}₺")
        if st.button("Seçiliyi Sil"):
            df = df.drop(sil_id).reset_index(drop=True)
            dosya_kaydet(df, VERI_DOSYASI)
            st.rerun()

else:
    st.info("Kayıt yok.")
