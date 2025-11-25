import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date
import calendar

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- DOSYA VE VERİ YÖNETİMİ ---
def dosya_kontrol_ve_yukle():
    """Dosya yapılarını kontrol eder ve eksik sütunları günceller (Migration)."""
    
    # 1. KATEGORİ DOSYASI GÜNCELLEME (Artık 'Tur' sütunu da var)
    if not os.path.exists(KATEGORI_DOSYASI):
        varsayilanlar = [
            {"Kategori": "Maaş", "Tur": "Gelir"},
            {"Kategori": "Ek Gelir", "Tur": "Gelir"},
            {"Kategori": "Market", "Tur": "Gider"},
            {"Kategori": "Kira", "Tur": "Gider"},
            {"Kategori": "Faturalar", "Tur": "Gider"},
            {"Kategori": "Eğlence", "Tur": "Gider"},
            {"Kategori": "Ulaşım", "Tur": "Gider"}
        ]
        pd.DataFrame(varsayilanlar).to_csv(KATEGORI_DOSYASI, index=False)
    else:
        # Mevcut dosyayı kontrol et, 'Tur' sütunu yoksa ekle
        df = pd.read_csv(KATEGORI_DOSYASI)
        if "Tur" not in df.columns:
            # Eski kategorilerin hepsini varsayılan olarak 'Gider' yapalım, kullanıcı düzeltir
            df["Tur"] = "Gider" 
            # Maaş kelimesi geçiyorsa Gelir yapalım (Basit tahmin)
            df.loc[df["Kategori"].str.contains("Maaş|Gelir", case=False, na=False), "Tur"] = "Gelir"
            df.to_csv(KATEGORI_DOSYASI, index=False)

    # 2. SABİT GİDERLER
    if not os.path.exists(SABITLER_DOSYASI):
        df_sabit = pd.DataFrame(columns=["Sabit Kalem", "Odeme Gunu"])
        df_sabit.to_csv(SABITLER_DOSYASI, index=False)
    else:
        df = pd.read_csv(SABITLER_DOSYASI)
        if "Odeme Gunu" not in df.columns:
            df["Odeme Gunu"] = 1
            df.to_csv(SABITLER_DOSYASI, index=False)

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
    bugun = date.today()
    try:
        hedef_gun = int(float(hedef_gun))
    except:
        return bugun 
        
    if hedef_gun < 1 or hedef_gun > 31:
        return bugun

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
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide") # Wide layout yaptık
dosya_kontrol_ve_yukle()

st.title("🐦 Kuşların Bütçe Makinesi")

