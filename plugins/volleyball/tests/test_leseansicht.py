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

from arbeitsordner import OHNE, Arbeitsordner, Zeile
from leseansicht_lesen import Leseansicht, Link, lies_leseansicht, wie_oft_eingebettet

PLAN = "gruppe/2026-09-15.md"


class LeseansichtTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def erzeuge(self, plan: Path) -> Leseansicht:
        """Erzeugt die Leseansicht dieses Plans und liest sie zurueck.

        Was auf der Konsole stand, liegt danach in `self.konsole`, eine Zeile
        je Eintrag.
        """
        fertig = self.ordner.starte("leseansicht.py", str(plan), "--bilder", "verweis",
                                    mit_wurzel=False)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.konsole = (fertig.stdout + fertig.stderr).splitlines()
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


class KopfTest(LeseansichtTest):
    ZEILEN = [Zeile("0–120", "Spiel", "Zwei gegen Zwei auf dem Kleinfeld")]

    def test_der_kurztitel_steht_in_der_ueberschrift_nach_dem_gedankenstrich(self) -> None:
        ansicht = self.ansicht(
            self.ZEILEN,
            titel="Training 01.10.2026 — Drei Sechser, 5-1 fürs Testspiel und 6-2 antesten")

        self.assertEqual(ansicht.kopf.titel, "Drei Sechser, 5-1 fürs Testspiel und 6-2 antesten")

    def test_ohne_gedankenstrich_ist_die_ganze_ueberschrift_der_kurztitel(self) -> None:
        # Ein Bindestrich wie in 5-1 ist kein Gedankenstrich.
        ansicht = self.ansicht(self.ZEILEN, titel="Training 15.09.2026, 5-1 gegen 6-2")

        self.assertEqual(ansicht.kopf.titel, "Training 15.09.2026, 5-1 gegen 6-2")

    def test_das_datum_steht_deutsch_und_kurz_mit_wochentag(self) -> None:
        ansicht = self.ansicht(self.ZEILEN, datum="2026-10-01")

        self.assertIn("Do, 01.10.2026", ansicht.kopf.angaben)

    def test_der_name_der_gruppe_kommt_aus_der_wurzeldatei(self) -> None:
        self.ordner.setze_gruppen({"h1-h2": {"name": "Herren 1 + Herren 2",
                                             "teams": ["herren-1", "herren-2"],
                                             "trainer": ["test"]}})

        ansicht = self.ansicht(self.ZEILEN, gruppe="h1-h2")

        self.assertIn("Herren 1 + Herren 2", ansicht.kopf.angaben)
        self.assertNotIn("h1-h2", ansicht.kopf.angaben)

    def test_ohne_namen_in_der_wurzeldatei_steht_das_kuerzel(self) -> None:
        self.ordner.setze_gruppen({"h1-h2": {"name": "Herren 1 + Herren 2"},
                                   "u16": {"teams": ["u16"]}})

        ansicht = self.ansicht(self.ZEILEN, gruppe="u16")

        self.assertIn("u16", ansicht.kopf.angaben)
        self.assertNotIn("Herren 1 + Herren 2", ansicht.kopf.angaben)

    def test_ausserhalb_eines_arbeitsordners_steht_das_kuerzel(self) -> None:
        # Ohne Wurzeldatei gibt es keinen Namen nachzuschlagen. Die
        # Leseansicht entsteht trotzdem, erzeuge() prueft den Exitcode.
        self.ordner.setze_gruppen({"h1-h2": {"name": "Herren 1 + Herren 2"}})
        plan = self.ordner.lege_plan_an(PLAN, self.ZEILEN, gruppe="h1-h2")
        fremd = plan.replace(self.ordner.lege_entwurfsordner_an() / plan.name)

        ansicht = self.erzeuge(fremd)

        self.assertIn("h1-h2", ansicht.kopf.angaben)

    def test_teilnehmer_und_dauer_stehen_im_kopf(self) -> None:
        ansicht = self.ansicht(self.ZEILEN, teilnehmer=18, dauer=120)

        self.assertIn("18 Teilnehmer", ansicht.kopf.angaben)
        self.assertIn("120 min", ansicht.kopf.angaben)

    def test_die_spielflaechen_sind_die_zahl_der_hallenteile(self) -> None:
        for spielflaechen, hallenteile in ((1, "1 Hallenteil"), (2, "2 Hallenteile")):
            with self.subTest(spielflaechen=spielflaechen):
                ansicht = self.ansicht(self.ZEILEN, spielflaechen=spielflaechen)

                self.assertIn(hallenteile, ansicht.kopf.angaben)

    def test_was_im_frontmatter_fehlt_faellt_weg_ohne_leere_trennzeichen(self) -> None:
        # Der Plan traegt immer datum und gruppe, wenn der Test sie nicht
        # weglaesst. Ein leeres Feld zaehlt wie ein fehlendes, die Vorlage
        # bringt etwa teilnehmer: leer mit.
        faelle = [
            ({}, ["Di, 15.09.2026", "gruppe"]),
            ({"gruppe": OHNE, "spielflaechen": 2}, ["Di, 15.09.2026", "2 Hallenteile"]),
            ({"datum": OHNE, "teilnehmer": 12, "dauer": None}, ["gruppe", "12 Teilnehmer"]),
            ({"datum": OHNE, "gruppe": OHNE, "dauer": 90}, ["90 min"]),
            ({"datum": OHNE, "gruppe": OHNE}, []),
        ]
        for frontmatter, angaben in faelle:
            with self.subTest(**{k: str(v) for k, v in frontmatter.items()}):
                kopf = self.ansicht(self.ZEILEN, **frontmatter).kopf

                self.assertEqual(kopf.angaben, angaben)
                for zeile in kopf.zeilen:
                    self.assertTrue(all(teil.strip() for teil in zeile.split("·")), zeile)


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


