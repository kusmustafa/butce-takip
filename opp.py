import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date
import calendar

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
# Eski dosya ismini sadece veri kurtarmak için tutuyoruz
ESKI_SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- DOSYA VE VERİ YÖNETİMİ ---
def sistem_kontrol_ve_goc():
    """Dosya yapılarını kontrol eder, eski ayrı yapıyı tek çatı altında birleştirir."""
    
    # 1. KATEGORİ DOSYASI OLUŞTURMA / GÜNCELLEME
    if not os.path.exists(KATEGORI_DOSYASI):
        # Dosya hiç yoksa varsayılanları oluştur
        varsayilanlar = [
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Kira", "Tur": "Gider", "VarsayilanGun": 1},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0},
            {"Kategori": "Faturalar", "Tur": "Gider", "VarsayilanGun": 0},
            {"Kategori": "Kredi Kartı", "Tur": "Gider", "VarsayilanGun": 15},
        ]
        pd.DataFrame(varsayilanlar).to_csv(KATEGORI_DOSYASI, index=False)
    else:
        # Dosya var, sütunları kontrol et
        df = pd.read_csv(KATEGORI_DOSYASI)
        degisiklik_var = False
        
        # 'Tur' sütunu yoksa ekle
        if "Tur" not in df.columns:
            df["Tur"] = "Gider"
            df.loc[df["Kategori"].str.contains("Maaş|Gelir", case=False, na=False), "Tur"] = "Gelir"
            degisiklik_var = True
            
        # 'VarsayilanGun' sütunu yoksa ekle
        if "VarsayilanGun" not in df.columns:
            df["VarsayilanGun"] = 0
            degisiklik_var = True
            
        if degisiklik_var:
            df.to_csv(KATEGORI_DOSYASI, index=False)

    # 2. ESKİ SABİT GİDERLERİ İÇERİ AKTARMA (MIGRATION)
    # Eğer eski sistemden kalan 'sabit_giderler.csv' varsa, onları kategoriye ekle ve dosyayı sil.
    if os.path.exists(ESKI_SABITLER_DOSYASI):
        try:
            df_eski = pd.read_csv(ESKI_SABITLER_DOSYASI)
            df_kat = pd.read_csv(KATEGORI_DOSYASI)
            
            for index, row in df_eski.iterrows():
                isim = row.get("Sabit Kalem")
                gun = row.get("Odeme Gunu", 0)
                
                # Eğer bu isimde bir kategori yoksa ekle
                if isim and isim not in df_kat["Kategori"].values:
                    yeni_veri = pd.DataFrame([{"Kategori": isim, "Tur": "Gider", "VarsayilanGun": gun}])
                    df_kat = pd.concat([df_kat, yeni_veri], ignore_index=True)
                # Eğer varsa ve günü 0 ise güncelle
                elif isim in df_kat["Kategori"].values:
                    df_kat.loc[df_kat["Kategori"] == isim, "VarsayilanGun"] = gun
            
            df_kat.to_csv(KATEGORI_DOSYASI, index=False)
            
            # Eski dosyayı yeniden isimlendir (Yedek olarak kalsın, sistem okumasın)
            os.rename(ESKI_SABITLER_DOSYASI, "sabit_giderler_yedek.bak")
        except:
            pass # Hata olursa akış bozulmasın

    # 3. ANA VERİ DOSYASI
    if not os.path.exists(VERI_DOSYASI):
        df_veri = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])
        df_veri.to_csv(VERI_DOSYASI, index=False)
    else:
        df = pd.read_csv(VERI_DOSYASI)
        if "Son Ödeme Tarihi" not in df.columns:
            df["Son Ödeme Tarihi"] = None
            df.to_csv(VERI_DOSYASI, index=False)

def verileri_oku(dosya_adi):
    return pd.read_csv(dosya_adi)

def dosya_kaydet(df, dosya_adi):
    df.to_csv(dosya_adi, index=False)