# Verileri Çek
try:
    df = verileri_oku(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"]) # Tarih formatını garantiye al
    df_kategoriler = verileri_oku(KATEGORI_DOSYASI)
    df_sabitler = verileri_oku(SABITLER_DOSYASI)
except Exception as e:
    st.error("Veri yüklenirken hata oluştu.")
    df = pd.DataFrame()
    df_kategoriler = pd.DataFrame()
    df_sabitler = pd.DataFrame()

# --- YAN MENÜ: FİLTRELEME VE AYARLAR ---
st.sidebar.header("🔍 Rapor Filtresi")

# Tarih Filtreleme Mantığı
if not df.empty:
    yillar = sorted(df["Tarih"].dt.year.unique(), reverse=True)
    secilen_yil = st.sidebar.selectbox("Yıl Seçin", yillar)
    
    # Türkçe Aylar
    aylar_dict = {i: ay for i, ay in enumerate(["Tümü", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", 
                                              "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
    
    secilen_ay_index = st.sidebar.selectbox("Ay Seçin", list(aylar_dict.keys()), format_func=lambda x: aylar_dict[x], index=datetime.now().month)
    
    # Filtreleme İşlemi
    df_filtered = df[df["Tarih"].dt.year == secilen_yil]
    if secilen_ay_index != 0: # 0 = Tümü
        df_filtered = df_filtered[df_filtered["Tarih"].dt.month == secilen_ay_index]
        filtre_mesaji = f"{secilen_yil} - {aylar_dict[secilen_ay_index]} Verileri"
    else:
        filtre_mesaji = f"{secilen_yil} Tüm Veriler"
else:
    df_filtered = df
    filtre_mesaji = "Veri Yok"

st.sidebar.divider()
st.sidebar.header("⚙️ Ayarlar")

tab_kat, tab_sabit, tab_reset = st.sidebar.tabs(["Kategoriler", "Sabitler", "Sistem"])

with tab_kat:
    st.write("**Yeni Kategori Ekle**")
    kat_tur = st.radio("Bu kategori ne için?", ["Gider", "Gelir"], horizontal=True)
    yeni_kat = st.text_input("Kategori Adı", placeholder="Örn: Bebek Bezi")
    
    if st.button("Kategori Ekle"):
        if yeni_kat and yeni_kat not in df_kategoriler["Kategori"].values:
            yeni_veri = pd.DataFrame({"Kategori": [yeni_kat], "Tur": [kat_tur]})
            df_kategoriler = pd.concat([df_kategoriler, yeni_veri], ignore_index=True)
            dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
            st.success("Eklendi!")
            st.rerun()
            
    # Silme (Türe göre filtreleyip gösterelim)
    st.divider()
    sil_tur = st.selectbox("Silinecek Türü Seç", ["Gider", "Gelir"])
    silinecek_liste = df_kategoriler[df_kategoriler["Tur"] == sil_tur]["Kategori"].tolist()
    sil_kat = st.selectbox("Silinecek Kategori", ["Seçiniz"] + silinecek_liste)
    
    if st.button("Sil") and sil_kat != "Seçiniz":
        df_kategoriler = df_kategoriler[df_kategoriler["Kategori"] != sil_kat]
        dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
        st.rerun()

with tab_sabit:
    st.caption("Sadece 'Gider' işlemleri içindir.")
    c1, c2 = st.columns([2, 1])
    yeni_sabit = c1.text_input("Gider Adı", placeholder="Örn: Netflix")
    yeni_gun = c2.number_input("Gün", 1, 31, 1)
    if st.button("Sabit Ekle"):
        if yeni_sabit:
            yeni_veri = pd.DataFrame({"Sabit Kalem": [yeni_sabit], "Odeme Gunu": [yeni_gun]})
            df_sabitler = pd.concat([df_sabitler, yeni_veri], ignore_index=True)
            dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
            st.rerun()
            
    # Sabit Silme
    sabit_list = df_sabitler["Sabit Kalem"].tolist() if not df_sabitler.empty else []
    sil_sabit = st.selectbox("Sabit Sil", ["Seçiniz"] + sabit_list)
    if st.button("Sabiti Sil") and sil_sabit != "Seçiniz":
        df_sabitler = df_sabitler[df_sabitler["Sabit Kalem"] != sil_sabit]
        dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
        st.rerun()

with tab_reset:
    if st.button("⚠️ Tüm Kategori Ayarlarını Sıfırla"):
        if os.path.exists(KATEGORI_DOSYASI): os.remove(KATEGORI_DOSYASI)
        st.rerun()

# --- ANA EKRAN: VERİ GİRİŞİ ---
st.subheader("📝 Yeni İşlem Ekle")

# İki sütunlu giriş ekranı
col_left, col_right = st.columns([1, 2])

with col_left:
    # 1. Önce Tür Seçimi (En tepeye koyduk ki aşağıyı etkilesin)
    islem_turu = st.radio("İşlem Türü", ["Gider", "Gelir"], horizontal=True)
    
    # 2. Türüne göre kategori listesini filtrele
    if not df_kategoriler.empty:
        filtrelenmis_kategoriler = df_kategoriler[df_kategoriler["Tur"] == islem_turu]["Kategori"].tolist()
    else:
        filtrelenmis_kategoriler = ["Genel"]
        
    secilen_kategori = st.selectbox("Kategori", filtrelenmis_kategoriler)
    tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)

with col_right:
    # 3. Sağ taraf dinamik değişecek
    islem_tarihi = st.date_input("Tarih", date.today())
    
    aciklama = ""
    son_odeme_val = None
    
    if islem_turu == "Gider":
        # Sadece Gider ise detayları göster
        giris_yontemi = st.radio("Tanım Şekli", ["Manuel Yaz", "Sabit Listeden Seç"], horizontal=True)
        
        if giris_yontemi == "Sabit Listeden Seç":
            if not df_sabitler.empty:
                secilen_sabit = st.selectbox("Sabit Gider Seç", df_sabitler["Sabit Kalem"].tolist())
                aciklama = secilen_sabit
                # Otomatik Tarih
                try:
                    sabit_gun = df_sabitler[df_sabitler["Sabit Kalem"] == secilen_sabit]["Odeme Gunu"].values[0]
                    onerilen = gelecek_odeme_tarihi_bul(sabit_gun)
                    st.caption(f"📅 Öneri: Ayın {int(sabit_gun)}. günü")
                    son_odeme_val = st.date_input("Son Ödeme Tarihi", value=onerilen)
                except:
                    son_odeme_val = st.date_input("Son Ödeme Tarihi", value=None)
            else:
                st.warning("Sabit listeniz boş. Ayarlardan ekleyebilirsiniz.")
                aciklama = st.text_input("Açıklama")
        else:
            aciklama = st.text_input("Açıklama", placeholder="Market, Benzin vb.")
            son_odeme_val = st.date_input("Son Ödeme Tarihi (Opsiyonel)", value=None)
            
    else:
        # Gelir ise sadece açıklama
        aciklama = st.text_input("Açıklama", placeholder="Maaş, Prim, Satış vb.")
        st.info("Gelir için son ödeme tarihi takibi yapılmaz.")

# Kaydet Butonu
if st.button("KAYDET", type="primary", use_container_width=True):
    yeni_satir = pd.DataFrame({
        "Tarih": [islem_tarihi],
        "Kategori": [secilen_kategori],
        "Tür": [islem_turu],
        "Tutar": [tutar],
        "Son Ödeme Tarihi": [son_odeme_val],
        "Açıklama": [aciklama]
    })
    df = pd.concat([df, yeni_satir], ignore_index=True)
    dosya_kaydet(df, VERI_DOSYASI)
    st.success("Kaydedildi!")
    st.rerun()

# --- RAPORLAR VE GRAFİKLER ---
st.divider()
st.header(f"📊 Rapor: {filtre_mesaji}")

if not df_filtered.empty:
    # 1. Özet Kartlar (Filtrelenmiş Veriye Göre)
    toplam_gelir = df_filtered[df_filtered["Tür"] == "Gelir"]["Tutar"].sum()
    toplam_gider = df_filtered[df_filtered["Tür"] == "Gider"]["Tutar"].sum()
    net_durum = toplam_gelir - toplam_gider
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Dönem Geliri", f"{toplam_gelir:,.0f} ₺")
    col2.metric("Dönem Gideri", f"{toplam_gider:,.0f} ₺")
    col3.metric("Dönem Net", f"{net_durum:,.0f} ₺", delta_color="normal" if net_durum > 0 else "inverse")

    # 2. Grafikler
    tab1, tab2, tab3 = st.tabs(["Pasta Grafiği", "Zaman Çizelgesi", "Detaylı Liste"])
    
    with tab1:
        # Pasta grafiği seçimi
        tur_secimi = st.radio("Hangi dağılımı görmek istersiniz?", ["Gider Dağılımı", "Gelir Dağılımı"], horizontal=True)
        hedef_tur = "Gider" if tur_secimi == "Gider Dağılımı" else "Gelir"
        
        subset = df_filtered[df_filtered["Tür"] == hedef_tur]
        if not subset.empty:
            fig = px.pie(subset, values="Tutar", names="Kategori", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"Bu dönemde {hedef_tur} kaydı bulunamadı.")
            
    with tab2:
        # Zaman Çizelgesi (Bar Chart)
        # Gün bazında grupla
        gunluk_ozet = df_filtered.groupby(["Tarih", "Tür"])["Tutar"].sum().reset_index()
        if not gunluk_ozet.empty:
            fig_bar = px.bar(gunluk_ozet, x="Tarih", y="Tutar", color="Tür", barmode="group", title="Günlük Hareketler")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Veri yok.")

    with tab3:
        # Filtrelenmiş liste ve silme
        st.dataframe(df_filtered.sort_values("Tarih", ascending=False), use_container_width=True)
        
        st.write("---")
        st.write("**Kayıt Silme (Tüm Zamanlardan):**")
        # Silme işlemi genelde ID üzerinden yapılır ama burada basitlik için tüm listeden seçtiriyoruz
        sil_id = st.selectbox("Silinecek Kaydı Seç", df.index, 
                             format_func=lambda x: f"{df.loc[x, 'Tarih'].strftime('%Y-%m-%d')} | {df.loc[x, 'Tür']} | {df.loc[x, 'Tutar']}₺ | {df.loc[x, 'Açıklama']}")
        
        if st.button("Seçili Kaydı Kalıcı Olarak Sil"):
            df = df.drop(sil_id).reset_index(drop=True)
            dosya_kaydet(df, VERI_DOSYASI)
            st.success("Silindi.")
            st.rerun()

else:
    st.info("Bu filtreye uygun kayıt bulunamadı. Lütfen filtreyi değiştirin veya yeni kayıt girin.")
