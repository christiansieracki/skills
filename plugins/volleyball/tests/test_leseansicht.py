"""Prueft die Leseansicht eines Trainingsplans gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Erzeugt wird ueber die Kommandozeile, wie der Skill es tut, und gelesen wird
die HTML-Datei, die dabei neben dem Plan entsteht. `leseansicht.py` nimmt kein
`--wurzel`, es findet den Arbeitsordner ueber den Pfad des Plans.

Die Tests pruefen, was ein Trainer in der Leseansicht findet. Das HTML liest
leseansicht_lesen.py in eine einfache Form zurueck, nur dort steht, welches
Markup was traegt.

Die Bilder kommen hier als Verweis statt eingebettet. Dann steht der Name
jeder Datei im HTML, und ihre Reihenfolge laesst sich ablesen. Welche Datei
gezeigt wird, entscheidet dieselbe Stelle wie beim Einbetten.
"""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path

from arbeitsordner import Arbeitsordner, Zeile
from leseansicht_lesen import Leseansicht, lies_leseansicht

PLAN = "gruppe/2026-09-15.md"


class LeseansichtTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def erzeuge(self, plan: Path) -> Leseansicht:
        """Erzeugt die Leseansicht dieses Plans und liest sie zurueck."""
        fertig = self.ordner.starte("leseansicht.py", str(plan), "--bilder", "verweis",
                                    mit_wurzel=False)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return lies_leseansicht(plan.with_suffix(".html").read_text(encoding="utf-8"))

    def ansicht(self, zeilen: list[Zeile], **plan) -> Leseansicht:
        """Die Leseansicht eines Plans aus diesen Zeilen.

        Freie Abschnitte und Frontmatter kommen als Schluesselwort, wie bei
        `lege_plan_an`.
        """
        return self.erzeuge(self.ordner.lege_plan_an(PLAN, zeilen, **plan))


class ProgrammpunktTest(LeseansichtTest):
    def test_jede_zeile_wird_ein_programmpunkt_zum_aufklappen(self) -> None:
        ansicht = self.ansicht([
            Zeile("0–10", "Ankommen", "Zonenbaggern im Paar", "ue-000002"),
            Zeile("10–35", "Hauptteil", "Annahme im Halbfeld", "ue-000001"),
        ])

        self.assertEqual(
            [(p.zeit, p.dauer, p.name, p.uebung, p.zugeklappt) for p in ansicht.programmpunkte],
            [("0–10", 10, "Ankommen", "Zonenbaggern im Paar", True),
             ("10–35", 25, "Hauptteil", "Annahme im Halbfeld", True)])

    def test_die_zweite_spalte_darf_auch_teil_oder_block_heissen(self) -> None:
        # Bis zur Welle zur Leseansicht hiess sie "Teil", davor "Block". Die
        # Plaene seit September gelten weiter.
        for spalte in ("Programmpunkt", "Teil", "Block"):
            with self.subTest(spalte=spalte):
                ansicht = self.ansicht([Zeile("10–35", "Hauptteil", "Annahme im Halbfeld")],
                                       spalte=spalte)

                (punkt,) = ansicht.programmpunkte
                self.assertEqual((punkt.name, punkt.uebung), ("Hauptteil", "Annahme im Halbfeld"))

    def test_eine_uhrzeit_bleibt_stehen_und_der_programmpunkt_hat_keine_dauer(self) -> None:
        ansicht = self.ansicht([Zeile("18:00", "Hauptteil", "Annahme im Halbfeld")])

        (punkt,) = ansicht.programmpunkte
        self.assertEqual((punkt.zeit, punkt.dauer, punkt.uebung),
                         ("18:00", None, "Annahme im Halbfeld"))

    def test_eine_zeitangabe_mit_bindestrich_hat_ihre_dauer(self) -> None:
        ansicht = self.ansicht([Zeile("46-93", "Hauptteil", "Annahme im Halbfeld")])

        (punkt,) = ansicht.programmpunkte
        self.assertEqual((punkt.zeit, punkt.dauer), ("46-93", 47))

    def test_aufgeklappt_stehen_heute_das_schaubild_und_warum_hier_untereinander(self) -> None:
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg", quelle="PlayDrill")

        ansicht = self.ansicht([Zeile("10–35", "Hauptteil", "Mit einem Bild", "ue-000030",
                                      heute="Drei Längsstreifen statt zwei",
                                      warum="Die Sechser stehen schon zusammen")])

        (punkt,) = ansicht.programmpunkte
        self.assertEqual(punkt.teile,
                         ["Heute", "Schaubild der Karte", "Quelle und ID", "Warum hier?"])
        self.assertEqual(punkt.heute, "Drei Längsstreifen statt zwei")
        self.assertEqual(punkt.warum, "Die Sechser stehen schon zusammen")
        self.assertTrue(punkt.warum_zugeklappt)

    def test_ohne_anpassung_steht_kein_heute(self) -> None:
        # "—" heisst in der Spalte Anpassung: heute nichts anders.
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar", heute="—"),
                                Zeile("10–35", "Hauptteil", "Annahme im Halbfeld")])

        self.assertEqual([p.heute for p in ansicht.programmpunkte], [None, None])

    def test_pause_und_umbau_erscheinen_gedaempft(self) -> None:
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
                                Zeile("10–12", "Pause", "Trinken"),
                                Zeile("12–15", "Umbau auf zwei Netze"),
                                Zeile("15–35", "Hauptteil", "Annahme im Halbfeld")])

        self.assertEqual([p.gedaempft for p in ansicht.programmpunkte],
                         [False, True, True, False])

    def test_ueber_dem_ablauf_steht_die_zahl_der_programmpunkte(self) -> None:
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
                                Zeile("10–35", "Hauptteil", "Annahme im Halbfeld")])
        einer = self.ansicht([Zeile("0–90", "Spiel", "Zwei gegen Zwei auf dem Kleinfeld")])

        self.assertEqual(ansicht.ablauf, "Ablauf · 2 Programmpunkte · Minuten ab Beginn")
        self.assertEqual(einer.ablauf, "Ablauf · 1 Programmpunkt · Minuten ab Beginn")


