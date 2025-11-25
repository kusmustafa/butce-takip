import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date, timedelta

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- YARDIMCI FONKSİYONLAR ---
def dosya_yukle(dosya_adi, varsayilan_liste, kolonlar):
    """Dosyayı yükler, yoksa varsayılanlarla oluşturur."""
    if not os.path.exists(dosya_adi):
        df = pd.DataFrame(varsayilan_liste, columns=kolonlar)
        df.to_csv(dosya_adi, index=False)
        return df
    return pd.read_csv(dosya_adi)

def verileri_yukle():
    """Ana veri dosyasını yükler."""
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])
        df.to_csv(VERI_DOSYASI, index=False)
        return df
    
    df = pd.read_csv(VERI_DOSYASI)
    if "Son Ödeme Tarihi" not in df.columns:
        df["Son Ödeme Tarihi"] = None
    return df

def dosya_kaydet(df, dosya_adi):
    df.to_csv(dosya_adi, index=False)

def gelecek_odeme_tarihi_bul(hedef_gun):
    """Bugüne göre bir sonraki ödeme tarihini hesaplar."""
    bugun = date.today()
    try:
        hedef_gun = int(hedef_gun)
    except:
        return bugun # Gün girilmemişse bugünü dön
        
    if hedef_gun < 1 or hedef_gun > 31:
        return bugun

    # Bu ayın hedef günü
    try:
        bu_ay_tarih = date(bugun.year, bugun.month, hedef_gun)
    except ValueError: # Örn: Şubat 30 hatası
        bu_ay_tarih = date(bugun.year, bugun.month, 28) # Basitçe ay sonuna çek

    if bu_ay_tarih >= bugun:
        return bu_ay_tarih
    else:
        # Tarih geçmiş, sonraki aya geç
        sonraki_ay = bugun.month + 1 if bugun.month < 12 else 1
        yil = bugun.year if bugun.month < 12 else bugun.year + 1
        try:
            return date(yil, sonraki_ay, hedef_gun)
        except ValueError:
            return date(yil, sonraki_ay, 28)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bütçe Asistanı", page_icon="💰", layout="centered")
st.title("🏠 Akıllı Bütçe Asistanı")

# Verileri Hazırla
df = verileri_yukle()

# Kategoriler
varsayilan_kat = [["Market"], ["Kira"], ["Faturalar"], ["Eğlence"], ["Maaş"]]
df_kategoriler = dosya_yukle(KATEGORI_DOSYASI, varsayilan_kat, ["Kategori"])
kategori_listesi = df_kategoriler["Kategori"].tolist()

# Sabit Giderler (İsim ve Gün Sütunu)
# Eğer eski dosya varsa ve 'Gun' sütunu yoksa eklemek için kontrol:
if os.path.exists(SABITLER_DOSYASI):
    df_sabitler = pd.read_csv(SABITLER_DOSYASI)
    if "Odeme Gunu" not in df_sabitler.columns:
        df_sabitler["Odeme Gunu"] = 0
        dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
else:
    varsayilan_sabitler = [["Ev Kirası", 1], ["Kredi Kartı", 15]]
    df_sabitler = pd.DataFrame(varsayilan_sabitler, columns=["Sabit Kalem", "Odeme Gunu"])
    dosya_kaydet(df_sabitler, SABITLER_DOSYASI)

# --- YAN MENÜ: AYARLAR ---
st.sidebar.header("⚙️ Ayarlar")
tab_kat, tab_sabit = st.sidebar.tabs(["Kategoriler", "Sabit Giderler"])

with tab_kat:
    yeni_kat = st.text_input("Yeni Kategori", placeholder="Örn: Sağlık")
    if st.button("Kategori Ekle"):
        if yeni_kat and yeni_kat not in kategori_listesi:
            df_kategoriler = pd.concat([df_kategoriler, pd.DataFrame({"Kategori": [yeni_kat]})], ignore_index=True)
            dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
            st.rerun()
            
    sil_kat = st.selectbox("Sil", ["Seçiniz"] + kategori_listesi)
    if st.button("Sil") and sil_kat != "Seçiniz":
        df_kategoriler = df_kategoriler[df_kategoriler["Kategori"] != sil_kat]
        dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
        st.rerun()

with tab_sabit:
    st.write("Sabit Ödeme Ekle:")
    c1, c2 = st.columns([2, 1])
    yeni_sabit_ad = c1.text_input("Gider Adı", placeholder="Örn: Ev Kredisi")
    yeni_sabit_gun = c2.number_input("Gün (Ayın kaçı?)", min_value=0, max_value=31, value=1, help="0 girerseniz tarih önerilmez.")
    
    if st.button("Sabit Ekle"):
        if yeni_sabit_ad:
            yeni_veri = pd.DataFrame({"Sabit Kalem": [yeni_sabit_ad], "Odeme Gunu": [yeni_sabit_gun]})
            df_sabitler = pd.concat([df_sabitler, yeni_veri], ignore_index=True)
            dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
            st.success("Eklendi!")
            st.rerun()
            
    # Silme işlemi
    sabit_dict = dict(zip(df_sabitler["Sabit Kalem"], df_sabitler["Odeme Gunu"]))
    sil_sabit = st.selectbox("Sabit Sil", ["Seçiniz"] + list(sabit_dict.keys()))
    if st.button("Sabiti Sil") and sil_sabit != "Seçiniz":
        df_sabitler = df_sabitler[df_sabitler["Sabit Kalem"] != sil_sabit]
        dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
        st.rerun()

