import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'

# --- VERİ YÖNETİMİ ---
def kategorileri_yukle():
    """Kategorileri dosyadan yükler, dosya yoksa varsayılanları oluşturur."""
    if not os.path.exists(KATEGORI_DOSYASI):
        varsayilanlar = ["Market", "Kira", "Faturalar", "Maaş", "Eğlence", "Ulaşım"]
        df_kat = pd.DataFrame(varsayilanlar, columns=["Kategori"])
        df_kat.to_csv(KATEGORI_DOSYASI, index=False)
    return pd.read_csv(KATEGORI_DOSYASI)

def verileri_yukle():
    """Ana veri dosyasını yükler."""
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama"])
        df.to_csv(VERI_DOSYASI, index=False)
        return df
    
    df = pd.read_csv(VERI_DOSYASI)
    
    # Eski kullanıcılar için sütun kontrolü (Geriye dönük uyumluluk)
    if "Son Ödeme Tarihi" not in df.columns:
        df["Son Ödeme Tarihi"] = None
        
    return df

def dosya_kaydet(df, dosya_adi):
    df.to_csv(dosya_adi, index=False)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bütçe Takip v2", page_icon="💰", layout="centered")

st.title("🏠 Gelişmiş Bütçe Takip")

# Verileri Hazırla
df = verileri_yukle()
df_kategoriler = kategorileri_yukle()
kategori_listesi = df_kategoriler["Kategori"].tolist()

# --- YAN MENÜ: İŞLEMLER ---
st.sidebar.header("📝 İşlemler")

# 1. Kategori Yönetimi (Expander ile gizlenebilir alan)
with st.sidebar.expander("⚙️ Kategori Ayarları"):
    st.write("Yeni Kategori Ekle:")
    yeni_kat = st.text_input("Kategori Adı", label_visibility="collapsed", placeholder="Örn: Okul")
    if st.button("Ekle"):
        if yeni_kat and yeni_kat not in kategori_listesi:
            yeni_veri = pd.DataFrame({"Kategori": [yeni_kat]})
            df_kategoriler = pd.concat([df_kategoriler, yeni_veri], ignore_index=True)
            dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
            st.success(f"{yeni_kat} eklendi!")
            st.rerun()
        elif yeni_kat in kategori_listesi:
            st.warning("Bu kategori zaten var.")

    st.write("Kategori Sil:")
    silinecek_kat = st.selectbox("Silinecek Kategori", ["Seçiniz"] + kategori_listesi)
    if st.button("Sil") and silinecek_kat != "Seçiniz":
        df_kategoriler = df_kategoriler[df_kategoriler["Kategori"] != silinecek_kat]
        dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
        st.success("Silindi.")
        st.rerun()

# 2. Veri Ekleme Formu
st.sidebar.divider()
st.sidebar.subheader("Yeni Kayıt")

with st.sidebar.form("ekleme_formu", clear_on_submit=True):
    tarih = st.date_input("İşlem Tarihi", datetime.now())
    tur = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
    
    # Güncel kategori listesini kullan
    kategori = st.selectbox("Kategori", kategori_listesi)
    
    tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0)
    
    # Sadece GİDER seçilirse Son Ödeme Tarihi görünsün
    son_odeme = None
    if tur == "Gider":
        st.caption("Opsiyonel: Kredi kartı veya fatura için son ödeme tarihi.")
        son_odeme_input = st.date_input("Son Ödeme Tarihi", value=None)
        if son_odeme_input:
            son_odeme = son_odeme_input
            
    aciklama = st.text_input("Açıklama")
    
    submit = st.form_submit_button("Kaydet")
    
    if submit:
        yeni_satir = pd.DataFrame({
            "Tarih": [tarih],
            "Kategori": [kategori],
            "Tür": [tur],
            "Tutar": [tutar],
            "Son Ödeme Tarihi": [son_odeme],
            "Açıklama": [aciklama]
        })
        df = pd.concat([df, yeni_satir], ignore_index=True)
        dosya_kaydet(df, VERI_DOSYASI)
        st.success("Kaydedildi!")
        st.rerun()

# --- ANA EKRAN: ÖZET ---
if not df.empty:
    # Temel Hesaplar
    toplam_gelir = df[df["Tür"] == "Gelir"]["Tutar"].sum()
    toplam_gider = df[df["Tür"] == "Gider"]["Tutar"].sum()
    net_durum = toplam_gelir - toplam_gider
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Gelir", f"{toplam_gelir:,.2f} ₺", delta_color="normal")
    col2.metric("Gider", f"{toplam_gider:,.2f} ₺", delta_color="inverse")
    col3.metric("Kasa", f"{net_durum:,.2f} ₺", delta=f"{net_durum:,.2f} ₺")
    
    st.divider()

    # --- GRAFİKLER ---
    tab1, tab2 = st.tabs(["📊 Analiz", "📅 Yaklaşan Ödemeler"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            gider_df = df[df["Tür"] == "Gider"]
            if not gider_df.empty:
                fig = px.pie(gider_df, values='Tutar', names='Kategori', title='Gider Dağılımı', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(df, x="Tarih", y="Tutar", color="Tür", title="Zaman Çizelgesi", barmode='group')
            st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        # Son ödeme tarihi olan ve henüz tarihi geçmemiş/bugün olan giderleri filtrele
        bugun = date.today()
        # Sadece son ödeme tarihi girilmiş olanlar
        odeme_df = df[df["Son Ödeme Tarihi"].notnull()].copy()
        
        if not odeme_df.empty:
            # Tarih formatını düzeltme ve sıralama
            odeme_df["Son Ödeme Tarihi"] = pd.to_datetime(odeme_df["Son Ödeme Tarihi"]).dt.date
            odeme_df = odeme_df.sort_values("Son Ödeme Tarihi")
            
            st.write("Son Ödeme Tarihi Girilen Kayıtlar:")
            st.dataframe(
                odeme_df[["Son Ödeme Tarihi", "Kategori", "Tutar", "Açıklama"]],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Henüz son ödeme tarihi girilmiş bir kayıt yok.")

    # --- GEÇMİŞ KAYITLAR VE SİLME ---
    st.divider()
    st.subheader("📋 Kayıt Geçmişi")
    
    # Tabloyu daha şık göstermek için
    st.dataframe(df.sort_values("Tarih", ascending=False), use_container_width=True)
    
    with st.expander("🗑️ Kayıt Silme"):
        sil_id = st.selectbox("Silinecek İşlem", df.index, 
                             format_func=lambda x: f"{df.loc[x, 'Tarih']} - {df.loc[x, 'Kategori']} - {df.loc[x, 'Tutar']} ₺")
        if st.button("Seçili Kaydı Sil"):
            df = df.drop(sil_id).reset_index(drop=True)
            dosya_kaydet(df, VERI_DOSYASI)
            st.warning("Kayıt silindi.")
            st.rerun()

else:
    st.info("👋 Hoş geldin! Sol menüden 'Kategori Ayarları'nı yaparak başlayabilirsin.")