class VorbereitungTest(LeseansichtTest):
    ZEILEN = [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
              Zeile("10–35", "Hauptteil", "Annahme im Halbfeld")]

    def test_jeder_uebrige_abschnitt_steht_in_der_reihenfolge_des_plans(self) -> None:
        ansicht = self.ansicht(
            self.ZEILEN,
            vorher="""
                ## Schwerpunkte dieser Einheit

                Annahme stabilisieren.

                ## Rahmenbedingungen

                Ein Hallenteil, ein Netz.
            """,
            neben_der_tabelle="Ablauf siehe unten, die Skizze steht bei Material.",
            nachher="""
                ## Material gesamt

                - Hütchen

                ### Für den Hauptteil

                Zwei Wagen Bälle.

                ## Nachbereitung

                Lief gut.
            """)

        self.assertEqual(
            [(a.ueberschrift, a.text, a.zugeklappt) for a in ansicht.vorbereitung],
            [("Schwerpunkte dieser Einheit", "Annahme stabilisieren.", True),
             ("Rahmenbedingungen", "Ein Hallenteil, ein Netz.", True),
             ("Ablauf", "Ablauf siehe unten, die Skizze steht bei Material.", True),
             ("Material gesamt", "Hütchen Für den Hauptteil Zwei Wagen Bälle.", True),
             ("Nachbereitung", "Lief gut.", True)])

    def test_der_knopf_vorbereitung_steht_nur_da_wenn_es_sie_gibt(self) -> None:
        mit = self.ansicht(self.ZEILEN, nachher="## Material gesamt\n\nBälle")
        ohne = self.ansicht(self.ZEILEN)

        self.assertEqual(mit.knoepfe, ["Vorbereitung"])
        self.assertEqual((ohne.knoepfe, ohne.vorbereitung), ([], []))

    def test_ein_leerer_abschnitt_steht_nicht_unter_vorbereitung(self) -> None:
        # Die Vorlage des Trainingsplans bringt Ueberschriften ohne Text mit,
        # etwa "## Schaubilder". Ein leeres Aufklappfeld sagt in der Halle
        # nichts.
        ansicht = self.ansicht(self.ZEILEN, nachher="## Schaubilder\n\n## Nachbereitung\n\n")

        self.assertEqual((ansicht.knoepfe, ansicht.vorbereitung), ([], []))