class ZuordnungTest(LeseansichtTest):
    """Beginnt die Ueberschrift eines Abschnitts mit einer Zeitangabe, gehoert
    er zu diesem Programmpunkt (Glossar, "Trainingsplan und Leseansicht")."""

    ZEILEN = [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
              Zeile("10–35", "Hauptteil", "Annahme im Halbfeld")]

    def abschnitte(self, punkt) -> list[tuple[str, str]]:
        return [(a.ueberschrift, a.text) for a in punkt.abschnitte]

    def meldungen(self, *ueberschriften: str) -> list[str]:
        """Die Zeilen der Konsole, die eine dieser Ueberschriften nennen."""
        return [z for z in self.konsole if any(u in z for u in ueberschriften)]

    def test_ein_abschnitt_mit_zeitangabe_nimmt_seine_unterabschnitte_mit(self) -> None:
        ansicht = self.ansicht(self.ZEILEN, nachher="""
            ## 10–35 Annahme in drei Streifen

            Erst die Annahme, dann das Zuspiel.

            ### Hallenskizze

            ```
            |  A1   A2   A3  |
            ```

            ## Nachbereitung

            Lief gut.
        """)

        ankommen, hauptteil = ansicht.programmpunkte
        self.assertEqual(self.abschnitte(ankommen), [])
        self.assertEqual(self.abschnitte(hauptteil), [
            ("Annahme in drei Streifen",
             "Erst die Annahme, dann das Zuspiel. Hallenskizze | A1 A2 A3 |")])
        self.assertEqual([a.ueberschrift for a in ansicht.vorbereitung], ["Nachbereitung"])

    def test_ein_unterabschnitt_mit_zeitangabe_wandert_allein(self) -> None:
        # Etwa die Athletik je Programmpunkt: Der Abschnitt darueber hat keine
        # Zeitangabe und bleibt mit seinem uebrigen Text unter Vorbereitung.
        ansicht = self.ansicht(self.ZEILEN, nachher="""
            ## Athletik

            Nach DVV Plan 1.

            ### 0–10 Athletik zum Ankommen

            Zehn Kniebeugen.

            ### Für zu Hause

            Dehnen.

            ### 10–35 Athletik im Hauptteil

            Zwanzig Liegestütze.
        """)

        ankommen, hauptteil = ansicht.programmpunkte
        self.assertEqual(self.abschnitte(ankommen),
                         [("Athletik zum Ankommen", "Zehn Kniebeugen.")])
        self.assertEqual(self.abschnitte(hauptteil),
                         [("Athletik im Hauptteil", "Zwanzig Liegestütze.")])
        self.assertEqual([(a.ueberschrift, a.text) for a in ansicht.vorbereitung],
                         [("Athletik", "Nach DVV Plan 1. Für zu Hause Dehnen.")])

    def test_mit_hallenteil_gilt_ein_abschnitt_nur_fuer_dessen_programmpunkt(self) -> None:
        # Zwei Programmpunkte zur selben Zeit, einer je Hallenteil. Ohne
        # Hallenteil in der Ueberschrift gilt der Abschnitt fuer beide.
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
                                Zeile("10–35", "Zuspiel, Hallenteil A", "Zuspiel im Dreieck"),
                                Zeile("10–35", "Annahme, Hallenteil B", "Annahme im Halbfeld")],
                               nachher="""
            ## Hallenskizzen

            ### 10–35 Hallenteil B: Hallenskizze

            Netz quer.

            ### 10–35 Hallenteil A: Hallenskizze

            Netz längs.

            ## 10–35 Wechsel

            Nach zwölf Minuten tauschen.
        """)

        _, a, b = ansicht.programmpunkte
        self.assertEqual((a.name, b.name), ("Zuspiel, Hallenteil A", "Annahme, Hallenteil B"))
        self.assertEqual(self.abschnitte(a), [("Hallenskizze", "Netz längs."),
                                              ("Wechsel", "Nach zwölf Minuten tauschen.")])
        self.assertEqual(self.abschnitte(b), [("Hallenskizze", "Netz quer."),
                                              ("Wechsel", "Nach zwölf Minuten tauschen.")])

    def test_eine_ueberschrift_wie_die_uebung_faellt_weg(self) -> None:
        # Sonst stuende derselbe Name zweimal untereinander. Die Zeitangabe
        # faellt auch im mitgenommenen Unterabschnitt weg, mit Bindestrich
        # geschrieben wie mit Halbgeviertstrich.
        ansicht = self.ansicht([Zeile("46–93", "Hauptteil", "Drei Sechser mit Zweierserie")],
                               nachher="""
            ## 46-93 Drei Sechser mit Zweierserie

            Sechs gegen sechs.

            ### 46–93 Hallenskizze

            Netz längs.
        """)

        (punkt,) = ansicht.programmpunkte
        self.assertEqual(self.abschnitte(punkt),
                         [("", "Sechs gegen sechs. Hallenskizze Netz längs.")])

    def test_mehrere_abschnitte_stehen_in_der_reihenfolge_des_plans(self) -> None:
        # Zwischen "Heute" und dem Schaubild der Karte. Die Ueberschriften
        # sind absichtlich nicht alphabetisch.
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg", quelle="PlayDrill")
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
             Zeile("10–35", "Hauptteil", "Mit einem Bild", "ue-000030",
                   heute="Drei Längsstreifen", warum="Die Sechser stehen schon")],
            nachher="""
                ## Material gesamt

                ### 10–35 Zuerst die Annahme

                Ein Wagen Bälle.

                ## 0–10 Einspielen

                Im Paar.

                ## 10–35 Danach das Zuspiel

                Zwei Netze.
            """)

        _, hauptteil = ansicht.programmpunkte
        self.assertEqual([a.ueberschrift for a in hauptteil.abschnitte],
                         ["Zuerst die Annahme", "Danach das Zuspiel"])
        self.assertEqual(hauptteil.teile, ["Heute", "Abschnitt", "Abschnitt",
                                           "Schaubild der Karte", "Quelle und ID",
                                           "Warum hier?"])

    def test_ein_leer_gewordener_abschnitt_fehlt_unter_vorbereitung(self) -> None:
        ansicht = self.ansicht(self.ZEILEN, nachher="""
            ## Hallenskizzen

            ### 0–10 Einspielen

            Paare an der Wand.

            ### 10–35 Annahme

            Drei Streifen.

            ## Nachbereitung

            Lief gut.
        """)

        self.assertEqual([a.ueberschrift for a in ansicht.vorbereitung], ["Nachbereitung"])
        self.assertEqual([[a.ueberschrift for a in p.abschnitte] for p in ansicht.programmpunkte],
                         [["Einspielen"], ["Annahme"]])

    def test_eine_zeitangabe_ohne_programmpunkt_wird_gemeldet(self) -> None:
        # Ein Tippfehler oder eine verschobene Zeit. Der Abschnitt bleibt
        # unter Vorbereitung, damit nichts verloren geht, und die Leseansicht
        # wird trotzdem geschrieben (erzeuge prueft den Exitcode 0).
        ansicht = self.ansicht(self.ZEILEN, nachher="""
            ## 35–60 Spiel

            Sechs gegen sechs.

            ## Hallenskizzen

            ### 10–35 Hallenteil B: Hallenskizze

            Netz quer.

            ### 10–35 Annahme in Streifen

            Drei Streifen.
        """)

        self.assertEqual([(a.ueberschrift, a.text) for a in ansicht.vorbereitung],
                         [("35–60 Spiel", "Sechs gegen sechs."),
                          ("Hallenskizzen", "10–35 Hallenteil B: Hallenskizze Netz quer.")])
        spiel = self.meldungen("35–60 Spiel")
        skizze = self.meldungen("10–35 Hallenteil B: Hallenskizze")
        self.assertEqual((len(spiel), len(skizze)), (1, 1), self.konsole)
        self.assertIn("Hallenteil B", skizze[0])
        self.assertEqual(self.meldungen("Annahme in Streifen"), [])

    def test_ein_alter_plan_behaelt_alle_abschnitte_unter_vorbereitung(self) -> None:
        # Die Plaene seit September schreiben die Zeit hinten, mitten oder
        # gar nicht in die Ueberschrift. Keine davon beginnt mit ihr. Der
        # Generator schreibt keinen Text um, auch kein "siehe unten".
        ueberschriften = ["Sechs mit sich, 0–10", "Bewegungsvorbereitung, Teil 10–18",
                          "Hauptteil: Drei Sechser mit Zweierserie, 18–35",
                          "Abschluss und Runde"]
        for spalte in ("Teil", "Block"):
            with self.subTest(spalte=spalte):
                ansicht = self.ansicht(
                    [Zeile("0–10", "Ankommen", "Sechs mit sich", heute="Ablauf siehe unten"),
                     Zeile("10–18", "Bewegungsvorbereitung", "DVV Plan 1"),
                     Zeile("18–35", "Hauptteil", "Drei Sechser mit Zweierserie",
                           heute="Ablauf siehe unten"),
                     Zeile("35–40", "Abschluss", "Runde")],
                    spalte=spalte,
                    nachher="\n\n".join(f"## {u}\n\nText zu {u}." for u in ueberschriften)
                            + "\n\n**Teil 0–10: Einspielen im Kreis**")

                self.assertEqual([p.abschnitte for p in ansicht.programmpunkte], [[]] * 4)
                self.assertEqual([p.heute for p in ansicht.programmpunkte],
                                 ["Ablauf siehe unten", None, "Ablauf siehe unten", None])
                self.assertEqual([a.ueberschrift for a in ansicht.vorbereitung], ueberschriften)
                self.assertEqual(self.meldungen(*ueberschriften), [])

    def test_ein_programmpunkt_mit_uhrzeit_bekommt_keinen_abschnitt(self) -> None:
        # "18:00" ist keine Zeitangabe. Eine Ueberschrift mit Uhrzeit beginnt
        # mit keiner, und der Abschnitt bleibt ohne Meldung, wo er ist.
        ansicht = self.ansicht([Zeile("18:00", "Hauptteil", "Annahme im Halbfeld")],
                               nachher="""
            ## 18:00 Annahme im Halbfeld

            Drei Streifen.

            ## 18:00–18:30 Aufbau

            Zwei Netze.
        """)

        (punkt,) = ansicht.programmpunkte
        self.assertEqual(punkt.abschnitte, [])
        self.assertEqual([a.ueberschrift for a in ansicht.vorbereitung],
                         ["18:00 Annahme im Halbfeld", "18:00–18:30 Aufbau"])
        self.assertEqual(self.meldungen("Annahme im Halbfeld", "Aufbau"), [])


