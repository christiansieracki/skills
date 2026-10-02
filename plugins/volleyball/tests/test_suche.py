"""Prueft die Suche gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Gesucht wird ueber die Kommandozeile und mit `--json`, so wie ein Skill es
tut, der die Treffer weiterverarbeitet. Die Zusagen, die hier festgehalten
werden, sind die, die sich am leichtesten unbemerkt verlieren: dass
`--spieler` die Anwesenden meint und keine Obergrenze, dass zu wenige
Spielflaechen eine Uebung wirklich herausfallen lassen, und was der
Disziplinfilter durchlaesst. Am letzten haengt, ob beim Planen einer
Beacheinheit eine Hallenuebung im Ergebnis steht.
"""

from __future__ import annotations

import json
import socket
import unittest

from arbeitsordner import Arbeitsordner

# Ein Trainer, der an einem anderen Rechner sitzt als dem, auf dem der Test
# laeuft.
TRAINER_ANDERER_RECHNER = {"anderer": {"nummer": "00", "rechner": ["ANDERER-RECHNER"]}}


class SucheTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def treffer(self, *argumente: str) -> list[dict]:
        """Sucht und gibt die maschinenlesbare Ausgabe zurueck.

        `json.loads` ist hier die eigentliche Zusicherung: die Ausgabe laesst
        sich ohne Textparserei auswerten.
        """
        fertig = self.ordner.starte("suche.py", "--json", *argumente)
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        return json.loads(fertig.stdout)

    def quelldateizeile(self, uid: str, vorhanden: tuple[str, ...] = (),
                        **felder) -> str:
        """Legt eine Karte an und gibt ihre Quelldatei-Zeile zurueck.

        Die Faelle weiter unten unterscheiden sich darin, wie die
        `quelldatei:` auf der Karte geschrieben ist und welche Dateien unter
        `quellen/` liegen, und pruefen alle dieselbe eine Zeile. `vorhanden`
        nennt diese Dateien relativ zu `quellen/`. Ihr Inhalt zaehlt nicht,
        nur dass es sie gibt.
        """
        for name in vorhanden:
            self.ordner.lege_quelldatei_an(name, b"")
        self.ordner.lege_karte_an(id=uid, **felder)
        fertig = self.ordner.starte("suche.py", "--id", uid, "--lang")
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        zeilen = [z for z in fertig.stdout.splitlines() if "Quelldatei" in z]
        self.assertEqual(1, len(zeilen), f"keine Quelldatei-Zeile:\n{fertig.stdout}")
        return zeilen[0]

    def test_ohne_filter_kommen_alle_uebungen_zurueck(self) -> None:
        # Der Fixture traegt Karten beider Disziplinen. Der Test haelt damit
        # auch fest, dass ohne Disziplinfilter alles zurueckkommt.
        gefunden = self.treffer()

        self.assertEqual(sorted(e["id"] for e in gefunden), sorted(self.ordner.ids))

    def test_jeder_treffer_traegt_die_felder_seiner_karte(self) -> None:
        (gefunden,) = self.treffer("--id", "ue-000003")

        self.assertEqual(gefunden["titel"], "Sideout-Serie über zwei Spielflächen")
        self.assertEqual(gefunden["element"], ["annahme", "angriff"])
        # Steht `disziplin` nicht in der Index-Projektion, erreicht das Feld die
        # Suche gar nicht, egal wie sauber es auf der Karte gepflegt ist.
        self.assertEqual(gefunden["disziplin"], ["halle"])
        self.assertEqual(gefunden["spielflaechen"], 2)
        self.assertEqual(gefunden["spieler_max"], 16)
        self.assertIs(gefunden["netz"], True)

    def test_zu_wenige_spielflaechen_lassen_die_uebung_herausfallen(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--spielflaechen", "1")]

        self.assertNotIn("ue-000003", gefunden)  # braucht zwei
        self.assertIn("ue-000002", gefunden)     # kommt mit einem aus

    def test_mehr_anwesende_als_die_obergrenze_bleiben_ein_treffer(self) -> None:
        # ue-000002 ist fuer hoechstens vier Spieler gedacht. Bei zwoelf
        # Anwesenden laeuft sie in drei Gruppen, sie faellt nicht heraus.
        gefunden = [e["id"] for e in self.treffer("--spieler", "12")]

        self.assertIn("ue-000002", gefunden)

    def test_die_trefferzeile_nennt_spielflaechen_und_gruppen(self) -> None:
        # Die lesbare Ausgabe zeigt zwei Dinge, die die JSON-Fassung nicht
        # hergibt: die Beschriftung des Spielflaechenfeldes und die Zahl der
        # Gruppen, in denen die Uebung bei so vielen Anwesenden laeuft.
        fertig = self.ordner.starte("suche.py", "--id", "ue-000002", "--spieler", "12", "--lang")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertIn("[3 Gruppen parallel]", fertig.stdout)
        self.assertIn("Spielflächen 1", fertig.stdout)

    def test_mit_genau_zaehlt_die_obergrenze_dann_doch(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--spieler", "12", "--genau")]

        self.assertNotIn("ue-000002", gefunden)  # Obergrenze 4
        self.assertIn("ue-000003", gefunden)     # 12 bis 16

    def test_der_disziplinfilter_beach_laesst_die_hallenkarte_draussen(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--disziplin", "beach")]

        self.assertIn("ue-000004", gefunden)     # nur beach
        self.assertIn("ue-000005", gefunden)     # halle und beach
        self.assertNotIn("ue-000001", gefunden)  # nur halle

    def test_der_disziplinfilter_halle_laesst_die_beachkarte_draussen(self) -> None:
        gefunden = [e["id"] for e in self.treffer("--disziplin", "halle")]

        self.assertIn("ue-000001", gefunden)
        self.assertIn("ue-000005", gefunden)
        self.assertNotIn("ue-000004", gefunden)

    def test_beide_werte_zusammen_treffen_jede_disziplin(self) -> None:
        # Mehrere Werte sind erlaubt und werden als Mengenschnitt gegen die
        # Liste auf der Karte verknuepft, genau wie beim Element.
        gefunden = [e["id"] for e in self.treffer("--disziplin", "halle", "beach")]

        self.assertIn("ue-000001", gefunden)  # nur halle
        self.assertIn("ue-000004", gefunden)  # nur beach
        self.assertIn("ue-000005", gefunden)  # beides

    def test_auch_die_kurze_trefferliste_nennt_die_disziplin(self) -> None:
        # Ab vier Treffern faellt die ausfuehrliche Darstellung weg. Gerade
        # dann soll auffallen, dass da eine Beachkarte zwischen den
        # Hallenkarten steht.
        fertig = self.ordner.starte("suche.py")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        zeile = next(z for z in fertig.stdout.splitlines() if z.startswith("ue-000004"))
        self.assertIn("beach", zeile)

    def test_die_ausfuehrliche_ausgabe_beschriftet_die_disziplin(self) -> None:
        fertig = self.ordner.starte("suche.py", "--id", "ue-000005", "--lang")

        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        self.assertIn("Disziplin    halle, beach", fertig.stdout)

    def schaubildzeilen(self, uid: str) -> list[str]:
        """Die Zeilen der ausfuehrlichen Ausgabe, die ein Schaubild nennen."""
        fertig = self.ordner.starte("suche.py", "--id", uid, "--lang")
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        return [z for z in fertig.stdout.splitlines() if "schaubilder/" in z]

    def test_ein_einzelnes_schaubild_steht_als_pfad_da(self) -> None:
        self.ordner.lege_karte_an(id="ue-000018", titel="Mit einem Bild",
                                  schaubild="ue-000018-aufbau.svg")

        self.assertEqual(self.schaubildzeilen("ue-000018"),
                         ["    Schaubild    schaubilder/ue-000018-aufbau.svg"])

    def test_eine_liste_nennt_jedes_schaubild_als_eigenen_pfad(self) -> None:
        # Ein Zirkel mit Uebersichtsblatt und zwei Stationen (#39). Jede Zeile
        # ist ein Pfad zum Kopieren, in der Reihenfolge der Karte. In einer
        # Zeile mit Kommas stuende `schaubilder/` nur vor dem ersten.
        self.ordner.lege_karte_an(
            id="ue-000019", titel="Zirkel mit drei Bildern",
            schaubild=["ue-000019-zirkel-1.png", "ue-000019-zirkel-2.png",
                       "ue-000019-zirkel-3.png"])

        zeilen = self.schaubildzeilen("ue-000019")

        self.assertEqual([z.split()[-1] for z in zeilen],
                         ["schaubilder/ue-000019-zirkel-1.png",
                          "schaubilder/ue-000019-zirkel-2.png",
                          "schaubilder/ue-000019-zirkel-3.png"])
        self.assertIn("Schaubilder", zeilen[0])
        # Die Pfade stehen untereinander, buendig mit dem ersten.
        spalte = zeilen[0].index("schaubilder/")
        self.assertEqual([z.index("schaubilder/") for z in zeilen], [spalte] * 3)

    def test_json_gibt_die_liste_der_schaubilder_weiter(self) -> None:
        # Der Skill volleyball-schaubild sucht seine Kandidaten mit --json:
        # Karten, deren `schaubild` leer ist. Eine Karte mit Liste hat Bilder
        # und darf dort nicht als Karte ohne Bild auftauchen (#39). Die Liste
        # kommt deshalb so an, wie sie auf der Karte steht.
        namen = ["ue-000020-zirkel-1.png", "ue-000020-zirkel-2.png"]
        self.ordner.lege_karte_an(id="ue-000020", titel="Zirkel mit zwei Bildern",
                                  schaubild=namen)

        nach_id = {e["id"]: e for e in self.treffer()}

        self.assertEqual(nach_id["ue-000020"]["schaubild"], namen)
        self.assertIsNone(nach_id["ue-000001"]["schaubild"])

    def test_eine_vorhandene_einzelne_datei_wird_zu_einem_pfad(self) -> None:
        # Der haeufigste Fall: jede PlayDrill-Karte nennt genau eine Datei.
        # Liegt sie unter quellen/, steht dort ein Pfad, den man kopieren
        # kann, so wie `schaubilder/<datei>` in der Zeile darueber.
        zeile = self.quelldateizeile(
            "ue-000013", vorhanden=("playdrill/Annahme Diagonal.pdf",),
            titel="Annahme diagonal",
            quelldatei="playdrill/Annahme Diagonal.pdf")

        self.assertEqual(
            "    Quelldatei   quellen/playdrill/Annahme Diagonal.pdf", zeile)

    def test_eine_fehlende_datei_wird_nicht_zu_einem_pfad(self) -> None:
        # Ein Mittrainer, dessen Nextcloud quellen/ nicht synchronisiert, hat
        # die Datei nicht. Die Zeile sieht bei ihm aus wie bisher, statt ihm
        # einen Pfad zu zeigen, unter dem nichts liegt.
        zeile = self.quelldateizeile(
            "ue-000014", titel="Annahme diagonal, ohne Quellen",
            quelldatei="playdrill/Annahme Diagonal.pdf")

        self.assertEqual(
            "    Quelldatei   in quellen/ · playdrill/Annahme Diagonal.pdf", zeile)

    def test_ein_absoluter_pfad_bekommt_kein_quellen_davor(self) -> None:
        # `quelldatei:` steht relativ zu quellen/, damit sie auf jedem Rechner
        # stimmt. Steht dort doch ein absoluter Pfad, zeigt er auf eine Datei,
        # die es gibt, und `quellen/` davor ergaebe trotzdem keinen Pfad.
        # Unter Windows gilt das auch fuer `/Users/...` ohne Laufwerk, obwohl
        # `is_absolute()` dazu nein sagt. Auf den anderen Systemen sind beide
        # Schreibweisen dieselbe.
        datei = self.ordner.lege_quelldatei_an("playdrill/Annahme Diagonal.pdf", b"")
        mit_laufwerk = datei.as_posix()
        ohne_laufwerk = "/" + datei.relative_to(datei.anchor).as_posix()
        for uid, wert in (("ue-000015", mit_laufwerk), ("ue-000016", ohne_laufwerk)):
            with self.subTest(wert=wert):
                zeile = self.quelldateizeile(
                    uid, titel=f"Annahme diagonal, absolut verwiesen ({uid})",
                    quelldatei=wert)

                self.assertEqual(f"    Quelldatei   in quellen/ · {wert}", zeile)

    def test_eine_liste_statt_freiem_text_laesst_die_suche_nicht_abbrechen(self) -> None:
        # Das Feld ist freier Text, aber wer zwei Seiten in eckige Klammern
        # setzt, bekommt vom Parser eine Liste. Die ist kein Pfad, und die
        # Suche darf an ihr nicht scheitern.
        zeile = self.quelldateizeile(
            "ue-000017", vorhanden=("magazin/seite-04.jpg", "magazin/seite-05.jpg"),
            titel="Abwehr über zwei Seiten, als Liste",
            quelldatei=["magazin/seite-04.jpg", "magazin/seite-05.jpg"])

        self.assertIn("in quellen/", zeile)
        self.assertEqual(1, zeile.count("quellen/"))

    def test_eine_uebung_ueber_zwei_seiten_nennt_beide_seiten(self) -> None:
        # Eine Uebung hoert selten da auf, wo die Seite aufhoert. Laeuft sie
        # ueber zwei Fotos, nennt `quelldatei:` laut DATENMODELL.md beide, und
        # beide liegen unter quellen/. Ein Praefix am Anfang der Angabe saesse
        # nur vor der ersten.
        zeile = self.quelldateizeile(
            "ue-000010", vorhanden=("magazin/seite-04.jpg", "magazin/seite-05.jpg"),
            titel="Abwehr über zwei Seiten",
            quelldatei="magazin/seite-04.jpg, magazin/seite-05.jpg")

        self.assertIn("in quellen/", zeile)
        self.assertIn("magazin/seite-04.jpg, magazin/seite-05.jpg", zeile)
        self.assertEqual(1, zeile.count("quellen/"))

    def test_zwei_seiten_mit_und_getrennt_werden_genauso_gezeigt(self) -> None:
        # Das Feld ist freier Text, und wer zwei Seiten nennt, trennt sie mal
        # mit einem Komma und mal mit einem "und". An der Schreibweise darf
        # die Ausgabe nicht haengen: die zweite Seite soll in beiden Faellen
        # genauso dastehen wie die erste.
        zeile = self.quelldateizeile(
            "ue-000011", vorhanden=("magazin/seite-04.jpg", "magazin/seite-05.jpg"),
            titel="Abwehr über zwei Seiten, anders geschrieben",
            quelldatei="magazin/seite-04.jpg und magazin/seite-05.jpg")

        self.assertIn("in quellen/", zeile)
        self.assertIn("magazin/seite-04.jpg und magazin/seite-05.jpg", zeile)
        self.assertEqual(1, zeile.count("quellen/"))

    def test_was_keine_datei_ist_wird_nicht_zu_einem_pfad(self) -> None:
        # Hinter dem Dateinamen steht oft eine Seitenzahl, und der Bestand
        # fuehrt Namen mit Leerzeichen darin. Nichts davon ist ein eigener
        # Pfad: `quellen/S. 1` gibt es nicht. Die Datei selbst liegt da, aber
        # der Wert ist mehr als ihr Name.
        zeile = self.quelldateizeile(
            "ue-000012", vorhanden=("unsortiert/Vorschlag Dienstag 14.09.23 _ H1.pdf",),
            titel="Vorschlag aus der Sammlung",
            quelldatei="unsortiert/Vorschlag Dienstag 14.09.23 _ H1.pdf, S. 1")

        self.assertIn(
            "in quellen/ · unsortiert/Vorschlag Dienstag 14.09.23 _ H1.pdf, S. 1",
            zeile)
        self.assertEqual(1, zeile.count("quellen/"))


class NaechsteIdTest(unittest.TestCase):
    """`suche.py --naechste-id`: die ID fuer die naechste Karte dieses Rechners.

    Jeder Trainer vergibt in seinem eigenen Bereich, dem mit seiner Nummer
    vorn (ADR-0011). Welcher Trainer an diesem Rechner sitzt, steht unter
    `trainer:` in der Wurzeldatei. Der Fixture traegt dort den Rechner, auf dem
    der Test laeuft, als Trainer 00.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def naechste_id(self) -> str:
        fertig = self.ordner.starte("suche.py", "--naechste-id")
        self.assertEqual(fertig.returncode, 0, fertig.stderr)
        return fertig.stdout.strip()

    def keine_id(self) -> str:
        """Ruft `--naechste-id` auf, wo es keine ID geben darf. Gibt die Meldung zurueck."""
        fertig = self.ordner.starte("suche.py", "--naechste-id")
        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertEqual(fertig.stdout, "", "auf stdout darf nichts stehen, was nach einer ID aussieht")
        return fertig.stderr

    def test_die_hoechste_id_im_eigenen_bereich_plus_eins(self) -> None:
        # Mit einer Luecke: gezaehlt wird von der hoechsten, nicht die Karten.
        self.ordner.lege_karte_an(id="ue-000009", titel="Die bisher höchste ID")

        self.assertEqual(self.naechste_id(), "ue-000010")

    def test_ein_leerer_bereich_beginnt_bei_eins(self) -> None:
        self.ordner.setze_trainer({**TRAINER_ANDERER_RECHNER,
                                   "neu": {"nummer": "01", "rechner": [socket.gethostname()]}})

        self.assertEqual(self.naechste_id(), "ue-010001")

    def test_karten_eines_anderen_trainers_zaehlen_nicht(self) -> None:
        # Der Fixture traegt die Karten 000001 bis 000005 von Trainer 00. Dazu eine hoehere
        # von Trainer 02. Fuer Trainer 01 zaehlt nur seine eigene.
        self.ordner.setze_trainer({**TRAINER_ANDERER_RECHNER,
                                   "neu": {"nummer": "01", "rechner": [socket.gethostname()]}})
        self.ordner.lege_karte_an(id="ue-010003", titel="Eine eigene Karte")
        self.ordner.lege_karte_an(id="ue-020007", titel="Karte eines dritten Trainers")

        self.assertEqual(self.naechste_id(), "ue-010004")

    def test_dateiname_und_id_zaehlen_beide(self) -> None:
        # Laufen beide auseinander, meldet der Linter die Karte. Bis dahin soll
        # keine der beiden Nummern ein zweites Mal vergeben werden.
        self.ordner.lege_karte_an(id="ue-000007", titel="Umbenannte Karte")
        karte = next((self.ordner.pfad / "uebungen").glob("ue-000007-*.md"))
        karte.rename(karte.with_name("ue-000009-umbenannte-karte.md"))

        self.assertEqual(self.naechste_id(), "ue-000010")

    def test_gross_und_kleinschreibung_des_rechners_zaehlt_nicht(self) -> None:
        self.ordner.setze_trainer({"test": {"nummer": "00",
                                            "rechner": [socket.gethostname().swapcase()]}})

        self.assertEqual(self.naechste_id(), "ue-000006")

    def test_ein_unbekannter_rechner_bekommt_keine_id(self) -> None:
        self.ordner.setze_trainer(TRAINER_ANDERER_RECHNER)

        meldung = self.keine_id()

        self.assertIn(socket.gethostname(), meldung)

    def test_die_meldung_nennt_die_trainer_und_die_naechste_freie_nummer(self) -> None:
        # Damit der Import-Skill fragen kann, wer da sitzt, ohne die
        # Wurzeldatei selbst auszulesen.
        self.ordner.setze_trainer({
            **TRAINER_ANDERER_RECHNER,
            "zweiter": {"nummer": "01", "rechner": ["ANDERER-RECHNER-2"]},
        })

        meldung = self.keine_id()

        self.assertIn("anderer (00)", meldung)
        self.assertIn("zweiter (01)", meldung)
        self.assertIn("Nummer 02", meldung)

    def test_ohne_abschnitt_trainer_gibt_es_keine_id(self) -> None:
        self.ordner.setze_trainer(None)

        meldung = self.keine_id()

        self.assertIn(socket.gethostname(), meldung)
        self.assertIn("Nummer 00", meldung, "der erste Trainer ueberhaupt bekommt 00")

    def test_zwei_trainer_mit_derselben_nummer_bekommen_keine_id(self) -> None:
        # Dann vergaeben beide dieselben IDs, und genau das soll die Nummer
        # verhindern.
        self.ordner.setze_trainer({
            "test": {"nummer": "00", "rechner": [socket.gethostname()]},
            "anderer": {"nummer": "00", "rechner": ["ANDERER-RECHNER"]},
        })

        meldung = self.keine_id()

        self.assertIn("anderer", meldung)

    def test_solange_es_vierstellige_ids_gibt_gibt_es_keine_neue(self) -> None:
        # Sonst bekaeme eine neue Karte ue-000042, und die alte ue-0042 wuerde
        # beim Umstellen zu derselben ID.
        self.ordner.lege_karte_an(id="ue-0042", titel="Karte von vor der Umstellung")

        meldung = self.keine_id()

        self.assertIn("ids_umstellen.py", meldung)

    def test_vor_der_umstellung_nennt_die_meldung_auch_den_rechner(self) -> None:
        # So sieht jeder Ordner aus, den 2.5.1 hinterlassen hat: vierstellige
        # Karten und kein Abschnitt trainer:. Dieser Rechner steht also in
        # keinem Eintrag, und die Meldung nennt ihn.
        self.ordner = Arbeitsordner(vor_der_umstellung=True)
        self.addCleanup(self.ordner.raeume_auf)

        meldung = self.keine_id()

        self.assertIn("ids_umstellen.py", meldung)
        self.assertIn(socket.gethostname(), meldung)



if __name__ == "__main__":
    unittest.main()
