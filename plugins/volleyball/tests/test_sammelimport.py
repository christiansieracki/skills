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

import os
import re
import shutil
import tempfile
import unicodedata
import unittest
from datetime import date
from pathlib import Path

from arbeitsordner import Arbeitsordner, auffaelligkeiten

ORDNER = "stapel"

# Gesucht wird hier nur im PATH. Das Skript sucht unter Windows auch neben
# git.exe. Steht pdftotext nur dort, werden diese Tests übersprungen, obwohl
# das Skript es fände. Die Suche neben git.exe prüft die Abnahme (#29).
BRAUCHT_PDFTOTEXT = unittest.skipUnless(
    shutil.which("pdftotext"), "pdftotext ist nicht im PATH")


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
             "karte": "ue-0001"},
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
        """Die Dateien, die die Planeingabe aufführt, je eine Überschrift."""
        return re.findall(r"^### `(.+)`$", self.planeingabe(), re.MULTILINE)

    def zu_datei(self, name: str) -> str:
        """Was die Planeingabe unter der Überschrift einer Datei sagt."""
        return self.planeingabe().split(f"### `{name}`\n", 1)[1].split("\n#", 1)[0]

    @BRAUCHT_PDFTOTEXT
    def test_bei_pdfs_steht_ihr_text_in_der_planeingabe(self) -> None:
        # Der Text steht unter seiner Datei, sonst lässt sich kein Übersichtsblatt
        # seinen Stationsblättern zuordnen. Das „ü" zeigt, dass pdftotext UTF-8
        # schreibt: Xpdf aus Git für Windows schreibt sonst Latin-1.
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
        # liest pdftotext gar nicht. Eine leere Überschrift hieße für den
        # Agenten nur, dass nichts dasteht, und er plante nach dem Dateinamen.
        self.ordner.lege_quell_pdf_an(f"{ORDNER}/scan.pdf", [])
        self.ordner.lege_quelldatei_an(f"{ORDNER}/kaputt.pdf", b"kein PDF")

        self.plane()

        for name in ("scan.pdf", "kaputt.pdf"):
            self.assertIn("selbst lesen", self.zu_datei(name))

    def lege_stationsuebersicht_an(self) -> None:
        """Ein Übersichtsblatt, dessen Stationsliste weit über die ersten Zeilen reicht."""
        self.ordner.lege_quell_pdf_an(
            f"{ORDNER}/zirkel.pdf",
            ["Stationsübersicht Sprungkraftzirkel",
             *(f"Station {n}: Sprünge über die kleine Kiste, 30 Sekunden" for n in range(1, 20)),
             "Station 20: Auslaufen und Dehnen"])

    @BRAUCHT_PDFTOTEXT
    def test_passt_der_text_in_einen_aufruf_kommt_er_ganz(self) -> None:
        # So bekommt ein Übersichtsblatt seine ganze Stationsliste, und der
        # Plan erkennt die Stationsblätter, die zu ihm gehören.
        self.lege_stationsuebersicht_an()

        self.plane()

        self.assertIn("Station 20: Auslaufen und Dehnen", self.zu_datei("zirkel.pdf"))

    @BRAUCHT_PDFTOTEXT
    def test_liegt_der_text_ueber_der_schwelle_stehen_nur_die_ersten_zeilen_da(self) -> None:
        # Das dicke PDF bringt den Ordner deutlich über die Schwelle im
        # Skript, gut 500 000 Zeichen gegen 400 000. Ganz passte der Text
        # nicht mehr in den Aufruf des Agenten. Dann bekommt jede Datei ihre
        # ersten Zeilen, das dicke PDF genauso wie das Übersichtsblatt.
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
        # Auch der Agent muss es wissen, sonst hält er den Anfang für alles.
        self.assertIn("ersten Zeilen", self.planeingabe().split("## Dateien", 1)[0])

    def bibliothek(self) -> dict[str, dict[str, str]]:
        """Die Bibliotheksliste der Planeingabe, je ID eine Zeile."""
        abschnitt = self.planeingabe().split("## Bibliothek", 1)[1]
        zeilen = [[z.strip() for z in zeile.strip().strip("|").split("|")]
                  for zeile in abschnitt.splitlines() if zeile.startswith("|")]
        kopf, _trenner, *rest = zeilen
        return {z[0]: dict(zip(kopf, z)) for z in rest}

    def test_die_bibliotheksliste_nennt_jede_karte_und_markiert_die_aus_diesem_ordner(self) -> None:
        # Daran erkennt der Plan, was schon importiert ist, und führt es mit
        # seiner ID, statt es ein zweites Mal entwerfen zu lassen. Eine Karte
        # über zwei Seiten nennt beide Dateien. Ein Ordner, der nur genauso
        # anfängt, ist ein anderer.
        self.ordner.lege_karte_an(id="ue-0006", titel="Abwehr vom Kasten", element=["abwehr"],
                                  quelldatei=f"{ORDNER}/Ü_Abwehr/kasten.pdf")
        self.ordner.lege_karte_an(id="ue-0007", titel="Über zwei Seiten",
                                  quelldatei=f"{ORDNER}/seite-01.jpg, {ORDNER}/seite-02.jpg")
        self.ordner.lege_karte_an(id="ue-0008", titel="Aus dem alten Stapel",
                                  quelldatei=f"{ORDNER}-alt/seite-01.jpg")
        self.ordner.lege_quelldatei_an(f"{ORDNER}/seite-09.jpg", b"")

        self.plane()

        liste = self.bibliothek()
        self.assertEqual(sorted(liste), sorted(self.ordner.ids))
        kasten = liste["ue-0006"]
        self.assertEqual(kasten["Titel"], "Abwehr vom Kasten")
        self.assertEqual(kasten["Element"], "abwehr")
        self.assertEqual(kasten["quelldatei"], f"{ORDNER}/Ü_Abwehr/kasten.pdf")
        self.assertEqual({uid for uid, zeile in liste.items() if zeile["Aus diesem Ordner"]},
                         {"ue-0006", "ue-0007"})

    def test_ein_foto_ueber_2_mb_ergibt_den_hinweis_auf_die_bildaufbereitung(self) -> None:
        # So schwer ist eine abfotografierte Magazinseite mit 50 Megapixeln.
        # Der Agent kann sie nicht öffnen, weder für den Plan noch für den
        # Entwurf. Zufallsbytes reichen, der Hinweis richtet sich nach der
        # Dateigröße, und so läuft der Test auch ohne Pillow.
        self.ordner.lege_quelldatei_an(f"{ORDNER}/unter/seite-01.jpg", os.urandom(3 * 1024 * 1024))
        self.ordner.lege_quelldatei_an(f"{ORDNER}/seite-02.jpg", b"klein genug")

        fertig = self.plane()

        self.assertIn("bilder_aufbereiten.py", fertig.stdout)
        self.assertIn("unter/seite-01.jpg", fertig.stdout)
        self.assertNotIn("seite-02.jpg", fertig.stdout)

    def test_ohne_pdftotext_gibt_es_einen_hinweis_und_die_eingabe_ohne_text(self) -> None:
        # Ein Mittrainer auf dem Mac ohne Poppler. Der Sammelimport wird für
        # ihn teurer, weil der Agent die PDFs selbst liest, aber er läuft
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

    def test_die_planeingabe_nennt_jede_datei_auch_aus_unterordnern(self) -> None:
        # PlayDrill sortiert seine Übungen in Unterordner, und eine Folge kann
        # über zwei davon verteilt sein. Der Plan muss sie alle sehen.
        namen = ["seite-01.jpg", "Ü_Abwehr/seite-02.jpg", "Ü_Abwehr/tiefer/notiz.txt"]
        for name in namen:
            self.ordner.lege_quelldatei_an(f"{ORDNER}/{name}", b"")

        self.plane()

        self.assertEqual(sorted(self.genannte_dateien()), sorted(namen))

    def test_ein_zweiter_lauf_nimmt_nur_dateien_die_in_keiner_zeile_stehen(self) -> None:
        # Nach dem ersten Durchgang sind neue Seiten dazugekommen. Nur sie
        # brauchen einen Plan, die anderen haben schon einen, auch der noch
        # offene Kandidat 2. Die sammelimport.md selbst ist keine Quelle.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["seite-01.jpg"], "status": "importiert",
             "karte": "ue-0001"},
            {"kandidat": 2, "dateien": ["unter/seite-02.jpg", "unter/seite-03.jpg"]},
        ])
        self.ordner.lege_quelldatei_an(f"{ORDNER}/unter/seite-04.jpg", b"")

        self.plane()

        self.assertEqual(self.genannte_dateien(), ["unter/seite-04.jpg"])

    def test_ohne_neue_dateien_entsteht_keine_planeingabe(self) -> None:
        # Dann gibt es nichts zu planen, und der Skill soll keinen Agenten
        # für eine leere Liste starten.
        self.ordner.lege_quellenordner_an(ORDNER, [{"kandidat": 1, "dateien": ["seite-01.jpg"]}])

        fertig = self.plane()

        self.assertIn("Keine neuen Dateien", fertig.stdout)
        self.assertFalse((self.ordner.pfad / "kartenentwuerfe").exists())

    def test_ein_umlaut_im_pfad_zaehlt_gleich_wie_das_dateisystem_ihn_auch_schreibt(self) -> None:
        # Jeder Übungsordner von PlayDrill beginnt mit „Ü_". macOS legt das Ü
        # als U mit zwei Punkten ab, zwei Zeichen, Windows als eines. Kommt
        # der Ordner über Nextcloud von einem Mac, stünde sonst jede Datei
        # darin beim zweiten Lauf als neu da, obwohl der Plan sie schon hat.
        self.ordner.lege_quellenordner_an(
            ORDNER, [{"kandidat": 1, "dateien": ["Ü_Abwehr/seite-01.jpg"]}])
        quellordner = self.ordner.pfad / "quellen" / ORDNER
        (quellordner / "Ü_Abwehr").rename(
            quellordner / unicodedata.normalize("NFD", "Ü_Abwehr"))

        fertig = self.plane()

        self.assertIn("Keine neuen Dateien", fertig.stdout)