class NachschlagenTest(LeseansichtTest):
    ZEILEN = [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
              Zeile("10–35", "Hauptteil", "Annahme im Halbfeld")]

    # Ohne Einrueckung, damit ein Test weitere Abschnitte anhaengen kann.
    NACHSCHLAGEN = textwrap.dedent("""
        ## Zum Nachschlagen

        Gilt den ganzen Abend.

        ### Die Sechser

        - Herren 1 auf Feld A

        ### Kommunikationsregeln

        1. „Ich“ in der Annahme.
    """)

    def test_jede_unterueberschrift_ist_ein_reiter_und_text_davor_steht_darueber(self) -> None:
        ansicht = self.ansicht(self.ZEILEN, nachher=self.NACHSCHLAGEN)

        self.assertEqual(ansicht.nachschlagen.vorweg, "Gilt den ganzen Abend.")
        self.assertEqual([(r.name, r.text) for r in ansicht.nachschlagen.reiter],
                         [("Die Sechser", "Herren 1 auf Feld A"),
                          ("Kommunikationsregeln", "„Ich“ in der Annahme.")])

    def test_zum_nachschlagen_steht_nicht_unter_vorbereitung(self) -> None:
        ansicht = self.ansicht(self.ZEILEN,
                               nachher=self.NACHSCHLAGEN + "\n## Material gesamt\n\nBälle\n")

        self.assertEqual([(a.ueberschrift, a.text) for a in ansicht.vorbereitung],
                         [("Material gesamt", "Bälle")])
        self.assertEqual([r.name for r in ansicht.nachschlagen.reiter],
                         ["Die Sechser", "Kommunikationsregeln"])
        self.assertEqual(ansicht.knoepfe, ["Nachschlagen", "Vorbereitung"])

    def test_der_knopf_nachschlagen_steht_nur_da_wenn_es_den_abschnitt_gibt(self) -> None:
        mit = self.ansicht(self.ZEILEN, nachher=self.NACHSCHLAGEN)
        leer = self.ansicht(self.ZEILEN, nachher="## Zum Nachschlagen\n\n### Die Sechser\n")
        ohne = self.ansicht(self.ZEILEN)

        self.assertEqual(mit.knoepfe, ["Nachschlagen"])
        self.assertEqual((leer.knoepfe, leer.nachschlagen, leer.vorbereitung), ([], None, []))
        self.assertEqual((ohne.knoepfe, ohne.nachschlagen), ([], None))


