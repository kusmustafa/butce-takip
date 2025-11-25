import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- GÜVENLİ VERİ YÖNETİMİ ---
def dosya_kontrol_ve_yukle():
    """Dosyaları kontrol eder, eksik veya bozuksa onarır."""
    
    # 1. Kategoriler Dosyası Kontrolü
    if not os.path.exists(KATEGORI_DOSYASI):
        df_kat = pd.DataFrame([["Market"], ["Kira"], ["Faturalar"], ["Eğlence"]], columns=["Kategori"])
        df_kat.to_csv(KATEGORI_DOSYASI, index=False)
    else:
        try:
            df = pd.read_csv(KATEGORI_DOSYASI)
            if "Kategori" not in df.columns:
                raise ValueError("Eski format")
        except:
            df_kat = pd.DataFrame([["Market"], ["Kira"], ["Faturalar"]], columns=["Kategori"])
            df_kat.to_csv(KATEGORI_DOSYASI, index=False)

    # 2. Sabit Giderler Dosyası Kontrolü
    if not os.path.exists(SABITLER_DOSYASI):
        df_sabit = pd.DataFrame(columns=["Sabit Kalem", "Odeme Gunu"])
        df_sabit.to_csv(SABITLER_DOSYASI, index=False)
    else:
        try:
            df = pd.read_csv(SABITLER_DOSYASI)
            if "Odeme Gunu" not in df.columns:
                df["Odeme Gunu"] = 1
                df.to_csv(SABITLER_DOSYASI, index=False)
        except:
            df_sabit = pd.DataFrame(columns=["Sabit Kalem", "Odeme Gunu"])
            df_sabit.to_csv(SABITLER_DOSYASI, index=False)

    # 3. Ana Veri Dosyası Kontrolü
    if not os.path.exists(VERI_DOSYASI):
        df_veri = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])
        df_veri.to_csv(VERI_DOSYASI, index=False)
    else:
        try:
            df = pd.read_csv(VERI_DOSYASI)
            if "Son Ödeme Tarihi" not in df.columns:
                df["Son Ödeme Tarihi"] = None
                df.to_csv(VERI_DOSYASI, index=False)
        except:
            pass

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

# --- UYGULAMA BAŞLANGICI ---
# İSİM GÜNCELLEMESİ BURADA YAPILDI
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="centered")

# Önce dosyaları kontrol et ve onar
dosya_kontrol_ve_yukle()

# BAŞLIK GÜNCELLEMESİ
st.title("🐦 Kuşların Bütçe Makinesi")

# Verileri Yükle
try:
    df = verileri_oku(VERI_DOSYASI)
    df_kategoriler = verileri_oku(KATEGORI_DOSYASI)
    df_sabitler = verileri_oku(SABITLER_DOSYASI)
except Exception as e:
    st.error(f"Veri okuma hatası. Lütfen sayfayı yenileyin.")
    df = pd.DataFrame()
    df_kategoriler = pd.DataFrame()
    df_sabitler = pd.DataFrame()

kategori_listesi = df_kategoriler["Kategori"].tolist() if not df_kategoriler.empty else ["Genel"]

# --- YAN MENÜ ---
st.sidebar.header("⚙️ Ayarlar")
tab_kat, tab_sabit, tab_sistem = st.sidebar.tabs(["Kategoriler", "Sabitler", "Sistem"])

with tab_kat:
    yeni_kat = st.text_input("Yeni Kategori", placeholder="Örn: Yem Parası 🐦")
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
    yeni_sabit_ad = c1.text_input("Gider Adı", placeholder="Örn: Yuva Kirası")
    yeni_sabit_gun = c2.number_input("Gün", min_value=1, max_value=31, value=1)
    
    if st.button("Sabit Ekle"):
        if yeni_sabit_ad:
            yeni_veri = pd.DataFrame({"Sabit Kalem": [yeni_sabit_ad], "Odeme Gunu": [yeni_sabit_gun]})
            df_sabitler = pd.concat([df_sabitler, yeni_veri], ignore_index=True)
            dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
            st.success("Eklendi!")
            st.rerun()
            
    sabit_list = df_sabitler["Sabit Kalem"].tolist() if not df_sabitler.empty else []
    sil_sabit = st.selectbox("Sabit Sil", ["Seçiniz"] + sabit_list)
    if st.button("Sabiti Sil") and sil_sabit != "Seçiniz":
        df_sabitler = df_sabitler[df_sabitler["Sabit Kalem"] != sil_sabit]
        dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
        st.rerun()