class PruefenTest(unittest.TestCase):
    """`pruefen` setzt den Status allein aus dem, was auf der Platte liegt.

    Die Rueckmeldung des Agenten zaehlt nicht: Im Probelauf hatten sechs
    Aufrufe ihren Entwurf geschrieben und brachen erst bei der Rueckmeldung ab.
    """

    def setUp(self) -> None:
        self.ordner = Arbeitsordner()
        self.addCleanup(self.ordner.raeume_auf)

    def pruefe(self, *kandidaten: dict) -> dict[str, dict[str, str]]:
        self.ordner.lege_quellenordner_an(ORDNER, list(kandidaten))
        fertig = self.ordner.starte("sammelimport.py", "pruefen", ORDNER)
        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        return self.ordner.uebersicht(ORDNER)

    def test_ohne_entwurf_bleibt_der_kandidat_offen_mit_grund(self) -> None:
        # Ein Kandidat, der als bereit gefuehrt wird, dessen Entwurf aber
        # nicht mehr da ist. Die Zeile folgt der Platte, nicht ihrem Stand.
        zeile = self.pruefe({"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"})["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("kein Entwurf", zeile["Notiz"])

    def test_ein_entwurf_ohne_rueckfrage_ist_bereit(self) -> None:
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Ohne Rückfrage",
            vorschlaege=["`level_max`: Technikübung, die Schwierigkeit steuert der Ball."])

        zeile = self.pruefe({"kandidat": 1, "dateien": ["a.pdf"]})["1"]

        self.assertEqual(zeile["Status"], "bereit")
        self.assertEqual(zeile["Notiz"], "")

    def test_eine_rueckfrage_mit_vermutung_ist_bereit(self) -> None:
        # Die Vermutung steht schon im Text des Entwurfs. Der Trainer bestaetigt
        # sie in der Tabelle wie einen Vorschlag, einzeln gefragt wird nicht.
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Mit Vermutung",
            rueckfragen=["Wie viele Spieler braucht die Übung? "
                         "Vermutung im Entwurf: mindestens 8, aus den Rollen."])

        zeile = self.pruefe({"kandidat": 1, "dateien": ["a.pdf"]})["1"]

        self.assertEqual(zeile["Status"], "bereit")

    def test_eine_rueckfrage_ohne_vermutung_ergibt_rueckfrage(self) -> None:
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Ohne Vermutung",
            rueckfragen=["Wie viele Spieler braucht die Übung? "
                         "Vermutung im Entwurf: mindestens 8, aus den Rollen.",
                         "Wohin kommen die gefangenen Bälle zurück? "
                         "Vermutung im Entwurf: keine"])

        zeile = self.pruefe({"kandidat": 1, "dateien": ["a.pdf"]})["1"]

        self.assertEqual(zeile["Status"], "rückfrage")

    def test_ohne_abschnitt_freigabe_bleibt_der_kandidat_offen(self) -> None:
        # Ohne den Abschnitt weiss niemand, was der Entwurf gedeutet und wo er
        # eine Luecke gefunden hat. Er wird neu entworfen.
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Ohne Freigabe", freigabe="")

        zeile = self.pruefe({"kandidat": 1, "dateien": ["a.pdf"]})["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("## Freigabe", zeile["Notiz"])

    def test_ohne_liste_der_rueckfragen_bleibt_der_kandidat_offen(self) -> None:
        # Beide Listen stehen immer da, eine leere heisst "keine". Fehlt eine,
        # ist nicht zu unterscheiden, ob der Agent nichts gefunden oder den
        # Entwurf nicht fertig geschrieben hat.
        self.ordner.lege_kartenentwurf_an(
            ORDNER, 1, titel="Nur Vorschläge", freigabe="## Freigabe\n\nVorschläge: keine\n")

        zeile = self.pruefe({"kandidat": 1, "dateien": ["a.pdf"]})["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("Rückfragen", zeile["Notiz"])

    def test_ohne_lesbares_frontmatter_bleibt_der_kandidat_offen(self) -> None:
        entwurf = self.ordner.pfad / "kartenentwuerfe" / ORDNER / "1.md"
        entwurf.parent.mkdir(parents=True)
        entwurf.write_text("# Abgebrochen\n\nDer Agent kam nur bis hier.\n", encoding="utf-8")

        zeile = self.pruefe({"kandidat": 1, "dateien": ["a.pdf"]})["1"]

        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("Frontmatter", zeile["Notiz"])

    def test_zeilen_mit_importiert_bleiben_unberuehrt(self) -> None:
        # Eine uebernommene Karte hat keinen Entwurf mehr. Faende pruefen sie
        # "offen", entwuerfe der naechste Durchgang dieselbe Uebung ein
        # zweites Mal.
        uebersicht = self.pruefe({
            "kandidat": 1, "dateien": ["a.pdf"], "status": "importiert",
            "karte": "ue-0001", "notiz": "spieler_min auf 6"})

        self.assertEqual(uebersicht["1"]["Status"], "importiert")
        self.assertEqual(uebersicht["1"]["Karte"], "ue-0001")
        self.assertEqual(uebersicht["1"]["Notiz"], "spieler_min auf 6")

    def test_eine_erledigte_zeile_bleibt_zeichengenau_stehen(self) -> None:
        # Unberuehrt heisst unberuehrt. Eine von Hand geschriebene Notiz mit
        # einem `|` darin und doppelten Leerzeichen ueberstuende sonst den
        # naechsten Aufruf nicht, obwohl an der Zeile nichts zu tun war.
        datei = self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "importiert", "karte": "ue-0001"},
            {"kandidat": 2, "dateien": ["b.pdf"]},
        ])
        text = datei.read_text(encoding="utf-8")
        von_hand = "| 1 | `a.pdf` | Übung  aus dem Test | uebung | importiert | ue-0001 | A | B |"
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
        self.ordner.lege_karte_an(id="ue-0009", titel="Die bisher höchste ID")

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
        karte = self.karte("ue-0010")
        self.assertIn("\nid: ue-0010\n", karte)
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
            ("importiert", "ue-0010", "spieler_min auf 6"))

    def test_zwei_kandidaten_bekommen_aufeinanderfolgende_ids(self) -> None:
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Erster Kandidat")
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Zweiter Kandidat")

        fertig = self.uebernimm("--kandidat", "1", "", "--kandidat", "2", "")

        self.assertEqual(fertig.returncode, 0, fertig.stdout + fertig.stderr)
        self.assertIn("titel: \"Erster Kandidat\"", self.karte("ue-0010"))
        self.assertIn("titel: \"Zweiter Kandidat\"", self.karte("ue-0011"))

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

    def test_ein_entwurf_der_die_pruefung_nicht_besteht_wird_nicht_uebernommen(self) -> None:
        # Zwischen pruefen und uebernehmen arbeitet der Skill die Antworten
        # des Trainers in den Entwurf ein. Geht dabei etwas kaputt, soll es
        # nicht als Karte in der Bibliothek landen. Der andere Kandidat im
        # selben Aufruf kommt trotzdem durch, und der Exitcode sagt, dass
        # nicht alles geklappt hat.
        self.ordner.lege_quellenordner_an(ORDNER, [
            {"kandidat": 1, "dateien": ["a.pdf"], "status": "bereit"},
            {"kandidat": 2, "dateien": ["b.pdf"], "status": "bereit"},
        ])
        self.ordner.lege_kartenentwurf_an(ORDNER, 1, titel="Kaputt", freigabe="")
        self.ordner.lege_kartenentwurf_an(ORDNER, 2, titel="Heil")

        fertig = self.uebernimm("--kandidat", "1", "", "--kandidat", "2", "")

        self.assertNotEqual(fertig.returncode, 0, fertig.stdout)
        self.assertIn("titel: \"Heil\"", self.karte("ue-0010"))
        self.assertEqual(list((self.ordner.pfad / "uebungen").glob("ue-0011-*")), [])
        zeile = self.ordner.uebersicht(ORDNER)["1"]
        self.assertEqual(zeile["Status"], "offen")
        self.assertIn("## Freigabe", zeile["Notiz"])

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


def zeile_mit(text: str, stichwort: str) -> str:
    """Die erste Zeile, in der das Stichwort steht. Fehlt es, faellt der Test."""
    for zeile in text.splitlines():
        if stichwort in zeile:
            return zeile
    raise AssertionError(f"{stichwort!r} steht nicht im Text:\n{text}")


if __name__ == "__main__":
    unittest.main()