class VerweisTest(LeseansichtTest):
    NACHSCHLAGEN = NachschlagenTest.NACHSCHLAGEN

    def test_ein_link_auf_einen_reiter_erscheint_beim_programmpunkt_als_verweis(self) -> None:
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar", "ue-000001",
                   heute="In den [Sechsern](#die-sechser), "
                         "[Regeln](#kommunikationsregeln) wie immer",
                   warum="Die [Sechser](#die-sechser) stehen schon zusammen"),
             Zeile("10–35", "Hauptteil", "Annahme im Halbfeld", heute="wie geplant")],
            nachher=self.NACHSCHLAGEN)

        erster, zweiter = ansicht.programmpunkte
        self.assertEqual(erster.verweise, ["Die Sechser", "Kommunikationsregeln"])
        self.assertEqual(erster.teile, ["Heute", "Quelle und ID", "Verweise", "Warum hier?"])
        self.assertEqual(zweiter.verweise, [])

    def test_der_link_im_text_fuehrt_ebenfalls_zum_reiter(self) -> None:
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar",
                   heute="In den [Sechsern](#die-sechser)")],
            nachher=self.NACHSCHLAGEN)

        (punkt,) = ansicht.programmpunkte
        self.assertEqual(punkt.links, [Link("Sechsern", "#die-sechser", "Die Sechser")])

    def test_der_anker_wird_gebildet_wie_bei_github_auch_mit_umlauten(self) -> None:
        # Klein geschrieben, Satzzeichen fallen weg, jedes Leerzeichen wird ein
        # Bindestrich. So fuehrt derselbe Link auch in der .md zum Abschnitt.
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar",
                   heute="[Läufer](#die-läufer-im-5-1-rotation) und "
                         "[Regeln](#regeln-ich--aus)")],
            nachher="""
                ## Zum Nachschlagen

                ### Die Läufer im 5-1 (Rotation)

                Der Z steht auf 1.

                ### Regeln: „Ich“ & „Aus“

                Wer den Ball nimmt, ruft.
            """)

        (punkt,) = ansicht.programmpunkte
        self.assertEqual(punkt.verweise,
                         ["Die Läufer im 5-1 (Rotation)", "Regeln: „Ich“ & „Aus“"])
        self.assertEqual([link.reiter for link in punkt.links], punkt.verweise)

    def test_ein_link_auf_etwas_anderes_bleibt_ein_gewoehnlicher_link(self) -> None:
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar",
                   heute="Wie beim [DVV](https://www.volleyball-verband.de), "
                         "Bälle siehe [Material](#material-gesamt)")],
            nachher=self.NACHSCHLAGEN + "\n## Material gesamt\n\nBälle\n")

        (punkt,) = ansicht.programmpunkte
        self.assertEqual(punkt.verweise, [])
        self.assertEqual(punkt.links,
                         [Link("DVV", "https://www.volleyball-verband.de", None),
                          Link("Material", "#material-gesamt", None)])

    def test_ein_link_in_einem_abschnitt_des_programmpunkts_wird_ein_verweis(self) -> None:
        # Auch aus den Abschnitten, die ueber ihre Zeitangabe zum
        # Programmpunkt gewandert sind (#53), mit ihren Unterabschnitten. Ein
        # Link unter Vorbereitung gehoert zu keinem Programmpunkt.
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
             Zeile("10–35", "Hauptteil", "Annahme im Halbfeld")],
            nachher=textwrap.dedent("""
                ## 10–35 Annahme in drei Streifen

                Aufstellung wie in den [Kommunikationsregeln](#kommunikationsregeln).

                ### Hallenskizze

                Die [Sechser](#die-sechser) stehen längs.

                ## Material gesamt

                Bälle für die [Sechser](#die-sechser).
            """) + self.NACHSCHLAGEN)

        ankommen, hauptteil = ansicht.programmpunkte
        self.assertEqual(hauptteil.verweise, ["Kommunikationsregeln", "Die Sechser"])
        self.assertEqual(hauptteil.teile, ["Abschnitt", "Verweise"])
        self.assertEqual(ankommen.verweise, [])


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
        # Der Text liest sich ohne Skript. Waere aus dem Plan ein Skript
        # geworden, fehlte "weg".
        self.assertEqual(ansicht.vorbereitung[0].text,
                         "Nicht <b>fett</b> & nicht <script>weg</script>")

    def test_der_text_jedes_reiters_steht_ausserhalb_von_skript(self) -> None:
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar")],
                               nachher=NachschlagenTest.NACHSCHLAGEN)

        for text in ("Gilt den ganzen Abend.", "Die Sechser", "Herren 1 auf Feld A",
                     "Kommunikationsregeln", "„Ich“ in der Annahme."):
            with self.subTest(text=text):
                self.assertIn(text, ansicht.text)

    def test_die_leseansicht_laedt_nichts_nach_und_kein_knopf_braucht_skript(self) -> None:
        # Das Skript steckt in der Datei, ohne Bibliothek und ohne Netz. Ohne
        # Skript sind Knoepfe und Verweise Links, die zum Abschnitt springen.
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg")
        ansicht = self.ansicht(
            [Zeile("0–10", "Ankommen", "Mit einem Bild", "ue-000030",
                   heute="heute [anders](#die-sechser)", warum="weil")],
            nachher=NachschlagenTest.NACHSCHLAGEN + "\n## Material gesamt\n\nBälle\n")

        self.assertEqual((ansicht.nachgeladen, ansicht.ereignisse), ([], []))
        self.assertEqual(ansicht.knoepfe, ["Nachschlagen", "Vorbereitung"])
        self.assertEqual(ansicht.programmpunkte[0].verweise, ["Die Sechser"])


