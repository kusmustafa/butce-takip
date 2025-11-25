import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime, date

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi", page_icon="🐦", layout="wide")

# --- CSS (Tablo başlıklarını ve metrikleri güzelleştirme) ---
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
def sistem_kontrol():
    # Kategori Dosyası
    if not os.path.exists(KATEGORI_DOSYASI):
        pd.DataFrame([
            {"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 0},
            {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}
        ]).to_csv(KATEGORI_DOSYASI, index=False)
    else:
        try:
            df = pd.read_csv(KATEGORI_DOSYASI)
            degisti = False
            for col in ["Kategori", "Tur", "VarsayilanGun"]:
                if col not in df.columns:
                    df[col] = 0 if col == "VarsayilanGun" else ("Gider" if col == "Tur" else "")
                    degisti = True
            if degisti: df.to_csv(KATEGORI_DOSYASI, index=False)
        except: pass

    # Veri Dosyası (Yeni Sütun: Durum)
    if not os.path.exists(VERI_DOSYASI):
        df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"])
        df.to_csv(VERI_DOSYASI, index=False)
    else:
        try:
            df = pd.read_csv(VERI_DOSYASI)
            degisiklik = False
            # Kritik sütunları kontrol et
            if "Son Ödeme Tarihi" not in df.columns:
                df["Son Ödeme Tarihi"] = None
                degisiklik = True
            # Yeni eklenen 'Durum' sütunu (Ödendi mi?)
            if "Durum" not in df.columns:
                df["Durum"] = False # Varsayılan olarak ödenmedi
                degisiklik = True
                
            if degisiklik: df.to_csv(VERI_DOSYASI, index=False)
        except: pass

def dosya_kaydet(df, yol): df.to_csv(yol, index=False)

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
    """
    Pandas tablosunu boyamak için kullanılan stil fonksiyonu.
    Girdi olarak tüm satırı (row) alır, renk kodlarını döndürür.
    """
    # Varsayılan renk (Beyaz/Şeffaf)
    renk = '' 
    
    try:
        # Eğer 'Durum' True ise (Kutu işaretliyse) -> YEŞİL
        if val['Durum'] == True:
            renk = 'background-color: #d4edda; color: #155724' # Açık yeşil arka plan, koyu yeşil yazı
        
        # Ödenmemiş ve Gider ise Tarihe Bak
        elif val['Tür'] == 'Gider' and pd.notnull(val['Son Ödeme Tarihi']):
            son_odeme = pd.to_datetime(val['Son Ödeme Tarihi']).date()
            bugun = date.today()
            
            if son_odeme < bugun:
                # Tarih geçmiş -> KIRMIZI
                renk = 'background-color: #f8d7da; color: #721c24' # Açık kırmızı
            else:
                # Tarih gelmemiş -> MAVİ
                renk = 'background-color: #cce5ff; color: #004085' # Açık mavi
    except:
        pass # Hata olursa renksiz bırak
        
    return [renk] * len(val)

# --- BAŞLANGIÇ ---
sistem_kontrol()
if 'form_tutar' not in st.session_state: st.session_state.form_tutar = 0.0
if 'form_aciklama' not in st.session_state: st.session_state.form_aciklama = ""

try:
    df = pd.read_csv(VERI_DOSYASI)
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors='coerce')
    df = df.dropna(subset=["Tarih"])
    # Durum sütunu boolean olmalı
    df["Durum"] = df["Durum"].fillna(False).astype(bool)
except:
    df = pd.DataFrame(columns=["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"])

try: df_kat = pd.read_csv(KATEGORI_DOSYASI)
except: df_kat = pd.DataFrame(columns=["Kategori", "Tur", "VarsayilanGun"])

