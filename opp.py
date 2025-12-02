import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi v23", page_icon="🐦", layout="wide")

# --- BAĞLANTIYI KUR ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SABİT KOLONLAR ---
KOLONLAR = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"]

# --- YARDIMCI FONKSİYONLAR ---
def verileri_cek():
    try:
        df = conn.read(worksheet="Veriler", ttl=0)
        if df.empty or "Tarih" not in df.columns:
            return pd.DataFrame(columns=KOLONLAR)
        df = df.dropna(how="all")
        for col in KOLONLAR:
            if col not in df.columns:
                df[col] = pd.NA
        return df
    except:
        return pd.DataFrame(columns=KOLONLAR)

def kategorileri_cek():
    # GÜVENLİK GÜNCELLEMESİ (v23):
    # Hata durumunda asla üzerine yazma!
    varsayilan = pd.DataFrame([
        {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
        {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}
    ])
    
    try:
        df = conn.read(worksheet="Kategoriler", ttl=0)
        
        # Eğer okuma başarılı ama tablo gerçekten boşsa:
        if df.empty:
            conn.update(worksheet="Kategoriler", data=varsayilan)
            return varsayilan
            
        # Eğer kolonlar eksikse:
        if "Kategori" not in df.columns:
            return varsayilan
            
        return df.dropna(how="all")
        
    except Exception as e:
        # Hata varsa SAKIN SİLME, sadece geçici olarak varsayılanı göster
        st.toast(f"Kategoriler anlık olarak okunamadı, bağlantıyı kontrol et. (Verilerin güvende)", icon="⚠️")
        return varsayilan

def verileri_kaydet(df):
    save_df = df.copy()
    save_df["Tarih"] = save_df["Tarih"].astype(str).replace('NaT', '')
    save_df["Son Ödeme Tarihi"] = save_df["Son Ödeme Tarihi"].astype(str).replace('NaT', '')
    save_df = save_df.fillna("") 
    for col in KOLONLAR:
        if col not in save_df.columns: save_df[col] = ""
    conn.update(worksheet="Veriler", data=save_df[KOLONLAR])

def kategorileri_kaydet(df):
    # Sadece yeni kategori eklendiğinde çalışır
    conn.update(worksheet="Kategoriler", data=df)

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

# --- BAŞLATMA ---
df = verileri_cek()
df_kat = kategorileri_cek()

# Veri Tiplerini Düzelt
if not df.empty:
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    if "Durum" in df.columns:
        df["Durum"] = df["Durum"].astype(str).str.lower().map(
            {'true': True, 'false': False, '1.0': True, '0.0': False, '1': True, '0': False, 'nan': False}
        ).fillna(False)
    else: df["Durum"] = False
    
    if "Tutar" in df.columns:
        df["Tutar"] = pd.to_numeric(df["Tutar"], errors='coerce').fillna(0.0)
    else: df["Tutar"] = 0.0

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    if st.button("🔄 Verileri Yenile"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    
    # Dönem Filtresi
    if not df.empty and "Tarih" in df.columns:
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
    else: df_filt = df; baslik = "Veri Yok"

    st.divider()
    with st.expander("Kategori Ekle"):
        with st.form("kategori_form", clear_on_submit=True):
            y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
            y_ad = st.text_input("Kategori Adı")
            y_gun = st.number_input("Gün", 0, 31, 0)
            kat_btn = st.form_submit_button("Ekle")
            if kat_btn and y_ad:
                # Önce mevcut kategorilerin en güncel halini al (Üzerine yazmamak için)
                try:
                    guncel_kat = conn.read(worksheet="Kategoriler", ttl=0)
                except:
                    guncel_kat = df_kat
                
                # Çakışma kontrolü
                if y_ad not in guncel_kat["Kategori"].values:
                    yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun if y_tur=="Gider" else 0}])
                    guncel_kat = pd.concat([guncel_kat, yeni], ignore_index=True)
                    kategorileri_kaydet(guncel_kat)
                    st.success(f"{y_ad} eklendi!")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.warning("Bu kategori zaten var.")

# --- SAYFA İÇERİĞİ ---
st.title("☁️ Kuşların Bütçe Makinesi v23")
st.caption(f"Rapor: **{baslik}** | Kayıt Yeri: **Google Sheets**")

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
else: st.info("Veri yok.")

st.divider()

col_sol, col_sag = st.columns([1, 1.5])

