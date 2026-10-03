"""Prueft `sammelimport.py` gegen einen kuenstlichen Arbeitsordner.

    <python> -m unittest discover -s plugins/volleyball/tests

Der Sammelimport ist ueber mehrere Sitzungen verteilt, und was ein Kandidat
ist, steht allein auf der Platte: in der Uebersicht der `sammelimport.md`, in
den Auftraegen und Kartenentwuerfen unter `kartenentwuerfe/<ordner>/`, und am
Ende als Karte in `uebungen/`. Genau das pruefen die Tests, nach einem Aufruf
ueber die Kommandozeile mit `--wurzel`, dazu Ausgabe und Exitcode. So ruft der
Skill das Skript auf, und das ist der Vertrag.

Plan und Entwurf legt hier der Test an. Im Betrieb schreiben sie der Skill und
die Agenten.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import tempfile
import unicodedata
import unittest
from datetime import date
from pathlib import Path

from arbeitsordner import OHNE, Arbeitsordner, PdfBild, auffaelligkeiten

ORDNER = "stapel"

# Gesucht wird hier nur im PATH. Das Skript sucht unter Windows auch neben
# git.exe. Steht pdftotext nur dort, werden diese Tests uebersprungen, obwohl
# das Skript es faende. Die Suche neben git.exe prueft die Abnahme (#29).
BRAUCHT_PDFTOTEXT = unittest.skipUnless(
    shutil.which("pdftotext"), "pdftotext ist nicht im PATH")

try:
    from PIL import Image
    HAT_PILLOW = True
except ImportError:
    HAT_PILLOW = False

BRAUCHT_PILLOW = unittest.skipUnless(HAT_PILLOW, "Pillow ist nicht installiert")


class VorbereitenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def test_ohne_freigegebenen_plan_bricht_es_ab_und_schreibt_nichts(self) -> None:
        # Vor der Freigabe steht der Zuschnitt noch nicht fest. Ein Auftrag fuer
        # einen Kandidaten, den der Trainer gleich zusammenlegt oder streicht,
        # kostete einen Kartenentwurf fuer nichts.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["seite-01.jpg"]}], freigegeben=None)

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("freigegeben", fertig.stdout + fertig.stderr)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def auftraege(self) -> list[str]:
        ordner = self.ordner.pfad / "kartenentwuerfe" / ORDNER
        return sorted(p.name for p in ordner.glob("*.auftrag.md"))

    def test_auftraege_fuer_genau_die_eingestellte_zahl_offener_kandidaten(self) -> None:
        # Vorn stehen die Kandidaten, die keinen Auftrag bekommen: fertig,
        # zurueckgestellt, gestrichen, oder schon mit einem Entwurf, der die
        # Pruefung besteht. Zaehlte einer davon mit, bekaemen die offenen 5 und
        # 6 keinen Auftrag, und der Durchgang waere kleiner als eingestellt.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["seite-01.jpg"], "status": "importiert",
             "karte": "ue-000001"},
            {"kandidat": 2, "dateien": ["seite-02.jpg"], "ergebnis": "zurückgestellt",
             "status": "zurückgestellt"},
            {"kandidat": 3, "dateien": ["seite-03.jpg"], "ergebnis": "übersprungen",
             "status": "übersprungen"},
            {"kandidat": 4, "dateien": ["seite-04.jpg"]},
            {"kandidat": 5, "dateien": ["seite-05.jpg"]},
            {"kandidat": 6, "dateien": ["seite-06.jpg"]},
            {"kandidat": 7, "dateien": ["seite-07.jpg"]},
        ], je_durchgang=2)
        self.ordner.lege_kartenentwurf_an(ORDNER, 4, titel="Schon entworfen")

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout)
        self.assertEqual(self.auftraege(), ["5.auftrag.md", "6.auftrag.md"])

    def in_arbeit(self) -> str | None:
        """Der Wert von `in_arbeit:` in den Einstellungen der sammelimport.md, oder None."""
        text = (self.ordner.pfad / "quellen" / ORDNER / "sammelimport.md").read_text(
            encoding="utf-8")
        treffer = re.search(r"^in_arbeit:[ \t]*(.*)$", text.split("\n---", 1)[0], re.MULTILINE)
        return treffer.group(1).strip('"') if treffer else None

    def test_vorbereiten_traegt_ein_welcher_trainer_seit_wann_daran_arbeitet(self) -> None:
        # Mit mehreren Trainern koennen zwei denselben Quellenordner zugleich
        # importieren und dieselben Kandidaten zweimal entwerfen (#38). Der
        # Eintrag sagt dem zweiten, wer schon dran ist. Die Uebersicht
        # bleibt dabei heil, obwohl im Frontmatter eine Zeile dazukommt.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "importiert", "karte": "ue-000001"},
            {"kandidat": 2, "dateien": ["b.pdf"]},
        ])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual(self.in_arbeit(), f"test, {date.today().isoformat()}")
        self.assertEqual(sorted(self.ordner.uebersicht(ORDNER)), ["1", "2"])
        self.assertEqual(self.auftraege(), ["2.auftrag.md"])

    def test_arbeitet_ein_anderer_trainer_daran_geht_es_nur_mit_trotzdem_weiter(self) -> None:
        # Ohne --trotzdem endet vorbereiten, nennt ihn und schreibt nichts,
        # auch die sammelimport.md bleibt Zeichen fuer Zeichen. Mit
        # --trotzdem geht es weiter, etwa wenn der Eintrag von einem
        # abgebrochenen Lauf stammt, und der Eintrag nennt jetzt diesen.
        datei = self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"]}], in_arbeit="anna, 2026-10-01")
        vorher = datei.read_text(encoding="utf-8")

        gestoppt = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertNotEqual(gestoppt.returncode, 0, gestoppt.stdout)
        self.assertIn("2026-10-01", zeile_mit(gestoppt.stdout, "anna"))
        self.assertIn("--trotzdem", gestoppt.stdout)
        self.assertEqual(datei.read_text(encoding="utf-8"), vorher)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

        weiter = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER, "--trotzdem")

        self.assertEqual(weiter.returncode, 0, weiter.stdout + weiter.stderr)
        self.assertEqual(self.auftraege(), ["1.auftrag.md"])
        self.assertEqual(self.in_arbeit(), f"test, {date.today().isoformat()}")

    def test_gehoert_der_rechner_zu_keinem_trainer_endet_vorbereiten(self) -> None:
        # Ohne Trainer laesst sich nicht eintragen, wer daran arbeitet, und
        # uebernehmen bekaeme am Ende keine ID. Besser vor dem ersten Auftrag.
        self.ordner.setze_trainer({"test": {"nummer": "00", "rechner": ["ANDERER-RECHNER"]}})
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"]}])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn(socket.gethostname(), fertig.stdout)
        self.assertIsNone(self.in_arbeit())
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_der_auftrag_nennt_was_der_agent_braucht(self) -> None:
        # Der Agent kann nicht nachfragen. Was nicht im Auftrag steht, muss er
        # raten oder als Rueckfrage schreiben. Eine Folge ueber zwei Seiten
        # zeigt zugleich, dass `quelldatei:` beide Dateien nennt, relativ zu
        # quellen/, so wie das Datenmodell es fuer zwei Seiten verlangt.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 8, "dateien": ["seite-08.jpg", "seite-09.jpg"],
             "was": "Zirkel über zwei Seiten", "ergebnis": "folge"},
        ], absprachen="Jede Seite nennt das Heft oben links.\n")

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout)
        auftrag = (self.ordner.pfad / "kartenentwuerfe" / ORDNER / "8.auftrag.md").read_text(
            encoding="utf-8")
        self.assertIn("Zirkel über zwei Seiten", auftrag)
        self.assertIn("`folge`", zeile_mit(auftrag, "Typ"))
        self.assertIn("stapel/seite-08.jpg, stapel/seite-09.jpg",
                      zeile_mit(auftrag, "quelldatei"))
        for seite in ("seite-08.jpg", "seite-09.jpg"):
            self.assertIn(
                (self.ordner.pfad / "quellen" / ORDNER / seite).resolve().as_posix(), auftrag)
        self.assertIn("Jede Seite nennt das Heft oben links.", auftrag)
        self.assertIn(
            (self.ordner.pfad / "kartenentwuerfe" / ORDNER / "8.md").resolve().as_posix(),
            zeile_mit(auftrag, "Zielpfad"))

    def test_eine_doppelte_nummer_bricht_ab_und_schreibt_nichts(self) -> None:
        # Die Nummer benennt Entwurf und Auftrag. Zwei Zeilen mit derselben
        # Nummer teilten sich eine Datei, und die zweite ueberschriebe still
        # den Auftrag der ersten.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 3, "dateien": ["a.pdf"]},
            {"kandidat": 3, "dateien": ["b.pdf"]},
        ])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("3", zeile_mit(fertig.stdout, "zweimal"))
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_ein_unbekannter_status_bricht_ab_und_schreibt_nichts(self) -> None:
        # Von Hand vertippt. Gaelte "Offen" als erledigt, bekaeme der Kandidat
        # nie einen Auftrag, und am Ende verschwaende der Entwurfsordner,
        # obwohl aus ihm nie eine Karte wurde.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"], "status": "Offen"}])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("Offen", fertig.stdout)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_der_quellenordner_darf_mit_quellen_davor_kommen(self) -> None:
        # So nennt ihn der Trainer: "Sammelimport ueber quellen/stapel".
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"]}])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", f"quellen/{ORDNER}/")

        self.assertEqual(fertig.returncode, 0, fertig.stdout)
        self.assertEqual(self.auftraege(), ["1.auftrag.md"])

    def test_der_auftrag_traegt_die_kennungen_des_arbeitsordners(self) -> None:
        # Die Kennungen kommen aus schwerpunkte.md der Wurzel und nicht aus
        # dem Plugin: jeder Verein hat seine eigenen. Die Kennung aus diesem
        # Test gibt es nur in diesem einen Arbeitsordner.
        self.ordner.ergaenze_schwerpunkt("nur-in-diesem-test", "halle")
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"]}])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout)
        auftrag = (self.ordner.pfad / "kartenentwuerfe" / ORDNER / "1.auftrag.md").read_text(
            encoding="utf-8")
        self.assertIn("halle", zeile_mit(auftrag, "`nur-in-diesem-test`"))
        self.assertIn("beach", zeile_mit(auftrag, "`nur-beach`"))
        # Ein Steuerungsschwerpunkt fuehrt keine Disziplinspalte und gilt
        # deshalb fuer beide. Das muss der Agent so lesen koennen.
        self.assertIn("beide", zeile_mit(auftrag, "`standortbestimmung`"))

    @BRAUCHT_PDFTOTEXT
    def test_der_auftrag_traegt_den_text_je_datei(self) -> None:
        # Ein Zirkel ueber zwei Blaetter. Der Agent muss wissen, welcher Text
        # auf dem Uebersichtsblatt steht und welcher auf der Station, sonst
        # landet die Stationsliste im Ablauf der falschen Station.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 4, "dateien": ["zirkel.pdf", "station-1.pdf"], "ergebnis": "folge"}])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/zirkel.pdf",
                                      ["Stationsübersicht Sprungkraftzirkel"])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/station-1.pdf",
                                      ["Station 1: Sprünge über die Kiste"])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout)
        auftrag = auftrag_von(self.ordner, 4)
        zirkel = unter_datei(auftrag, "zirkel.pdf")
        self.assertIn("Stationsübersicht Sprungkraftzirkel", zirkel)
        self.assertNotIn("Station 1", zirkel)
        self.assertIn("Station 1: Sprünge über die Kiste", unter_datei(auftrag, "station-1.pdf"))

    @BRAUCHT_PDFTOTEXT
    def test_ein_pdf_ohne_textebene_sagt_dem_agenten_dass_er_es_selbst_lesen_muss(self) -> None:
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["scan.pdf"]}])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/scan.pdf", [])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("selbst lesen", unter_datei(auftrag_von(self.ordner, 1), "scan.pdf"))

    def test_ohne_pdftotext_sagt_der_auftrag_dass_der_agent_das_pdf_selbst_liest(self) -> None:
        # Wie bei der Planeingabe: teurer, aber kein Abbruch (ADR-0008). Der
        # Hinweis kommt einmal je Lauf, nicht einmal je Auftrag.
        leer = Path(tempfile.mkdtemp(prefix="ohne-pdftotext-"))
        self.addCleanup(shutil.rmtree, leer, True)
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"]}, {"kandidat": 2, "dateien": ["b.pdf"]}])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/a.pdf", ["Abwehr vom Kasten"])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/b.pdf", ["Sprungkraftzirkel"])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER,
                                    umgebung={"PATH": str(leer)})

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual(fertig.stdout.count("pdftotext fehlt"), 1, fertig.stdout)
        self.assertNotIn("Abwehr vom Kasten", auftrag_von(self.ordner, 1))
        self.assertIn("selbst lesen", unter_datei(auftrag_von(self.ordner, 1), "a.pdf"))


PLAYDRILL = {"textmarke": "Ausführung:", "platzhalter": "hier könnte ihr Text stehen"}

# Kopf und Ansage eines PlayDrill-Blatts, ueber 150 Zeichen. Zaehlte der
# ganze Text, haette jedes Blatt genug, auch eins, unter dessen "Ausfuehrung:"
# nur der Platzhalter steht.
PLAYDRILL_KOPF = [
    "Abwehr gegen den Kasten",
    "Trainer/Ersteller: Stege",
    "ZEIT: 10 Min-Spieler 6+",
    "Ansage:",
    "Zu besetzende Positionen: 2 Angreifer auf Kasten, 2 Ballanreicher, 2 Fänger,",
    "der Rest in zwei Gruppen in der Abwehr.",
]


class AblaufAusDemBildTest(unittest.TestCase):
    """Ob der Ablauf aus dem Bild kommt, entscheidet eine Regel, nicht das Modell.

    Steht nach der Textmarke einer Quelle zu wenig, muss der Agent den Ablauf
    aus der Quellgrafik lesen, und der Trainer prueft ihn einzeln. Das soll nicht
    am Urteil des Agenten haengen (#29, Geschichte 44).
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def ablauf(self, kandidat: int) -> str:
        """Was der Auftrag zum Ablauf aus dem Bild sagt, die ganze Zeile."""
        return zeile_mit(auftrag_von(self.ordner, kandidat), "Ablauf aus dem Bild")

    def bereite_vor(self) -> None:
        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)

    @BRAUCHT_PDFTOTEXT
    def test_nur_der_platzhalter_nach_der_textmarke_ergibt_ablauf_aus_dem_bild(self) -> None:
        # Das Blatt schreibt "Koennte" gross, die Einstellung klein, so wie bei
        # PlayDrill wirklich. Der Platzhalter gilt trotzdem als Platzhalter.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["leer.pdf"]},
            {"kandidat": 2, "dateien": ["ausfuehrlich.pdf"]},
        ], **PLAYDRILL)
        self.ordner.lege_quell_pdf_an(
            f"{ORDNER}/leer.pdf", [*PLAYDRILL_KOPF, "Ausführung: hier Könnte ihr Text stehen"])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/ausfuehrlich.pdf", [
            *PLAYDRILL_KOPF,
            "Ausführung: Die Angreifer schlagen abwechselnd vom Kasten auf beide",
            "Abwehrgruppen. Wer abgewehrt hat, stellt sich hinten an, und der Fänger",
            "bringt den Ball zurück zum Anreicher.",
        ])

        self.bereite_vor()

        self.assertIn(": ja", self.ablauf(1))
        self.assertIn(": nein", self.ablauf(2))
        # Die Begruendung nennt die Textmarke so, wie sie eingestellt ist.
        self.assertIn("„Ausführung:“", self.ablauf(1))

    @BRAUCHT_PDFTOTEXT
    def test_traegt_eine_datei_die_textmarke_nicht_zaehlt_ihr_ganzer_text(self) -> None:
        # 22 von 260 PlayDrill-Blaettern schreiben "Ausfuehrung(1)" oder
        # "Ausfuehrung 1", ohne Doppelpunkt und mit vollem Ablauf dahinter.
        # Das ist kein fehlender Ablauf. Ein Blatt, auf dem nur der Titel
        # steht, hat dagegen auch ohne Marke zu wenig.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["ohne-doppelpunkt.pdf"]},
            {"kandidat": 2, "dateien": ["nur-titel.pdf"]},
        ], **PLAYDRILL)
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/ohne-doppelpunkt.pdf", [
            "Standweitsprung", "Ausführung(1) Standweitsprung über die Spielfeldbreite,",
            "neun Meter. Ziel bei den Damen höchstens vier Sprünge, bei den Herren drei.",
            "(2) Standhochsprung auf die Matten als Wettkampf, zwei Versuche je Spieler."])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/nur-titel.pdf", ["Terraband_Kraftpart"])

        self.bereite_vor()

        self.assertIn(": nein", self.ablauf(1))
        self.assertIn(": ja", self.ablauf(2))

    @BRAUCHT_PDFTOTEXT
    def test_ohne_textmarke_in_den_einstellungen_zaehlt_der_ganze_text(self) -> None:
        # Eine Magazinquelle hat keine feste Stelle fuer den Ablauf. Dann zaehlt
        # alles, auch der Kopf, und ein Platzhalter darunter faellt nicht auf.
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"]}])
        self.ordner.lege_quell_pdf_an(
            f"{ORDNER}/a.pdf", [*PLAYDRILL_KOPF, "Ausführung: hier Könnte ihr Text stehen"])

        self.bereite_vor()

        self.assertIn(": nein", self.ablauf(1))

    def test_ohne_text_entscheidet_der_agent(self) -> None:
        # Eine abfotografierte Seite hat keine Textebene. Ob dort ein Ablauf
        # steht, sieht nur, wer sie liest.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["seite-24.jpg"]}], **PLAYDRILL)

        self.bereite_vor()

        self.assertNotIn(": ja", self.ablauf(1))
        self.assertNotIn(": nein", self.ablauf(1))
        self.assertIn("entscheidest du", self.ablauf(1))


