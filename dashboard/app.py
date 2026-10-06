"""Dashboard Streamlit pour l'API de classification des réclamations.

Trois usages :
  1. Analyser une réclamation unique et voir prédiction + entités + priorité + routage.
  2. Analyser un lot de réclamations (saisie multi-ligne ou fichier CSV).
  3. Consulter un tableau de bord de statistiques globales (GET /api/stats).
"""
from __future__ import annotations

import io
import os

import pandas as pd
import streamlit as st

from api_client import APIError, classify, classify_batch, get_health, get_stats

st.set_page_config(
    page_title="Classification des réclamations",
    page_icon="📮",
    layout="wide",
)

PRIORITY_STYLE = {
    "HAUTE": ("🔴", "#DC2626"),
    "MOYENNE": ("🟠", "#D97706"),
    "BASSE": ("🟢", "#16A34A"),
}


def _priority_badge(priorite: str) -> str:
    emoji, color = PRIORITY_STYLE.get(priorite, ("⚪", "#64748B"))
    return f"<span style='color:{color}; font-weight:700;'>{emoji} {priorite}</span>"


# --------------------------------------------------------------------------
# Etat de session (URL de l'API persistée entre les interactions)
# --------------------------------------------------------------------------
if "api_base_url" not in st.session_state:
    st.session_state.api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")


# --------------------------------------------------------------------------
# Barre latérale : configuration + santé du service
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("📮 Réclamations")
    st.caption("Interface pilotant l'API FastAPI de classification.")

    st.session_state.api_base_url = st.text_input(
        "URL de l'API", value=st.session_state.api_base_url
    ).rstrip("/")

    st.divider()
    st.subheader("État du service")
    if st.button("🔄 Vérifier la connexion", use_container_width=True):
        st.session_state["_force_health_check"] = True

    try:
        health = get_health(st.session_state.api_base_url)
        if health["status"] == "ok":
            st.success("API opérationnelle")
        else:
            st.warning("API en mode dégradé")
        st.caption(
            f"Modèle de classification : {'✅ chargé' if health['modele_classification_charge'] else '❌ absent'}"
        )
        st.caption(
            f"Extraction d'entités : {'🧠 spaCy' if health['modele_ner_charge'] else '🔤 repli regex'}"
        )
        if health.get("detail"):
            st.caption(f"Détail : {health['detail']}")
    except APIError as exc:
        st.error(str(exc))


# --------------------------------------------------------------------------
# Contenu principal
# --------------------------------------------------------------------------
st.title("Classification automatique des réclamations")

tab_unique, tab_batch, tab_dashboard = st.tabs(
    ["🔍 Analyser une réclamation", "📦 Traitement en lot", "📊 Tableau de bord"]
)


# ============================================================
# Onglet 1 : réclamation unique
# ============================================================
with tab_unique:
    st.subheader("Soumettre une réclamation")

    exemple = (
        "Mon colis TRK-2890 est arrivé à la mauvaise adresse à Sfax, "
        "ça fait 5 jours que j'attends une solution."
    )
    text = st.text_area(
        "Texte de la réclamation",
        placeholder=exemple,
        height=140,
        key="single_text",
    )
    col_btn, col_example = st.columns([1, 1])
    with col_btn:
        submit = st.button("Analyser", type="primary", use_container_width=True)
    with col_example:
        if st.button("Charger un exemple", use_container_width=True):
            st.session_state["single_text"] = exemple
            st.rerun()

    if submit:
        if not text.strip():
            st.warning("Veuillez saisir un texte avant d'analyser.")
        else:
            with st.spinner("Analyse en cours..."):
                try:
                    resultat = classify(st.session_state.api_base_url, text)
                except APIError as exc:
                    st.error(str(exc))
                    resultat = None

            if resultat:
                st.divider()
                c1, c2, c3 = st.columns(3)
                c1.metric("Catégorie prédite", resultat["categorie"])
                c2.metric("Confiance du modèle", f"{resultat['confiance_categorie']:.0%}")
                c3.metric("Équipe de routage", resultat["equipe_routage"])

                st.markdown(
                    f"**Priorité :** {_priority_badge(resultat['priorite'])} "
                    f"&nbsp;·&nbsp; score {resultat['score_priorite']:.2f}",
                    unsafe_allow_html=True,
                )
                if resultat["declencheur_regle_dure"]:
                    st.info(f"Déclencheur de règle dure : `{resultat['declencheur_regle_dure']}`")
                if resultat["escalade_manager"]:
                    st.error("⚠️ Escalade manager requise (dommage majeur ou plainte forte).")

                st.markdown("**Entités extraites**")
                entites = resultat["entites"]
                if entites:
                    st.table(pd.DataFrame(entites.items(), columns=["Type", "Valeur"]))
                else:
                    st.caption("Aucune entité détectée dans ce texte.")

                with st.expander("Réponse brute (JSON)"):
                    st.json(resultat)


