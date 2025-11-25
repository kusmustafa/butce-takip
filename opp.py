import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- AYARLAR VE VERİ YÖNETİMİ ---
DOSYA_ADI = 'aile_butcesi.csv'

def verileri_yukle():
    if not os.path.exists(DOSYA_ADI):
        # Dosya yoksa boş bir yapı oluştur
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Açıklama"])
        df.to_csv(DOSYA_ADI, index=False)
    return pd.read_csv(DOSYA_ADI)

def verileri_kaydet(df):
    df.to_csv(DOSYA_ADI, index=False)

# --- SAYFA YAPISI ---
st.set_page_config(page_title="Aile Bütçe Takip", page_icon="💰", layout="centered")

st.title("🏠 Aile Gelir/Gider Takip Sistemi")

# Verileri Çek
df = verileri_yukle()

# --- YAN MENÜ: VERİ EKLEME ---
st.sidebar.header("Yeni İşlem Ekle")

with st.sidebar.form("ekleme_formu", clear_on_submit=True):
    tarih = st.date_input("Tarih", datetime.now())
    tur = st.selectbox("İşlem Türü", ["Gider", "Gelir"])
    
    kategoriler = ["Market", "Kira", "Faturalar", "Maaş", "Eğlence", "Diğer"]
    kategori = st.selectbox("Kategori", kategoriler)
    
    tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0)
    aciklama = st.text_input("Açıklama (Opsiyonel)")
    
    submit = st.form_submit_button("Kaydet")
    
    if submit:
        yeni_veri = pd.DataFrame({
            "Tarih": [tarih],
            "Kategori": [kategori],
            "Tür": [tur],
            "Tutar": [tutar],
            "Açıklama": [aciklama]
        })
        df = pd.concat([df, yeni_veri], ignore_index=True)
        verileri_kaydet(df)
        st.success("İşlem başarıyla eklendi!")
        st.rerun() # Sayfayı yenile

# --- ANA EKRAN: ÖZET DURUM ---
st.divider()

if not df.empty:
    # Hesaplamalar
    toplam_gelir = df[df["Tür"] == "Gelir"]["Tutar"].sum()
    toplam_gider = df[df["Tür"] == "Gider"]["Tutar"].sum()
    net_durum = toplam_gelir - toplam_gider

    # Metrik Kartları
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Gelir", f"{toplam_gelir:,.2f} TL", delta_color="normal")
    col2.metric("Toplam Gider", f"{toplam_gider:,.2f} TL", delta_color="inverse")
    col3.metric("Net Durum", f"{net_durum:,.2f} TL", delta=f"{net_durum:,.2f} TL")

    # --- GRAFİKLER ---
    st.subheader("📊 Aylık Analiz")
    
    tab1, tab2 = st.tabs(["Gider Dağılımı", "Zaman Çizelgesi"])
    
    with tab1:
        # Sadece giderleri alıp pasta grafiği yapalım
        gider_df = df[df["Tür"] == "Gider"]
        if not gider_df.empty:
            fig_pie = px.pie(gider_df, values='Tutar', names='Kategori', title='Nereye Ne Harcadık?')
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Henüz gider kaydı yok.")

    with tab2:
        # Tarih bazlı çubuk grafik
        fig_bar = px.bar(df, x="Tarih", y="Tutar", color="Tür", title="Gelir vs Gider Zamanla Değişim", barmode='group')
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- VERİ TABLOSU VE SİLME ---
    st.subheader("📝 Son İşlemler")
    
    # Silme işlemi için her satıra bir seçim kutusu koymak yerine
    # basitçe indekse göre silme yapalım (Streamlit'te en kolayı budur)
    silinecek_id = st.selectbox("Silmek istediğiniz işlemi seçin (ID - Açıklama):", 
                                options=df.index, 
                                format_func=lambda x: f"{x} - {df.loc[x, 'Tür']} - {df.loc[x, 'Tutar']} TL ({df.loc[x, 'Açıklama']})")
    
    if st.button("Seçili İşlemi Sil"):
        df = df.drop(silinecek_id).reset_index(drop=True)
        verileri_kaydet(df)
        st.warning("İşlem silindi.")
        st.rerun()

    st.dataframe(df, use_container_width=True)

else:
    st.info("Henüz hiç kayıt girmediniz. Sol menüden ekleme yapabilirsiniz.")
