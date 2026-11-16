"""Szenen für die bewegte Vorschau der Verwaltung: Höhepunkt, Wortbeitrag oder ein bestimmter Gag eines Stils
gezielt zeigen (vis_scenes liefert die Auswahl, vis_force stellt den Zustand nach kurzem Vorlauf ein)."""

VIS_GAG_LABELS = {
    # Kellertreppe
    "spinne": "Spinne mit Kopfhörern", "maeuse": "Mäuse-Polonaise", "staub": "Hand mit Staubwedel",
    "socke": "Waschmaschine frisst Socke", "arm": "Zombie verliert den Arm", "glas": "Zombie futtert Einmachglas",
    "polonaise": "Zombie in der Polonaise", "xylophon": "Skelett-Xylophon", "zerfall": "Skelett zerfällt",
    "hausverwalter": "Hausverwalter-Zombie", "vampir": "Graf Kellerstein", "mumie": "Mumie wickelt sich ab",
    # Mittelalter-Metal
    "visier": "Visier klappt zu", "moench": "Mönch beim Crowdsurfen", "steckenpferd": "Steckenpferd-Ritter",
    "katapult": "Katapult mit Kohlkopf", "solo": "Gitarrensolo", "walldeath": "Wall of Death",
    "fraeulein": "Burgfräulein wirft Rose", "drache": "Drache headbangt mit", "met": "Trommler trinkt Met",
    # Überraschungsparty
    "hund": "Hund frisst die Torte", "kerzen": "Trickkerzen", "geschenk": "Kastenteufel im Geschenk",
    # Weihnachten (jugendfrei)
    "schornstein": "Schornstein", "plaetzchen": "Plätzchen", "geschenketurm": "Geschenketurm",
    "wunschzettel": "Wunschzettel", "schlitten": "Schlitten einparken", "lebkuchen": "Lebkuchenmann",
    "katze": "Katze im Baum", "stromausfall": "Stromausfall", "glatteis": "Glatteis", "wichtelchor": "Wichtel-Chor",
}


def vis_scenes(style):
    """Auswahl für die bewegte Vorschau: [[id, Beschriftung], …]; Gags als "gag:<name>"."""
    out = [["play", "Abspielen"], ["boom", "Höhepunkt"], ["talk", "Wortbeitrag"]]
    gags = {"cellar": CL_GAGS, "metal": MT_GAGS, "party": PT_GAGS, "xmas": FUN_GAGS}.get(style, {})
    out += [["gag:" + n, VIS_GAG_LABELS.get(n, n.capitalize())] for n in gags]
    if style == "xmas":                                             # Feierabend-Gags (schaltet ihn für die Vorschau an)
        out += [["feier:" + n, "Feierabend: " + VIS_GAG_LABELS.get(n, n.capitalize())]
                for n in PARTY_GAGS if n not in FUN_GAGS]
    return out


def vis_force(r, style, scene, t):
    """Zustand des Stils für eine Szene einstellen (nach dem Vorlauf; r._vis_states ist gefüllt)."""
    st = r._vis_states.get(style)
    if st is None or scene in ("play", "talk"):
        return
    kind, _, name = scene.partition(":")
    if style == "cellar":
        for c in st.get("crew") or []:
            c["mode"] = "idle"
        if kind == "boom":
            st["boom"], st["booms"], st["gag"] = t, st.get("booms", 0) + 1, None
        elif kind == "gag":
            st["gag"], st["next_gag"] = (name, t), t + 99
    elif style == "metal":
        if kind == "boom":
            st["boom"], st["gag"] = t, None
        elif kind == "gag":
            st["gag"], st["next_gag"], st["boom"] = (name, t), t + 99, -99.0
    elif style == "party":
        if kind == "boom":
            st.update(phase="surprise", phase_t=t)
        elif kind == "gag":
            st.update(phase="party", phase_t=t - 30, gag=(name, t), next_gag=t + 99)
            if name == "hund":
                st["eaten"], st["dog"] = 0.0, None
    elif style == "xmas":
        if kind == "gag" and "fun" in st:
            r._xmas_fun_start(st["fun"], name)
            st["fun"]["next"] = 1e9
        elif kind == "feier" and "party" in st:
            ps = st["party"]
            ps.update(phase="mid", next=1e9, micro_at=1e9, pegel=max(ps.get("pegel", 0), 0.7))
            ps["props"].update({"puddle", "sign"})
            r._xmas_party_start(ps, name)
    elif style == "dancer" and kind == "boom":
        st["spin_t"] = t
