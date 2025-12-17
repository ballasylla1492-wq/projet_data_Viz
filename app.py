# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from branca.colormap import linear
import geopandas as gpd
import subprocess

# ---------------------------
# 1️⃣ Charger les données
# ---------------------------
dep_geo = gpd.read_file(
    "https://france-geojson.gregoiredavid.fr/repo/departements.geojson"
)

ma_base = pd.read_csv("délinquance.csv", sep=";")
ma_base["Code_insee"] = ma_base["Code_departement"].astype(str).str.zfill(2)
# Virgule → point pour les taux
ma_base["taux_pour_mille"] = (
    ma_base["taux_pour_mille"]
    .astype(str)
    .str.replace(",", ".", regex=False)
    .astype(float)
)

indicateurs_cibles = [
    "Homicides",
    "Trafic de stupéfiants",
    "Destructions et dégradations volontaires",
    "Vols d'accessoires sur véhicules",
    "Vols dans les véhicules"
]

idf_sel = (
    ma_base[
        (ma_base["Code_region"] == 11) &
        (ma_base["indicateur"].isin(indicateurs_cibles))
    ]
    .groupby(
        ["Code_departement", "indicateur", "annee", "insee_pop"],
        as_index=False
    )
    .agg({
        "nombre": "sum",
        "taux_pour_mille": "mean"
    })
)

table_idf = idf_sel.sort_values(
    ["Code_departement", "indicateur"]
)

données = dep_geo.merge(
    table_idf,
    left_on="code",
    right_on="Code_departement",
    how="inner"
)

df = données

# ---------------------------
# 2️⃣ Sidebar : filtres
# ⚠️ Doit être le premier appel Streamlit.
st.set_page_config(layout="wide")
# ---------------------------
st.sidebar.header("Filtres")

annee_sel = st.sidebar.selectbox(
    "Choisir une année",
    sorted(df["annee"].unique())
)

indic_sel = st.sidebar.selectbox(
    "Choisir un indicateur",
    df["indicateur"].unique()
)




# Filtrer le dataframe
df_f = df[
    (df["annee"] == annee_sel) &
    (df["indicateur"] == indic_sel) 
]

df_time = df[
    (df["indicateur"] == indic_sel) 
]

# ---------------------------
# 3️⃣ Onglets : Graphiques / Carte
# ---------------------------
tab_graph, tab_map = st.tabs(["📊 Graphiques                   ", "🗺 Carte"])

# -------------------- Onglet Graphiques --------------------
with tab_graph:
    st.header(f"Évolution temporelle et répartition par département : {indic_sel} ({annee_sel})")

    # Créer deux colonnes
    col1, col2 = st.columns(2)

    # ---------- Colonne gauche : Courbe ----------
    with col1:
        fig_line = px.line(
            df_time,
            x="annee",
            y="taux_pour_mille",
            color="Code_departement",
            markers=True,
            labels={"taux_pour_mille":"Taux pour 1 000 hab."},
            title=f"Taux pour 1 000 habitants - {indic_sel}"
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ---------- Colonne droite : Diagramme en barres ----------
    with col2:
        fig_bar = px.bar(
            df_f,
            x="nom",
            y="nombre",
            color="Code_departement",
            labels={"nombre":"Nombre de cas"},
            title=f"Nombre de {indic_sel} par département en {annee_sel}"
        )
        # Rotation des labels
        fig_bar.update_layout(
            xaxis_tickangle=-45,
            xaxis_title="",  # enlever le titre pour l'axe x
        )
        st.plotly_chart(fig_bar, use_container_width=True)

   

# -------------------- Onglet Carte --------------------
# ---------------------------
# 3️⃣ Préparer le tooltip HTML (AVANT la carte)
# ---------------------------
# -------------------- Onglet Carte --------------------
# -------------------- Onglet Carte --------------------
with tab_map:

    st.header(f"🗺️ Carte interactive par indicateur ({annee_sel})")

    # CSS plein écran
    st.markdown("""
    <style>
    .folium-container {
        width: 100% !important;
        height: 100vh !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Carte
    p = folium.Map(
        location=[48.85, 2.35],
        zoom_start=9,
        tiles="OpenStreetMap"
    )

    # Palette rouge pour tous les indicateurs
    palette_dict = {indic: linear.Reds_09 for indic in indicateurs_cibles}

    for indic in indicateurs_cibles:

        # Filtrer par indicateur ET année sélectionnée
        data_indic = df_f[df_f["indicateur"] == indic]

        # Si pas de données pour cet indicateur/année, passer
        if data_indic.empty:
            continue

        # Colormap dynamique selon les valeurs des départements
        vmin = data_indic["nombre"].min()
        vmax = data_indic["nombre"].max()
        if vmin == vmax:
            vmax = vmin + 1

        colormap = palette_dict[indic].scale(vmin, vmax)
        colormap.caption = f"{indic} - Nombre ({annee_sel})"

        # Fonction de style
        def style_function(feature, data=data_indic, colormap=colormap):
            code_dep = feature["properties"]["Code_departement"]
            row = data[data["Code_departement"] == code_dep]
            if row.empty:
                return {"fillOpacity": 0}
            value = row["nombre"].values[0]
            return {
                "fillColor": colormap(value),
                "color": "black",
                "weight": 0.7,
                "fillOpacity": 0.75
            }

        # Tooltip HTML
        tooltip = folium.GeoJsonTooltip(
            fields=["Code_departement", "nom", "nombre", "taux_pour_mille", "insee_pop"],
            aliases=[
                "Département :",
                "Nom :",
                f"{indic} :",
                "Taux pour 1 000 hab. :",
                "Population :"
            ],
            localize=True
        )

        # Créer une couche par indicateur
        layer = folium.FeatureGroup(name=indic)

        folium.GeoJson(
            data_indic,
            style_function=style_function,
            tooltip=tooltip,
            highlight_function=lambda x: {"weight": 3, "color": "blue", "fillOpacity":0.9}
        ).add_to(layer)

        layer.add_to(p)
        colormap.add_to(p)


    # Afficher la carte
    st_folium(p, width=1600, height=800)