class OhneSkriptTest(LeseansichtTest):
    """Die Leseansicht muss lesbar sein, wo kein JavaScript laeuft (ADR-0012).

    Auf dem iPhone zeigen WhatsApp und die Dateien-App eine HTML-Datei zuerst
    in einer Vorschau, und ob dort Skript laeuft, ist nicht verlaesslich.
    """

    def test_der_text_jedes_abschnitts_steht_ausserhalb_von_skript(self) -> None:
        texte = ["Vorweg ein Satz unter dem Titel.", "Annahme stabilisieren.",
                 "Erst die Hütchen, dann das Netz.", "A1 auf Position 4",
                 "Zwei Wagen Bälle.", "Bänder und Matten", "Lief gut."]
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar")],
            vorher=f"""
                {texte[0]}

                ## Schwerpunkte dieser Einheit

                {texte[1]}
            """,
            neben_der_tabelle=f"""
                {texte[2]}

                ```
                |  {texte[3]}  |
                ```
            """,
            nachher=f"""
                ## Material gesamt

                ### Für den Hauptteil

                - {texte[4]}

                | Was | Wo |
                |---|---|
                | {texte[5]} | Geräteraum |

                ## Nachbereitung

                **{texte[6]}**
            """)

        for text in texte:
            with self.subTest(text=text):
                self.assertIn(text, ansicht.text)

    def test_html_aus_dem_plan_erscheint_als_text(self) -> None:
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar", heute="<b>drei</b> Streifen")],
            nachher="## Organisation\n\nNicht <b>fett</b> & nicht <script>weg</script>")

        (punkt,) = ansicht.programmpunkte
        self.assertEqual(punkt.heute, "<b>drei</b> Streifen")
        self.assertEqual(ansicht.vorbereitung[0].text,
                         "Nicht <b>fett</b> & nicht <script>weg</script>")
        self.assertEqual(ansicht.skripte, [])

    def test_die_leseansicht_enthaelt_kein_javascript(self) -> None:
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg")
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Mit einem Bild", "ue-000030",
                   heute="heute anders", warum="weil")],
            nachher="## Material gesamt\n\nBälle")

        self.assertEqual((ansicht.skripte, ansicht.ereignisse), ([], []))


class ListeZumAufklappenTest(LeseansichtTest):
    """Eine Tabelle, die mit `Nr | Übung` beginnt, wird eine Liste zum Aufklappen.

    Vier Spalten sind auf dem Handy so unlesbar wie frueher die Ablauftabelle.
    Gedacht ist sie fuer die Athletik, die Regel haengt aber nur an den
    Spalten.
    """

    def abschnitt(self, tabelle: str):
        """Der einzige Abschnitt unter Vorbereitung eines Plans mit dieser Tabelle."""
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar")],
                               nachher="## Athletik\n\n" + textwrap.dedent(tabelle))
        (abschnitt,) = ansicht.vorbereitung
        return abschnitt

    def test_nummer_name_und_dosierung_im_kopf_die_beschreibung_beim_aufklappen(self) -> None:
        abschnitt = self.abschnitt("""
            | Nr | Übung | Worauf es ankommt | Heute |
            |---|---|---|---|
            | 1 | Ausfallschritt mit Drehung | Blick zur hinteren Hand | 3–5 Wdh. je Seite |
            | 2 | Tiefe Hocke | Fersen bleiben am Boden | 20 s |
        """)

        self.assertEqual(abschnitt.tabellen, [])
        (liste,) = abschnitt.listen
        self.assertEqual(
            [(e.titel, e.heute, e.inhalt, e.zugeklappt) for e in liste],
            [("1. Ausfallschritt mit Drehung", "3–5 Wdh. je Seite",
              [("", "Blick zur hinteren Hand")], True),
             ("2. Tiefe Hocke", "20 s", [("", "Fersen bleiben am Boden")], True)])

    def test_mehrere_uebrige_spalten_stehen_mit_ihrer_ueberschrift(self) -> None:
        abschnitt = self.abschnitt("""
            | Nr | Übung | Worauf es ankommt | Heute | Material |
            |---|---|---|---|---|
            | 1 | Tiefe Hocke | Fersen bleiben am Boden | 20 s | Matte |
        """)

        ((eintrag,),) = abschnitt.listen
        self.assertEqual((eintrag.titel, eintrag.heute, eintrag.inhalt),
                         ("1. Tiefe Hocke", "20 s",
                          [("Worauf es ankommt", "Fersen bleiben am Boden"),
                           ("Material", "Matte")]))

    def test_ohne_spalte_heute_steht_im_kopf_nur_nummer_und_name(self) -> None:
        abschnitt = self.abschnitt("""
            | Nr | Übung | Worauf es ankommt |
            |---|---|---|
            | 1 | Tiefe Hocke | Fersen bleiben am Boden |
        """)

        ((eintrag,),) = abschnitt.listen
        self.assertEqual((eintrag.titel, eintrag.heute, eintrag.inhalt),
                         ("1. Tiefe Hocke", None, [("", "Fersen bleiben am Boden")]))

    def test_eine_tabelle_die_nicht_mit_nr_und_uebung_beginnt_bleibt_eine_tabelle(self) -> None:
        # Die Sechser haben auch eine Nummer, sind aber keine Uebungsliste.
        abschnitt = self.abschnitt("""
            | Nr | Sechser | Annahme |
            |---|---|---|
            | 1 | Rot | Dreierriegel |

            | Übung | Nr | Heute |
            |---|---|---|
            | Tiefe Hocke | 1 | 20 s |
        """)

        self.assertEqual(abschnitt.listen, [])
        self.assertEqual(abschnitt.tabellen,
                         [[["Nr", "Sechser", "Annahme"], ["1", "Rot", "Dreierriegel"]],
                          [["Übung", "Nr", "Heute"], ["Tiefe Hocke", "1", "20 s"]]])