def gelecek_odeme_tarihi_bul(hedef_gun):
    """Bugüne göre bir sonraki ödeme tarihini hesaplar."""
    bugun = date.today()
    try:
        hedef_gun = int(float(hedef_gun))
    except:
        return bugun 
        
    if hedef_gun < 1 or hedef_gun > 31:
        return None # Gün yoksa None dön

    try:
        bu_ay_tarih = date(bugun.year, bugun.month, hedef_gun)
    except ValueError:
        bu_ay_tarih = date(bugun.year, bugun.month, 28)

    if bu_ay_tarih >= bugun:
        return bu_ay_tarih
    else:
        sonraki_ay = bugun.month + 1 if bugun.month < 12 else 1
        yil = bugun.year if bugun.month < 12 else bugun.year + 1
        try:
            return date(yil, sonraki_ay, hedef_gun)
        except ValueError:
            return date(yil, sonraki_ay, 28)

# --- SAYFA YAPISI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")
sistem_kontrol_ve_goc()

st.title("🐦 Kuşların Bütçe Makinesi v5")

# Verileri Yükle
try:
    df = verileri_oku(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"])
    df_kategoriler = verileri_oku(KATEGORI_DOSYASI)
except:
    df = pd.DataFrame()
    df_kategoriler = pd.DataFrame()

# --- YAN MENÜ: FİLTRE VE AYARLAR ---
st.sidebar.header("🔍 Dönem Seçimi")

if not df.empty:
    yillar = sorted(df["Tarih"].dt.year.unique(), reverse=True)
    secilen_yil = st.sidebar.selectbox("Yıl", yillar)
    
    aylar_dict = {i: ay for i, ay in enumerate(["Tümü", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                                              "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
    secilen_ay_index = st.sidebar.selectbox("Ay", list(aylar_dict.keys()), format_func=lambda x: aylar_dict[x], index=datetime.now().month)
    
    df_filtered = df[df["Tarih"].dt.year == secilen_yil]
    if secilen_ay_index != 0:
        df_filtered = df_filtered[df_filtered["Tarih"].dt.month == secilen_ay_index]
        filtre_mesaji = f"{aylar_dict[secilen_ay_index]} {secilen_yil}"
    else:
        filtre_mesaji = f"{secilen_yil} Tümü"
else:
    df_filtered = df
    filtre_mesaji = "Veri Yok"

st.sidebar.divider()
st.sidebar.header("⚙️ Kategori Yönetimi")

with st.sidebar.expander("Yeni Kategori Ekle / Sil", expanded=False):
    st.write("**Yeni Ekle:**")
    yeni_tur = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
    yeni_ad = st.text_input("Kategori Adı", placeholder="Örn: İnternet Faturası")
    
    yeni_gun = 0
    if yeni_tur == "Gider":
        st.caption("Eğer sabit bir ödeme günü varsa belirtin (Yoksa 0):")
        yeni_gun = st.number_input("Ödeme Günü (Ayın kaçı?)", 0, 31, 0)
    
    if st.button("Listeye Ekle"):
        if yeni_ad and yeni_ad not in df_kategoriler["Kategori"].values:
            yeni_veri = pd.DataFrame([{"Kategori": yeni_ad, "Tur": yeni_tur, "VarsayilanGun": yeni_gun}])
            df_kategoriler = pd.concat([df_kategoriler, yeni_veri], ignore_index=True)
            dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
            st.success("Eklendi!")
            st.rerun()
        elif yeni_ad in df_kategoriler["Kategori"].values:
            st.warning("Bu kategori zaten var.")

    st.divider()
    st.write("**Sil:**")
    silinecek_kat = st.selectbox("Kategori Seç", ["Seçiniz"] + df_kategoriler["Kategori"].tolist())
    if st.button("Sil") and silinecek_kat != "Seçiniz":
        df_kategoriler = df_kategoriler[df_kategoriler["Kategori"] != silinecek_kat]
        dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
        st.rerun()

# --- ANA EKRAN: HIZLI VERİ GİRİŞİ ---
st.subheader("📝 İşlem Ekle")

c1, c2, c3, c4 = st.columns([1, 1.5, 1, 1])

with c1:
    tur_secimi = st.radio("İşlem", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")

# Kategori listesini türe göre filtrele
if not df_kategoriler.empty:
    filtrelenmis_liste = df_kategoriler[df_kategoriler["Tur"] == tur_secimi]
    kategori_options = filtrelenmis_liste["Kategori"].tolist()
else:
    kategori_options = []

with c2:
    secilen_kategori = st.selectbox("Kategori", kategori_options)

with c3:
    tutar = st.number_input("Tutar", min_value=0.0, step=50.0, label_visibility="collapsed", placeholder="Tutar")

with c4:
    # Kaydet butonu (Tasarım için sağa yasladık)
    st.write("") # Boşluk
    st.write("") # Boşluk
    kaydet_btn = st.button("KAYDET 💾", type="primary", use_container_width=True)

# DETAY ALANI (Sadece Giderse ve Gerekliyse)
aciklama = ""
son_odeme_val = None
islem_tarihi = date.today()

# Seçilen kategorinin varsayılan günü var mı?
varsayilan_gun = 0
if secilen_kategori and not df_kategoriler.empty:
    kat_bilgisi = df_kategoriler[df_kategoriler["Kategori"] == secilen_kategori]
    if not kat_bilgisi.empty:
        varsayilan_gun = kat_bilgisi["VarsayilanGun"].values[0]

with st.expander("İşlem Detayları / Tarih Değiştir", expanded=(varsayilan_gun > 0)):
    d1, d2 = st.columns(2)
    with d1:
        islem_tarihi = st.date_input("İşlem Tarihi", date.today())
        aciklama = st.text_input("Açıklama (Opsiyonel)", placeholder="Detay yazabilirsiniz...")
    
    with d2:
        if tur_secimi == "Gider":
            # Otomatik Tarih Önerisi
            if varsayilan_gun > 0:
                onerilen = gelecek_odeme_tarihi_bul(varsayilan_gun)
                st.info(f"📅 Bu kategori için varsayılan gün: Ayın {int(varsayilan_gun)}'i")
                son_odeme_val = st.date_input("Son Ödeme Tarihi", value=onerilen)
            else:
                st.caption("Bu kategori için otomatik tarih yok.")
                son_odeme_val = st.date_input("Son Ödeme Tarihi (Opsiyonel)", value=None)

# Kaydetme Mantığı
if kaydet_btn:
    if not secilen_kategori:
        st.error("Lütfen kategori seçiniz.")
    else:
        yeni_satir = pd.DataFrame({
            "Tarih": [islem_tarihi],
            "Kategori": [secilen_kategori],
            "Tür": [tur_secimi],
            "Tutar": [tutar],
            "Son Ödeme Tarihi": [son_odeme_val],
            "Açıklama": [aciklama]
        })
        df = pd.concat([df, yeni_satir], ignore_index=True)
        dosya_kaydet(df, VERI_DOSYASI)
        st.success(f"{secilen_kategori} - {tutar}₺ Kaydedildi!")
        st.rerun()

# --- RAPORLAR ---
st.divider()
st.header(f"📊 Durum: {filtre_mesaji}")

if not df_filtered.empty:
    gelir = df_filtered[df_filtered["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filtered[df_filtered["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gelir", f"{gelir:,.0f} ₺")
    col2.metric("Gider", f"{gider:,.0f} ₺")
    col3.metric("Kalan", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")

    t1, t2, t3 = st.tabs(["Pasta Grafiği", "Harcama Detayı", "Liste"])
    
    with t1:
        # Gelir/Gider seçimi yerine sadece dönemin baskın türünü veya kullanıcı seçimini gösterelim
        gider_data = df_filtered[df_filtered["Tür"] == "Gider"]
        if not gider_data.empty:
            fig = px.pie(gider_data, values="Tutar", names="Kategori", title="Gider Dağılımı", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Bu dönem gider yok.")
            
    with t2:
        # Kategorilere göre bar grafik
        if not gider_data.empty:
            cat_group = gider_data.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
            st.bar_chart(cat_group, x="Kategori", y="Tutar")
            
    with t3:
        # Liste ve Silme
        st.dataframe(df_filtered.sort_values("Tarih", ascending=False), use_container_width=True)
        
        st.write("---")
        sil_id = st.selectbox("Silinecek Kayıt", df.index, 
                             format_func=lambda x: f"{df.loc[x, 'Tarih'].strftime('%Y-%m-%d')} - {df.loc[x, 'Kategori']} - {df.loc[x, 'Tutar']}₺")
        if st.button("Kaydı Sil"):
            df = df.drop(sil_id).reset_index(drop=True)
            dosya_kaydet(df, VERI_DOSYASI)
            st.rerun()
else:
    st.info("Bu tarihlerde kayıt bulunamadı.")