# --- YAN MENÜ ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    with st.expander("Verileri Sıfırla"):
        if st.button("Her Şeyi Sil"):
            if os.path.exists(VERI_DOSYASI): os.remove(VERI_DOSYASI)
            if os.path.exists(KATEGORI_DOSYASI): os.remove(KATEGORI_DOSYASI)
            st.rerun()
            
    st.divider()
    st.subheader("🔍 Filtre")
    if not df.empty:
        yil_listesi = sorted(df["Tarih"].dt.year.unique(), reverse=True)
        secenekler = ["Tüm Zamanlar"] + list(yil_listesi)
        secilen_yil = st.selectbox("Dönem", secenekler)
        
        if secilen_yil == "Tüm Zamanlar":
            df_filt = df; baslik = "Tüm Zamanlar"
        else:
            df_filt = df[df["Tarih"].dt.year == secilen_yil]
            ay_map = {i: ay for i, ay in enumerate(["Yılın Tamamı", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"])}
            idx = datetime.now().month if secilen_yil == datetime.now().year else 0
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
    
    # Bekleyen Ödemeler Hesabı
    bekleyen = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]["Tutar"].sum()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Gelir", f"{gelir:,.0f} ₺")
    k2.metric("Gider", f"{gider:,.0f} ₺")
    k3.metric("Net", f"{net:,.0f} ₺", delta_color="normal" if net > 0 else "inverse")
    k4.metric("Ödenmemiş Borç", f"{bekleyen:,.0f} ₺", delta_color="inverse")
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
            st.caption(f"📅 Sabit Gün: {varsayilan_gun}")
            son_odeme = st.date_input("Son Ödeme", value=oneri)
        elif tur_secimi == "Gider":
             son_odeme = st.date_input("Son Ödeme", value=None)

        if st.button("KAYDET", type="primary", use_container_width=True):
            if secilen_kat and tutar > 0:
                yeni_satir = pd.DataFrame({
                    "Tarih": [pd.to_datetime(giris_tarihi)],
                    "Kategori": [secilen_kat],
                    "Tür": [tur_secimi],
                    "Tutar": [float(tutar)],
                    "Son Ödeme Tarihi": [son_odeme],
                    "Açıklama": [aciklama],
                    "Durum": [False] # Yeni kayıtlar ödenmedi olarak başlar
                })
                df = pd.concat([df, yeni_satir], ignore_index=True)
                dosya_kaydet(df, VERI_DOSYASI)
                st.session_state["form_tutar"] = 0.0
                st.session_state["form_aciklama"] = ""
                st.success("Kaydedildi!"); st.rerun()
            else: st.error("Eksik bilgi!")

with col_sag:
    tab_grafik, tab_liste = st.tabs(["📊 Analiz", "📋 Liste ve Ödeme"])
    
    with tab_grafik:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sub_df = df_filt[df_filt["Tür"] == "Gider"]
            
            # Pasta: Ödenmiş vs Ödenmemiş
            st.caption("Ödeme Durumu")
            durum_df = sub_df.groupby("Durum")["Tutar"].sum().reset_index()
            durum_df["Durum"] = durum_df["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            fig_durum = px.pie(durum_df, values="Tutar", names="Durum", hole=0.5, color="Durum", color_discrete_map={"Ödendi ✅":"#28a745", "Ödenmedi ❌":"#dc3545"})
            fig_durum.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=200)
            st.plotly_chart(fig_durum, use_container_width=True)

            st.caption("Kategori Bazlı Harcama")
            grp = sub_df.groupby("Kategori")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False).head(5)
            st.bar_chart(grp, x="Kategori", y="Tutar", height=200)

    with tab_liste:
        st.info("Kutucuğu (✅) işaretleyip ödenmiş yapabilirsiniz. Tabloyu kaydırabilirsiniz.")
        
        # 1. VERİ DÜZENLEME (Tick atma yeri)
        if not df_filt.empty:
            # Görünümü ayarla
            edit_df = df_filt.sort_values("Tarih", ascending=False).copy()
            
            # Streamlit data_editor kullanarak interaktif tablo
            # column_config ile Durum sütununu checkbox yapıyoruz
            edited_data = st.data_editor(
                edit_df,
                column_config={
                    "Durum": st.column_config.CheckboxColumn(
                        "Ödendi?",
                        help="Ödeme yapıldıysa işaretleyin",
                        default=False,
                    ),
                    "Tarih": st.column_config.DateColumn("Tarih", format="DD.MM.YYYY"),
                    "Son Ödeme Tarihi": st.column_config.DateColumn("Son Ödeme", format="DD.MM.YYYY"),
                    "Tutar": st.column_config.NumberColumn("Tutar (TL)", format="%.0f ₺"),
                },
                disabled=["Tarih", "Kategori", "Tür", "Tutar", "Açıklama", "Son Ödeme Tarihi"], # Sadece 'Durum' değişebilsin
                hide_index=True,
                use_container_width=True,
                height=400,
                key="editor"
            )
            
            # DEĞİŞİKLİK KONTROLÜ VE KAYIT
            # Eğer editördeki veriler ile orijinal veri farklıysa kaydet
            # Bunu yapmak için indexleri eşleştirip Durum sütununu güncelliyoruz
            
            # Sadece değişen indexleri bulup ana tabloyu (df) güncelleyeceğiz
            if not edited_data.equals(edit_df):
                # Değişiklikleri ana dataframe'e aktar
                for index, row in edited_data.iterrows():
                    # Orijinal df'deki ilgili satırı bul ve güncelle
                    if index in df.index:
                        df.at[index, "Durum"] = row["Durum"]
                
                dosya_kaydet(df, VERI_DOSYASI)
                st.rerun() # Sayfayı yenile ki renkli tablo da güncellensin (Aşağıdaki)

        # 2. RENKLİ GÖRÜNÜM (Sadece görsel, düzenlenemez)
        with st.expander("🎨 Renkli Görünüm (Sadece İzleme)", expanded=True):
            if not df_filt.empty:
                # Pandas Styler ile boyama
                # Tarihleri stringe çeviriyoruz yoksa styler bozulabiliyor
                view_df = df_filt.sort_values("Tarih", ascending=False).copy()
                
                # Styler objesini oluştur
                styler = view_df.style.apply(renklendir, axis=1)
                
                # Formatlama
                styler.format({"Tarih": lambda t: t.strftime("%d-%m-%Y") if pd.notnull(t) else "",
                               "Son Ödeme Tarihi": lambda t: pd.to_datetime(t).strftime("%d-%m-%Y") if pd.notnull(t) else "",
                               "Tutar": "{:.0f} ₺"})
                
                st.dataframe(styler, use_container_width=True, height=400, hide_index=True)
                
                # Renk Açıklamaları (Legend)
                st.caption("✅ Yeşil: Ödendi | 🔴 Kırmızı: Gecikti | 🔵 Mavi: Bekliyor")

        # Silme Butonu
        if not df_filt.empty:
            c_del1, c_del2 = st.columns([3,1])
            with c_del1:
                sil_id = st.selectbox("Silinecek Kayıt", df_filt.index, 
                                     format_func=lambda x: f"{df.loc[x,'Tarih'].strftime('%d.%m')} | {df.loc[x,'Kategori']} | {df.loc[x,'Tutar']}₺",
                                     label_visibility="collapsed")
            with c_del2:
                if st.button("Sil"):
                    df = df.drop(sil_id).reset_index(drop=True)
                    dosya_kaydet(df, VERI_DOSYASI); st.rerun()