class UmschalterTest(LeseansichtTest):
    """Hell, Dunkel oder System, damit der Trainer die Ansicht an die Halle anpasst.

    Was der Umschalter mit Skript tut, prueft die Abnahme im Browser (#50,
    Testing Decisions). Hier steht, was ohne Skript gilt.
    """

    def test_ohne_skript_ist_der_umschalter_verborgen(self) -> None:
        # Ein Umschalter, der nichts tut, waere schlimmer als keiner.
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar")])

        umschalter = ansicht.umschalter
        self.assertEqual((umschalter.wahl, umschalter.voreingestellt),
                         (["Hell", "Dunkel", "System"], "System"))
        self.assertFalse(umschalter.sichtbar)

    def test_ohne_skript_folgt_das_farbschema_dem_geraet(self) -> None:
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar")])

        self.assertEqual(ansicht.farbschema,
                         {"": "light", "(prefers-color-scheme:dark)": "dark"})


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

    def test_auch_im_programmpunkt_wird_die_tabelle_eine_liste(self) -> None:
        # Die Athletik je Programmpunkt, als ### mit Zeitangabe (#53).
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar")],
                               nachher="""
            ## Athletik

            ### 0–10 Athletik

            | Nr | Übung | Worauf es ankommt | Heute |
            |---|---|---|---|
            | 1 | Tiefe Hocke | Fersen bleiben am Boden | 20 s |
        """)

        (punkt,) = ansicht.programmpunkte
        (abschnitt,) = punkt.abschnitte
        ((eintrag,),) = abschnitt.listen
        self.assertEqual((eintrag.titel, eintrag.heute), ("1. Tiefe Hocke", "20 s"))
        self.assertEqual(abschnitt.tabellen, [])


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


