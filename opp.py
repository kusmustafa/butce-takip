import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")

# --- DOSYA YÖNETİMİ ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'

# --- YARDIMCI FONKSİYONLAR ---
def dosya_kaydet(df, yol): df.to_csv(yol, index=False)

def sistem_kontrol():
    # Kategori Dosyası
    if not os.path.exists(KATEGORI_DOSYASI):
        pd.DataFrame([
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}
        ]).to_csv(KATEGORI_DOSYASI, index=False)
    
    # Veri Dosyası
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"])
        df.to_csv(VERI_DOSYASI, index=False)
    else:
        try:
            df = pd.read_csv(VERI_DOSYASI)
            degisti = False
            for col in ["Son Ödeme Tarihi", "Açıklama", "Durum"]:
                if col not in df.columns:
                    df[col] = False if col == "Durum" else None
                    degisti = True
            if degisti: df.to_csv(VERI_DOSYASI, index=False)
        except: pass

def tarih_onerisi_hesapla(gun):
    """Verilen güne göre bu ayın veya gelecek ayın tarihini bulur"""
    if not gun or gun == 0: return None
    bugun = date.today()
    try: h_gun = int(gun)
    except: return None
    if not (1 <= h_gun <= 31): return None
    
    # Hedef tarih bu ayın X'i olsun
    try: bu_ay_tarih = date(bugun.year, bugun.month, h_gun)
    except: bu_ay_tarih = date(bugun.year, bugun.month, 28) # Şubat koruması

    # Eğer bu tarih geçtiyse (örn: bugün ayın 20'si, hedef 15'i), sonraki aya at
    # Ancak bugün ayın 15'i ve hedef 15 ise, bugünü önerir.
    if bu_ay_tarih >= bugun:
        return bu_ay_tarih
    else:
        s_ay = bugun.month + 1 if bugun.month < 12 else 1
        yil = bugun.year if bugun.month < 12 else bugun.year + 1
        try: return date(yil, s_ay, h_gun)
        except: return date(yil, s_ay, 28)

def durum_ikonu_belirle(row):
    try:
        durum = str(row.get('Durum', False)).lower() == 'true'
        tur = row.get('Tür', '')
        son_odeme = row.get('Son Ödeme Tarihi')
        
        if tur == 'Gelir': return "💰 Gelir"
        if durum: return "✅ Ödendi"
        
        if pd.notnull(son_odeme) and str(son_odeme) != 'nan':
            tarih_obj = pd.to_datetime(son_odeme).date()
            if tarih_obj < date.today(): return "🔴 Gecikti"
            elif tarih_obj == date.today(): return "🟠 Bugün"
            else: return "🔵 Bekliyor"
        return "⚪ Belirsiz"
    except: return "⚪ Belirsiz"

# --- BAŞLATMA ---
sistem_kontrol()

# Veri Yükleme
try:
    df = pd.read_csv(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    df["Durum"] = df["Durum"].astype(str).map({'True': True, 'False': False, 'true': True, 'false': False}).fillna(False)
except:
    df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"])

try: df_kat = pd.read_csv(KATEGORI_DOSYASI)
except: df_kat = pd.DataFrame(columns=["Kategori", "Tur", "VarsayilanGun"])

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    with st.expander("🚨 Verileri Sıfırla"):
        if st.button("Her Şeyi Sil"):
            if os.path.exists(VERI_DOSYASI): os.remove(VERI_DOSYASI)
            if os.path.exists(KATEGORI_DOSYASI): os.remove(KATEGORI_DOSYASI)
            st.rerun()
    
    st.divider()
    
    if not df.empty:
        yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True)
        secenekler = ["Tüm Zamanlar"] + list(yil_list)
        secilen_yil = st.selectbox("Dönem", secenekler)
        
        if secilen_yil == "Tüm Zamanlar":
            df_filt = df; baslik = "Tüm Zamanlar"
        else:
            df_filt = df[df["Tarih"].dt.year == secilen_yil]
            ay_map = {i: ay for i, ay in enumerate(["Yılın Tamamı", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
            now = datetime.now()
            idx = now.month if secilen_yil == now.year else 0
            secilen_ay_index = st.selectbox("Ay", list(ay_map.keys()), format_func=lambda x: ay_map[x], index=idx)
            
            if secilen_ay_index != 0:
                df_filt = df_filt[df_filt["Tarih"].dt.month == secilen_ay_index]
                baslik = f"{ay_map[secilen_ay_index]} {secilen_yil}"
            else: baslik = f"{secilen_yil} Tamamı"
    else:
        df_filt = df; baslik = "Veri Yok"

    st.divider()
    with st.expander("Kategori Ekle"):
        with st.form("kategori_form", clear_on_submit=True):
            y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
            y_ad = st.text_input("Kategori Adı")
            y_gun = st.number_input("Gün", 0, 31, 0)
            kat_btn = st.form_submit_button("Ekle")
            
            if kat_btn and y_ad:
                df_kat = df_kat[df_kat["Kategori"] != y_ad]
                yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun if y_tur=="Gider" else 0}])
                df_kat = pd.concat([df_kat, yeni], ignore_index=True)
                dosya_kaydet(df_kat, KATEGORI_DOSYASI); st.rerun()

# --- ÜST BİLGİ ---
st.title("🐦 Kuşların Bütçe Makinesi")
st.caption(f"Rapor: **{baslik}**")

