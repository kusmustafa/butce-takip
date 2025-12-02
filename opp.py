import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi v26", page_icon="🐦", layout="wide")

# --- BAĞLANTIYI KUR ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- SABİT DEĞERLER ---
KOLONLAR = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# --- YARDIMCI FONKSİYONLAR ---
def verileri_cek():
    try:
        df = conn.read(worksheet="Veriler", ttl=0)
        if df.empty or "Tarih" not in df.columns:
            return pd.DataFrame(columns=KOLONLAR)
        df = df.dropna(how="all")
        for col in KOLONLAR:
            if col not in df.columns: df[col] = pd.NA
        return df
    except: return pd.DataFrame(columns=KOLONLAR)

def kategorileri_cek():
    varsayilan = pd.DataFrame([{"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 1}, {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}])
    try:
        df = conn.read(worksheet="Kategoriler", ttl=0)
        if df.empty:
            conn.update(worksheet="Kategoriler", data=varsayilan)
            return varsayilan
        if "Kategori" not in df.columns: return varsayilan
        return df.dropna(how="all")
    except: return varsayilan

def verileri_kaydet(df):
    save_df = df.copy()
    save_df["Tarih"] = save_df["Tarih"].astype(str).replace('NaT', '')
    save_df["Son Ödeme Tarihi"] = save_df["Son Ödeme Tarihi"].astype(str).replace('NaT', '')
    save_df = save_df.fillna("") 
    for col in KOLONLAR:
        if col not in save_df.columns: save_df[col] = ""
    conn.update(worksheet="Veriler", data=save_df[KOLONLAR])

def kategorileri_kaydet(df):
    conn.update(worksheet="Kategoriler", data=df)

def tarih_olustur(yil, ay_ismi, gun):
    try: ay_index = AYLAR.index(ay_ismi) + 1
    except: ay_index = datetime.now().month
    try: h_gun = int(float(gun)); 
    except: h_gun = 1
    if h_gun <= 0: h_gun = 1
    try: return date(yil, ay_index, h_gun)
    except ValueError: return date(yil, ay_index, 28)

def son_odeme_hesapla(islem_tarihi, varsayilan_gun):
    if not varsayilan_gun or varsayilan_gun == 0: return islem_tarihi
    try:
        v_gun = int(float(varsayilan_gun))
        return tarih_olustur(islem_tarihi.year, AYLAR[islem_tarihi.month-1], v_gun)
    except: return islem_tarihi

# --- BAŞLATMA ---
df = verileri_cek()
df_kat = kategorileri_cek()

if not df.empty:
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    if "Durum" in df.columns:
        df["Durum"] = df["Durum"].astype(str).str.lower().map({'true': True, 'false': False, '1.0': True, '0.0': False, '1': True, '0': False, 'nan': False}).fillna(False)
    else: df["Durum"] = False
    if "Tutar" in df.columns: df["Tutar"] = pd.to_numeric(df["Tutar"], errors='coerce').fillna(0.0)
    else: df["Tutar"] = 0.0

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    if st.button("🔄 Verileri Yenile"): st.cache_data.clear(); st.rerun()
    st.divider()
    
    if not df.empty and "Tarih" in df.columns:
        yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True)
        if datetime.now().year not in yil_list: yil_list.insert(0, datetime.now().year)
        secenekler = ["Tüm Zamanlar"] + list(yil_list)
        secilen_yil_filtre = st.selectbox("Dönem (Yıl)", secenekler)
        
        if secilen_yil_filtre == "Tüm Zamanlar":
            df_filt = df; baslik = "Tüm Zamanlar"
        else:
            df_filt = df[df["Tarih"].dt.year == secilen_yil_filtre]
            now = datetime.now()
            varsayilan_ay_index = now.month if secilen_yil_filtre == now.year else 0
            ay_secenekleri = ["Yılın Tamamı"] + AYLAR
            secilen_ay_filtre = st.selectbox("Dönem (Ay)", ay_secenekleri, index=varsayilan_ay_index)
            if secilen_ay_filtre != "Yılın Tamamı":
                ay_no = AYLAR.index(secilen_ay_filtre) + 1
                df_filt = df_filt[df_filt["Tarih"].dt.month == ay_no]
                baslik = f"{secilen_ay_filtre} {secilen_yil_filtre}"
            else: baslik = f"{secilen_yil_filtre} Tamamı"
    else: df_filt = df; baslik = "Veri Yok"

    st.divider()
    with st.expander("Kategori Ekle"):
        with st.form("kategori_form", clear_on_submit=True):
            y_tur = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
            y_ad = st.text_input("Kategori Adı")
            y_gun = st.number_input("Varsayılan Gün", 0, 31, 0)
            kat_btn = st.form_submit_button("Ekle")
            if kat_btn and y_ad:
                try: guncel_kat = conn.read(worksheet="Kategoriler", ttl=0)
                except: guncel_kat = df_kat
                if y_ad not in guncel_kat["Kategori"].values:
                    yeni = pd.DataFrame([{"Kategori": y_ad, "Tur": y_tur, "VarsayilanGun": y_gun}])
                    guncel_kat = pd.concat([guncel_kat, yeni], ignore_index=True)
                    kategorileri_kaydet(guncel_kat)
                    st.success(f"{y_ad} eklendi!"); st.cache_data.clear(); st.rerun()
                else: st.warning("Zaten var.")

# --- SAYFA İÇERİĞİ ---
st.title("☁️ Kuşların Bütçe Makinesi v26")
st.caption(f"Rapor: **{baslik}** | Mod: **Analiz Dashboard**")

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

col_sol, col_sag = st.columns([1, 1.5])

with col_sol:
    st.subheader("📝 Dönem Bazlı Giriş")
    c_donem1, c_donem2 = st.columns(2)
    current_year = datetime.now().year
    current_month_idx = datetime.now().month - 1
    with c_donem1: yil_secimi = st.selectbox("Yıl", range(current_year-2, current_year+2), index=2) 
    with c_donem2: ay_secimi = st.selectbox("Ay", AYLAR, index=current_month_idx)
    c_tur1, c_tur2 = st.columns(2)
    with c_tur1: tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
    kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
    secilen_kat = st.selectbox("Kategori", kat_listesi, index=None, placeholder="Seçiniz...")
    varsayilan_gun = 0
    if secilen_kat and not df_kat.empty:
        row = df_kat[df_kat["Kategori"] == secilen_kat]
        if not row.empty:
            try: varsayilan_gun = int(float(row.iloc[0]["VarsayilanGun"]))
            except: varsayilan_gun = 0
    kayit_tarihi = tarih_olustur(yil_secimi, ay_secimi, varsayilan_gun)
    if secilen_kat:
        gun_mesaji = f"Ayın {varsayilan_gun}." if varsayilan_gun > 0 else "Ayın 1."
        st.caption(f"Tarih: **{kayit_tarihi.strftime('%d.%m.%Y')}** ({gun_mesaji})")
    son_odeme_oneri = son_odeme_hesapla(kayit_tarihi, varsayilan_gun)

    with st.form("islem_formu", clear_on_submit=True):
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)
        aciklama = st.text_input("Açıklama")
        son_odeme = st.date_input("Son Ödeme", value=son_odeme_oneri)
        if st.form_submit_button("KAYDET", type="primary"):
            if secilen_kat and tutar > 0:
                yeni = pd.DataFrame([{
                    "Tarih": pd.to_datetime(kayit_tarihi), "Kategori": secilen_kat, 
                    "Tür": tur_secimi, "Tutar": float(tutar), "Son Ödeme Tarihi": son_odeme, 
                    "Açıklama": aciklama, "Durum": False
                }])
                try:
                    df_final = pd.concat([df, yeni], ignore_index=True)
                    verileri_kaydet(df_final)
                    st.success("Kaydedildi!"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Hata: {e}")
            else: st.error("Eksik bilgi!")

with col_sag:
    # --- YENİ DASHBOARD TASARIMI ---
    tab_grafik, tab_liste = st.tabs(["📊 Özet Dashboard", "📋 Düzenle"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub_gider = df_filt[df_filt["Tür"] == "Gider"].copy()
            sub_gider["Durum_Etiket"] = sub_gider["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            
            # --- 1. SIRA: İKİ TANE PASTA GRAFİĞİ YAN YANA ---
            c_g1, c_g2 = st.columns(2)
            
            with c_g1:
                st.markdown("##### 1. Ödeme Durumu")
                fig1 = px.pie(sub_gider, values="Tutar", names="Durum_Etiket", hole=0.4,
                             color="Durum_Etiket",
                             color_discrete_map={"Ödendi ✅":"#28a745", "Ödenmedi ❌":"#dc3545"})
                fig1.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
                fig1.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig1, use_container_width=True)
                
            with c_g2:
                st.markdown("##### 2. Nereye Harcandı?")
                # Bar yerine Pasta Grafiği (Kategoriler)
                fig2 = px.pie(sub_gider, values="Tutar", names="Kategori", hole=0.4, title="")
                fig2.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0), showlegend=False)
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig2, use_container_width=True)

            # --- 2. SIRA: ÖNERİ GRAFİĞİ (ZAMAN ÇİZELGESİ) ---
            st.divider()
            st.markdown("##### 3. Harcama Zamanlaması (Trend)")
            
            # Veriyi tarihe göre grupla
            trend_data = sub_gider.groupby("Tarih")["Tutar"].sum().reset_index().sort_values("Tarih")
            
            # Area Chart (Alan Grafiği) - Altı dolu çizgi
            fig3 = px.area(trend_data, x="Tarih", y="Tutar", markers=True)
            fig3.update_layout(height=300, margin=dict(t=10, b=0, l=0, r=0), 
                             xaxis_title="", yaxis_title="Tutar (TL)")
            fig3.update_traces(line_color="#FF4B4B") # Streamlit kırmızısı
            st.plotly_chart(fig3, use_container_width=True)

        else: st.info("Grafik için yeterli gider kaydı yok.")
            
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
                    st.success("Güncellendi!"); st.cache_data.clear(); st.rerun()
                except Exception as e: st.error(f"Hata: {e}")
