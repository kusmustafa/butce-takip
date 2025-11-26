import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi v21", page_icon="🐦", layout="wide")

# --- DOSYA YÖNETİMİ ---
VERI_DOSYASI = 'aile_butcesi.csv'
KATEGORI_DOSYASI = 'kategoriler.csv'

# --- YARDIMCI FONKSİYONLAR ---
def dosya_kaydet(df, yol): df.to_csv(yol, index=False)

def sistem_kontrol():
    if not os.path.exists(KATEGORI_DOSYASI):
        pd.DataFrame([{"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
                      {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}]).to_csv(KATEGORI_DOSYASI, index=False)
    
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

def durum_ikonu_belirle(row):
    try:
        durum = str(row.get('Durum', False)).lower() == 'true'
        tur = row.get('Tür', '')
        son_odeme = row.get('Son Ödeme Tarihi')
        
        if tur == 'Gelir': return "💰"
        if durum: return "✅"
        
        if pd.notnull(son_odeme) and str(son_odeme) != 'nan':
            tarih_obj = pd.to_datetime(son_odeme).date()
            if tarih_obj < date.today(): return "🔴"
            elif tarih_obj == date.today(): return "🟠"
            else: return "🔵"
        return "⚪"
    except: return "⚪"

# --- BAŞLATMA ---
sistem_kontrol()

try:
    df = pd.read_csv(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    # Durum sütununu boolean'a çevir (Excel düzenleme için önemli)
    df["Durum"] = df["Durum"].astype(str).map({'True': True, 'False': False, 'true': True, 'false': False, '1.0': True, '0.0': False}).fillna(False)
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
st.title("🐦 Kuşların Bütçe Makinesi v21")
st.caption(f"Rapor: **{baslik}** | Mod: **Excel Düzenleme Aktif**")

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
                df = pd.concat([df, yeni], ignore_index=True)
                dosya_kaydet(df, VERI_DOSYASI)
                st.success("✅ Kaydedildi!"); st.rerun()
            else: st.error("⚠️ Eksik bilgi!")

with col_sag:
    # Sekmeler
    tab_grafik, tab_liste = st.tabs(["📊 İnteraktif Analiz", "📋 Tablo Düzenle (Excel Modu)"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            # Sadece Gider Verileri
            sub_gider = df_filt[df_filt["Tür"] == "Gider"].copy()
            sub_gider["Durum_Etiket"] = sub_gider["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            
            # --- 1. SOL GRAFİK: ANA DURUM ---
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.write("###### 1. Ödeme Durumu (Tıkla 👇)")
                fig_main = px.pie(sub_gider, values="Tutar", names="Durum_Etiket", hole=0.4,
                                 color="Durum_Etiket",
                                 color_discrete_map={"Ödendi ✅":"#28a745", "Ödenmedi ❌":"#dc3545"})
                fig_main.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, showlegend=False)
                selected_event = st.plotly_chart(fig_main, on_select="rerun", use_container_width=True)
            
            # --- 2. SAĞ GRAFİK: DETAY ---
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
                else: st.info("Veri yok.")
            
            if secilen_dilim: st.caption("💡 Filtreyi kaldırmak için grafik boşluğuna çift tıklayın.")

    with tab_liste:
        st.write("###### 🖊️ Verileri Doğrudan Düzenle")
        
        # v21: Excel Tarzı Editör
        # Filtrelenmiş veriyi gösteriyoruz ama indexleri koruyoruz ki ana tabloyu güncelleyebilelim.
        
        # Kategori listesini dropdown için hazırla
        tum_kategoriler = df_kat["Kategori"].unique().tolist() if not df_kat.empty else []

        duzenlenmis_df = st.data_editor(
            df_filt.sort_values("Tarih", ascending=False), # Görüntüleme için sıralı
            column_config={
                "Durum": st.column_config.CheckboxColumn("Ödendi?", help="Ödemeyi işaretle", default=False),
                "Tutar": st.column_config.NumberColumn("Tutar", format="%.2f ₺", min_value=0, step=10),
                "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                "Son Ödeme Tarihi": st.column_config.DateColumn("Son Ödeme", format="DD.MM.YYYY"),
                "Kategori": st.column_config.SelectboxColumn("Kategori", options=tum_kategoriler, required=True),
                "Tür": st.column_config.SelectboxColumn("Tür", options=["Gider", "Gelir"], required=True),
            },
            hide_index=True,
            use_container_width=True,
            num_rows="dynamic", # Satır Ekle/Sil Aktif
            key="data_editor"
        )

        # Değişiklik Kontrolü ve Kaydetme
        # Ekranda görünen (filtered) veride bir değişiklik olduysa butonu çıkar
        if not df_filt.sort_values("Tarih", ascending=False).equals(duzenlenmis_df):
            st.warning("⚠️ Tabloda değişiklik yaptınız. Kaydetmeyi unutmayın!")
            
            col_save, col_info = st.columns([1, 2])
            with col_save:
                if st.button("💾 Değişiklikleri Kaydet", type="primary", use_container_width=True):
                    # 1. Filtre dışındaki verileri al (df_rest)
                    # Not: df_filt'in orijinal indexleri df ile aynıdır.
                    # Ancak data_editor yeni satır eklerse indexleri olmayabilir.
                    
                    # Güvenli Yöntem:
                    # Mevcut görünümdeki (df_filt) indexleri ana tablodan (df) düşür.
                    # Sonra editörden gelen (duzenlenmis_df) veriyi ana tabloya ekle.
                    
                    # Filtre kapsamındaki eski verileri sil
                    indices_to_drop = df_filt.index
                    df_new = df.drop(indices_to_drop)
                    
                    # Editörden gelen yeni veriyi formatla
                    duzenlenmis_df["Tarih"] = pd.to_datetime(duzenlenmis_df["Tarih"])
                    
                    # Yeni tabloyu oluştur (Eski Kalanlar + Yeni Düzenlenenler)
                    df_final = pd.concat([df_new, duzenlenmis_df], ignore_index=True)
                    
                    # Kaydet ve Yenile
                    dosya_kaydet(df_final, VERI_DOSYASI)
                    st.success("Veritabanı güncellendi!")
                    st.rerun()
            
            with col_info:
                st.caption("Satır silmek için satırı seçip 'Delete' tuşuna basın.")
