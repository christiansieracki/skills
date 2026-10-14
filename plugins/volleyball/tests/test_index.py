"""Prueft `index.py` gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

`index.py` ist der Linter und baut mit `--md` zugleich die Lesebrille
`index.md`. Geprueft wird, was auf der Konsole ankommt und was in der Datei
steht: das ist es, was ein Skill und ein Mensch zu sehen bekommen, und damit
der Vertrag.
Eine interne Pruefroutine direkt aufzurufen hiesse, ihre Verdrahtung
nachzubauen. Der Test braeche dann beim ersten Umbau, ohne dass sich das
Verhalten geaendert haette.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from arbeitsordner import OHNE, Arbeitsordner, auffaelligkeiten


# Der Text einer Wissenskarte, der einen der beiden Abschnitte nicht hat.
NUR_KERNAUSSAGEN = """
    ## Kernaussagen

    - Steht da.
"""
NUR_TRAINING = """
    ## Was das fürs Training heißt

    - Steht da.
"""

# Der Text einer Wissenskarte mit einem Bild an der Kernaussage, wie
# DATENMODELL.md ihn zeigt. `{bild}` ist der Name unter schaubilder/.
MIT_BILD = """
    ## Kernaussagen

    - Eine Bildreihe zeigt es.

      ![Bildreihe](../schaubilder/{bild})

    ## Was das fürs Training heißt

    - Steht da.