class VergroessernTest(LeseansichtTest):
    """Hallenskizze und Schaubild lassen sich auf dem Handy vergroessern (#57).

    Das tut das Skript in einer Ansicht. Wie es sich im Browser verhaelt,
    prueft die Abnahme (#50, Testing Decisions). Hier steht, was ohne Skript
    gilt und was die Datei dafuer nicht doppelt braucht.
    """

    def test_ohne_skript_erscheint_kein_knopf_zum_vergroessern(self) -> None:
        # Ein Knopf, der nichts tut, waere schlimmer als keiner. Bild und
        # Skizze stehen trotzdem da, und der Browser zoomt wie gewohnt.
        self.ordner.lege_schaubild_an("ue-000030-aufbau.svg")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild",
                                  schaubild="ue-000030-aufbau.svg")
        ansicht = self.ansicht([Zeile("0–10", "Ankommen", "Zonenbaggern im Paar"),
                                Zeile("10–35", "Hauptteil", "Mit einem Bild", "ue-000030")],
                               nachher="""
            ## 10–35 Hallenskizze

            ```
            |  A1   A2   A3  |
            ```
        """)

        self.assertEqual(ansicht.vergroessern, [])
        self.assertIn("| A1 A2 A3 |", ansicht.text)
        self.assertEqual(len(ansicht.programmpunkte[1].schaubilder), 1)

    def test_jedes_eingebettete_schaubild_steht_genau_einmal_in_der_datei(self) -> None:
        # Die Ansicht nimmt das Bild beim Oeffnen aus dem Programmpunkt.
        # Zweimal eingebettet waere die Datei, die per WhatsApp aufs Handy
        # geht, doppelt so gross. Jedes Bild bekommt einen eigenen Inhalt,
        # sonst stuende derselbe zu Recht mehrmals da.
        namen = ["ue-000030-aufbau.svg", "ue-000031-uebersicht.svg", "ue-000031-station-1.svg"]
        for name in namen:
            self.ordner.lege_schaubild_an(name).write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg"><title>{name}</title></svg>',
                encoding="utf-8")
        self.ordner.lege_karte_an(id="ue-000030", titel="Mit einem Bild", schaubild=namen[0])
        self.ordner.lege_karte_an(id="ue-000031", titel="Zirkel mit zwei Bildern",
                                  schaubild=namen[1:])
        plan = self.ordner.lege_plan_an(PLAN, [
            Zeile("0–10", "Ankommen", "Mit einem Bild", "ue-000030"),
            Zeile("10–35", "Hauptteil", "Zirkel mit zwei Bildern", "ue-000031")])

        # Ohne --bilder: Einbetten ist der Standard.
        fertig = self.ordner.starte("leseansicht.py", str(plan), mit_wurzel=False)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        seite = plan.with_suffix(".html").read_text(encoding="utf-8")
        for name in namen:
            with self.subTest(name=name):
                datei = self.ordner.pfad / "schaubilder" / name
                self.assertEqual(wie_oft_eingebettet(seite, datei), 1)


