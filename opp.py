import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date, timedelta
from streamlit_gsheets import GSheetsConnection
import time
import re
import yfinance as yf

# --- 1. GÜVENLİK KONTROLÜ ---
st.set_page_config(page_title="Kuşların Bütçe Makinesi v32", page_icon="🐦", layout="wide")

def giris_kontrol():
    if "giris_yapildi" not in st.session_state:
        st.session_state.giris_yapildi = False

    # Secrets yoksa geliştirici modu (açık)
    if "genel" not in st.secrets:
        st.session_state.giris_yapildi = True
        return

    if not st.session_state.giris_yapildi:
        st.markdown("## 🔒 Bütçe Koruması")
        c1, c2 = st.columns([2,1])
        with c1:
            sifre = st.text_input("Giriş Şifresi:", type="password")
        with c2:
            st.write("") # Boşluk
            st.write("") 
            if st.button("Giriş Yap", type="primary"):
                if sifre == st.secrets["genel"]["sifre"]:
                    st.session_state.giris_yapildi = True
                    st.success("Giriş Başarılı!")
                    st.rerun()
                else:
                    st.error("Hatalı Şifre!")
        st.stop()

giris_kontrol()

# --- BAĞLANTI ---
conn = st.connection("gsheets", type=GSheetsConnection)
KOLONLAR = ["Tarih", "Kategori", "Tür", "Tutar", "Son Ödeme Tarihi", "Açıklama", "Durum"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# --- YARDIMCI FONKSİYONLAR ---
def verileri_cek():
    try:
        df = conn.read(worksheet="Veriler", ttl=0)
        if df.empty or "Tarih" not in df.columns: return pd.DataFrame(columns=KOLONLAR)
        df = df.dropna(how="all")
        for col in KOLONLAR:
            if col not in df.columns: df[col] = pd.NA
        return df
    except: return pd.DataFrame(columns=KOLONLAR)

def kategorileri_cek():
    varsayilan = pd.DataFrame([{"Kategori": "Maaş", "Tur": "Gelir", "VarsayilanGun": 1}, {"Kategori": "Market", "Tur": "Gider", "VarsayilanGun": 0}])
    try:
        df = conn.read(worksheet="Kategoriler", ttl=0)
        if df.empty: conn.update(worksheet="Kategoriler", data=varsayilan); return varsayilan
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

def kategorileri_kaydet(df): conn.update(worksheet="Kategoriler", data=df)

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

def csv_indir(df): return df.to_csv(index=False).encode('utf-8')

def etiketleri_analiz_et(df):
    etiket_verisi = []
    for _, row in df.iterrows():
        aciklama = str(row["Açıklama"]).lower()
        bulunanlar = re.findall(r"#(\w+)", aciklama)
        if bulunanlar:
            bolunmus_tutar = row["Tutar"] / len(bulunanlar)
            for etiket in bulunanlar: etiket_verisi.append({"Etiket": etiket, "Tutar": bolunmus_tutar})
    if etiket_verisi: return pd.DataFrame(etiket_verisi).groupby("Etiket")["Tutar"].sum().reset_index().sort_values("Tutar", ascending=False)
    else: return pd.DataFrame()

@st.cache_data(ttl=3600) 
def piyasa_verileri_getir():
    try:
        tickers = yf.download("TRY=X EURTRY=X GC=F", period="1d", progress=False)['Close']
        dolar = tickers['TRY=X'].iloc[-1]
        euro = tickers['EURTRY=X'].iloc[-1]
        ons_altin = tickers['GC=F'].iloc[-1]
        gram_altin = (ons_altin / 31.1035) * dolar
        return dolar, euro, gram_altin
    except:
        return 0, 0, 0

# --- YAN MENÜ: GÜNCELLEME BUTONU (EN ÜSTTE) ---
with st.sidebar:
    # BU BUTON F5 YERİNE GEÇER
    if st.button("🔄 Verileri ve Kurları Güncelle", type="primary", use_container_width=True):
        st.cache_data.clear() # Kurlar yeniden çekilsin diye önbelleği temizle
        st.rerun()            # Uygulamayı yeniden başlat (Şifre gitmez!)
    
    st.divider()

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

# --- YAN MENÜ DEVAMI ---
with st.sidebar:
    # DÖVİZ BİLGİ KARTI
    st.header("💰 Piyasa Durumu")
    usd, eur, gram = piyasa_verileri_getir()
    
    if usd > 0:
        c1, c2, c3 = st.columns(3)
        c1.metric("Dolar", f"{usd:.2f}")
        c2.metric("Euro", f"{eur:.2f}")
        c3.metric("Gr.Altın", f"{gram:.0f}")
        st.caption(f"🕒 Son Güncelleme: {datetime.now().strftime('%H:%M')}")
    else:
        st.warning("Veri çekilemedi.")
    
    st.divider()
    
    st.header("⚙️ Ayarlar")
    st.download_button(label="📥 Yedeği İndir", data=csv_indir(df), file_name=f"Yedek_{datetime.now().strftime('%d%m%Y')}.csv", mime='text/csv')
    st.divider()
    
    # ARAMA MODU
    st.subheader("🔍 Arama Motoru")
    arama_terimi = st.text_input("Kelime Ara", placeholder="Migros, Tatil, Sigorta...", help="Enter'a basınca tüm zamanlarda arar.")
    
    if not arama_terimi:
        st.divider()
        secilen_yil_filtre = datetime.now().year; secilen_ay_filtre = "Yılın Tamamı"
        if not df.empty and "Tarih" in df.columns:
            yil_list = sorted(df["Tarih"].dt.year.unique(), reverse=True)
            if datetime.now().year not in yil_list: yil_list.insert(0, datetime.now().year)
            secilen_yil_filtre = st.selectbox("Dönem (Yıl)", ["Tüm Zamanlar"] + list(yil_list))
            if secilen_yil_filtre == "Tüm Zamanlar":
                df_filt = df; baslik = "Tüm Zamanlar"; ay_no = 0
            else:
                df_filt = df[df["Tarih"].dt.year == secilen_yil_filtre]
                now = datetime.now(); varsayilan_ay = now.month if secilen_yil_filtre == now.year else 0
                secilen_ay_filtre = st.selectbox("Dönem (Ay)", ["Yılın Tamamı"] + AYLAR, index=varsayilan_ay)
                if secilen_ay_filtre != "Yılın Tamamı":
                    ay_no = AYLAR.index(secilen_ay_filtre) + 1
                    df_filt = df_filt[df_filt["Tarih"].dt.month == ay_no]
                    baslik = f"{secilen_ay_filtre} {secilen_yil_filtre}"
                else: baslik = f"{secilen_yil_filtre} Tamamı"; ay_no = 0
        else: df_filt = df; baslik = "Veri Yok"; ay_no = 0

        st.divider()
        with st.expander("🛠️ Toplu İşlemler"):
            if secilen_ay_filtre != "Yılın Tamamı" and secilen_yil_filtre != "Tüm Zamanlar":
                if st.button("⏮️ Geçen Ayı Kopyala"):
                    hy = secilen_yil_filtre; ha = ay_no
                    if ha == 1: ka = 12; ky = hy - 1
                    else: ka = ha - 1; ky = hy
                    kdf = df[(df["Tarih"].dt.year == ky) & (df["Tarih"].dt.month == ka) & (df["Tür"] == "Gider")]
                    if not kdf.empty:
                        kopya = []
                        for _, row in kdf.iterrows():
                            kb = df_kat[df_kat["Kategori"] == row["Kategori"]]
                            if not kb.empty and int(float(kb.iloc[0]["VarsayilanGun"])) > 0:
                                vg = int(float(kb.iloc[0]["VarsayilanGun"]))
                                yt = tarih_olustur(hy, secilen_ay_filtre, vg)
                                yso = son_odeme_hesapla(yt, vg)
                                kopya.append({"Tarih": pd.to_datetime(yt), "Kategori": row["Kategori"], "Tür": "Gider", "Tutar": row["Tutar"], "Son Ödeme Tarihi": yso, "Açıklama": f"{row['Açıklama']} (Kopya)", "Durum": False})
                        if kopya: verileri_kaydet(pd.concat([df, pd.DataFrame(kopya)], ignore_index=True)); st.success("Kopyalandı!"); time.sleep(1); st.rerun()
                        else: st.warning("Sabit gider yok.")
                    else: st.error("Veri yok.")
            else: st.info("Ay seçin.")
    else:
        mask = df.astype(str).apply(lambda x: x.str.contains(arama_terimi, case=False)).any(axis=1)
        df_filt = df[mask]
        baslik = f"🔍 Sonuçlar: '{arama_terimi}'"

    st.divider()
    with st.expander("📂 Kategori"):
        t1, t2 = st.tabs(["Ekle", "Düzenle"])
        with t1:
            with st.form("ke"):
                yt = st.radio("Tip", ["Gider", "Gelir"], horizontal=True)
                ya = st.text_input("Ad")
                yg = st.number_input("Gün", 0, 31, 0)
                if st.form_submit_button("Ekle") and ya:
                    gk = conn.read(worksheet="Kategoriler", ttl=0) if not df_kat.empty else df_kat
                    if ya not in gk["Kategori"].values: kategorileri_kaydet(pd.concat([gk, pd.DataFrame([{"Kategori": ya, "Tur": yt, "VarsayilanGun": yg}])], ignore_index=True)); st.success("Tamam"); st.rerun()
        with t2:
            if not df_kat.empty:
                sk = st.selectbox("Seç", df_kat["Kategori"].tolist())
                sr = df_kat[df_kat["Kategori"] == sk].iloc[0]
                da = st.text_input("Ad", value=sr['Kategori'])
                dt = st.selectbox("Tür", ["Gider", "Gelir"], index=0 if sr['Tur']=="Gider" else 1)
                dg = st.number_input("Gün", 0, 31, int(float(sr['VarsayilanGun'])))
                c1, c2 = st.columns(2)
                with c1: 
                    if st.button("Güncelle"):
                        df_kat.loc[df_kat["Kategori"]==sk, ["Kategori","Tur","VarsayilanGun"]] = [da, dt, dg]
                        kategorileri_kaydet(df_kat)
                        if sk != da and not df.empty: df.loc[df["Kategori"]==sk, "Kategori"] = da; verileri_kaydet(df)
                        st.success("Tamam"); st.rerun()
                with c2: 
                    if st.button("Sil"):
                        if sk in df["Kategori"].values: st.error("Kayıt var!")
                        else: kategorileri_kaydet(df_kat[df_kat["Kategori"]!=sk]); st.success("Silindi"); st.rerun()

    st.divider()
    if st.button("🚪 Çıkış Yap"):
        st.session_state.giris_yapildi = False
        st.rerun()

# --- İÇERİK ---
st.title("☁️ Kuşların Bütçe Makinesi v32")
st.caption(f"Rapor: **{baslik}**")

if arama_terimi:
    st.subheader("🔍 Arama Modu Aktif")
    st.markdown(f"**'{arama_terimi}'** aranıyor. Yeni kayıt girmek için aramayı temizleyin.")
    if not df_filt.empty: st.caption(f"Toplam **{len(df_filt)}** kayıt bulundu.")

if not df_filt.empty:
    gelir = df_filt[df_filt["Tür"] == "Gelir"]["Tutar"].sum()
    gider = df_filt[df_filt["Tür"] == "Gider"]["Tutar"].sum()
    net = gelir - gider
    bekleyen = df_filt[(df_filt["Tür"]=="Gider") & (df_filt["Durum"]==False)]["Tutar"].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Gelir", f"{gelir:,.0f} ₺")
    c2.metric("Gider", f"{gider:,.0f} ₺")
    c3.metric("Net", f"{net:,.0f} ₺", delta_color="normal" if net>0 else "inverse")
    c4.metric("Ödenmemiş", f"{bekleyen:,.0f} ₺", delta_color="inverse")
else: st.info("Sonuç yok.")
st.divider()

cL, cR = st.columns([1, 1.5])
with cL:
    if arama_terimi:
        st.info("Arama modundayken veri girişi kapalıdır.")
    else:
        st.subheader("📝 Veri Girişi")
        y = st.selectbox("Yıl", range(datetime.now().year-2, datetime.now().year+2), index=2)
        m = st.selectbox("Ay", AYLAR, index=datetime.now().month-1)
        t = st.radio("Tür", ["Gider", "Gelir"], horizontal=True)
        kl = df_kat[df_kat["Tur"] == t]["Kategori"].tolist() if not df_kat.empty else []
        k = st.selectbox("Kategori", kl, index=None)
        vg = 0
        if k and not df_kat.empty:
            r = df_kat[df_kat["Kategori"]==k]
            if not r.empty: vg = int(float(r.iloc[0]["VarsayilanGun"]))
        kt = tarih_olustur(y, m, vg)
        if k: st.caption(f"Tarih: **{kt.strftime('%d.%m.%Y')}**")
        so = son_odeme_hesapla(kt, vg)
        
        with st.form("giris"):
            tu = st.number_input("Tutar", step=50.0)
            ac = st.text_input("Açıklama")
            sot = st.date_input("Son Ödeme", value=so)
            if st.form_submit_button("KAYDET", type="primary"):
                if k and tu > 0:
                    yeni = pd.DataFrame([{"Tarih": pd.to_datetime(kt), "Kategori": k, "Tür": t, "Tutar": float(tu), "Son Ödeme Tarihi": sot, "Açıklama": ac, "Durum": False}])
                    verileri_kaydet(pd.concat([df, yeni], ignore_index=True)); st.success("Kaydedildi"); st.cache_data.clear(); st.rerun()
                else: st.error("Eksik!")

with cR:
    tab1, tab2 = st.tabs(["📊 Analiz", "📋 Liste"])
    with tab1:
        if not df_filt.empty and "Gider" in df_filt["Tür"].values:
            sg = df_filt[df_filt["Tür"]=="Gider"].copy()
            sg["Durum_Etiket"] = sg["Durum"].map({True: "Ödendi ✅", False: "Ödenmedi ❌"})
            c1, c2 = st.columns(2)
            with c1: 
                st.markdown("##### 1. Kategori")
                st.plotly_chart(px.pie(sg, values="Tutar", names="Kategori", hole=0.4), use_container_width=True)
            with c2: 
                st.markdown("##### 2. Etiket (#)")
                edf = etiketleri_analiz_et(sg)
                if not edf.empty: st.plotly_chart(px.bar(edf, x="Etiket", y="Tutar", color="Etiket", text="Tutar").update_traces(texttemplate='%{text:.2s}', textposition='outside').update_layout(showlegend=False, height=250, margin=dict(t=0,b=0,l=0,r=0)), use_container_width=True)
                else: st.info("Etiket yok.")
            st.divider()
            st.markdown("##### 3. Harcama Trendi")
            st.plotly_chart(px.area(sg.groupby("Tarih")["Tutar"].sum().reset_index().sort_values("Tarih"), x="Tarih", y="Tutar", markers=True).update_traces(line_color="#FF4B4B"), use_container_width=True)
    
    with tab2:
        if not df_filt.empty:
            edt = df_filt.sort_values("Tarih", ascending=False).copy()
            edt["Tarih"] = edt["Tarih"].dt.date
            if "Son Ödeme Tarihi" in edt.columns: edt["Son Ödeme Tarihi"] = pd.to_datetime(edt["Son Ödeme Tarihi"], errors='coerce').dt.date
            
            if arama_terimi:
                st.dataframe(edt, hide_index=True, use_container_width=True)
                st.caption("ℹ️ Arama modundayken düzenleme kapalıdır.")
            else:
                duzenli = st.data_editor(edt, column_config={"Durum": st.column_config.CheckboxColumn(default=False), "Tutar": st.column_config.NumberColumn(format="%.2f ₺"), "Kategori": st.column_config.SelectboxColumn(options=df_kat["Kategori"].unique().tolist()), "Tür": st.column_config.SelectboxColumn(options=["Gider", "Gelir"])}, hide_index=True, use_container_width=True, num_rows="dynamic")
                if st.button("💾 Kaydet"):
                    dfr = df.drop(df_filt.index); duzenli["Tarih"] = pd.to_datetime(duzenli["Tarih"])
                    verileri_kaydet(pd.concat([dfr, duzenli], ignore_index=True)); st.success("Tamam"); st.cache_data.clear(); st.rerun()