"""


def disziplin_zu(index_md: str, uebung_id: str) -> set[str]:
    """Die Disziplinzelle jeder Tabellenzeile, die zu einer Uebung gehoert.

    Eine Uebung steht in so vielen Tabellen, wie sie Elemente hat. In allen
    muss dasselbe stehen, deshalb eine Menge: bleibt sie einelementig, sind
    sich die Zeilen einig.
    """
    zellen = set()
    for zeile in index_md.splitlines():
        if zeile.startswith("|") and f"{uebung_id}-" in zeile:
            zellen.add(zeile.split("|")[2].strip())
    return zellen


class LinterTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_sauberer_arbeitsordner_meldet_nichts(self) -> None:
        fertig = self.ordner.starte("index.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        # Zeigt zugleich, dass der Fixture ueberhaupt gelesen wurde: ein leerer
        # Ordner waere ebenfalls ohne Auffaelligkeit.
        self.assertIn(f"Übungen: {len(self.ordner.ids)}", fertig.stdout)
        self.assertEqual(auffaelligkeiten(fertig.stdout), [])
        self.assertIn("Keine Auffälligkeiten", fertig.stdout)

    def test_unbekannter_schwerpunkt_wird_gemeldet(self) -> None:
        self.ordner.lege_karte_an(
            id="ue-000009",
            titel="Karte mit erfundenem Schwerpunkt",
            schwerpunkt=["gibt-es-nicht"],
        )

        fertig = self.ordner.starte("index.py")

        gemeldet = auffaelligkeiten(fertig.stdout)
        self.assertEqual(len(gemeldet), 1, fertig.stdout)
        self.assertIn("ue-000009", gemeldet[0])
        self.assertIn("gibt-es-nicht", gemeldet[0])

    def test_fehlende_disziplin_wird_gemeldet(self) -> None:
        # Das ist der Fall, fuer den es keinen stillen Default gibt: eine Karte,
        # bei der das Feld beim Import vergessen wurde.
        self.ordner.lege_karte_an(
            id="ue-000010", titel="Karte ganz ohne Disziplin", disziplin=OHNE,
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000010", gemeldet[0])
        self.assertIn("disziplin", gemeldet[0])

    def test_leere_disziplin_wird_gemeldet(self) -> None:
        self.ordner.lege_karte_an(
            id="ue-000011", titel="Karte mit leerer Disziplinliste", disziplin=[],
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000011", gemeldet[0])
        self.assertIn("disziplin", gemeldet[0])

    def test_unbekannte_disziplin_wird_gemeldet(self) -> None:
        # Ein Tippfehler macht die Karte sonst unauffindbar: kein Filter trifft
        # sie mehr.
        self.ordner.lege_karte_an(
            id="ue-000012", titel="Karte mit erfundener Disziplin", disziplin=["strand"],
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000012", gemeldet[0])
        self.assertIn("strand", gemeldet[0])

    def test_disziplin_als_einzelwert_wird_gemeldet(self) -> None:
        # `disziplin: halle` statt `disziplin: [halle]`. Ohne eigene Pruefung
        # liefe die Wertepruefung ueber die Buchstaben und meldete fuenfmal.
        self.ordner.lege_karte_an(
            id="ue-000013", titel="Karte mit Disziplin ohne Klammern", disziplin="halle",
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000013", gemeldet[0])
        self.assertIn("disziplin", gemeldet[0])

    def test_hallenkarte_mit_beachschwerpunkt_wird_gemeldet(self) -> None:
        # Der Fall aus dem Ticket: die Karte ist fuer die Halle, der
        # Schwerpunkt gilt laut Liste nur fuer den Sand. Eins von beidem ist
        # falsch, und ohne Meldung laeuft die Zuordnung still auseinander.
        self.ordner.lege_karte_an(
            id="ue-000015",
            titel="Hallenkarte mit Beachschwerpunkt",
            disziplin=["halle"],
            schwerpunkt=["nur-beach"],
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000015", gemeldet[0])
        self.assertIn("nur-beach", gemeldet[0])

    def test_beachkarte_mit_hallenschwerpunkt_wird_gemeldet(self) -> None:
        # Spiegelbildlich, damit die Regel nicht nur in eine Richtung greift:
        # laufwege-rotation meint 5-1 und 6-2, die gibt es im Sand nicht.
        self.ordner.lege_karte_an(
            id="ue-000016",
            titel="Beachkarte mit Hallenschwerpunkt",
            disziplin=["beach"],
            schwerpunkt=["laufwege-rotation"],
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000016", gemeldet[0])
        self.assertIn("laufwege-rotation", gemeldet[0])

    def test_beachkarte_mit_beachschwerpunkt_meldet_nichts(self) -> None:
        self.ordner.lege_karte_an(
            id="ue-000017",
            titel="Beachkarte mit Beachschwerpunkt",
            disziplin=["beach"],
            schwerpunkt=["nur-beach"],
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_karte_fuer_beide_mit_hallenschwerpunkt_meldet_nichts(self) -> None:
        # Eine Disziplin der Karte reicht. Sonst koennte eine Karte fuer beides
        # nie einen Schwerpunkt tragen, den es nur in einer Disziplin gibt.
        self.ordner.lege_karte_an(
            id="ue-000018",
            titel="Karte für beides mit Hallenschwerpunkt",
            disziplin=["halle", "beach"],
            schwerpunkt=["laufwege-rotation"],
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_kennung_ohne_disziplinspalte_bleibt_erlaubt(self) -> None:
        # Die Steuerungsschwerpunkte tragen keine Disziplinspalte. Liest der
        # Parser nur noch dreispaltige Zeilen, fallen sie aus der erlaubten
        # Menge und die bestehende Pruefung meldete sie als unbekannt.
        self.ordner.lege_karte_an(
            id="ue-000019",
            titel="Karte mit Schwerpunkt ohne Disziplinspalte",
            schwerpunkt=["standortbestimmung"],
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_vertippte_disziplin_in_schwerpunkte_md_wird_gemeldet(self) -> None:
        # Die Datei wird von Hand gepflegt. Faellt ein Tippfehler in der
        # Disziplinspalte still auf "beide" zurueck, ist genau die Pruefung
        # aus, um die es hier geht, und niemand merkt es.
        self.ordner.ergaenze_schwerpunkt("vertippt", "Halle")

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("schwerpunkte.md", gemeldet[0])
        self.assertIn("vertippt", gemeldet[0])

    def test_leere_disziplinspalte_meldet_nichts(self) -> None:
        # Die leere Zelle ist der zugesagte Rueckfall, der Tippfehler ist es
        # nicht. Ohne diesen Test waere beides dasselbe.
        self.ordner.ergaenze_schwerpunkt("ohne-angabe", "")

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_toter_schaubild_verweis_wird_gemeldet(self) -> None:
        # Der Fall aus dem Ticket, und zwar der haeufige: der Ordner steht, nur
        # diese eine Datei ist umbenannt oder geloescht worden.
        self.ordner.lege_schaubild_an("ue-000020-alter-name.svg")
        self.ordner.lege_karte_an(
            id="ue-000020",
            titel="Karte mit totem Schaubild-Verweis",
            schaubild="gibt-es-nicht.svg",
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000020", gemeldet[0])
        self.assertIn("gibt-es-nicht.svg", gemeldet[0])

    def test_vorhandenes_schaubild_meldet_nichts(self) -> None:
        self.ordner.lege_schaubild_an("ue-000021-aufbau.svg")
        self.ordner.lege_karte_an(
            id="ue-000021",
            titel="Karte mit vorhandenem Schaubild",
            schaubild="ue-000021-aufbau.svg",
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_eine_liste_von_schaubildern_meldet_nichts_wenn_jedes_da_ist(self) -> None:
        # Ein Zirkel aus Uebersichtsblatt und Stationsblaettern traegt je
        # Blatt ein Bild (#39).
        for name in ("ue-000023-zirkel-1.png", "ue-000023-zirkel-2.png"):
            self.ordner.lege_schaubild_an(name)
        self.ordner.lege_karte_an(
            id="ue-000023", titel="Zirkel mit zwei Bildern",
            schaubild=["ue-000023-zirkel-1.png", "ue-000023-zirkel-2.png"],
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_aus_einer_liste_wird_genau_das_fehlende_schaubild_gemeldet(self) -> None:
        # Die beiden anderen sind da. Die Meldung nennt das fehlende allein,
        # sonst sucht der Trainer unter drei Namen nach dem einen.
        for name in ("ue-000024-zirkel-1.png", "ue-000024-zirkel-3.png"):
            self.ordner.lege_schaubild_an(name)
        self.ordner.lege_karte_an(
            id="ue-000024", titel="Zirkel mit einem fehlenden Bild",
            schaubild=["ue-000024-zirkel-1.png", "ue-000024-zirkel-2.png",
                       "ue-000024-zirkel-3.png"],
        )

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-000024", gemeldet[0])
        self.assertIn("ue-000024-zirkel-2.png", gemeldet[0])
        self.assertNotIn("zirkel-1", gemeldet[0])
        self.assertNotIn("zirkel-3", gemeldet[0])

    def test_karte_ohne_schaubild_meldet_nichts(self) -> None:
        # Das Feld ist optional. Die Standardkarten fuehren es leer, hier fehlt
        # es ganz. Beide Schreibweisen duerfen nichts ausloesen.
        self.ordner.lege_karte_an(
            id="ue-000022", titel="Karte ganz ohne Schaubild", schaubild=OHNE,
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_karte_fuer_halle_und_beach_meldet_nichts(self) -> None:
        self.ordner.lege_karte_an(
            id="ue-000014", titel="Karte für beide Disziplinen", disziplin=["halle", "beach"],
        )

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_vierstellige_id_auf_einer_karte_wird_mit_hinweis_gemeldet(self) -> None:
        # Seit 3.0.0 gilt nur das sechsstellige Format (ADR-0011). Eine Karte,
        # die noch vierstellig heisst, kommt aus einem Ordner, der nicht
        # umgestellt ist. Die Meldung sagt, womit das geht.
        self.ordner.lege_karte_an(id="ue-0042", titel="Karte von vor der Umstellung")

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("ue-0042", gemeldet[0])
        self.assertIn("ids_umstellen.py", gemeldet[0])

    def test_trainingsplan_mit_sechsstelliger_id_meldet_nichts(self) -> None:
        self.ordner.lege_trainingsplan_an("gruppe/2026-09-15.md", "ue-000001", "ue-000003")

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_vierstellige_id_in_einem_trainingsplan_wird_mit_hinweis_gemeldet(self) -> None:
        # Den sah bisher niemand: `verwendet` sammelt nur, was zum Muster
        # passt, und eine vierstellige ID fiel still heraus. Der Plan zeigte
        # dann auf keine Uebung, und die Einsatzhistorie fehlte.
        self.ordner.lege_trainingsplan_an("gruppe/2026-09-15.md", "ue-000001", "ue-0003")

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("trainings/gruppe/2026-09-15.md", gemeldet[0])
        self.assertIn("ue-0003", gemeldet[0])
        self.assertIn("ids_umstellen.py", gemeldet[0])


class WissenskarteTest(unittest.TestCase):
    """Der Linter liest `wissen/` neben `uebungen/` (#66).

    Die Regeln stehen in DATENMODELL.md unter "Die Wissenskarte". Jede Regel
    meldet ihre Karte genau einmal, mit der Datei vorn wie bei der Uebung.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_gueltige_wissenskarten_melden_nichts(self) -> None:
        # Eine mit Bild an der Kernaussage und Uebungen, eine fuer den Sand
        # mit einem Steuerungsschwerpunkt, der keine Disziplinspalte hat und
        # damit fuer beide gilt, und eine ganz ohne `schwerpunkt` und
        # `uebungen`: Ein Beitrag ueber Schlaf hat keine Kennung.
        self.ordner.lege_schaubild_an("wi-000001-bildreihe.png")
        self.ordner.lege_wissenskarte_an(
            id="wi-000001", thema=["technik", "methodik"], disziplin=["halle", "beach"],
            uebungen=["ue-000001", "ue-000004"],
            rumpf=MIT_BILD.format(bild="wi-000001-bildreihe.png"))
        self.ordner.lege_wissenskarte_an(
            id="wi-000002", titel="Wie steuert man die Belastung im Sand?",
            thema=["trainingslehre"], disziplin=["beach"], schwerpunkt=["standortbestimmung"])
        self.ordner.lege_wissenskarte_an(
            id="wi-000003", titel="Was hat Schlaf mit der Reaktion zu tun?",
            thema=["physiologie"], schwerpunkt=OHNE, uebungen=OHNE)

        fertig = self.ordner.starte("index.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_eine_id_ausserhalb_des_musters_wird_gemeldet(self) -> None:
        self.ordner.lege_wissenskarte_an(id="wi-0042")

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("wi-0042", gemeldet[0])
        self.assertIn("wi-######", gemeldet[0])

    def test_ein_dateiname_ohne_die_id_vorn_wird_gemeldet(self) -> None:
        karte = self.ordner.lege_wissenskarte_an(id="wi-000031")
        karte.rename(karte.with_name("wi-000032-umbenannt.md"))

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertTrue(gemeldet[0].startswith("wissen/wi-000032-umbenannt.md: "), gemeldet[0])
        self.assertIn("wi-000031", gemeldet[0])

    def test_eine_doppelte_id_wird_gemeldet(self) -> None:
        # Ein Trainer an zwei Rechnern, bevor Nextcloud abgleicht.
        self.ordner.lege_wissenskarte_an(id="wi-000033", titel="Die eine Frage?")
        self.ordner.lege_wissenskarte_an(id="wi-000033", titel="Die andere Frage?")

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("wi-000033", gemeldet[0])
        self.assertIn("gibt es schon", gemeldet[0])

    def test_eine_karte_im_ordner_der_anderen_sorte_wird_einmal_gemeldet(self) -> None:
        # Eine Uebungskarte in wissen/ und eine Wissenskarte in uebungen/,
        # beide fuer sich richtig. Mit den Regeln des falschen Ordners
        # geprueft, meldete jede jedes Feld der anderen Sorte. Die eine
        # Meldung sagt, wohin sie gehoert.
        wissen = self.ordner.lege_wissenskarte_an(id="wi-000041")
        wissen.rename(self.ordner.pfad / "uebungen" / wissen.name)
        self.ordner.lege_karte_an(id="ue-000040", titel="Übung unter dem Wissen")
        uebung = next((self.ordner.pfad / "uebungen").glob("ue-000040-*.md"))
        uebung.rename(self.ordner.pfad / "wissen" / uebung.name)

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 2, gemeldet)
        (in_wissen,) = [z for z in gemeldet if z.startswith("wissen/ue-000040-")]
        (in_uebungen,) = [z for z in gemeldet if z.startswith("uebungen/wi-000041-")]
        self.assertIn("uebungen/", in_wissen.split(": ", 1)[1])
        self.assertIn("wissen/", in_uebungen.split(": ", 1)[1])

    def test_jede_regel_meldet_ihre_karte_genau_einmal(self) -> None:
        # Je Regel eine Karte mit genau diesem einen Fehler, alle in einem
        # Arbeitsordner und einem Lauf. Ein Lauf je Regel kostete jedes Mal
        # einen Arbeitsordner und einen Interpreter.
        faelle = {
            "wi-000011": ({"titel": "Ein Titel ohne Fragezeichen"}, "Ein Titel ohne Fragezeichen"),
            "wi-000012": ({"thema": OHNE}, "thema"),
            "wi-000013": ({"thema": []}, "thema"),
            "wi-000014": ({"thema": ["technik", "geschichte"]}, "geschichte"),
            # `thema: technik` statt `thema: [technik]`. Ohne eigene Pruefung
            # liefe die Wertepruefung ueber die Buchstaben.
            "wi-000015": ({"thema": "technik"}, "thema"),
            # Pflicht und ohne Vorgabe, wie bei der Uebungskarte: Wissen nur
            # ueber den Sand soll nicht still bei der Halle landen.
            "wi-000016": ({"disziplin": OHNE}, "disziplin"),
            "wi-000017": ({"disziplin": []}, "disziplin"),
            "wi-000018": ({"disziplin": ["halle", "strand"]}, "strand"),
            "wi-000019": ({"schwerpunkt": ["gibt-es-nicht"]}, "gibt-es-nicht"),
            # Eine inhaltliche Kennung, die in keiner Disziplin der Karte gilt.
            "wi-000020": ({"disziplin": ["halle"], "schwerpunkt": ["nur-beach"]}, "nur-beach"),
            "wi-000021": ({"quelle": ""}, "quelle"),
            "wi-000022": ({"quelle": OHNE}, "quelle"),
            # ue-000001 gibt es, ue-000099 nicht. Gemeldet wird die eine.
            "wi-000023": ({"uebungen": ["ue-000001", "ue-000099"]}, "ue-000099"),
            "wi-000024": ({"rumpf": NUR_TRAINING}, "## Kernaussagen"),
            "wi-000025": ({"rumpf": NUR_KERNAUSSAGEN}, "## Was das fürs Training heißt"),
            "wi-000026": ({"rumpf": MIT_BILD.format(bild="wi-000026-gibt-es-nicht.png")},
                          "../schaubilder/wi-000026-gibt-es-nicht.png"),
        }
        for uid, (felder, _) in faelle.items():
            self.ordner.lege_wissenskarte_an(id=uid, **felder)

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        for uid, (felder, stichwort) in faelle.items():
            with self.subTest(karte=uid, felder=felder):
                zur_karte = [z for z in gemeldet if z.startswith(f"wissen/{uid}-")]
                self.assertEqual(len(zur_karte), 1, gemeldet)
                self.assertIn(stichwort, zur_karte[0])
        self.assertEqual(len(gemeldet), len(faelle), gemeldet)


class WissenImIndexTest(unittest.TestCase):
    """Der Index fuehrt die Wissenskarten unter eigenem Schluessel (#67).

    Welche Wissenskarten auf eine Uebung zeigen, pflegt niemand auf der
    Uebungskarte. Der Index rechnet es aus den `uebungen` der Wissenskarten
    aus. Gelesen wird die index.json, deren Pfad `index.py --still` nennt.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def index(self) -> dict:
        fertig = self.ordner.starte("index.py", "--still")
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        return json.loads(Path(fertig.stdout.strip()).read_text(encoding="utf-8"))

    def test_der_index_nennt_jede_wissenskarte_und_bei_der_uebung_die_die_auf_sie_zeigen(
            self) -> None:
        # Zwei Karten zeigen auf ue-000001, eine davon auch auf ue-000004, die
        # dritte auf keine Uebung. Die uebrigen Uebungen tragen nichts.
        self.ordner.lege_wissenskarte_an(id="wi-000001", uebungen=["ue-000001", "ue-000004"])
        self.ordner.lege_wissenskarte_an(id="wi-000002", titel="Die zweite Frage?",
                                         uebungen=["ue-000001"])
        self.ordner.lege_wissenskarte_an(id="wi-000003", titel="Die Frage ohne Übung?",
                                         uebungen=OHNE)

        index = self.index()

        self.assertEqual(sorted(k["id"] for k in index["wissen"]),
                         ["wi-000001", "wi-000002", "wi-000003"])
        self.assertEqual({e["id"]: e["hintergrund"] for e in index["uebungen"]}, {
            "ue-000001": ["wi-000001", "wi-000002"],
            "ue-000002": [],
            "ue-000003": [],
            "ue-000004": ["wi-000001"],
            "ue-000005": [],
        })

    def test_die_konsole_zaehlt_die_wissenskarten_neben_den_uebungen(self) -> None:
        # Wie "Übungen: n" zeigt die Zahl, dass wissen/ ueberhaupt gelesen
        # wurde: ein Lauf ohne den Ordner meldete ebenfalls nichts.
        self.ordner.lege_wissenskarte_an(id="wi-000001")
        self.ordner.lege_wissenskarte_an(id="wi-000002", titel="Die zweite Frage?")

        fertig = self.ordner.starte("index.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertIn(f"Übungen: {len(self.ordner.ids)}\n", fertig.stdout)
        self.assertIn("Wissenskarten: 2\n", fertig.stdout)


class SzenenTest(unittest.TestCase):
    """Die Szenen in `schaubilder/`, gelesen und nicht gezeichnet (#47)."""

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_eine_szene_mit_fehler_wird_mit_datei_und_grund_gemeldet(self) -> None:
        self.ordner.lege_szene_an("ue-000030", """
            form: halle
            spieler:
              - bei: 9
        """)
        self.ordner.lege_schaubild_an("ue-000030.svg")

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("schaubilder/ue-000030.szene.yml", gemeldet[0])
        # Der Grund ist der des Lesers, so wie schaubild.py ihn auch nennt.
        self.assertIn("Spieler 1: 9 ist keine Position", gemeldet[0])

    def test_ein_bild_aelter_als_seine_szene_wird_gemeldet_und_nach_dem_neuzeichnen_nicht_mehr(
            self) -> None:
        szene = self.ordner.lege_szene_an("ue-000031", "form: halle")
        bild = self.ordner.lege_schaubild_an("ue-000031.svg")
        # Die Szene ist nach dem Bild geaendert worden, eine Stunde spaeter.
        stand = bild.stat().st_mtime
        os.utime(bild, (stand - 3600, stand - 3600))

        vorher = auffaelligkeiten(self.ordner.starte("index.py").stdout)
        gezeichnet = self.ordner.starte("schaubild.py", "ue-000031")
        nachher = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(gezeichnet.returncode, 0, gezeichnet.stdout)

        self.assertEqual(len(vorher), 1, vorher)
        self.assertIn(szene.relative_to(self.ordner.pfad).as_posix(), vorher[0])
        self.assertIn("ue-000031.svg", vorher[0])
        # Der Aufruf, der es behebt, steht in der Meldung.
        self.assertIn("schaubild.py ue-000031", vorher[0])
        self.assertEqual(nachher, [])

    def test_eine_szene_ohne_bild_wird_gemeldet(self) -> None:
        self.ordner.lege_szene_an("ue-000032-2", "form: beach")

        fertig = self.ordner.starte("index.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        gemeldet = auffaelligkeiten(fertig.stdout)
        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("schaubilder/ue-000032-2.szene.yml", gemeldet[0])
        self.assertIn("ue-000032-2.svg", gemeldet[0])
        self.assertIn("schaubild.py ue-000032-2", gemeldet[0])

    def test_eine_szene_mit_juengerem_bild_meldet_nichts(self) -> None:
        # Die Reihenfolge, in der volleyball-schaubild beide schreibt: erst
        # die Szene, dann das Bild aus ihr.
        self.ordner.lege_szene_an("ue-000033", "form: halle")
        gezeichnet = self.ordner.starte("schaubild.py", "ue-000033")

        fertig = self.ordner.starte("index.py")

        self.assertEqual(gezeichnet.returncode, 0, gezeichnet.stdout)
        self.assertEqual(auffaelligkeiten(fertig.stdout), [])


class KonfliktkopienTest(unittest.TestCase):
    """Konfliktkopien von Nextcloud, irgendwo im Arbeitsordner (#47).

    Welche Namen der Client schreibt, steht in DATENMODELL.md unter
    "Konfliktkopien".
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_eine_konfliktkopie_irgendwo_im_arbeitsordner_wird_gemeldet(self) -> None:
        schwerpunkte = self.ordner.pfad / "schwerpunkte.md"
        uebersicht = self.ordner.lege_quellenordner_an(
            "playdrill", [{"kandidat": 1, "dateien": ["a.pdf"]}])
        plan = self.ordner.lege_trainingsplan_an("gruppe/2026-09-15.md", "ue-000001")
        erste = self.ordner.lege_konfliktkopie_an(
            plan, " (conflicted copy anna 2026-10-03 101500)")
        kopien = {
            self.ordner.lege_konfliktkopie_an(schwerpunkte): schwerpunkte,
            # So hiessen sie bei aelteren Clients, hier unter quellen/.
            self.ordner.lege_konfliktkopie_an(uebersicht, "_conflict-20261003-101500"):
                uebersicht,
            erste: plan,
            # Die Kopie einer Kopie gehoert zur ersten Kopie, wie beim Client.
            self.ordner.lege_konfliktkopie_an(erste): erste,
        }

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), len(kopien), gemeldet)
        for kopie, original in kopien.items():
            name = kopie.relative_to(self.ordner.pfad).as_posix()
            with self.subTest(name=name):
                (zeile,) = [z for z in gemeldet if z.startswith(f"{name}: ")]
                self.assertIn("Konfliktkopie", zeile)
                # Womit sie zusammenzufuehren ist, steht dabei.
                self.assertIn(original.name, zeile.removeprefix(name))

    def test_ein_name_in_anderer_schreibung_wird_zum_umbenennen_gemeldet(self) -> None:
        # Zwei Dateien auf dem Server, deren Namen sich nur in Gross- und
        # Kleinschreibung unterscheiden. Unter Windows hat nur eine Platz,
        # die andere legt der Client unter neuem Namen ab. Zusammenzufuehren
        # ist da nichts, es sind zwei verschiedene Dateien.
        bild = self.ordner.lege_schaubild_an("ue-000001.svg")
        kopie = self.ordner.lege_konfliktkopie_an(bild, " (case clash from 2026-10-03 101500)")

        gemeldet = auffaelligkeiten(self.ordner.starte("index.py").stdout)

        self.assertEqual(len(gemeldet), 1, gemeldet)
        name = f"schaubilder/{kopie.name}"
        self.assertTrue(gemeldet[0].startswith(f"{name}: "), gemeldet[0])
        self.assertIn("ue-000001.svg", gemeldet[0].removeprefix(name))
        self.assertIn("umbenennen", gemeldet[0])
        self.assertNotIn("zusammenfuehren", gemeldet[0])

    def test_ein_name_mit_conflict_ohne_die_marke_des_clients_meldet_nichts(self) -> None:
        # Der Client selbst saehe hier `_conflict-` und hielte die Datei fuer
        # eine Konfliktkopie. Geschrieben hat er so einen Namen nie: Zur Marke
        # gehoeren Datum und Uhrzeit.
        self.ordner.lege_quelldatei_an("artikel/team_conflict-loesen.pdf", b"")

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [])

    def test_die_konfliktkopie_einer_karte_ist_keine_zweite_karte(self) -> None:
        # Sonst stuende dieselbe Uebung zweimal in der Suche, und der Linter
        # meldete zu der einen Ursache dazu die doppelte ID.
        self.ordner.lege_konfliktkopie_an(
            next((self.ordner.pfad / "uebungen").glob("ue-000001-*.md")))

        fertig = self.ordner.starte("index.py")

        self.assertIn(f"Übungen: {len(self.ordner.ids)}", fertig.stdout)
        gemeldet = auffaelligkeiten(fertig.stdout)
        self.assertEqual(len(gemeldet), 1, gemeldet)
        self.assertIn("Konfliktkopie", gemeldet[0])


class IndexMdTest(unittest.TestCase):
    """Die Lesebrille `index.md`, gebaut mit `--md`.

    Sie zeigt die Bibliothek ungefiltert. Deshalb muss an jeder Zeile stehen,
    fuer welche Disziplin die Uebung gedacht ist. Sonst steht eine Beachuebung
    ununterscheidbar zwischen den Hallenuebungen, und das ist genau der Fall,
    den der Disziplinfilter in der Suche verhindern soll.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def baue(self) -> str:
        fertig = self.ordner.starte("index.py", "--md")
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        return (self.ordner.pfad / "index.md").read_text(encoding="utf-8")

    def test_ohne_md_entsteht_keine_index_md(self) -> None:
        # Die Wurzeldatei stellt den Neubau auf ausdrueckliche Ansage. Ein Lauf
        # ohne das Flag darf die Datei deshalb nicht anfassen.
        fertig = self.ordner.starte("index.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertFalse((self.ordner.pfad / "index.md").exists())

    def test_die_uebungstabelle_fuehrt_eine_disziplinspalte(self) -> None:
        self.assertIn(
            "| Übung | Disziplin | Level | Spieler | Dauer | Zuletzt |", self.baue()
        )

    def test_die_beachkarte_ist_in_der_tabelle_zu_erkennen(self) -> None:
        self.assertEqual(disziplin_zu(self.baue(), "ue-000004"), {"beach"})

    def test_die_hallenkarte_ist_in_der_tabelle_zu_erkennen(self) -> None:
        self.assertEqual(disziplin_zu(self.baue(), "ue-000001"), {"halle"})

    def test_die_karte_fuer_beide_zeigt_beide_werte(self) -> None:
        self.assertEqual(disziplin_zu(self.baue(), "ue-000005"), {"halle, beach"})


if __name__ == "__main__":
    unittest.main()