class QuellgrafikTest(unittest.TestCase):
    """Die Quellgrafik aus dem PDF: von `vorbereiten` ausgeschnitten, bei `uebernehmen` Schaubild.

    PlayDrill bettet in jedes Blatt eine Quellgrafik mit Transparenzmaske ein.
    Der Agent soll sie ansehen koennen, ohne das PDF zu oeffnen, und auf der
    fertigen Karte steht sie als Schaubild (#29, Geschichte 33).
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)
        self.entwuerfe = self.ordner.pfad / "kartenentwuerfe" / ORDNER

    @BRAUCHT_PILLOW
    def test_die_quellgrafik_ist_auf_ihren_inhalt_zugeschnitten(self) -> None:
        # Vor der Quellgrafik steht ein kleines Logo im PDF. Genommen wird das
        # groessere Bild, und von ihm nur, was deckend ist: 68 x 46 Pixel.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 3, "dateien": ["kasten.pdf"]}], quellgrafik_ausschneiden=True)
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/kasten.pdf", ["Abwehr vom Kasten"], bilder=[
            PdfBild(20, 20, deckend=(0, 0, 20, 20)),
            PdfBild(90, 60, deckend=(12, 5, 80, 51)),
        ])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        quellgrafik = self.entwuerfe / "3.quellgrafik.png"
        with Image.open(quellgrafik) as bild:
            self.assertEqual(bild.size, (68, 46))
            self.assertEqual(bild.convert("RGBA").getpixel((0, 0)), (30, 120, 200, 255))
        # Der Agent sieht sie sich unter dem absoluten Pfad an und traegt sie
        # unter ihrem Namen in den Entwurf ein, neben dem sie liegt.
        zeile = zeile_mit(auftrag_von(self.ordner, 3), "Quellgrafik")
        self.assertIn(quellgrafik.resolve().as_posix(), zeile)
        self.assertIn("schaubild: 3.quellgrafik.png", zeile)

    @BRAUCHT_PILLOW
    def test_jedes_pdf_mit_bild_gibt_eine_quellgrafik_in_der_reihenfolge_der_dateien(self) -> None:
        # Ein Zirkel (#39): vorn das Uebersichtsblatt, wie der Zerlegungsplan
        # es setzt (#35), dann zwei Stationen, dazwischen ein Blatt ohne
        # Bild. Alphabetisch stuende die Uebersicht zuletzt. Jedes Blatt mit
        # Bild gibt eine Quellgrafik, durchnummeriert ohne Luecke, und die
        # Groesse zeigt, aus welchem Blatt sie stammt.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 5, "dateien": ["zirkel.pdf", "station-1.pdf", "notizen.pdf",
                                        "station-2.pdf"],
             "ergebnis": "folge"}], quellgrafik_ausschneiden=True)
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/zirkel.pdf", ["Übersicht"], bilder=[
            PdfBild(50, 40, deckend=(5, 5, 45, 35))])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/station-1.pdf", ["Station 1"], bilder=[
            PdfBild(90, 60, deckend=(0, 0, 90, 60))])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/notizen.pdf", ["Nur Text"])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/station-2.pdf", ["Station 2"], bilder=[
            PdfBild(30, 20, deckend=(0, 0, 30, 20))])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        erwartet = [("5.quellgrafik-1.png", "zirkel.pdf", (40, 30)),
                    ("5.quellgrafik-2.png", "station-1.pdf", (90, 60)),
                    ("5.quellgrafik-3.png", "station-2.pdf", (30, 20))]
        self.assertEqual(sorted(p.name for p in self.entwuerfe.glob("5.quellgrafik*")),
                         [name for name, _, _ in erwartet])
        auftrag = auftrag_von(self.ordner, 5)
        for name, pdf, groesse in erwartet:
            with Image.open(self.entwuerfe / name) as bild:
                self.assertEqual(bild.size, groesse, name)
            zeile = zeile_mit(auftrag, (self.entwuerfe / name).resolve().as_posix())
            self.assertIn(f"`{pdf}`", zeile)
        # Der Agent traegt sie als Liste ein, in genau dieser Folge.
        self.assertIn(
            "`schaubild: [5.quellgrafik-1.png, 5.quellgrafik-2.png, 5.quellgrafik-3.png]`",
            zeile_mit(auftrag, "Quellgrafiken"))
        zeilen = auftrag.splitlines()
        self.assertLess(*(zeilen.index(zeile_mit(auftrag, f"5.quellgrafik-{i}.png`"))
                          for i in (1, 2)))
        self.assertLess(*(zeilen.index(zeile_mit(auftrag, f"5.quellgrafik-{i}.png`"))
                          for i in (2, 3)))

    @BRAUCHT_PILLOW
    def test_laesst_sich_ein_bild_nicht_lesen_fehlt_nur_dieses(self) -> None:
        # Auch wenn es das Bild der Uebersicht ist (entschieden am
        # 02.10.2026): Die Stationen bekommen ihre Quellgrafiken trotzdem,
        # gezaehlt ohne Luecke. Fuer die Uebersicht laesst sich spaeter ein
        # Schaubild zeichnen. Ausgabe und Auftrag nennen das PDF, damit der
        # Agent dort selbst nachsieht.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 5, "dateien": ["zirkel.pdf", "station-1.pdf", "station-2.pdf"],
             "ergebnis": "folge"}], quellgrafik_ausschneiden=True)
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/zirkel.pdf", ["Übersicht"], bilder=[
            PdfBild(50, 40, deckend=(5, 5, 45, 35), kaputt=True)])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/station-1.pdf", ["Station 1"], bilder=[
            PdfBild(90, 60, deckend=(0, 0, 90, 60))])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/station-2.pdf", ["Station 2"], bilder=[
            PdfBild(30, 20, deckend=(0, 0, 30, 20))])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertEqual(sorted(p.name for p in self.entwuerfe.glob("5.quellgrafik*")),
                         ["5.quellgrafik-1.png", "5.quellgrafik-2.png"])
        for name, groesse in (("5.quellgrafik-1.png", (90, 60)), ("5.quellgrafik-2.png", (30, 20))):
            with Image.open(self.entwuerfe / name) as bild:
                self.assertEqual(bild.size, groesse, name)
        auftrag = auftrag_von(self.ordner, 5)
        self.assertIn("schaubild: [5.quellgrafik-1.png, 5.quellgrafik-2.png]",
                      zeile_mit(auftrag, "Quellgrafiken"))
        self.assertIn("im PDF selbst", zeile_mit(auftrag, "`zirkel.pdf`:"))
        self.assertIn("zirkel.pdf", zeile_mit(fertig.stdout, "Keine Quellgrafik"))

    @BRAUCHT_PILLOW
    def test_pruefen_nennt_die_pdfs_ohne_quellgrafik_auch_ohne_die_ausgabe_von_vorbereiten(
            self) -> None:
        # Nach einem Abbruch ist die Ausgabe von vorbereiten weg, und am Ende
        # des Durchgangs nennt der Skill die Karten, denen eine Quellgrafik
        # fehlt, mit dem PDF (#36). Er liest sie aus `pruefen --json`, und das
        # liest sie aus dem Auftrag. Bei 5 fehlt nur das Bild der Uebersicht,
        # bei 6 das einzige, 7 hat seins, und 8 hat ein PDF ohne Bild: Dort
        # fehlt nichts, es gab nichts auszuschneiden.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 5, "dateien": ["zirkel.pdf", "station-1.pdf", "station-2.pdf"],
             "ergebnis": "folge"},
            {"kandidat": 6, "dateien": ["Ü_Abwehr/kasten, hoch.pdf"]},
            {"kandidat": 7, "dateien": ["glatt.pdf"]},
            {"kandidat": 8, "dateien": ["nur-text.pdf"]},
        ], quellgrafik_ausschneiden=True)
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/zirkel.pdf", ["Übersicht"], bilder=[
            PdfBild(50, 40, deckend=(5, 5, 45, 35), kaputt=True)])
        for name in ("station-1.pdf", "station-2.pdf", "glatt.pdf"):
            self.ordner.lege_quell_pdf_an(f"{ORDNER}/{name}", [name], bilder=[
                PdfBild(30, 20, deckend=(0, 0, 30, 20))])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/Ü_Abwehr/kasten, hoch.pdf", ["Kasten"], bilder=[
            PdfBild(90, 60, deckend=(12, 5, 80, 51), kaputt=True)])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/nur-text.pdf", ["Nur Text"])
        vorbereitet = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)
        self.assertEqual(vorbereitet.returncode, 0, vorbereitet.stdout + vorbereitet.stderr)
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 5, typ="folge", titel="Zirkel",
            schaubild=["5.quellgrafik-1.png", "5.quellgrafik-2.png"])
        self.ordner.lege_kartenentwurf_an(ORDNER, 6, titel="Kasten")
        self.ordner.lege_kartenentwurf_an(ORDNER, 7, titel="Glatt", schaubild="7.quellgrafik.png")

        fertig = self.ordner.starte("sammelimport.py", "pruefen", "--json", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        freigabe = {k["kandidat"]: k for k in json.loads(fertig.stdout)["kandidaten"]}
        # Die Blaetter haben kaum Text, die Entwuerfe sind deshalb `rückfrage`.
        for kandidat in ("5", "6", "7"):
            self.assertNotEqual(freigabe[kandidat]["status"], "offen", freigabe[kandidat]["notiz"])
        self.assertEqual(freigabe["5"]["quellgrafik_fehlt"], ["zirkel.pdf"])
        self.assertEqual(freigabe["6"]["quellgrafik_fehlt"], ["Ü_Abwehr/kasten, hoch.pdf"])
        self.assertEqual(freigabe["7"]["quellgrafik_fehlt"], [])
        self.assertNotIn("8", freigabe)

    @BRAUCHT_PILLOW
    def test_ein_bild_das_sich_nicht_lesen_laesst_nennen_ausgabe_und_auftrag(self) -> None:
        # Sonst saehe der Agent im Auftrag keine Quellgrafik und wuesste nicht,
        # ob es keine gibt oder ob er sie im PDF suchen muss.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 3, "dateien": ["kasten.pdf"]}], quellgrafik_ausschneiden=True)
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/kasten.pdf", ["Abwehr vom Kasten"], bilder=[
            PdfBild(90, 60, deckend=(12, 5, 80, 51), kaputt=True)])

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("kasten.pdf", zeile_mit(fertig.stdout, "Quellgrafik"))
        self.assertIn("im PDF selbst", zeile_mit(auftrag_von(self.ordner, 3), "Quellgrafik"))
        self.assertFalse((self.entwuerfe / "3.quellgrafik.png").exists())

    def test_ohne_pillow_bricht_es_vor_dem_ersten_auftrag_ab(self) -> None:
        # Wie in test_bilder.py: Ein PIL.py, das beim Import abbricht,
        # verdeckt das echte Paket. So laeuft der Test auch dort, wo Pillow
        # installiert ist. Ohne Abbruch kaemen 30 Karten ohne Bild heraus.
        schatten = Path(tempfile.mkdtemp(prefix="ohne-pillow-"))
        self.addCleanup(shutil.rmtree, schatten, True)
        (schatten / "PIL.py").write_text(
            'raise ImportError("Pillow ist fuer diesen Test ausgeblendet")\n', encoding="utf-8")
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 3, "dateien": ["kasten.pdf"]}], quellgrafik_ausschneiden=True)

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER,
                                    umgebung={"PYTHONPATH": str(schatten)})

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("pip install Pillow", fertig.stdout)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_mit_der_alten_einstellung_bricht_es_ab_und_nennt_die_neue(self) -> None:
        # Bis zum 02.10.2026 hiess die Einstellung anders (#49). Liefe
        # vorbereiten mit dem alten Namen weiter, schnitte es still nichts
        # aus, und die Karten kaemen ohne Bild heraus.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 3, "dateien": ["kasten.pdf"]}], feldbild_ausschneiden=True)

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("feldbild_ausschneiden", fertig.stdout)
        self.assertIn("quellgrafik_ausschneiden", fertig.stdout)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_fehlt_die_eingetragene_quellgrafik_geht_der_kandidat_zurueck_auf_offen(self) -> None:
        # Etwa weil sie jemand beim Aufraeumen geloescht hat. Die Karte zeigte
        # nach der Uebernahme ins Leere. Eine Quellgrafik neben dem Entwurf
        # reicht dagegen, ob sie aus dem PDF kommt, sieht pruefen nicht.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Ohne Bild daneben",
                                          schaubild="1.quellgrafik.png")
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Mit Bild daneben",
                                          schaubild="2.quellgrafik.png")
        (self.entwuerfe / "2.quellgrafik.png").write_bytes(b"ein Bild")

        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        uebersicht = self.ordner.uebersicht(ORDNER)
        self.assertEqual(uebersicht["1"]["Status"], "offen")
        self.assertIn("1.quellgrafik.png", uebersicht["1"]["Notiz"])
        self.assertEqual(uebersicht["2"]["Status"], "bereit")

    def test_ein_entwurf_traegt_nur_seine_eigene_quellgrafik_ein(self) -> None:
        # Vertippt: Kandidat 1 nennt die Quellgrafik von Kandidat 2. Sie liegt
        # neben dem Entwurf, aber uebernehmen truege sie weg, und Kandidat 2
        # stuende ohne da. Der Auftrag liegt auch daneben und ist kein Bild.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"]},
            {"kandidat": 2, "dateien": ["b.pdf"]},
        ])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Fremdes Bild",
                                          schaubild="2.quellgrafik.png")
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Auftrag als Bild",
                                          schaubild="2.auftrag.md")
        (self.entwuerfe / "2.quellgrafik.png").write_bytes(b"das Bild von 2")
        (self.entwuerfe / "2.auftrag.md").write_text("# Auftrag\n", encoding="utf-8")

        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        uebersicht = self.ordner.uebersicht(ORDNER)
        for kandidat, eingetragen in (("1", "2.quellgrafik.png"), ("2", "2.auftrag.md")):
            self.assertEqual(uebersicht[kandidat]["Status"], "offen")
            self.assertIn(eingetragen, uebersicht[kandidat]["Notiz"])

    def test_eine_liste_besteht_wenn_jede_eingetragene_quellgrafik_daneben_liegt(self) -> None:
        # Kandidat 1 traegt seine beiden Quellgrafiken ein, und beide liegen da.
        # Bei 2 fehlt die zweite, bei 3 steht eine fremde in der Liste. Die
        # Notiz nennt genau das, woran es liegt (#39).
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": n, "dateien": [f"{n}.pdf"], "ergebnis": "folge"} for n in (1, 2, 3)])
        for kandidat, liste in ((1, ["1.quellgrafik-1.png", "1.quellgrafik-2.png"]),
                                (2, ["2.quellgrafik-1.png", "2.quellgrafik-2.png"]),
                                (3, ["3.quellgrafik-1.png", "4.quellgrafik-1.png"])):
            self.ordner.lege_kartenentwurf_an(ORDNER, kandidat, typ="folge",
                                              titel=f"Zirkel {kandidat}", schaubild=liste)
        for name in ("1.quellgrafik-1.png", "1.quellgrafik-2.png", "2.quellgrafik-1.png",
                     "3.quellgrafik-1.png", "4.quellgrafik-1.png"):
            (self.entwuerfe / name).write_bytes(b"ein Bild")

        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        uebersicht = self.ordner.uebersicht(ORDNER)
        self.assertEqual(uebersicht["1"]["Status"], "bereit", uebersicht["1"]["Notiz"])
        self.assertEqual(uebersicht["2"]["Status"], "offen")
        self.assertIn("2.quellgrafik-2.png", uebersicht["2"]["Notiz"])
        self.assertNotIn("2.quellgrafik-1.png", uebersicht["2"]["Notiz"])
        self.assertEqual(uebersicht["3"]["Status"], "offen")
        self.assertIn("4.quellgrafik-1.png", uebersicht["3"]["Notiz"])

    def test_eine_doppelt_eingetragene_quellgrafik_weist_den_entwurf_ab(self) -> None:
        # Sie liegt da und ist die eigene, aber uebernehmen kann sie nur einmal
        # verschieben. Beim zweiten Mal fehlte sie, und die Karte stuende
        # schon in uebungen/.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["1.pdf"], "ergebnis": "folge"}])
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, typ="folge", titel="Zirkel",
            schaubild=["1.quellgrafik-1.png", "1.quellgrafik-2.png", "1.quellgrafik-1.png"])
        for name in ("1.quellgrafik-1.png", "1.quellgrafik-2.png"):
            (self.entwuerfe / name).write_bytes(b"ein Bild")

        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        zeile = self.ordner.uebersicht(ORDNER)["1"]
        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("1.quellgrafik-1.png zweimal", zeile["Notiz"])

    def lege_freigegebenen_entwurf_an(self) -> None:
        """Kandidat 3 mit Quellgrafik, freigegeben. Die naechste freie ID ist ue-000010."""
        self.ordner.lege_karte_an(id="ue-000009", titel="Die bisher höchste ID")
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 3, "dateien": ["kasten.pdf"], "status": "bereit"}])
        self.ordner.lege_kartenentwurf_an(ORDNER, 3, titel="Abwehr vom Kasten",
                                          quelldatei=f"{ORDNER}/kasten.pdf",
                                          schaubild="3.quellgrafik.png")
        (self.entwuerfe / "3.quellgrafik.png").write_bytes(b"die Quellgrafik")

    def test_nach_uebernehmen_ist_die_quellgrafik_das_schaubild_der_karte(self) -> None:
        # So liegen die PlayDrill-Bilder schon heute: unter dem Namen der
        # Karte, und die Leseansicht zeigt sie. Den Ordner schaubilder/ gibt
        # es im kuenstlichen Arbeitsordner noch nicht.
        self.lege_freigegebenen_entwurf_an()

        fertig = self.ordner.starte("sammelimport.py", "uebernehmen", ORDNER, "--kandidat", "3", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        name = "ue-000010-abwehr-vom-kasten"
        self.assertEqual((self.ordner.pfad / "schaubilder" / f"{name}.png").read_bytes(),
                         b"die Quellgrafik")
        karte = (self.ordner.pfad / "uebungen" / f"{name}.md").read_text(encoding="utf-8")
        self.assertIn(f"\nschaubild: {name}.png\n", karte)
        self.assertFalse((self.entwuerfe / "3.quellgrafik.png").exists())
        index = self.ordner.starte("index.py")
        self.assertEqual(auffaelligkeiten(index.stdout), [], index.stdout)

    def lege_freigegebenen_zirkel_an(self) -> None:
        """Kandidat 5, eine Folge mit drei Quellgrafiken, freigegeben.

        Die naechste freie ID ist ue-000010.
        """
        self.ordner.lege_karte_an(id="ue-000009", titel="Die bisher höchste ID")
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 5, "dateien": ["zirkel.pdf", "station-1.pdf", "station-2.pdf"],
             "ergebnis": "folge", "status": "bereit"}])
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 5, typ="folge", titel="Zirkel",
            schaubild=["5.quellgrafik-1.png", "5.quellgrafik-2.png", "5.quellgrafik-3.png"])
        for nr in (1, 2, 3):
            (self.entwuerfe / f"5.quellgrafik-{nr}.png").write_bytes(f"Blatt {nr}".encode())

    def test_mehrere_quellgrafiken_werden_durchnummeriert_und_als_liste_eingetragen(self) -> None:
        # Unter dem Namen der Karte, mit Nummer, in der Reihenfolge aus dem
        # Entwurf. Die Leseansicht zeigt sie so (#39).
        self.lege_freigegebenen_zirkel_an()

        fertig = self.ordner.starte("sammelimport.py", "uebernehmen", ORDNER, "--kandidat", "5", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        namen = [f"ue-000010-zirkel-{nr}.png" for nr in (1, 2, 3)]
        for nr, name in enumerate(namen, 1):
            self.assertEqual((self.ordner.pfad / "schaubilder" / name).read_bytes(),
                             f"Blatt {nr}".encode())
        karte = (self.ordner.pfad / "uebungen" / "ue-000010-zirkel.md").read_text(encoding="utf-8")
        self.assertIn(f"\nschaubild: [{', '.join(namen)}]\n", karte)
        self.assertEqual(list(self.entwuerfe.glob("5.quellgrafik*")), [])
        index = self.ordner.starte("index.py")
        self.assertEqual(auffaelligkeiten(index.stdout), [], index.stdout)

    def test_eine_liste_mit_einer_quellgrafik_wird_ein_einzelner_name(self) -> None:
        # Eine einzelne Quellgrafik bleibt ein einzelner Name, auch wenn der
        # Agent sie in eckige Klammern gesetzt hat.
        self.ordner.lege_karte_an(id="ue-000009", titel="Die bisher höchste ID")
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 3, "dateien": ["kasten.pdf"], "status": "bereit"}])
        self.ordner.lege_kartenentwurf_an(ORDNER, 3, titel="Abwehr vom Kasten",
                                          schaubild=["3.quellgrafik.png"])
        (self.entwuerfe / "3.quellgrafik.png").write_bytes(b"die Quellgrafik")

        fertig = self.ordner.starte("sammelimport.py", "uebernehmen", ORDNER, "--kandidat", "3", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        name = "ue-000010-abwehr-vom-kasten"
        karte = (self.ordner.pfad / "uebungen" / f"{name}.md").read_text(encoding="utf-8")
        self.assertIn(f"\nschaubild: {name}.png\n", karte)
        self.assertTrue((self.ordner.pfad / "schaubilder" / f"{name}.png").is_file())

    def test_liegt_eins_der_nummerierten_schon_da_wird_nichts_geschrieben(self) -> None:
        # Wie bei der einzelnen Quellgrafik: In schaubilder/ wird nichts
        # ueberschrieben. Auch die beiden anderen bleiben neben dem Entwurf,
        # sonst fehlten sie beim naechsten Versuch.
        self.lege_freigegebenen_zirkel_an()
        schon_da = self.ordner.lege_schaubild_an("ue-000010-zirkel-2.png")
        vorher = schon_da.read_bytes()

        fertig = self.ordner.starte("sammelimport.py", "uebernehmen", ORDNER, "--kandidat", "5", "")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("ue-000010-zirkel-2.png", zeile_mit(fertig.stdout, "nicht übernommen"))
        self.assertEqual(schon_da.read_bytes(), vorher)
        self.assertEqual(sorted(p.name for p in (self.ordner.pfad / "schaubilder").iterdir()),
                         ["ue-000010-zirkel-2.png"])
        self.assertEqual(list((self.ordner.pfad / "uebungen").glob("ue-000010-*")), [])
        self.assertEqual(len(list(self.entwuerfe.glob("5.quellgrafik-*.png"))), 3)

    @BRAUCHT_PILLOW
    def test_drei_pdfs_mit_bild_ergeben_eine_karte_mit_drei_schaubildern(self) -> None:
        # Der ganze Weg (#39): vorbereiten schneidet aus, der Agent traegt die
        # Liste ein, wie der Auftrag sie vorgibt, und nach der Freigabe zeigt
        # die Karte die Bilder in der Reihenfolge der Spalte Dateien. Die
        # Groesse jedes Bildes verraet, aus welchem Blatt es stammt.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 5, "dateien": ["zirkel.pdf", "station-1.pdf", "station-2.pdf"],
             "ergebnis": "folge"}], quellgrafik_ausschneiden=True)
        for datei, groesse in (("zirkel.pdf", (40, 30)), ("station-1.pdf", (90, 60)),
                               ("station-2.pdf", (30, 20))):
            self.ordner.lege_quell_pdf_an(f"{ORDNER}/{datei}", [datei], bilder=[
                PdfBild(*groesse, deckend=(0, 0, *groesse))])
        vorbereitet = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)
        self.assertEqual(vorbereitet.returncode, 0, vorbereitet.stdout + vorbereitet.stderr)
        liste = re.search(r"`schaubild: \[([^\]]+)\]`",
                          zeile_mit(auftrag_von(self.ordner, 5), "Quellgrafiken")).group(1)
        self.ordner.lege_kartenentwurf_an(ORDNER, 5, typ="folge", titel="Sprungkraftzirkel",
                                          schaubild=liste.split(", "))

        fertig = self.ordner.starte("sammelimport.py", "uebernehmen", ORDNER, "--kandidat", "5", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        karte = (self.ordner.pfad / "uebungen" / "ue-000006-sprungkraftzirkel.md").read_text(
            encoding="utf-8")
        namen = [f"ue-000006-sprungkraftzirkel-{nr}.png" for nr in (1, 2, 3)]
        self.assertIn(f"\nschaubild: [{', '.join(namen)}]\n", karte)
        for name, groesse in zip(namen, ((40, 30), (90, 60), (30, 20))):
            with Image.open(self.ordner.pfad / "schaubilder" / name) as bild:
                self.assertEqual(bild.size, groesse, name)

    def test_ein_schaubild_unter_dem_kartennamen_wird_nicht_ueberschrieben(self) -> None:
        # Unter der naechsten freien ID gibt es noch keine Karte, eine Datei
        # in schaubilder/ kann trotzdem dort liegen, etwa von Hand
        # hingelegt. Bei der Abnahme von Welle 1c ist schon einmal eine
        # Ansicht in schaubilder/ verloren gegangen, weil ein Skript sie
        # ueberschrieb.
        self.lege_freigegebenen_entwurf_an()
        schon_da = self.ordner.lege_schaubild_an("ue-000010-abwehr-vom-kasten.png")
        vorher = schon_da.read_bytes()

        fertig = self.ordner.starte("sammelimport.py", "uebernehmen", ORDNER, "--kandidat", "3", "")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("ue-000010-abwehr-vom-kasten.png",
                      zeile_mit(fertig.stdout, "nicht übernommen"))
        self.assertEqual(schon_da.read_bytes(), vorher)
        self.assertEqual(list((self.ordner.pfad / "uebungen").glob("ue-000010-*")), [])
        self.assertTrue((self.entwuerfe / "3.quellgrafik.png").exists())


class PlaneingabeTest(unittest.TestCase):
    """`vorbereiten --plan` legt an, woraus der Agent den Zerlegungsplan macht.

    Der Agent liest nur diese eine Datei, in einem Aufruf: welche Dateien der
    Quellenordner hat, was in ihren PDFs steht und was die Bibliothek schon
    kennt. Was hier fehlt, sieht er nicht.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def plane(self, **starte):
        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", "--plan", ORDNER, **starte)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return fertig

    def planeingabe(self) -> str:
        return (self.ordner.pfad / "kartenentwuerfe" / ORDNER / "planeingabe.md").read_text(
            encoding="utf-8")

    def genannte_dateien(self) -> list[str]:
        """Die Dateien, die die Planeingabe auffuehrt, je eine Ueberschrift."""
        return re.findall(r"^### `(.+)`$", self.planeingabe(), re.MULTILINE)

    def zu_datei(self, name: str) -> str:
        """Was die Planeingabe unter der Ueberschrift einer Datei sagt."""
        return unter_datei(self.planeingabe(), name)

    def test_die_planeingabe_nennt_jede_datei_auch_aus_unterordnern(self) -> None:
        # PlayDrill sortiert seine Uebungen in Unterordner, und eine Folge kann
        # ueber zwei davon verteilt sein. Der Agent muss sie alle sehen.
        namen = ["seite-01.jpg", "Ü_Abwehr/seite-02.jpg", "Ü_Abwehr/tiefer/notiz.txt"]
        for name in namen:
            self.ordner.lege_quelldatei_an(f"{ORDNER}/{name}", b"")

        self.plane()

        self.assertEqual(sorted(self.genannte_dateien()), sorted(namen))
        # Die Namen stehen relativ zum Quellenordner. Oeffnen muss der Agent
        # die Dateien trotzdem, jedes Foto und jedes PDF ohne Text, also
        # steht der Quellenordner einmal absolut im Kopf.
        kopf = self.planeingabe().split("## Dateien", 1)[0]
        self.assertIn((self.ordner.pfad / "quellen" / ORDNER).resolve().as_posix(), kopf)

    def test_ein_zweiter_lauf_nimmt_nur_dateien_die_in_keiner_zeile_stehen(self) -> None:
        # Nach dem ersten Durchgang sind neue Seiten dazugekommen. Nur sie
        # brauchen einen Plan, die anderen haben schon einen, auch der noch
        # offene Kandidat 2. Die sammelimport.md selbst ist keine Quelle.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["seite-01.jpg"], "status": "importiert",
             "karte": "ue-000001"},
            {"kandidat": 2, "dateien": ["unter/seite-02.jpg", "unter/seite-03.jpg"]},
        ])
        self.ordner.lege_quelldatei_an(f"{ORDNER}/unter/seite-04.jpg", b"")

        self.plane()

        self.assertEqual(self.genannte_dateien(), ["unter/seite-04.jpg"])

    def naechste_nummer(self) -> int:
        """Die naechste freie Kandidatennummer laut Planeingabe."""
        return int(re.search(r"Kandidatennummer: (\d+)", self.planeingabe()).group(1))

    def test_die_planeingabe_nennt_die_naechste_freie_kandidatennummer(self) -> None:
        # Die Nummer bleibt und benennt Entwurf und Auftrag. Finge ein zweiter
        # Lauf wieder bei 1 an, stuende Kandidat 1 zweimal in der Uebersicht.
        # Gezaehlt wird ab der hoechsten, nicht ab der Zahl der Zeilen: Die
        # Luecke entsteht, wenn der Trainer zwei Kandidaten zusammenlegt.
        self.ordner.lege_quelldatei_an(f"{ORDNER}/seite-01.jpg", b"")
        self.plane()
        self.assertEqual(self.naechste_nummer(), 1)

        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["seite-01.jpg"], "status": "importiert",
             "karte": "ue-000001"},
            {"kandidat": 4, "dateien": ["seite-04.jpg"], "ergebnis": "übersprungen",
             "status": "übersprungen"},
            {"kandidat": 2, "dateien": ["seite-02.jpg"]},
        ])
        self.ordner.lege_quelldatei_an(f"{ORDNER}/seite-05.jpg", b"")
        self.plane()
        self.assertEqual(self.naechste_nummer(), 5)

    def test_ohne_neue_dateien_entsteht_keine_planeingabe(self) -> None:
        # Dann gibt es nichts zu planen, und der Skill soll keinen Agenten
        # fuer eine leere Liste starten.
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["seite-01.jpg"]}])

        fertig = self.plane()

        self.assertIn("Keine neuen Dateien", fertig.stdout)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_ein_umlaut_im_pfad_zaehlt_gleich_wie_das_dateisystem_ihn_auch_schreibt(self) -> None:
        # Jeder Uebungsordner von PlayDrill beginnt mit einem grossen U mit
        # Umlaut. macOS legt ihn als U und zwei Punkte ab, zwei Zeichen,
        # Windows als eines. Kommt der Ordner ueber Nextcloud von einem Mac,
        # stuende sonst jede Datei darin beim zweiten Lauf als neu da, obwohl
        # der Plan sie schon hat.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["Ü_Abwehr/seite-01.jpg"]}])
        quellordner = self.ordner.pfad / "quellen" / ORDNER
        (quellordner / "Ü_Abwehr").rename(
            quellordner / unicodedata.normalize("NFD", "Ü_Abwehr"))

        fertig = self.plane()

        self.assertIn("Keine neuen Dateien", fertig.stdout)

    def test_ohne_laesst_einen_ordner_mit_allem_darunter_und_eine_datei_aus(self) -> None:
        # PlayDrill hat neben den Uebungsordnern Aufstellungen, Vorlagen und
        # die Logs des Trainers. Ohne `ohne:` kaeme jede dieser Dateien bei
        # jedem Lauf als neu wieder. Der Nachbarordner mit demselben Anfang
        # bleibt drin: ausgelassen wird der Ordner, nicht jeder Name, der so
        # beginnt.
        self.ordner.lege_quellenordner_an(
            ORDNER, [], freigegeben=None, ohne=["Ü_In Bearbeitung", "IMPORT_LOG.md"])
        for name in ("Ü_In Bearbeitung/a.pdf", "Ü_In Bearbeitung/tiefer/b.pdf",
                     "IMPORT_LOG.md", "Ü_In Bearbeitung-alt/c.pdf", "seite-01.jpg"):
            self.ordner.lege_quelldatei_an(f"{ORDNER}/{name}", b"")

        self.plane()

        self.assertEqual(sorted(self.genannte_dateien()),
                         ["seite-01.jpg", "Ü_In Bearbeitung-alt/c.pdf"])

    def test_was_ohne_auslaesst_gilt_beim_zweiten_lauf_nicht_als_neu(self) -> None:
        # Der Plan hat keine Zeile fuer die ausgelassenen Dateien, und das
        # soll so bleiben. Beim zweiten Lauf ist deshalb nichts neu.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["seite-01.jpg"]}], ohne=["Aufst_Pos_D"])
        self.ordner.lege_quelldatei_an(f"{ORDNER}/Aufst_Pos_D/6-2.pdf", b"")

        fertig = self.plane()

        self.assertIn("Keine neuen Dateien", fertig.stdout)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_ohne_als_liste_in_blockform_bricht_ab(self) -> None:
        # Der Parser liest eine Liste aus `- `-Zeilen als leer (DATENMODELL.md).
        # Still uebergangen kaeme jede ausgelassene Datei wieder in die
        # Planeingabe, bei PlayDrill 85 Stueck.
        datei = self.ordner.lege_quellenordner_an(ORDNER, [], freigegeben=None)
        text = datei.read_text(encoding="utf-8")
        datei.write_text(text.replace("---\n\n", "ohne:\n  - Aufst_Pos_D\n---\n\n", 1),
                         encoding="utf-8")
        self.ordner.lege_quelldatei_an(f"{ORDNER}/Aufst_Pos_D/6-2.pdf", b"")

        fertig = self.ordner.starte("sammelimport.py", "vorbereiten", "--plan", ORDNER)

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("eckigen Klammern", zeile_mit(fertig.stdout, "ohne"))
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    @BRAUCHT_PDFTOTEXT
    def test_bei_pdfs_steht_ihr_text_in_der_planeingabe(self) -> None:
        # Der Text steht unter seiner Datei, sonst laesst sich kein Uebersichtsblatt
        # seinen Stationsblaettern zuordnen. Der Umlaut zeigt, dass pdftotext UTF-8
        # schreibt: Xpdf aus Git fuer Windows schreibt sonst Latin-1.
        self.ordner.lege_quell_pdf_an(
            f"{ORDNER}/Ü_Abwehr/kasten.pdf",
            ["Abwehr vom Kasten", "Ausführung: Der Trainer schlägt vom Kasten."])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/Ü_Abwehr/zirkel.pdf", ["Sprungkraftzirkel"])

        self.plane()

        kasten = self.zu_datei("Ü_Abwehr/kasten.pdf")
        self.assertIn("Abwehr vom Kasten", kasten)
        self.assertIn("Ausführung: Der Trainer schlägt vom Kasten.", kasten)
        self.assertNotIn("Sprungkraftzirkel", kasten)
        self.assertIn("Sprungkraftzirkel", self.zu_datei("Ü_Abwehr/zirkel.pdf"))

    @BRAUCHT_PDFTOTEXT
    def test_ein_pdf_ohne_text_sagt_dem_agenten_dass_er_es_selbst_lesen_muss(self) -> None:
        # Ein eingescanntes Blatt hat keine Textebene, eine kaputte Datei
        # liest pdftotext gar nicht. Eine leere Ueberschrift hiesse fuer den
        # Agenten nur, dass nichts dasteht, und er plante nach dem Dateinamen.
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/scan.pdf", [])
        self.ordner.lege_quelldatei_an(f"{ORDNER}/kaputt.pdf", b"kein PDF")

        self.plane()

        for name in ("scan.pdf", "kaputt.pdf"):
            self.assertIn("selbst lesen", self.zu_datei(name))

    def lege_stationsuebersicht_an(self) -> None:
        """Ein Uebersichtsblatt, dessen Stationsliste weit ueber die ersten Zeilen reicht."""
        self.ordner.lege_quell_pdf_an(
            f"{ORDNER}/zirkel.pdf",
            ["Stationsübersicht Sprungkraftzirkel",
             *(f"Station {n}: Sprünge über die kleine Kiste, 30 Sekunden" for n in range(1, 20)),
             "Station 20: Auslaufen und Dehnen"])

    @BRAUCHT_PDFTOTEXT
    def test_passt_der_text_in_einen_aufruf_kommt_er_ganz(self) -> None:
        # So bekommt ein Uebersichtsblatt seine ganze Stationsliste, und der
        # Agent erkennt die Stationsblaetter, die zu ihm gehoeren.
        self.lege_stationsuebersicht_an()

        self.plane()

        self.assertIn("Station 20: Auslaufen und Dehnen", self.zu_datei("zirkel.pdf"))

    @BRAUCHT_PDFTOTEXT
    def test_liegt_der_text_ueber_der_schwelle_stehen_nur_die_ersten_zeilen_da(self) -> None:
        # Das dicke PDF bringt den Ordner deutlich ueber die Schwelle im
        # Skript, gut 500 000 Zeichen gegen 400 000. Ganz passte der Text
        # nicht mehr in den Aufruf des Agenten. Dann bekommt jede Datei ihre
        # ersten Zeilen, das dicke PDF genauso wie das Uebersichtsblatt.
        self.lege_stationsuebersicht_an()
        zeile = "Aufbau und Ablauf der Übung, dazu die Dosierung. " * 2
        self.ordner.lege_quell_pdf_an(
            f"{ORDNER}/dick.pdf",
            *([f"Zeile {seite * 60 + n:04d}: {zeile}" for n in range(60)] for seite in range(100)))

        fertig = self.plane()

        zirkel = self.zu_datei("zirkel.pdf")
        self.assertIn("Stationsübersicht Sprungkraftzirkel", zirkel)
        self.assertNotIn("Station 20", zirkel)
        dick = self.zu_datei("dick.pdf")
        self.assertIn("Zeile 0000", dick)
        self.assertNotIn("Zeile 5999", dick)
        self.assertIn("ersten Zeilen", fertig.stdout)
        # Auch der Agent muss es wissen, sonst haelt er den Anfang fuer alles.
        self.assertIn("ersten Zeilen", self.planeingabe().split("## Dateien", 1)[0])

    def bibliothek(self) -> dict[str, dict[str, str]]:
        """Die Bibliotheksliste der Planeingabe, je ID eine Zeile."""
        abschnitt = self.planeingabe().split("## Bibliothek", 1)[1]
        zeilen = [[z.strip() for z in zeile.strip().strip("|").split("|")]
                  for zeile in abschnitt.splitlines() if zeile.startswith("|")]
        kopf, _trenner, *rest = zeilen
        return {z[0]: dict(zip(kopf, z)) for z in rest}

    def test_die_bibliotheksliste_nennt_jede_karte_und_markiert_die_aus_diesem_ordner(self) -> None:
        # Daran erkennt der Agent, was schon importiert ist, und fuehrt es mit
        # seiner ID, statt es ein zweites Mal entwerfen zu lassen. Eine Karte
        # ueber zwei Seiten nennt beide Dateien. Ein Ordner, der nur genauso
        # anfaengt, ist ein anderer.
        self.ordner.lege_karte_an(id="ue-000006", titel="Abwehr vom Kasten", element=["abwehr"],
                                  quelldatei=f"{ORDNER}/Ü_Abwehr/kasten.pdf")
        self.ordner.lege_karte_an(id="ue-000007", titel="Über zwei Seiten",
                                  quelldatei=f"{ORDNER}/seite-01.jpg, {ORDNER}/seite-02.jpg")
        self.ordner.lege_karte_an(id="ue-000008", titel="Aus dem alten Stapel",
                                  quelldatei=f"{ORDNER}-alt/seite-01.jpg")
        self.ordner.lege_quelldatei_an(f"{ORDNER}/seite-09.jpg", b"")

        self.plane()

        liste = self.bibliothek()
        self.assertEqual(sorted(liste), sorted(self.ordner.ids))
        kasten = liste["ue-000006"]
        self.assertEqual(kasten["Titel"], "Abwehr vom Kasten")
        self.assertEqual(kasten["Element"], "abwehr")
        self.assertEqual(kasten["quelldatei"], f"{ORDNER}/Ü_Abwehr/kasten.pdf")
        self.assertEqual({uid for uid, zeile in liste.items() if zeile["Aus diesem Ordner"]},
                         {"ue-000006", "ue-000007"})

    def test_ein_foto_ueber_2_mb_ergibt_den_hinweis_auf_die_bildaufbereitung(self) -> None:
        # So schwer ist eine abfotografierte Magazinseite mit 50 Megapixeln.
        # Der Agent kann sie nicht oeffnen, weder fuer den Zerlegungsplan noch
        # fuer den Entwurf. Zufallsbytes reichen, der Hinweis richtet sich nach der
        # Dateigroesse, und so laeuft der Test auch ohne Pillow.
        self.ordner.lege_quelldatei_an(f"{ORDNER}/unter/seite-01.jpg", os.urandom(3 * 1024 * 1024))
        self.ordner.lege_quelldatei_an(f"{ORDNER}/seite-02.jpg", b"klein genug")

        fertig = self.plane()

        self.assertIn("bilder_aufbereiten.py", fertig.stdout)
        self.assertIn("unter/seite-01.jpg", fertig.stdout)
        self.assertNotIn("seite-02.jpg", fertig.stdout)

    def test_ein_schweres_foto_unter_ohne_ergibt_keinen_hinweis(self) -> None:
        # Was `ohne:` auslaesst, oeffnet kein Agent. Der Hinweis kaeme sonst
        # bei jedem Lauf wieder, fuer ein Foto, das niemand lesen muss.
        self.ordner.lege_quellenordner_an(ORDNER, [], freigegeben=None, ohne=["Vorlagen"])
        self.ordner.lege_quelldatei_an(f"{ORDNER}/Vorlagen/seite-01.jpg",
                                       os.urandom(3 * 1024 * 1024))
        self.ordner.lege_quelldatei_an(f"{ORDNER}/seite-02.jpg", b"klein genug")

        fertig = self.plane()

        self.assertNotIn("bilder_aufbereiten.py", fertig.stdout)
        self.assertNotIn("seite-01.jpg", fertig.stdout)

    def test_ohne_pdftotext_gibt_es_einen_hinweis_und_die_eingabe_ohne_text(self) -> None:
        # Ein Mittrainer auf dem Mac ohne Poppler. Der Sammelimport wird fuer
        # ihn teurer, weil der Agent die PDFs selbst liest, aber er laeuft
        # (ADR-0008). Der PATH zeigt auf einen leeren Ordner: Dort gibt es
        # weder pdftotext noch git.exe, neben dem das Skript sonst sucht.
        leer = Path(tempfile.mkdtemp(prefix="ohne-pdftotext-"))
        self.addCleanup(shutil.rmtree, leer, True)
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/a.pdf", ["Abwehr vom Kasten"])
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/b.pdf", ["Sprungkraftzirkel"])

        fertig = self.plane(umgebung={"PATH": str(leer)})

        self.assertEqual(fertig.stdout.count("pdftotext fehlt"), 1, fertig.stdout)
        self.assertIn("brew install poppler", fertig.stdout)
        self.assertEqual(self.genannte_dateien(), ["a.pdf", "b.pdf"])
        self.assertNotIn("Abwehr vom Kasten", self.planeingabe())
        self.assertIn("selbst lesen", self.zu_datei("a.pdf"))