if not df_filt.empty:
    gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    bekleyen = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]["Tutar"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Gelir", f"{gelir:,.0f} ₺")
    k2.metric("Gider", f"{gider:,.0f} ₺")
    k3.metric("Net", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")
    k4.metric("Ödenmemiş", f"{bekleyen:,.0f} ₺", delta_color="inverse")
else: st.info("Kayıt yok.")

st.divider()

# --- GÖVDE (Hibrit Yapı) ---
col_sol, col_sag = st.columns([1, 1.5])

with col_sol:
    st.subheader("📝 Veri Girişi")
    
    # 1. BÖLÜM: FORM DIŞI (Kategori Seçimi)
    # Form dışında olduğu için seçince sayfa yenilenir ve tarih hesaplanır.
    c_tur1, c_tur2 = st.columns(2)
    with c_tur1: tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
    
    kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
    secilen_kat = st.selectbox("Kategori (Seçince tarih güncellenir)", kat_listesi, index=None, placeholder="Kategori Seçiniz...")

    # Tarih Önerisini Hesapla
    varsayilan_gun = 0
    oneri_tarih = None
    if secilen_kat and not df_kat.empty:
        row = df_kat[df_kat["Kategori"] == secilen_kat]
        if not row.empty: varsayilan_gun = int(row.iloc[0]["VarsayilanGun"])
    
    if tur_secimi == "Gider" and varsayilan_gun > 0:
        oneri_tarih = tarih_onerisi_hesapla(varsayilan_gun)
        if oneri_tarih:
            st.info(f"💡 Otomatik Tarih: **{oneri_tarih.strftime('%d.%m.%Y')}**")

    # 2. BÖLÜM: FORM İÇİ (Tutar, Açıklama, Kaydet)
    # Enter ile kaydetmek ve temizlemek için burası form içinde olmalı.
    with st.form("islem_formu", clear_on_submit=True):
        giris_tarihi = st.date_input("İşlem Tarihi", date.today())
        
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)
        aciklama = st.text_input("Açıklama")
        
        # Son Ödeme Tarihi (Öneri varsa onu varsayılan yap)
        son_odeme = st.date_input("Son Ödeme", value=oneri_tarih)
        
        kaydet_btn = st.form_submit_button("KAYDET (Enter)", type="primary")
        
        if kaydet_btn:
            if secilen_kat and tutar > 0:
                yeni = pd.DataFrame({
                    "Tarih": [pd.to_datetime(giris_tarihi)],
                    "Kategori": [secilen_kat],
                    "Tür": [tur_secimi],
                    "Tutar": [float(tutar)],
                    "Son Ödeme Tarihi": [son_odeme],
                    "Açıklama": [aciklama],
                    "Durum": [False]
                })
                df = pd.concat([df, yeni], ignore_index=True)
                dosya_kaydet(df, VERI_DOSYASI)
                st.success("✅ Kaydedildi!")
                st.rerun()
            else:
                st.error("⚠️ Kategori (yukarıda) veya Tutar eksik!")

with col_sag:
    tab_grafik, tab_liste = st.tabs(["📊 Analiz", "📋 Liste ve Ödeme"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub = df_filt[df_filt["Tür"] == "Gider"]
            df_pie = sub.groupby("Durum")["Tutar"].sum().reset_index()
            df_pie["Durum"] = df_pie["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            fig = px.pie(df_pie, values="Tutar", names="Durum", hole=0.5, color="Durum", 
                         color_discrete_map={"Ödendi ✅":"#28a745", "Ödenmedi ❌":"#dc3545"})
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200)
            st.plotly_chart(fig, use_container_width=True)

            grp = sub.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False).head(5)
            st.bar_chart(grp, x="Kategori", y="Tutar", height=200)

    with tab_liste:
        if not df_filt.empty:
            view_df = df_filt.sort_values("Tarih", ascending=False).copy()
            view_df["Durum"] = view_df.apply(durum_ikonu_belirle, axis=1)
            
            view_df["Tarih"] = view_df["Tarih"].dt.strftime('%d.%m.%Y')
            view_df["Son Ödeme Tarihi"] = pd.to_datetime(view_df["Son Ödeme Tarihi"]).dt.strftime('%d.%m.%Y').fillna("-")
            
            final_cols = ["Durum", "Tarih", "Kategori", "Tutar", "Son Ödeme Tarihi", "Açıklama"]
            st.dataframe(view_df[final_cols], use_container_width=True, hide_index=True)
            
            st.divider()
            c_odeme, c_sil = st.columns(2)
            
            with c_odeme:
                odenmemisler = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]
                if not odenmemisler.empty:
                    sec_odeme = st.selectbox("Ödenecek Borç", odenmemisler.index, 
                                            format_func=lambda x: f"{df.loc[x,'Kategori']} - {df.loc[x,'Tutar']}₺")
                    if st.button("✅ Ödendi Yap"):
                        df.at[sec_odeme, "Durum"] = True
                        dosya_kaydet(df, VERI_DOSYASI); st.rerun()
                else: st.caption("Borç yok.")

            with c_sil:
                sil_id = st.selectbox("Silinecek Kayıt", df_filt.index, 
                                     format_func=lambda x: f"{df.loc[x,'Kategori']} - {df.loc[x,'Tutar']}₺",
                                     key="sil_box")
                if st.button("🗑️ Sil"):
                    df = df.drop(sil_id).reset_index(drop=True)
                    dosya_kaydet(df, VERI_DOSYASI); st.rerun()
