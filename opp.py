import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from streamlit_gsheets import GSheetsConnection

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi v22 (Bulut)", page_icon="☁️", layout="wide")

# --- BAĞLANTIYI KUR ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- YARDIMCI FONKSİYONLAR ---
def verileri_cek():
    # Veriler sekmesini oku
    try:
        df = conn.read(worksheet="Veriler", ttl=0) # ttl=0 önbellek yapma demek (anlık veri)
        df = df.dropna(how="all") # Tamamen boş satırları sil
        return df
    except:
        # Eğer sayfa boşsa başlıkları oluştur
        return pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"])

def kategorileri_cek():
    try:
        df = conn.read(worksheet="Kategoriler", ttl=0)
        df = df.dropna(how="all")
        if df.empty: raise Exception("Boş")
        return df
    except:
        # Varsayılan kategoriler
        varsayilan = pd.DataFrame([
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}
        ])
        conn.update(worksheet="Kategoriler", data=varsayilan)
        return varsayilan

def verileri_kaydet(df):
    # Tarihleri string formatına çevir ki Sheets bozulmasın
    save_df = df.copy()
    save_df["Tarih"] = save_df["Tarih"].astype(str)
    save_df["Son Ödeme Tarihi"] = save_df["Son Ödeme Tarihi"].astype(str).replace('NaT', '')
    conn.update(worksheet="Veriler", data=save_df)

def kategorileri_kaydet(df):
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

# --- VERİ HAZIRLIĞI ---
df = verileri_cek()
df_kat = kategorileri_cek()

# Tipleri düzelt
if not df.empty:
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    df["Durum"] = df["Durum"].astype(str).map({'True': True, 'False': False, 'TRUE': True, 'FALSE': False, '1.0': True, '0.0': False}).fillna(False)
    df["Tutar"] = pd.to_numeric(df["Tutar"], errors='coerce').fillna(0.0)

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    if st.button("🔄 Verileri Yenile"):
        st.cache_data.clear()
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
                kategorileri_kaydet(df_kat)
                st.success("Eklendi")
                st.rerun()

# --- ÜST BİLGİ ---
st.title("☁️ Kuşların Bütçe Makinesi v22")
st.caption(f"Rapor: **{baslik}** | Kayıt Yeri: **Google Sheets (Güvenli)**")

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
    st.subheader("📝 Hızlı Veri Girişi")
    
    c_tur1, c_tur2 = st.columns(2)
    with c_tur1: tur_secimi = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
    kat_listesi = df_kat[df_kat["Tur"] == tur_secimi]["Kategori"].tolist() if not df_kat.empty else []
    secilen_kat = st.selectbox("Kategori", kat_listesi, index=None, placeholder="Kategori Seçiniz...")

    varsayilan_gun = 0
    oneri_tarih = None
    if secilen_kat and not df_kat.empty:
        row = df_kat[df_kat["Kategori"] == secilen_kat]
        if not row.empty: varsayilan_gun = int(row.iloc[0]["VarsayilanGun"])
    
    if tur_secimi == "Gider" and varsayilan_gun > 0:
        oneri_tarih = tarih_onerisi_hesapla(varsayilan_gun)
        if oneri_tarih: st.info(f"💡 Otomatik Tarih: **{oneri_tarih.strftime('%d.%m.%Y')}**")

    with st.form("islem_formu", clear_on_submit=True):
        giris_tarihi = st.date_input("İşlem Tarihi", date.today())
        tutar = st.number_input("Tutar (TL)", min_value=0.0, step=50.0)
        aciklama = st.text_input("Açıklama")
        son_odeme = st.date_input("Son Ödeme", value=oneri_tarih)
        
        if st.form_submit_button("KAYDET (Enter)", type="primary"):
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
                # Ana df'ye ekle ve kaydet
                df_final = pd.concat([df, yeni], ignore_index=True)
                verileri_kaydet(df_final)
                st.success("✅ Buluta Kaydedildi!"); st.rerun()
            else: st.error("⚠️ Eksik bilgi!")

with col_sag:
    tab_grafik, tab_liste = st.tabs(["📊 İnteraktif Analiz", "📋 Tablo Düzenle (Excel Modu)"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub_gider = df_filt[df_filt["Tür"] == "Gider"].copy()
            sub_gider["Durum_Etiket"] = sub_gider["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.write("###### 1. Ödeme Durumu")
                fig_main = px.pie(sub_gider, values="Tutar", names="Durum_Etiket", hole=0.4,
                                 color="Durum_Etiket",
                                 color_discrete_map={"Ödendi ✅":"#28a745", "Ödenmedi ❌":"#dc3545"})
                fig_main.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=False)
                selected_event = st.plotly_chart(fig_main, on_select="rerun", use_container_width=True)
            
            with col_g2:
                secilen_dilim = None
                try:
                    if selected_event and "selection" in selected_event and selected_event["selection"]["points"]:
                        secilen_dilim = selected_event["selection"]["points"][0]["label"]
                except: pass

                if secilen_dilim:
                    st.write(f"###### 2. Detay: {secilen_dilim}")
                    detail_df = sub_gider[sub_gider["Durum_Etiket"] == secilen_dilim]
                else:
                    st.write("###### 2. Detay: Tümü")
                    detail_df = sub_gider

                if not detail_df.empty:
                    cat_group = detail_df.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
                    fig_detail = px.bar(cat_group, x="Kategori", y="Tutar", color="Kategori", text="Tutar")
                    fig_detail.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=False)
                    fig_detail.update_traces(texttemplate='%{text:.2s}', textposition='outside')
                    st.plotly_chart(fig_detail, use_container_width=True)
    
    with tab_liste:
        st.write("###### 🖊️ Bulut Verilerini Düzenle")
        
        editor_df = df_filt.sort_values("Tarih", ascending=False).copy()
        if not editor_df.empty:
            editor_df["Tarih"] = editor_df["Tarih"].dt.date
            editor_df["Son Ödeme Tarihi"] = pd.to_datetime(editor_df["Son Ödeme Tarihi"], errors='coerce').dt.date

        tum_kategoriler = df_kat["Kategori"].unique().tolist() if not df_kat.empty else []

        duzenlenmis_df = st.data_editor(
            editor_df,
            column_config={
                "Durum": st.column_config.CheckboxColumn("Ödendi?", default=False),
                "Tutar": st.column_config.NumberColumn("Tutar", format="%.2f ₺"),
                "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                "Son Ödeme Tarihi": st.column_config.DateColumn("Son Ödeme", format="DD.MM.YYYY"),
                "Kategori": st.column_config.SelectboxColumn("Kategori", options=tum_kategoriler),
                "Tür": st.column_config.SelectboxColumn("Tür", options=["Gider", "Gelir"]),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic",
            key="gsheet_editor"
        )

        if st.button("💾 Değişiklikleri Buluta Gönder", type="primary", use_container_width=True):
            try:
                # 1. Filtre dışındakileri al
                indices_to_drop = df_filt.index
                df_rest = df.drop(indices_to_drop)
                
                # 2. Yeni veriyi formatla
                duzenlenmis_df["Tarih"] = pd.to_datetime(duzenlenmis_df["Tarih"])
                
                # 3. Birleştir ve Gönder
                df_final = pd.concat([df_rest, duzenlenmis_df], ignore_index=True)
                verileri_kaydet(df_final)
                st.success("Google Sheets güncellendi! 🚀")
                st.cache_data.clear() # Cache temizle ki yeni veriyi çeksin
                st.rerun()
            except Exception as e:
                st.error(f"Hata: {e}")
