import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- AYARLAR ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
SABITLER_DOSYASI = 'sabit_giderler.csv'  # Yeni dosya: Sabit ödeme kalemleri

# --- VERİ YÖNETİMİ ---
def dosya_yukle(dosya_adi, varsayilan_liste, kolon_adi):
    """Genel dosya yükleme ve oluşturma fonksiyonu"""
    if not os.path.exists(dosya_adi):
        df = pd.DataFrame(varsayilan_liste, columns=[kolon_adi])
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
    # Sütun kontrolü
    if "Son Ödeme Tarihi" not in df.columns:
        df["Son Ödeme Tarihi"] = None
    return df

def dosya_kaydet(df, dosya_adi):
    df.to_csv(dosya_adi, index=False)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Bütçe Takip v3", page_icon="💰", layout="centered")
st.title("🏠 Gelişmiş Bütçe Takip")

# Verileri Hazırla
df = verileri_yukle()

# Kategorileri Yükle
varsayilan_kat = ["Kredi Kartı", "Fatura", "Kira", "Market", "Eğlence", "Maaş"]
df_kategoriler = dosya_yukle(KATEGORI_DOSYASI, varsayilan_kat, "Kategori")
kategori_listesi = df_kategoriler["Kategori"].tolist()

# Sabit Giderleri Yükle
varsayilan_sabitler = ["Ev Kirası", "Yapı Kredi Kartı", "İş Bankası Kartı", "Elektrik Faturası"]
df_sabitler = dosya_yukle(SABITLER_DOSYASI, varsayilan_sabitler, "Sabit Kalem")
sabit_listesi = df_sabitler["Sabit Kalem"].tolist()

# --- YAN MENÜ: AYARLAR ---
st.sidebar.header("⚙️ Ayarlar")

# Sekmeli Ayar Menüsü
tab_kat, tab_sabit = st.sidebar.tabs(["Kategoriler", "Sabit Giderler"])

with tab_kat:
    yeni_kat = st.text_input("Yeni Kategori", placeholder="Örn: Benzin")
    if st.button("Kategori Ekle"):
        if yeni_kat and yeni_kat not in kategori_listesi:
            df_kategoriler = pd.concat([df_kategoriler, pd.DataFrame({"Kategori": [yeni_kat]})], ignore_index=True)
            dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
            st.success("Eklendi!")
            st.rerun()
            
    silinecek_kat = st.selectbox("Silinecek Kategori", ["Seçiniz"] + kategori_listesi)
    if st.button("Kategoriyi Sil") and silinecek_kat != "Seçiniz":
        df_kategoriler = df_kategoriler[df_kategoriler["Kategori"] != silinecek_kat]
        dosya_kaydet(df_kategoriler, KATEGORI_DOSYASI)
        st.rerun()

with tab_sabit:
    st.caption("Sık kullandığın ödeme isimlerini buraya ekle.")
    yeni_sabit = st.text_input("Yeni Sabit Gider", placeholder="Örn: Netflix")
    if st.button("Sabit Ekle"):
        if yeni_sabit and yeni_sabit not in sabit_listesi:
            df_sabitler = pd.concat([df_sabitler, pd.DataFrame({"Sabit Kalem": [yeni_sabit]})], ignore_index=True)
            dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
            st.success("Eklendi!")
            st.rerun()
            
    silinecek_sabit = st.selectbox("Silinecek Sabit", ["Seçiniz"] + sabit_listesi)
    if st.button("Sabiti Sil") and silinecek_sabit != "Seçiniz":
        df_sabitler = df_sabitler[df_sabitler["Sabit Kalem"] != silinecek_sabit]
        dosya_kaydet(df_sabitler, SABITLER_DOSYASI)
        st.rerun()

# --- YAN MENÜ: VERİ GİRİŞİ ---
st.sidebar.divider()
st.sidebar.header("📝 Yeni Kayıt")

