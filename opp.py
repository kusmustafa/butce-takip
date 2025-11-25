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

# --- DOSYA YÖNETİMİ ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'
ESKI_SABITLER_DOSYASI = 'sabit_giderler.csv'

# --- YARDIMCI FONKSİYONLAR ---
def dosya_kaydet(df, yol): df.to_csv(yol, index=False)

def sistem_kontrol():
    # Kategori Dosyası
    if not os.path.exists(KATEGORI_DOSYASI):
        pd.DataFrame([
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}
        ]).to_csv(KATEGORI_DOSYASI, index=False)
    
    # Veri Dosyası ve Sütun Kontrolleri
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"])
        df.to_csv(VERI_DOSYASI, index=False)
    else:
        try:
            df = pd.read_csv(VERI_DOSYASI)
            degisti = False
            # Sütun eksikse ekle
            for col in ["Son Ödeme Tarihi", "Açıklama"]:
                if col not in df.columns: df[col] = None; degisti = True
            
            if "Durum" not in df.columns:
                df["Durum"] = False; degisti = True
            
            if degisti: df.to_csv(VERI_DOSYASI, index=False)
        except: pass

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

def renklendir(val):
    renk = ''
    try:
        durum = bool(val.get('Durum', False))
        tur = val.get('Tür', '')
        son_odeme = val.get('Son Ödeme Tarihi')
        
        if durum:
            renk = 'background-color: #d4edda; color: #155724' # Yeşil (Ödendi)
        elif tur == 'Gider' and pd.notnull(son_odeme):
            if pd.to_datetime(son_odeme).date() < date.today():
                renk = 'background-color: #f8d7da; color: #721c24' # Kırmızı (Gecikti)
            else:
                renk = 'background-color: #cce5ff; color: #004085' # Mavi (Bekliyor)
    except: pass
    return [renk] * len(val)

# --- BAŞLATMA ---
sistem_kontrol()
if 'form_tutar' not in st.session_state: st.session_state.form_tutar = 0.0
if 'form_aciklama' not in st.session_state: st.session_state.form_aciklama = ""

# Veri Yükleme (Hata Korumalı)
try:
    df = pd.read_csv(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    
    # Durum Sütununu Zorla Boolean Yap (Çökme sebebi genelde budur)
    if "Durum" not in df.columns: df["Durum"] = False
    df["Durum"] = df["Durum"].fillna(False).astype(bool)
    
except Exception as e:
    st.error(f"Veri yüklenemedi: {e}")
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
    st.subheader("🔍 Filtre")
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
        y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
        y_ad = st.text_input("Kategori Adı")
        y_gun = st.number_input("Gün", 0, 31, 0) if y_tur == "Gider" else 0
        if st.button("Ekle"):
            if y_ad:
                df_kat = df_kat[df_kat["Kategori"] != y_ad]
                yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun}])
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

# --- GÖVDE ---
col_sol, col_sag = st.columns([1, 1.5])

with col_sol:
    st.subheader("📝 Veri Girişi")
    with st.container(border=True):
        giris_tarihi = st.date_input("İşlem Tarihi", date.today())
        
        c_tur1, c_tur2 = st.columns(2)
        with c_tur1: tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True, label_visibility="collapsed")
        
        kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
        secilen_kat = st.selectbox("Kategori", kat_listesi, index=None, placeholder="Seçiniz...")
        
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0, key="form_tutar")
        aciklama = st.text_input("Açıklama", key="form_aciklama")
        
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
                st.session_state["form_tutar"] = 0.0
                st.session_state["form_aciklama"] = ""
                st.success("Kaydedildi!"); st.rerun()
            else: st.error("Eksik bilgi!")

with col_sag:
    tab_grafik, tab_liste = st.tabs(["📊 Analiz", "📋 Liste ve Ödeme"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub = df_filt[df_filt["Tür"] == "Gider"]
            # Pasta
            df_pie = sub.groupby("Durum")["Tutar"].sum().reset_index()
            df_pie["Durum"] = df_pie["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            fig = px.pie(df_pie, values="Tutar", names="Durum", hole=0.5, color="Durum", 
                         color_discrete_map={"Ödendi ✅":"#28a745", "Ödenmedi ❌":"#dc3545"})
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200)
            st.plotly_chart(fig, use_container_width=True)
            # Bar
            grp = sub.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False).head(5)
            st.bar_chart(grp, x="Kategori", y="Tutar", height=200)

    with tab_liste:
        st.info("Kutucuğu (✅) işaretleyip ödenmiş yapabilirsiniz.")
        if not df_filt.empty:
            edit_df = df_filt.sort_values("Tarih", ascending=False).copy()
            
            # --- GÜVENLİ EDİTÖR ---
            try:
                edited = st.data_editor(
                    edit_df,
                    column_config={
                        "Durum": st.column_config.CheckboxColumn("Ödendi?", default=False),
                        "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                        "Son Ödeme Tarihi": st.column_config.DateColumn("Son Ödeme", format="DD.MM.YYYY"),
                        "Tutar": st.column_config.NumberColumn("Tutar", format="%.0f ₺")
                    },
                    disabled=["Tarih", "Kategori", "Tür", "Tutar", "Açıklama", "Son Ödeme Tarihi"],
                    hide_index=True, use_container_width=True, height=400, key="editor"
                )
                
                # Değişiklikleri Kaydet
                if not edited.equals(edit_df):
                    for i, r in edited.iterrows():
                        if i in df.index:
                            df.at[i, "Durum"] = r["Durum"]
                    dosya_kaydet(df, VERI_DOSYASI)
                    st.rerun()
            except Exception as e:
                st.error("Tablo görüntülenirken hata oluştu. Lütfen 'Verileri Sıfırla'yı deneyin.")
                st.dataframe(edit_df) # Hata olursa düz tablo göster

        # Renkli Görünüm
        with st.expander("🎨 Renkli Görünüm", expanded=True):
            if not df_filt.empty:
                try:
                    view_df = df_filt.sort_values("Tarih", ascending=False).copy()
                    styler = view_df.style.apply(renklendir, axis=1)
                    styler.format({"Tarih": lambda t: t.strftime("%d-%m-%Y") if pd.notnull(t) else "",
                                   "Son Ödeme Tarihi": lambda t: pd.to_datetime(t).strftime("%d-%m-%Y") if pd.notnull(t) else "",
                                   "Tutar": "{:.0f} ₺"})
                    st.dataframe(styler, use_container_width=True, height=400, hide_index=True)
                except: st.write("Renklendirme yüklenemedi.")

        # Silme
        if not df_filt.empty:
            sil_id = st.selectbox("Silinecek", df_filt.index, 
                                 format_func=lambda x: f"{df.loc[x,'Tutar']}₺ - {df.loc[x,'Kategori']}", 
                                 label_visibility="collapsed")
            if st.button("Sil"):
                df = df.drop(sil_id).reset_index(drop=True)
                dosya_kaydet(df, VERI_DOSYASI); st.rerun()