with tab_sistem:
    st.warning("Acil Durum Butonu")
    if st.button("Ayarları Sıfırla (Reset)"):
        if os.path.exists(SABITLER_DOSYASI):
            os.remove(SABITLER_DOSYASI)
            st.success("Sıfırlandı. Sayfayı yenileyin.")
            st.rerun()

# --- ANA EKRAN ---
st.divider()
st.subheader("📝 Yeni İşlem")

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
                
                try:
                    secilen_gun = df_sabitler[df_sabitler["Sabit Kalem"] == secilen_sabit]["Odeme Gunu"].values[0]
                    onerilen_tarih = gelecek_odeme_tarihi_bul(secilen_gun)
                    st.caption(f"📅 Öneri: Ayın {int(secilen_gun)}. günü")
                    son_odeme_val = st.date_input("Son Ödeme Tarihi", value=onerilen_tarih)
                except:
                    st.warning("Tarih hesaplanamadı.")
                    son_odeme_val = st.date_input("Son Ödeme Tarihi", value=None)
            else:
                st.warning("Listeniz boş.")
                aciklama = st.text_input("Açıklama")
        else:
            aciklama = st.text_input("Açıklama", placeholder="Market vs.")
            son_odeme_val = st.date_input("Son Ödeme Tarihi (Opsiyonel)", value=None)
    else:
        aciklama = st.text_input("Açıklama", placeholder="Maaş, Prim vb.")

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
    st.success("Kayıt Başarılı! 🐦")

# --- RAPORLAR ---
st.divider()

if not df.empty:
    gelir = df[df["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df[df["Tür"] == "Gider"]["Tutar"].sum()
    kasa = gelir - gider
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Gelir", f"{gelir:,.0f} ₺")
    c2.metric("Gider", f"{gider:,.0f} ₺")
    c3.metric("Kasa Durumu", f"{kasa:,.0f} ₺", delta_color="normal" if kasa > 0 else "inverse")

    t1, t2, t3 = st.tabs(["📊 Grafikler", "💳 Kart Detay", "📅 Takvim"])
    
    with t1:
        giderler = df[df["Tür"] == "Gider"]
        if not giderler.empty:
            fig = px.pie(giderler, values="Tutar", names="Kategori", title="Harcama Dağılımı")
            st.plotly_chart(fig, use_container_width=True)
            
    with t2:
        if not giderler.empty:
            ozet = giderler.groupby("Açıklama")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
            st.bar_chart(ozet, x="Açıklama", y="Tutar")
            
    with t3:
        gelecek = df[df["Son Ödeme Tarihi"].notnull()].copy()
        if not gelecek.empty:
            gelecek["Son Ödeme Tarihi"] = pd.to_datetime(gelecek["Son Ödeme Tarihi"]).dt.date
            gelecek = gelecek.sort_values("Son Ödeme Tarihi")
            st.dataframe(gelecek[["Son Ödeme Tarihi", "Açıklama", "Tutar"]], use_container_width=True, hide_index=True)
        else:
            st.info("Planlanmış ödeme yok.")
            
    with st.expander("📋 Kayıt Geçmişi / Silme"):
        st.dataframe(df.sort_values("Tarih", ascending=False), use_container_width=True)
        sil_id = st.selectbox("Silinecek Kayıt", df.index, format_func=lambda x: f"{df.loc[x, 'Açıklama']} - {df.loc[x, 'Tutar']}₺")
        if st.button("Sil"):
            df = df.drop(sil_id).reset_index(drop=True)
            dosya_kaydet(df, VERI_DOSYASI)
            st.rerun()
else:
    st.info("Henüz kayıt yok. Kuşların Bütçe Makinesi hazır! 🐦")