with st.sidebar.form("ekleme_formu", clear_on_submit=True):
    tarih = st.date_input("İşlem Tarihi", datetime.now())
    tur = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
    kategori = st.selectbox("Kategori", kategori_listesi)
    tutar = st.number_input("Tutar (TL)", min_value=0.0, step=10.0)
    
    # Gider ise detaylar
    son_odeme = None
    aciklama = ""
    
    if tur == "Gider":
        # Açıklama Giriş Yöntemi Seçimi
        giris_yontemi = st.radio("Ödeme Tanımı", ["Listeden Seç", "Manuel Yaz"], horizontal=True, label_visibility="collapsed")
        
        if giris_yontemi == "Listeden Seç":
            if sabit_listesi:
                aciklama = st.selectbox("Sabit Gider Seçiniz", sabit_listesi)
            else:
                st.warning("Listeniz boş, ayarlardan ekleyin.")
                aciklama = st.text_input("Açıklama Giriniz")
        else:
            aciklama = st.text_input("Açıklama Giriniz", placeholder="Örn: Market alışverişi")
            
        st.caption("Son Ödeme Tarihi (Varsa):")
        son_odeme_input = st.date_input("Son Ödeme", value=None)
        if son_odeme_input:
            son_odeme = son_odeme_input
            
    else: # Gelir ise
        aciklama = st.text_input("Açıklama", placeholder="Örn: Maaş")

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

# --- ANA EKRAN ---
if not df.empty:
    # Özet Kartlar
    toplam_gelir = df[df["Tür"] == "Gelir"]["Tutar"].sum()
    toplam_gider = df[df["Tür"] == "Gider"]["Tutar"].sum()
    net_durum = toplam_gelir - toplam_gider
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Gelir", f"{toplam_gelir:,.0f} ₺", delta_color="normal")
    c2.metric("Gider", f"{toplam_gider:,.0f} ₺", delta_color="inverse")
    c3.metric("Kasa", f"{net_durum:,.0f} ₺", delta=f"{net_durum:,.0f} ₺")
    
    st.divider()

    # Tablar
    tab1, tab2, tab3 = st.tabs(["📊 Genel Bakış", "💳 Kredi/Borç Detayı", "📅 Ödeme Takvimi"])
    
    with tab1:
        # Gelir/Gider Trendi ve Pasta
        col_a, col_b = st.columns(2)
        with col_a:
            gider_df = df[df["Tür"] == "Gider"]
            if not gider_df.empty:
                # Kategorilere göre grupla
                kat_ozet = gider_df.groupby("Kategori")["Tutar"].sum().reset_index()
                fig = px.pie(kat_ozet, values='Tutar', names='Kategori', title='Kategori Bazlı Harcama', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        with col_b:
             # Aylık Trend
             df['Ay'] = pd.to_datetime(df['Tarih']).dt.strftime('%Y-%m')
             aylik_ozet = df.groupby(['Ay', 'Tür'])['Tutar'].sum().reset_index()
             fig_bar = px.bar(aylik_ozet, x='Ay', y='Tutar', color='Tür', barmode='group', title="Aylık Gelir/Gider")
             st.plotly_chart(fig_bar, use_container_width=True)

    with tab2:
        # Sadece sabit giderlerden (kartlar vb) ne kadar harcanmış
        st.subheader("Ödeme Kalemi Bazlı Analiz")
        if not gider_df.empty:
            # Açıklamaya göre grupla (YKB, İş bankası vb. ne kadar tutmuş)
            kalem_ozet = gider_df.groupby("Açıklama")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
            st.bar_chart(kalem_ozet, x="Açıklama", y="Tutar")
            st.dataframe(kalem_ozet, use_container_width=True)
        else:
            st.info("Henüz veri yok.")

    with tab3:
        # Yaklaşan ödemeler
        odeme_df = df[df["Son Ödeme Tarihi"].notnull()].copy()
        if not odeme_df.empty:
            odeme_df["Son Ödeme Tarihi"] = pd.to_datetime(odeme_df["Son Ödeme Tarihi"]).dt.date
            odeme_df = odeme_df.sort_values("Son Ödeme Tarihi")
            st.dataframe(odeme_df[["Son Ödeme Tarihi", "Açıklama", "Tutar", "Kategori"]], 
                         use_container_width=True, hide_index=True)
        else:
            st.info("Yaklaşan ödeme bulunmuyor.")

    # Geçmiş Tablosu
    with st.expander("📋 Tüm Kayıtları Gör / Düzenle"):
        st.dataframe(df.sort_values("Tarih", ascending=False), use_container_width=True)
        sil_id = st.selectbox("Silinecek Kayıt", df.index, 
                             format_func=lambda x: f"{df.loc[x, 'Tarih']} | {df.loc[x, 'Açıklama']} | {df.loc[x, 'Tutar']}₺")
        if st.button("Seçili Kaydı Sil"):
            df = df.drop(sil_id).reset_index(drop=True)
            dosya_kaydet(df, VERI_DOSYASI)
            st.rerun()
else:
    st.info("Henüz kayıt yok. Sol menüden başlayabilirsiniz.")