class PruefenTest(unittest.TestCase):
    """`pruefen` setzt den Status allein aus dem, was auf der Platte liegt.

    Die Rueckmeldung des Agenten zaehlt nicht: Im Probelauf hatten sechs
    Aufrufe ihren Entwurf geschrieben und brachen erst bei der Rueckmeldung ab.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def plane(self, *kandidaten: dict) -> None:
        """Der freigegebene Plan. Ohne Angabe ein offener Kandidat 1 mit `a.pdf`."""
        self.ordner.lege_quellenordner_an(
            ORDNER, list(kandidaten) or [{"kandidat": 1, "dateien": ["a.pdf"]}])

    def pruefe(self) -> dict[str, dict[str, str]]:
        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return self.ordner.uebersicht(ORDNER)

    def test_ohne_entwurf_bleibt_der_kandidat_offen_mit_grund(self) -> None:
        # Ein Kandidat, der als bereit gefuehrt wird, dessen Entwurf aber
        # nicht mehr da ist. Die Zeile folgt der Platte, nicht ihrem Stand.
        self.plane({"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"})

        zeile = self.pruefe()["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("kein Entwurf", zeile["Notiz"])

    def test_ein_entwurf_ohne_rueckfrage_ist_bereit(self) -> None:
        self.plane()
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Ohne Rückfrage",
            vorschlaege=["`level_max`: Technikübung, die Schwierigkeit steuert der Ball."])

        zeile = self.pruefe()["1"]

        self.assertEqual(zeile["Status"], "bereit")
        self.assertEqual(zeile["Notiz"], "")

    def test_eine_rueckfrage_mit_vermutung_ist_bereit(self) -> None:
        # Die Vermutung steht schon im Text des Entwurfs. Der Trainer bestaetigt
        # sie in der Tabelle wie einen Vorschlag, einzeln gefragt wird nicht.
        self.plane()
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Mit Vermutung",
            rueckfragen=["Wie viele Spieler braucht die Übung? "
                         "Vermutung im Entwurf: mindestens 8, aus den Rollen."])

        zeile = self.pruefe()["1"]

        self.assertEqual(zeile["Status"], "bereit")

    def test_eine_rueckfrage_ohne_vermutung_ergibt_rueckfrage(self) -> None:
        self.plane()
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Ohne Vermutung",
            rueckfragen=["Wie viele Spieler braucht die Übung? "
                         "Vermutung im Entwurf: mindestens 8, aus den Rollen.",
                         "Wohin kommen die gefangenen Bälle zurück? "
                         "Vermutung im Entwurf: keine"])

        zeile = self.pruefe()["1"]

        self.assertEqual(zeile["Status"], "rückfrage")

    def test_ein_fehlerhafter_entwurf_geht_zurueck_auf_offen_mit_grund(self) -> None:
        # Je Kandidat ein Fehler, sonst ist der Entwurf heil. Der Agent hat
        # nicht nachfragen koennen, und was hier durchkaeme, stuende nach der
        # Freigabe so auf der Karte. Die Notiz nennt, woran es lag, damit der
        # Trainer es sieht, bevor der naechste Durchgang neu entwirft.
        quellen = self.ordner.pfad / "quellen"
        faelle = {
            "unbekanntes Element": ({"element": ["aufwaermen"]}, "aufwaermen"),
            "unbekannte Kennung": ({"schwerpunkt": ["gibt-es-nicht"]}, "gibt-es-nicht"),
            "Kennung mit falscher Disziplin": (
                {"disziplin": ["halle"], "schwerpunkt": ["nur-beach"]}, "nur-beach"),
            # Ohne Klammern liest der Parser einen Text, keine Liste. Der
            # Grund soll das sagen und nicht jeden Buchstaben als Kennung melden.
            "Kennung ohne eckige Klammern": ({"schwerpunkt": "annahme"}, "eckigen Klammern"),
            "quelldatei ohne Datei dahinter": (
                {"quelldatei": f"{ORDNER}/fehlt.pdf"}, "fehlt.pdf"),
            "quelldatei leer": ({"quelldatei": None}, "quelldatei"),
            # Die Datei gibt es, aber der Pfad stimmt nur auf diesem Rechner.
            "absolute quelldatei": (
                {"quelldatei": (quellen / ORDNER / "a.pdf").resolve().as_posix()}, "absolut"),
            "Rückfrage ohne Vermutungsmarke": (
                {"rueckfragen": ["Wie viele Spieler braucht die Übung?"]},
                "Vermutung im Entwurf"),
            "Rückfrage mit zwei Fragen": (
                {"rueckfragen": ["Wie viele Spieler? Und wie viele Bälle? "
                                 "Vermutung im Entwurf: keine"]}, "Fragezeichen"),
            # Die ID vergibt erst uebernehmen (ADR-0010).
            "Entwurf mit id": ({"id": "ue-000099"}, "ue-000099"),
            "fehlendes Feld": ({"spieler_min": OHNE}, "spieler_min"),
            # Ohne Feld oder Ueberschrift vorn laesst sich der Vorschlag
            # keiner Spalte der Tabelle zuordnen.
            "Vorschlag ohne Ziel": (
                {"vorschlaege": ["Die Schwierigkeit steuert der Ball."]}, "Backticks"),
            "Vorschlag zu einem Feld, das es nicht gibt": (
                {"vorschlaege": ["`spielerzahl`: aus den Rollen."]}, "spielerzahl"),
            # Die Spalte "aus dem Bild" nennt den Abschnitt, damit der Trainer
            # ihn im Entwurf findet. Vertippt faende er ihn nicht.
            "Vorschlag zu einem Abschnitt, den es nicht gibt": (
                {"vorschlaege": ["`## Ablaf`, Schritt 2: aus den Pfeilen im Bild."]}, "Ablaf"),
        }
        self.plane(*({"kandidat": nr, "dateien": ["a.pdf"]} for nr in range(len(faelle) + 1)))
        self.ordner.lege_kartenentwurf_an(ORDNER, 0, titel="Heil")
        for nr, (fall, (felder, _)) in enumerate(faelle.items(), 1):
            self.ordner.lege_kartenentwurf_an(ORDNER, nr, titel=fall, **felder)

        uebersicht = self.pruefe()

        self.assertEqual(uebersicht["0"]["Status"], "bereit", uebersicht["0"]["Notiz"])
        for nr, (fall, (_, stichwort)) in enumerate(faelle.items(), 1):
            with self.subTest(fall):
                self.assertEqual(uebersicht[str(nr)]["Status"], "offen")
                self.assertIn(stichwort, uebersicht[str(nr)]["Notiz"])

    def test_zwei_seiten_in_quelldatei_bestehen_wenn_es_beide_gibt(self) -> None:
        # Eine Uebung ueber zwei Magazinseiten nennt beide, durch Komma
        # getrennt (DATENMODELL.md). Fehlt eine davon, faellt der Entwurf durch.
        self.plane({"kandidat": 1, "dateien": ["seite-24.jpg", "seite-25.jpg"]},
                   {"kandidat": 2, "dateien": ["seite-26.jpg"]})
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Beide da")
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 2, titel="Eine fehlt",
            quelldatei=f"{ORDNER}/seite-26.jpg, {ORDNER}/seite-27.jpg")

        uebersicht = self.pruefe()

        self.assertEqual(uebersicht["1"]["Status"], "bereit", uebersicht["1"]["Notiz"])
        self.assertEqual(uebersicht["2"]["Status"], "offen")
        self.assertIn("seite-27.jpg", uebersicht["2"]["Notiz"])

    def test_zwei_dateien_von_denen_eine_ein_komma_im_namen_traegt(self) -> None:
        # Am Komma getrennt hiesse die erste "stapel/a", und jeder neue
        # Entwurf fiele wieder durch. Fehlt eine Datei, nennt die Notiz genau
        # sie, auch wenn sie vorn steht, und nicht ein Bruchstueck der anderen.
        # Das gilt auch, wenn die fehlende selbst ein Komma traegt.
        self.plane({"kandidat": 1, "dateien": ["a, b.pdf", "c.pdf"]},
                   {"kandidat": 2, "dateien": ["d, e.pdf"]},
                   {"kandidat": 3, "dateien": ["d, e.pdf"]},
                   {"kandidat": 4, "dateien": ["c.pdf"]})
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Beide da", quelldatei=f"{ORDNER}/a, b.pdf, {ORDNER}/c.pdf")
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 2, titel="Hinten fehlt eine",
            quelldatei=f"{ORDNER}/d, e.pdf, {ORDNER}/fehlt-hinten.pdf")
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 3, titel="Vorn fehlt eine",
            quelldatei=f"{ORDNER}/fehlt-vorn.pdf, {ORDNER}/d, e.pdf")
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 4, titel="Die mit Komma fehlt",
            quelldatei=f"{ORDNER}/fehlt, mit komma.pdf, {ORDNER}/c.pdf")

        uebersicht = self.pruefe()

        self.assertEqual(uebersicht["1"]["Status"], "bereit", uebersicht["1"]["Notiz"])
        for nr, fehlt in (("2", "fehlt-hinten.pdf"), ("3", "fehlt-vorn.pdf"),
                          ("4", "fehlt, mit komma.pdf")):
            with self.subTest(kandidat=nr):
                self.assertEqual(uebersicht[nr]["Status"], "offen")
                self.assertEqual(uebersicht[nr]["Notiz"],
                                 f"quelldatei {ORDNER}/{fehlt} gibt es unter quellen/ nicht")

    def freigabe(self) -> dict[str, dict]:
        """`pruefen --json`, je Kandidat, was die Freigabe im Chat braucht."""
        fertig = self.ordner.starte("sammelimport.py", "pruefen", "--json", ORDNER)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return {k["kandidat"]: k for k in json.loads(fertig.stdout)["kandidaten"]}

    def test_json_trennt_vorschlaege_zu_feldern_von_vorschlaegen_zu_textstellen(self) -> None:
        # Die Vorschlaege zu Feldern stehen in der Tabelle in ihrer Spalte, die
        # zu Textstellen ergeben die Spalte "aus dem Bild". Getrennt wird am
        # Ziel in Backticks vorn: ein Feld oder die Ueberschrift eines
        # Abschnitts.
        self.plane()
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Mit Vorschlägen", spieler_min=8,
                                          vorschlaege=[
            "`level_max`: Technikübung, die Schwierigkeit steuert der Ball.",
            "`## Ablauf`, Schritt 2: Die Wege kommen aus den gelben Pfeilen im Bild.",
            "`spieler_min`: aus den Rollen im Bild gezählt.",
        ])

        kandidat = self.freigabe()["1"]

        self.assertEqual(kandidat["status"], "bereit")
        self.assertEqual(kandidat["vorschlaege"]["felder"], [
            {"feld": "level_max", "text": "Technikübung, die Schwierigkeit steuert der Ball."},
            {"feld": "spieler_min", "text": "aus den Rollen im Bild gezählt."},
        ])
        self.assertEqual(kandidat["vorschlaege"]["textstellen"], [
            {"abschnitt": "## Ablauf", "wo": "Schritt 2",
             "text": "Die Wege kommen aus den gelben Pfeilen im Bild."},
        ])
        # Die Felder fuer die Tabelle, so wie sie im Entwurf stehen. Der
        # Trainer korrigiert dort etwa die Spielerzahl direkt.
        self.assertEqual(kandidat["felder"]["titel"], "Mit Vorschlägen")
        self.assertEqual(kandidat["felder"]["spieler_min"], 8)
        self.assertEqual(kandidat["felder"]["disziplin"], ["halle"])

    def test_json_trennt_rueckfragen_mit_vermutung_von_denen_ohne(self) -> None:
        # Die ohne Vermutung fragt der Skill einzeln, mit der Quellgrafik. Die mit
        # Vermutung bestaetigt der Trainer in der Tabelle wie einen Vorschlag.
        self.plane()
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Mit Rückfragen", rueckfragen=[
            "Wie viele Spieler braucht die Übung? "
            "Vermutung im Entwurf: mindestens 8, aus den Rollen.",
            "Wohin kommen die gefangenen Bälle zurück? Vermutung im Entwurf: keine",
        ])

        kandidat = self.freigabe()["1"]

        self.assertEqual(kandidat["status"], "rückfrage")
        self.assertEqual(kandidat["rueckfragen"]["mit_vermutung"], [
            {"nr": 1, "frage": "Wie viele Spieler braucht die Übung?",
             "vermutung": "mindestens 8, aus den Rollen."},
        ])
        self.assertEqual(kandidat["rueckfragen"]["ohne_vermutung"], [
            {"nr": 2, "frage": "Wohin kommen die gefangenen Bälle zurück?"},
        ])
        self.assertFalse(kandidat["ablauf_aus_dem_bild"])
        self.assertEqual(kandidat["entwurf"], (
            self.ordner.pfad / "kartenentwuerfe" / ORDNER / "1.md").resolve().as_posix())

    def test_json_nennt_jede_quellgrafik_in_der_reihenfolge_des_entwurfs(self) -> None:
        # Bei den Einzelfragen zeigt der Skill die Quellgrafiken im Chat, bei
        # mehreren alle (#36, #39). Kandidat 2 hat keine, die Liste ist leer.
        self.plane({"kandidat": 1, "dateien": ["zirkel.pdf", "station-1.pdf"], "ergebnis": "folge"},
                   {"kandidat": 2, "dateien": ["b.pdf"]})
        entwuerfe = self.ordner.pfad / "kartenentwuerfe" / ORDNER
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, typ="folge", titel="Zirkel",
                                          schaubild=["1.quellgrafik-1.png", "1.quellgrafik-2.png"])
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Ohne Bild")
        for name in ("1.quellgrafik-1.png", "1.quellgrafik-2.png"):
            (entwuerfe / name).write_bytes(b"ein Bild")

        freigabe = self.freigabe()

        self.assertEqual(freigabe["1"]["status"], "bereit", freigabe["1"]["notiz"])
        self.assertEqual(freigabe["1"]["quellgrafiken"],
                         [(entwuerfe / name).resolve().as_posix()
                          for name in ("1.quellgrafik-1.png", "1.quellgrafik-2.png")])
        self.assertEqual(freigabe["2"]["quellgrafiken"], [])
        # Ohne Auftrag, wie hier, fehlt auch keine.
        self.assertEqual(freigabe["2"]["quellgrafik_fehlt"], [])

    def test_json_nennt_nur_kandidaten_mit_entwurf(self) -> None:
        # Bei PlayDrill warten nach dem ersten Durchgang ueber 200 Kandidaten
        # ohne Entwurf. Fuer die Freigabe haben sie nichts, im Chat kosteten sie
        # bei jedem Aufruf zehntausende Tokens (#36). Die Uebersicht traegt sie
        # trotzdem.
        self.plane({"kandidat": 1, "dateien": ["a.pdf"]}, {"kandidat": 2, "dateien": ["b.pdf"]})
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Mit Entwurf")

        freigabe = self.freigabe()

        self.assertEqual(list(freigabe), ["1"])
        zeile = self.ordner.uebersicht(ORDNER)["2"]
        self.assertEqual((zeile["Status"], zeile["Notiz"]), ("offen", "kein Entwurf"))

    def test_json_setzt_den_status_wie_ohne_json(self) -> None:
        # Der Skill ruft nach einem Durchgang nur `pruefen --json` auf. Auch
        # dann muss die Uebersicht stimmen, und ein abgewiesener Entwurf
        # traegt seinen Grund, statt Felder fuer die Tabelle.
        self.plane()
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Abgewiesen", element=["aufwaermen"])

        kandidat = self.freigabe()["1"]

        self.assertEqual(kandidat["status"], "offen")
        self.assertIn("aufwaermen", kandidat["notiz"])
        self.assertEqual(kandidat["felder"], {})
        zeile = self.ordner.uebersicht(ORDNER)["1"]
        self.assertEqual((zeile["Status"], zeile["Notiz"]), ("offen", kandidat["notiz"]))

    @BRAUCHT_PDFTOTEXT
    def test_ein_ablauf_aus_dem_bild_ergibt_rueckfrage_auch_mit_vermutung(self) -> None:
        # Die Vermutung des Agenten ist hier der ganze Ablauf. Den bestaetigt
        # der Trainer nicht in einer Tabellenzeile, sondern einzeln, mit
        # Quellgrafik und Ablauftext vor sich (#29, Geschichte 22).
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"]}],
                                          **PLAYDRILL)
        self.ordner.lege_quell_pdf_an(
            f"{ORDNER}/a.pdf", [*PLAYDRILL_KOPF, "Ausführung: hier Könnte ihr Text stehen"])
        vorbereitet = self.ordner.starte("sammelimport.py", "vorbereiten", ORDNER)
        self.assertEqual(vorbereitet.returncode, 0, vorbereitet.stdout + vorbereitet.stderr)
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Aus dem Bild",
            rueckfragen=["Laufen die Abwehrspieler nach jedem Ball hinten an? "
                         "Vermutung im Entwurf: ja, so zeigen es die Pfeile."])

        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        zeile = self.ordner.uebersicht(ORDNER)["1"]
        self.assertEqual(zeile["Status"], "rückfrage")
        self.assertIn("Ablauf aus dem Bild", zeile["Notiz"])

    def test_ohne_abschnitt_freigabe_bleibt_der_kandidat_offen(self) -> None:
        # Ohne den Abschnitt weiss niemand, was der Entwurf gedeutet und wo er
        # eine Luecke gefunden hat. Er wird neu entworfen.
        self.plane()
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Ohne Freigabe", freigabe="")

        zeile = self.pruefe()["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("## Freigabe", zeile["Notiz"])

    def test_ohne_liste_der_rueckfragen_bleibt_der_kandidat_offen(self) -> None:
        # Beide Listen stehen immer da, eine leere heisst "keine". Fehlt eine,
        # ist nicht zu unterscheiden, ob der Agent nichts gefunden oder den
        # Entwurf nicht fertig geschrieben hat.
        self.plane()
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Nur Vorschläge", freigabe="## Freigabe\n\nVorschläge: keine\n")

        zeile = self.pruefe()["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("Rückfragen", zeile["Notiz"])

    def test_ohne_lesbares_frontmatter_bleibt_der_kandidat_offen(self) -> None:
        self.plane()
        entwurf = self.ordner.pfad / "kartenentwuerfe" / ORDNER / "1.md"
        entwurf.parent.mkdir(parents=True)
        entwurf.write_text("# Abgebrochen\n\nDer Agent kam nur bis hier.\n", encoding="utf-8")

        zeile = self.pruefe()["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("Frontmatter", zeile["Notiz"])

    def test_zeilen_mit_importiert_bleiben_unberuehrt(self) -> None:
        # Eine uebernommene Karte hat keinen Entwurf mehr. Faende pruefen sie
        # "offen", entwuerfe der naechste Durchgang dieselbe Uebung ein
        # zweites Mal.
        self.plane({"kandidat": 1, "dateien": ["a.pdf"], "status": "importiert",
                    "karte": "ue-000001", "notiz": "spieler_min auf 6"})

        uebersicht = self.pruefe()

        self.assertEqual(uebersicht["1"]["Status"], "importiert")
        self.assertEqual(uebersicht["1"]["Karte"], "ue-000001")
        self.assertEqual(uebersicht["1"]["Notiz"], "spieler_min auf 6")

    def test_eine_erledigte_zeile_bleibt_zeichengenau_stehen(self) -> None:
        # Unberuehrt heisst unberuehrt. Eine von Hand geschriebene Notiz mit
        # einem `|` darin und doppelten Leerzeichen ueberstuende sonst den
        # naechsten Aufruf nicht, obwohl an der Zeile nichts zu tun war.
        datei = self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "importiert", "karte": "ue-000001"},
            {"kandidat": 2, "dateien": ["b.pdf"]},
        ])
        text = datei.read_text(encoding="utf-8")
        von_hand = "| 1 | `a.pdf` | Übung  aus dem Test | uebung | importiert | ue-000001 | A | B |"
        datei.write_text(
            text.replace(zeile_mit(text, "| importiert |"), von_hand), encoding="utf-8")

        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)

        self.assertEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn(von_hand + "\n", datei.read_text(encoding="utf-8"))


class UebernehmenTest(unittest.TestCase):
    """`uebernehmen` macht aus freigegebenen Entwuerfen Karten mit ID (ADR-0010)."""

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)
        # Eine Luecke in den IDs des Fixtures: Die naechste freie ID ist die
        # hoechste plus eins, nicht die Zahl der Karten plus eins.
        self.ordner.lege_karte_an(id="ue-000009", titel="Die bisher höchste ID")

    def uebernimm(self, *argumente: str):
        return self.ordner.starte("sammelimport.py", "uebernehmen", ORDNER, *argumente)

    def karte(self, uid: str) -> str:
        treffer = list((self.ordner.pfad / "uebungen").glob(f"{uid}-*.md"))
        self.assertEqual(len(treffer), 1, [p.name for p in treffer])
        return treffer[0].read_text(encoding="utf-8")

    def test_die_karte_bekommt_die_naechste_freie_id_und_das_datum_von_heute(self) -> None:
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"}])
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Annahme über die Diagonale",
            vorschlaege=["`level_max`: Technikübung, die Schwierigkeit steuert der Ball."])

        fertig = self.uebernimm("--kandidat", "1", "unverändert")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        karte = self.karte("ue-000010")
        self.assertIn("\nid: ue-000010\n", karte)
        self.assertIn(f"\nangelegt: {date.today().isoformat()}\n", karte)
        self.assertIn("\n## Ablauf\n", karte)
        # Vorschlaege und Rueckfragen sind mit der Freigabe erledigt. Auf der
        # Karte in der Halle haetten sie nichts zu suchen.
        self.assertNotIn("## Freigabe", karte)
        self.assertNotIn("Vorschläge", karte)

    def test_danach_ist_der_entwurf_weg_und_die_uebersicht_zeigt_die_karte(self) -> None:
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"]},
        ])
        entwurf = self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Freigegeben")
        auftrag = entwurf.with_name("1.auftrag.md")
        auftrag.write_text("# Auftrag aus einem frueheren Durchgang\n", encoding="utf-8")

        fertig = self.uebernimm("--kandidat", "1", "spieler_min auf 6")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertFalse(entwurf.exists())
        self.assertFalse(auftrag.exists())
        zeile = self.ordner.uebersicht(ORDNER)["1"]
        self.assertEqual(
            (zeile["Status"], zeile["Karte"], zeile["Notiz"]),
            ("importiert", "ue-000010", "spieler_min auf 6"))

    def test_zwei_kandidaten_bekommen_aufeinanderfolgende_ids(self) -> None:
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Erster Kandidat")
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Zweiter Kandidat")

        fertig = self.uebernimm("--kandidat", "1", "", "--kandidat", "2", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("titel: \"Erster Kandidat\"", self.karte("ue-000010"))
        self.assertIn("titel: \"Zweiter Kandidat\"", self.karte("ue-000011"))

    def test_die_id_kommt_aus_dem_bereich_des_trainers_an_diesem_rechner(self) -> None:
        # Dieselbe naechste ID wie `suche.py --naechste-id` (ADR-0011). Die
        # Karten des Fixtures gehoeren Trainer 00, an diesem Rechner sitzt
        # einer mit 01, und dessen Bereich ist noch leer.
        self.ordner.setze_trainer({
            "test": {"nummer": "00", "rechner": ["ANDERER-RECHNER"]},
            "zweiter": {"nummer": "01", "rechner": [socket.gethostname()]},
        })
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"}])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Vom zweiten Trainer")

        fertig = self.uebernimm("--kandidat", "1", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("\nid: ue-010001\n", self.karte("ue-010001"))
        self.assertEqual(self.ordner.uebersicht(ORDNER)["1"]["Karte"], "ue-010001")

    def test_gehoert_der_rechner_zu_keinem_trainer_wird_nichts_geschrieben(self) -> None:
        self.ordner.setze_trainer({"test": {"nummer": "00", "rechner": ["ANDERER-RECHNER"]}})
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"}])
        entwurf = self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Wartet auf seine ID")

        fertig = self.uebernimm("--kandidat", "1", "")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn(socket.gethostname(), fertig.stdout)
        self.assertEqual(len(list((self.ordner.pfad / "uebungen").glob("*.md"))),
                         len(self.ordner.ids))
        self.assertTrue(entwurf.exists())
        self.assertEqual(self.ordner.uebersicht(ORDNER)["1"]["Status"], "bereit")

    def test_fehlt_der_quellenordner_bricht_es_ab_bevor_es_etwas_schreibt(self) -> None:
        # Ein Rechner, dessen Nextcloud quellen/ nicht abgleicht. Die
        # Entwuerfe liegen da, die Uebersicht und die Quellen nicht. Die
        # Meldung sagt, welcher Ordner fehlt, statt nach einer Datei darin
        # zu fragen.
        entwurf = self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Ohne Quellen")
        vorher = sorted(p.name for p in (self.ordner.pfad / "uebungen").iterdir())

        fertig = self.uebernimm("--kandidat", "1", "")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn(f"quellen/{ORDNER}/", zeile_mit(fertig.stdout, "gibt es"))
        self.assertIn("Nichts übernommen", fertig.stdout)
        self.assertTrue(entwurf.exists())
        self.assertEqual(sorted(p.name for p in (self.ordner.pfad / "uebungen").iterdir()),
                         vorher)

    def test_danach_meldet_der_linter_keine_auffaelligkeit(self) -> None:
        # Der Pruefvertrag aus test_index.py. Eine Karte, die der Linter
        # beanstandet, waere nicht fertig, obwohl sie schon in uebungen/ liegt.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"}])
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Lint-sauber", quelldatei=f"{ORDNER}/a.pdf",
            rueckfragen=["Wie viele Bälle? Vermutung im Entwurf: zwei je Paar."])
        uebernommen = self.uebernimm("--kandidat", "1", "")
        self.assertEqual(uebernommen.returncode, 0, uebernommen.stdout + uebernommen.stderr)

        fertig = self.ordner.starte("index.py")

        self.assertEqual(auffaelligkeiten(fertig.stdout), [], fertig.stdout)
        self.assertIn(f"Übungen: {len(self.ordner.ids) + 1}", fertig.stdout)

    def test_ein_freigegebener_entwurf_der_die_pruefung_nicht_besteht_bleibt_stehen(self) -> None:
        # Zwischen pruefen und uebernehmen arbeitet der Skill die Antworten
        # des Trainers in den Entwurf ein. Geht dabei etwas kaputt, soll es
        # nicht als Karte in der Bibliothek landen. Ginge der Kandidat dafuer
        # auf offen, entwuerfe ihn der naechste Durchgang neu, und die
        # Antworten waeren ueberschrieben. Also bleiben Entwurf und Status,
        # die Ausgabe nennt den Fehler, und der Skill bessert aus. Der andere
        # Kandidat im selben Aufruf kommt trotzdem durch, und der Exitcode
        # sagt, dass nicht alles geklappt hat.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "rückfrage",
             "notiz": "1 Rückfrage ohne Vermutung"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ])
        entwurf = self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Kaputt", freigabe="")
        vorher = entwurf.read_text(encoding="utf-8")
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Heil")

        fertig = self.uebernimm("--kandidat", "1", "", "--kandidat", "2", "")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("## Freigabe", zeile_mit(fertig.stdout, "  1  "))
        self.assertIn("titel: \"Heil\"", self.karte("ue-000010"))
        self.assertEqual(list((self.ordner.pfad / "uebungen").glob("ue-000011-*")), [])
        self.assertEqual(entwurf.read_text(encoding="utf-8"), vorher)
        zeile = self.ordner.uebersicht(ORDNER)["1"]
        self.assertEqual((zeile["Status"], zeile["Notiz"]),
                         ("rückfrage", "1 Rückfrage ohne Vermutung"))

    def test_ist_nichts_mehr_offen_verschwindet_der_entwurfsordner(self) -> None:
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "ergebnis": "zurückgestellt",
             "status": "zurückgestellt"},
        ])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Der letzte offene")

        fertig = self.uebernimm("--kandidat", "1", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe" / ORDNER).exists())

    def test_uebersprungen_und_ergaenzt_setzen_nur_den_status(self) -> None:
        # Kandidat 1 hat der Trainer bei der Freigabe gestrichen, Kandidat 2
        # war ein Duplikat von ue-000003, und der Skill hat diese Karte schon
        # ergaenzt. Keiner von beiden wird Karte. Kandidat 3 ist noch offen
        # und haelt den Entwurfsordner fest, so zeigt sich, dass Entwurf,
        # Auftrag und Quellgrafiken einzeln verschwinden. Kandidat 2 hat zwei,
        # mit Nummer (#39).
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf", "b2.pdf"], "status": "rückfrage"},
            {"kandidat": 3, "dateien": ["c.pdf"]},
        ])
        entwuerfe = self.ordner.pfad / "kartenentwuerfe" / ORDNER
        for nr, quellgrafiken in ((1, ["1.quellgrafik.png"]),
                                  (2, ["2.quellgrafik-1.png", "2.quellgrafik-2.png"])):
            self.ordner.lege_kartenentwurf_an(ORDNER, nr, titel=f"Kandidat {nr}",
                                              schaubild=quellgrafiken)
            (entwuerfe / f"{nr}.auftrag.md").write_text("# Auftrag\n", encoding="utf-8")
            for quellgrafik in quellgrafiken:
                (entwuerfe / quellgrafik).write_bytes(b"ein Bild")
        vorher = sorted(p.name for p in (self.ordner.pfad / "uebungen").iterdir())

        fertig = self.uebernimm("--uebersprungen", "1", "Vorlage ohne Übung",
                                "--ergaenzt", "2", "ue-000003")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        uebersicht = self.ordner.uebersicht(ORDNER)
        self.assertEqual(
            (uebersicht["1"]["Status"], uebersicht["1"]["Karte"], uebersicht["1"]["Notiz"]),
            ("übersprungen", "", "Vorlage ohne Übung"))
        self.assertEqual((uebersicht["2"]["Status"], uebersicht["2"]["Karte"]),
                         ("ergänzt", "ue-000003"))
        self.assertEqual(sorted(p.name for p in (self.ordner.pfad / "uebungen").iterdir()),
                         vorher)
        self.assertFalse((self.ordner.pfad / "schaubilder").exists())
        self.assertEqual(sorted(p.name for p in entwuerfe.iterdir()), [])
        self.assertEqual(uebersicht["3"]["Status"], "offen")

    def test_ergaenzt_mit_unbekannter_id_und_gestrichen_ohne_grund_aendern_nichts(self) -> None:
        # Vertippt. Die Uebersicht zeigte sonst auf eine Karte, die es nicht
        # gibt, und niemand faende, wohin das Duplikat gegangen ist. Ein
        # Streichen ohne Grund ginge genauso verloren.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ])
        entwurf = self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Duplikat")

        fertig = self.uebernimm("--ergaenzt", "1", "ue-000300", "--uebersprungen", "2", " ")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("ue-000300", zeile_mit(fertig.stdout, "  1  "))
        self.assertIn("Grund", zeile_mit(fertig.stdout, "  2  "))
        uebersicht = self.ordner.uebersicht(ORDNER)
        self.assertEqual((uebersicht["1"]["Status"], uebersicht["2"]["Status"]),
                         ("bereit", "bereit"))
        self.assertTrue(entwurf.exists())

    def test_ist_nichts_mehr_offen_ist_der_eintrag_in_arbeit_weg(self) -> None:
        # Erst ein Durchgang, nach dem Kandidat 2 noch offen ist: Der Eintrag
        # bleibt, denn die Arbeit am Quellenordner laeuft weiter. Dann der
        # letzte, und danach darf ein anderer Trainer ohne --trotzdem ran.
        # Die Uebersicht stimmt danach noch, obwohl im Frontmatter eine Zeile
        # weggefallen ist.
        datei = self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ], in_arbeit="test, 2026-10-01")
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Erster Durchgang")
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Zweiter Durchgang")

        erster = self.uebernimm("--kandidat", "1", "")

        self.assertEqual(erster.returncode, 0, erster.stdout + erster.stderr)
        self.assertIn('in_arbeit: "test, 2026-10-01"\n', datei.read_text(encoding="utf-8"))

        zweiter = self.uebernimm("--kandidat", "2", "")

        self.assertEqual(zweiter.returncode, 0, zweiter.stdout + zweiter.stderr)
        self.assertNotIn("in_arbeit", datei.read_text(encoding="utf-8"))
        uebersicht = self.ordner.uebersicht(ORDNER)
        self.assertEqual([(z["Status"], z["Karte"]) for z in uebersicht.values()],
                         [("importiert", "ue-000010"), ("importiert", "ue-000011")])

    def test_solange_etwas_offen_ist_bleibt_der_entwurfsordner(self) -> None:
        # Die Gegenprobe: Ein Durchgang ist fertig, der naechste nicht.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Freigegeben")
        entwurf = self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Noch nicht freigegeben")

        fertig = self.uebernimm("--kandidat", "1", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertTrue(entwurf.exists())


def auftrag_von(arbeitsordner: Arbeitsordner, kandidat: int) -> str:
    """Der Auftrag, den `vorbereiten` fuer einen Kandidaten angelegt hat."""
    return (arbeitsordner.pfad / "kartenentwuerfe" / ORDNER / f"{kandidat}.auftrag.md").read_text(
        encoding="utf-8")


def unter_datei(text: str, name: str) -> str:
    """Was Planeingabe oder Auftrag unter der Ueberschrift einer Datei sagen.

    Jede Datei hat dort eine Ueberschrift `### \\`<name>\\``, relativ zum
    Quellenordner. Was darunter steht, reicht bis zur naechsten Ueberschrift.
    """
    return text.split(f"### `{name}`\n", 1)[1].split("\n#", 1)[0]


def zeile_mit(text: str, stichwort: str) -> str:
    """Die erste Zeile, in der das Stichwort steht. Fehlt es, faellt der Test."""
    for zeile in text.splitlines():
        if stichwort in zeile:
            return zeile
    raise AssertionError(f"{stichwort!r} steht nicht im Text:\n{text}")


if __name__ == "__main__":
    unittest.main()