with col_sol:
    st.subheader("📝 Hızlı Veri Girişi")
    c_tur1, c_tur2 = st.columns(2)
    with c_tur1: tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
    
    kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
    secilen_kat = st.selectbox("Kategori", kat_listesi, index=None, placeholder="Kategori Seçiniz...")
    
    varsayilan_gun = 0; oneri_tarih = None
    if secilen_kat and not df_kat.empty:
        row = df_kat[df_kat["Kategori"] == secilen_kat]
        if not row.empty: varsayilan_gun = int(row.iloc[0]["VarsayilanGun"])
    if tur_secimi == "Gider" and varsayilan_gun > 0:
        oneri_tarih = tarih_onerisi_hesapla(varsayilan_gun)
        if oneri_tarih: st.info(f"💡 Otomatik: **{oneri_tarih.strftime('%d.%m.%Y')}**")

    with st.form("islem_formu", clear_on_submit=True):
        giris_tarihi = st.date_input("İşlem Tarihi", date.today())
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)
        aciklama = st.text_input("Açıklama")
        son_odeme = st.date_input("Son Ödeme", value=oneri_tarih)
        if st.form_submit_button("KAYDET", type="primary"):
            if secilen_kat and tutar > 0:
                yeni = pd.DataFrame([{
                    "Tarih": pd.to_datetime(giris_tarihi),
                    "Kategori": secilen_kat, "Tür": tur_secimi, "Tutar": float(tutar),
                    "Son Ödeme Tarihi": son_odeme, "Açıklama": aciklama, "Durum": False
                }])
                try:
                    df_final = pd.concat([df, yeni], ignore_index=True)
                    verileri_kaydet(df_final)
                    st.success("Kaydedildi!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"Kayıt Hatası: {e}")
            else: st.error("Eksik bilgi!")

with col_sag:
    tab_grafik, tab_liste = st.tabs(["📊 Analiz", "📋 Düzenle"])
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub_gider = df_filt[df_filt["Tür"] == "Gider"].copy()
            sub_gider["Durum_Etiket"] = sub_gider["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            c1, c2 = st.columns(2)
            with c1:
                fig = px.pie(sub_gider, values="Tutar", names="Durum_Etiket", hole=0.4, color="Durum_Etiket", color_discrete_map={"Ödendi ✅":"#28a745", "Ödenmedi ❌":"#dc3545"})
                fig.update_layout(height=250, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                evt = st.plotly_chart(fig, on_select="rerun", use_container_width=True)
            with c2:
                sel = evt["selection"]["points"][0]["label"] if evt and "selection" in evt and evt["selection"]["points"] else None
                det = sub_gider[sub_gider["Durum_Etiket"] == sel] if sel else sub_gider
                if not det.empty:
                    grp = det.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
                    fig2 = px.bar(grp, x="Kategori", y="Tutar", color="Kategori", text="Tutar")
                    fig2.update_layout(height=250, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    fig2.update_traces(texttemplate='%{text:.2s}', textposition='outside')
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.info("Veri yok")
    with tab_liste:
        if not df_filt.empty and "Tarih" in df_filt.columns:
            edt = df_filt.sort_values("Tarih", ascending=False).copy()
            edt["Tarih"] = edt["Tarih"].dt.date
            if "Son Ödeme Tarihi" in edt.columns:
                edt["Son Ödeme Tarihi"] = pd.to_datetime(edt["Son Ödeme Tarihi"], errors='coerce').dt.date
            
            duzenli = st.data_editor(
                edt,
                column_config={
                    "Durum": st.column_config.CheckboxColumn("Ödendi?", default=False),
                    "Tutar": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
                    "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                    "Son Ödeme Tarihi": st.column_config.DateColumn("Son Ödeme", format="DD.MM.YYYY"),
                    "Kategori": st.column_config.SelectboxColumn("Kategori", options=df_kat["Kategori"].unique().tolist() if not df_kat.empty else []),
                    "Tür": st.column_config.SelectboxColumn("Tür", options=["Gider", "Gelir"]),
                },
                hide_index=True, use_container_width=True, num_rows="dynamic", key="editor"
            )
            if st.button("💾 Değişiklikleri Gönder", type="primary"):
                try:
                    df_rest = df.drop(df_filt.index)
                    duzenli["Tarih"] = pd.to_datetime(duzenli["Tarih"])
                    verileri_kaydet(pd.concat([df_rest, duzenli], ignore_index=True))
                    st.success("Güncellendi!")
                    st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Hata: {e}")