class SchaubildTest(LeseansichtTest):

    def bilder(self, *ids: str) -> list[str]:
        """Erzeugt die Leseansicht eines Plans mit diesen IDs. Gibt die Bilder in ihrer Folge zurueck.

        Je Bild der Dateiname, auf den es verweist.
        """
        ansicht = self.erzeuge(self.ordner.lege_trainingsplan_an(PLAN, *ids))
        return [bild.datei.rsplit("/", 1)[-1]
                for punkt in ansicht.programmpunkte for bild in punkt.schaubilder]

    def test_unter_dem_schaubild_stehen_quelle_und_id_der_karte(self) -> None:
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg", quelle="PlayDrill")

        (punkt,) = self.erzeuge(self.ordner.lege_trainingsplan_an(PLAN, "ue-000030")).programmpunkte

        self.assertEqual([bild.beschriftung for bild in punkt.schaubilder], [""])
        self.assertEqual((punkt.quelle, punkt.id), ("PlayDrill", "ue-000030"))

    def test_mehrere_schaubilder_sind_gezaehlt(self) -> None:
        namen = ["ue-000031-uebersicht.png", "ue-000031-station-1.png"]
        for name in namen:
            self.ordner.lege_schaubild_an(name)
        self.ordner.lege_karte_an(id="ue-000031", titel="Zirkel mit zwei Bildern",
                                  schaubild=namen)

        (punkt,) = self.erzeuge(self.ordner.lege_trainingsplan_an(PLAN, "ue-000031")).programmpunkte

        self.assertEqual([bild.beschriftung for bild in punkt.schaubilder],
                         ["Schaubild 1 von 2", "Schaubild 2 von 2"])

    def test_ohne_schaubild_bleiben_quelle_und_id_der_karte(self) -> None:
        # Damit man die Karte findet. Fruehere Leseansichten zeigten die ID
        # neben der Uebung.
        (punkt,) = self.erzeuge(self.ordner.lege_trainingsplan_an(PLAN, "ue-000001")).programmpunkte

        self.assertNotIn("Schaubild der Karte", punkt.teile)
        self.assertEqual((punkt.quelle, punkt.id), ("Testbestand", "ue-000001"))

    def test_ein_einzelnes_schaubild_steht_bei_seiner_uebung(self) -> None:
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg")

        self.assertEqual(self.bilder("ue-000030"), ["ue-000030-aufbau.svg"])

    def test_eine_liste_zeigt_alle_bilder_in_ihrer_reihenfolge(self) -> None:
        # Absichtlich nicht alphabetisch: Die Folge kommt von der Karte, bei
        # einem Zirkel das Uebersichtsblatt vorn (#39).
        namen = ["ue-000031-uebersicht.png", "ue-000031-station-2.png",
                 "ue-000031-station-1.png"]
        for name in namen:
            self.ordner.lege_schaubild_an(name)
        self.ordner.lege_karte_an(id="ue-000031", titel="Zirkel mit drei Bildern",
                                  schaubild=namen)

        self.assertEqual(self.bilder("ue-000031"), namen)

    def test_fehlt_ein_bild_der_liste_faellt_nur_dieses_weg(self) -> None:
        # Wie bei einem einzelnen Bild: Eine Leseansicht ohne ein Bild ist
        # brauchbar, eine mit totem Verweis nicht. Den Verweis meldet der
        # Linter.
        for name in ("ue-000032-zirkel-1.png", "ue-000032-zirkel-3.png"):
            self.ordner.lege_schaubild_an(name)
        self.ordner.lege_karte_an(
            id="ue-000032", titel="Zirkel mit einem fehlenden Bild",
            schaubild=["ue-000032-zirkel-1.png", "ue-000032-zirkel-2.png",
                       "ue-000032-zirkel-3.png"])

        self.assertEqual(self.bilder("ue-000032"),
                         ["ue-000032-zirkel-1.png", "ue-000032-zirkel-3.png"])


if __name__ == "__main__":
    unittest.main()