# --- ANA EKRAN: VERİ GİRİŞİ (FORM KULLANILMADI - CANLI ETKİLEŞİM İÇİN) ---
st.divider()
st.subheader("📝 Yeni İşlem")

# Giriş Alanları
col_giris1, col_giris2 = st.columns(2)

with col_giris1:
    tur = st.radio("İşlem Türü", ["Gider", "Gelir"], horizontal=True)
    kategori = st.selectbox("Kategori", kategori_listesi)
    tutar = st.number_input("Tutar (TL)", min_value=0.0, step=100.0)

with col_giris2:
    tarih = st.date_input("İşlem Tarihi", date.today())
    
    aciklama = ""
    son_odeme_val = None
    
    if tur == "Gider":
        giris_tipi = st.radio("Tanım", ["Listeden Seç", "Manuel"], horizontal=True, label_visibility="collapsed")
        
        if giris_tipi == "Listeden Seç":
            if not df_sabitler.empty:
                secilen_sabit = st.selectbox("Sabit Gider", df_sabitler["Sabit Kalem"].tolist())
                aciklama = secilen_sabit
                
                # --- OTOMATİK TARİH HESAPLAMA ---
                # Seçilen sabit giderin gününü bul
                secilen_gun = df_sabitler[df_sabitler["Sabit Kalem"] == secilen_sabit]["Odeme Gunu"].values[0]
                
                if secilen_gun > 0:
                    onerilen_tarih = gelecek_odeme_tarihi_bul(secilen_gun)
                    st.caption(f"📅 Öneri: Ayın {secilen_gun}. günü")
                    son_odeme_val = st.date_input("Son Ödeme Tarihi", value=onerilen_tarih)
                else:
                    son_odeme_val = st.date_input("Son Ödeme Tarihi", value=None)
            else:
                st.warning("Ayarlardan sabit gider ekleyin.")
        else:
            aciklama = st.text_input("Açıklama", placeholder="Market vs.")
            son_odeme_val = st.date_input("Son Ödeme Tarihi (Opsiyonel)", value=None)
    else:
        aciklama = st.text_input("Açıklama", placeholder="Maaş, Prim vb.")

# Kaydet Butonu (Geniş)
if st.button("KAYDET", type="primary", use_container_width=True):
    yeni_satir = pd.DataFrame({
        "Tarih": [tarih],
        "Kategori": [kategori],
        "Tür": [tur],
        "Tutar": [tutar],
        "Son Ödeme Tarihi": [son_odeme_val],
        "Açıklama": [aciklama]
    })
    df = pd.concat([df, yeni_satir], ignore_index=True)
    dosya_kaydet(df, VERI_DOSYASI)
    st.success("✅ İşlem başarıyla kaydedildi!")
    # Sayfayı yenilemeye gerek yok, tablo aşağıda güncellenir. 
    # Ancak form temizlensin istersen st.rerun() açabilirsin.

# --- RAPORLAR ---
st.divider()

if not df.empty:
    # Özet Kartlar
    gelir = df[df["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df[df["Tür"] == "Gider"]["Tutar"].sum()
    kasa = gelir - gider
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Gelir", f"{gelir:,.0f} ₺")
    c2.metric("Gider", f"{gider:,.0f} ₺")
    c3.metric("Net", f"{kasa:,.0f} ₺", delta_color="normal" if kasa > 0 else "inverse")

    # Sekmeler
    t1, t2, t3 = st.tabs(["📊 Grafikler", "💳 Kart/Borç Detay", "📅 Ödeme Takvimi"])
    
    with t1:
        giderler = df[df["Tür"] == "Gider"]
        if not giderler.empty:
            fig = px.pie(giderler, values="Tutar", names="Kategori", title="Harcama Dağılımı")
            st.plotly_chart(fig, use_container_width=True)
            
    with t2:
        if not giderler.empty:
            # Açıklamaya göre harcama (Hangi karta ne kadar?)
            ozet = giderler.groupby("Açıklama")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
            st.bar_chart(ozet, x="Açıklama", y="Tutar")
            
    with t3:
        # Yaklaşan Ödemeler
        gelecek = df[df["Son Ödeme Tarihi"].notnull()].copy()
        if not gelecek.empty:
            gelecek["Son Ödeme Tarihi"] = pd.to_datetime(gelecek["Son Ödeme Tarihi"]).dt.date
            gelecek = gelecek.sort_values("Son Ödeme Tarihi")
            st.dataframe(gelecek[["Son Ödeme Tarihi", "Açıklama", "Tutar"]], use_container_width=True, hide_index=True)
        else:
            st.info("Planlanmış ödeme yok.")
            
    # Geçmiş Listesi
    with st.expander("📋 İşlem Geçmişi / Silme"):
        st.dataframe(df.sort_values("Tarih", ascending=False), use_container_width=True)
        sil_id = st.selectbox("Silinecek Kayıt", df.index, format_func=lambda x: f"{df.loc[x, 'Açıklama']} - {df.loc[x, 'Tutar']}₺")
        if st.button("Sil"):
            df = df.drop(sil_id).reset_index(drop=True)
            dosya_kaydet(df, VERI_DOSYASI)
            st.rerun()

else:
    st.info("Kayıt bulunamadı.")