class GesperrtTest(LeseansichtTest):
    """Eine Leseansicht, die sich nicht schreiben laesst, wird gemeldet (#75).

    Bei der Abnahme von 1d war eine Leseansicht gesperrt: Der Nextcloud-Client
    setzt einen Verweigern-Eintrag in die Dateirechte, wenn die Datei auf dem
    Server kein Schreibrecht hat. `leseansicht.py` brach mit einem Traceback
    ab. Hier steht dafuer eine schreibgeschuetzte Datei, die laesst sich auf
    jedem Rechner mit os.chmod herstellen.

    Jeder Test gilt fuer das Ziel neben dem Plan und fuer eins aus `--out`.
    """

    ALT = "<p>Die Leseansicht vom letzten Erzeugen</p>"

    def gesperrt(self) -> list[tuple[Path, int, str]]:
        """Erzeugt die Leseansicht eines Plans in eine gesperrte Datei, je Ziel einmal.

        Vorher steht in der Datei ALT. Zurueck kommen je Ziel die Datei, der
        Exitcode und die ganze Ausgabe des Aufrufs.
        """
        plan = self.ordner.lege_plan_an(PLAN, [Zeile("0–10", "Ankommen", "Zonenbaggern im Paar")])
        aus_out = self.ordner.pfad / "handy" / "training.html"
        laeufe = []
        for ziel, argumente in ((plan.with_suffix(".html"), []),
                                (aus_out, ["--out", str(aus_out)])):
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(self.ALT, encoding="utf-8")
            ziel.chmod(0o444)
            # Unter Windows raeumt rmtree eine schreibgeschuetzte Datei nicht weg.
            self.addCleanup(ziel.chmod, 0o666)
            fertig = self.ordner.starte("leseansicht.py", str(plan), *argumente,
                                        mit_wurzel=False)
            laeufe.append((ziel, fertig.returncode, fertig.stdout + fertig.stderr))
        return laeufe

    def test_der_aufruf_endet_ohne_traceback_und_nicht_mit_null(self) -> None:
        for ziel, exitcode, ausgabe in self.gesperrt():
            with self.subTest(ziel=ziel.name):
                self.assertNotEqual(exitcode, 0)
                self.assertNotIn("Traceback", ausgabe)

    def test_die_meldung_nennt_die_datei_mit_pfad(self) -> None:
        for ziel, _, ausgabe in self.gesperrt():
            with self.subTest(ziel=ziel.name):
                self.assertIn(str(ziel), ausgabe)

    def test_die_gesperrte_datei_bleibt_wie_sie_war(self) -> None:
        # Die Rechte fasst das Skript nicht an, auch nicht, um doch noch zu
        # schreiben.
        for ziel, _, _ in self.gesperrt():
            with self.subTest(ziel=ziel.name):
                self.assertEqual(ziel.read_text(encoding="utf-8"), self.ALT)


if __name__ == "__main__":
    unittest.main()
