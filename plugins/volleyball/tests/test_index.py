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

import unittest

from arbeitsordner import OHNE, Arbeitsordner, auffaelligkeiten


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