# ============================================================
# Onglet 2 : traitement en lot
# ============================================================
with tab_batch:
    st.subheader("Analyser un lot de réclamations")

    source = st.radio(
        "Source des textes",
        ["Saisie manuelle (une réclamation par ligne)", "Fichier CSV"],
        horizontal=True,
    )

    texts: list[str] = []

    if source.startswith("Saisie"):
        raw = st.text_area(
            "Une réclamation par ligne",
            height=180,
            placeholder="Colis cassé à l'arrivée\n20 jours de retard depuis la commande\nJe veux être remboursé",
        )
        texts = [line.strip() for line in raw.splitlines() if line.strip()]
    else:
        uploaded = st.file_uploader("Fichier CSV avec une colonne de texte", type=["csv"])
        if uploaded is not None:
            df_upload = pd.read_csv(uploaded)
            col = st.selectbox("Colonne contenant le texte de la réclamation", df_upload.columns)
            texts = df_upload[col].dropna().astype(str).tolist()
            st.caption(f"{len(texts)} lignes détectées.")

    if st.button("Analyser le lot", type="primary", disabled=not texts):
        with st.spinner(f"Analyse de {len(texts)} réclamation(s)..."):
            try:
                batch_result = classify_batch(st.session_state.api_base_url, texts)
            except APIError as exc:
                st.error(str(exc))
                batch_result = None

        if batch_result:
            df_res = pd.DataFrame(batch_result["resultats"])
            st.success(f"{batch_result['total']} réclamation(s) analysée(s).")

            c1, c2, c3 = st.columns(3)
            c1.metric("Priorité HAUTE", int((df_res["priorite"] == "HAUTE").sum()))
            c2.metric("Escalades manager", int(df_res["escalade_manager"].sum()))
            c3.metric("Confiance moyenne", f"{df_res['confiance_categorie'].mean():.0%}")

            st.dataframe(
                df_res[
                    [
                        "reclamation_brute",
                        "categorie",
                        "confiance_categorie",
                        "priorite",
                        "equipe_routage",
                        "escalade_manager",
                    ]
                ],
                use_container_width=True,
            )

            csv_buffer = io.StringIO()
            df_res.to_csv(csv_buffer, index=False)
            st.download_button(
                "⬇️ Télécharger les résultats (CSV)",
                data=csv_buffer.getvalue(),
                file_name="resultats_classification.csv",
                mime="text/csv",
            )


# ============================================================
# Onglet 3 : tableau de bord de statistiques
# ============================================================
with tab_dashboard:
    st.subheader("Statistiques globales du service")
    st.caption("Cumulées depuis le dernier démarrage de l'API (compteurs en mémoire).")

    if st.button("🔄 Rafraîchir les statistiques"):
        st.rerun()

    try:
        stats = get_stats(st.session_state.api_base_url)
    except APIError as exc:
        st.error(str(exc))
        stats = None

    if stats:
        if stats["total_reclamations_traitees"] == 0:
            st.info("Aucune réclamation traitée pour l'instant. Testez l'onglet d'analyse !")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total traité", stats["total_reclamations_traitees"])
            c2.metric(
                "Confiance moyenne",
                f"{stats['confiance_moyenne']:.0%}" if stats["confiance_moyenne"] is not None else "—",
            )
            c3.metric("Escalades manager", stats["escalades_manager"])
            c4.metric("Uptime", f"{stats['uptime_secondes'] / 60:.1f} min")

            st.divider()
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                st.markdown("**Par catégorie**")
                if stats["par_categorie"]:
                    st.bar_chart(pd.Series(stats["par_categorie"], name="Nombre"))
                else:
                    st.caption("Pas encore de données.")

            with col_b:
                st.markdown("**Par priorité**")
                if stats["par_priorite"]:
                    ordre = ["HAUTE", "MOYENNE", "BASSE"]
                    serie = pd.Series(stats["par_priorite"]).reindex(
                        [p for p in ordre if p in stats["par_priorite"]]
                    )
                    st.bar_chart(serie)
                else:
                    st.caption("Pas encore de données.")

            with col_c:
                st.markdown("**Par équipe de routage**")
                if stats["par_equipe_routage"]:
                    st.bar_chart(pd.Series(stats["par_equipe_routage"], name="Nombre"))
                else:
                    st.caption("Pas encore de données.")

            if stats["declencheurs_regle_dure"]:
                st.markdown("**Déclencheurs de règle dure**")
                st.table(
                    pd.DataFrame(
                        stats["declencheurs_regle_dure"].items(),
                        columns=["Déclencheur", "Occurrences"],
                    )
                )
