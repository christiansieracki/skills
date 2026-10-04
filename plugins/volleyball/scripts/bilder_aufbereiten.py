#!/usr/bin/env python3
"""Bereitet Quellbilder auf, damit sie sich überhaupt lesen lassen.

    <python> bilder_aufbereiten.py                          # alles unter quellen/
    <python> bilder_aufbereiten.py quellen/magazin-09-2026   # ein Unterordner
    <python> bilder_aufbereiten.py --wurzel <pfad> --ja      # ohne Rückfrage

Der Anlass sind abfotografierte Seiten: 50 Megapixel und 7 MB je Datei lassen
sich nicht öffnen, und mit EXIF-Orientierung 6 liegen sie zusätzlich quer. Was
über 2 MB wiegt, wird deshalb auf 2000 Pixel lange Kante verkleinert und nach
seiner EXIF-Orientierung geradegedreht. Was darunter liegt, bleibt unangetastet.
Die Aufbereitung soll nichts verschlechtern, was schon in Ordnung war.

Das Original wird ersetzt, unter demselben Dateinamen, nach einer einzigen
Rückfrage für den ganzen Stapel. Ein zweites Bild daneben machte `quelldatei:`
auf den Karten mehrdeutig und höbe die Ersparnis auf, statt sie zu halbieren.
Das ist der einzige unumkehrbare Schritt; `--ja` überspringt die Rückfrage für
den, der schon weiß, was kommt.

TIFF und HEIC werden immer zu JPEG, auch unter 2 MB. Das Lesewerkzeug des
Agenten zeigt nur PNG und JPEG, und ein Foto vom iPhone ist ein HEIC. Das JPEG
bekommt denselben Namen mit `.jpg`, das Original fällt nach derselben
Rückfrage weg. Liegen bleibt eine solche Datei, wenn eine Karte mit
`quelldatei:` auf sie zeigt, denn sonst bräche der Verweis. Ebenso, wenn das
JPEG eine andere Datei überschriebe, und ein mehrseitiges TIFF, denn ein JPEG
fasst nur eine Seite.

Dieses Skript braucht Pillow immer (ADR-0005). Fehlt Pillow, bricht das Skript
mit einem Installationshinweis ab und schreibt nichts. Sonst braucht Pillow nur
der Sammelimport, wenn er die Quellgrafik aus dem PDF ausschneidet. Die
übrigen Skripte des Plugins laufen davon unberührt weiter mit der
Standardbibliothek.

HEIC öffnet Pillow erst mit dem Zusatzpaket pillow-heif, optional wie Pillow
selbst (Nachtrag zu ADR-0005). Fehlt das Paket, nennt das Skript die
HEIC-Dateien samt Installationshinweis, lässt sie liegen und bereitet die
übrigen auf.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import finde_wurzel, interpreter, konsole_vorbereiten, lies_uebungen  # noqa: E402

# Ab hier gilt eine Datei als zu schwer. Die Schwelle steht auf der Dateigröße
# und nicht auf der Pixelzahl, weil sie sich ohne Bildbibliothek ablesen lässt:
# was gar nicht angefasst wird, muss auch nicht geöffnet werden.
SCHWELLE = 2 * 1024 * 1024
ZIELKANTE = 2000
QUALITAET = 85

ENDUNGEN = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".heif"}
JPEG_ENDUNGEN = {".jpg", ".jpeg"}

# Was so endet, kann der Agent nicht lesen, egal wie klein es ist. Es wird
# deshalb immer zu JPEG, siehe ziel().
NUR_ALS_JPEG = {".tif", ".tiff", ".heic", ".heif"}
HEIC_ENDUNGEN = {".heic", ".heif"}

# EXIF-Tag 0x0112. 1 heißt "schon richtig herum", 6 heißt "für die Anzeige um
# 90 Grad drehen". Den Wert tragen alle fünfzehn Magazinseiten.
ORIENTIERUNG = 274


# --------------------------------------------------------------------------
# Pillow
# --------------------------------------------------------------------------

def pillow_da() -> bool:
    """Sagt, ob Pillow benutzbar ist, und meldet im Klartext, wenn nicht.

    Der Aufruf steht ganz am Anfang von main(), vor jedem Blick in den Ordner.
    Ohne Bildbibliothek soll nicht erst eine Dateiliste erscheinen, die dann
    doch niemand bearbeiten kann.
    """
    try:
        # Der Import ist die Pruefung, die Namen werden hier nicht gebraucht.
        # Geholt werden beide, weil eine halbe Installation sonst erst mitten
        # im Stapel auffiele.
        from PIL import Image, ImageOps  # noqa: F401
    except ImportError:
        print("Für die Bildaufbereitung fehlt Pillow.\n")
        print("Installieren mit:")
        print(f"  {interpreter()} -m pip install Pillow\n")
        print("Pillow brauchen nur dieses Skript und das Ausschneiden der Quellgrafik")
        print("im Sammelimport. Die übrigen Skripte des Plugins laufen ohne es weiter.")
        return False
    return True


def pillow_heif_da() -> bool:
    """Sagt, ob pillow-heif da ist, und meldet es bei Pillow an.

    Erst die Anmeldung bringt Image.open() dazu, ein HEIC zu öffnen.
    """
    try:
        from pillow_heif import register_heif_opener
    except ImportError:
        return False
    register_heif_opener()
    return True


# --------------------------------------------------------------------------
# Auswählen
# --------------------------------------------------------------------------

def kandidaten(ordner: Path) -> tuple[list[Path], list[Path]]:
    """Die Bilder, die aufbereitet werden, und die, die liegen bleiben.

    Aufbereitet wird, was über der Schwelle liegt, und jedes TIFF und HEIC.
    Liegen bleibt ein JPEG oder PNG unter der Schwelle.

    Gesucht wird auch in Unterordnern: `quellen/` sammelt Quelle für Quelle in
    eigenen Ordnern, und ein Aufruf auf `quellen/` soll den ganzen Bestand
    lesbar machen, nicht nur dessen oberste Ebene.
    """
    aufbereiten: list[Path] = []
    bleiben: list[Path] = []
    for pfad in sorted(ordner.rglob("*")):
        endung = pfad.suffix.lower()
        if not pfad.is_file() or endung not in ENDUNGEN:
            continue
        if endung in NUR_ALS_JPEG or pfad.stat().st_size > SCHWELLE:
            aufbereiten.append(pfad)
        else:
            bleiben.append(pfad)
    return aufbereiten, bleiben


def wird_jpeg(pfad: Path) -> bool:
    """Ein TIFF oder HEIC, das als JPEG mit `.jpg` neu entsteht."""
    return pfad.suffix.lower() in NUR_ALS_JPEG


def ziel(pfad: Path) -> Path:
    """Wohin das aufbereitete Bild kommt: dieselbe Datei, bei TIFF und HEIC mit `.jpg`."""
    return pfad.with_suffix(".jpg") if wird_jpeg(pfad) else pfad


def halte_heic_zurueck(ordner: Path, pfade: list[Path]) -> list[Path]:
    """Die HEIC-Dateien, wenn pillow-heif fehlt. Sie werden genannt.

    Nach dem Paket wird erst gefragt, wenn ein HEIC im Stapel liegt: Wer
    keins hat, braucht es nicht. Fehlt es, bleiben nur die HEIC-Dateien
    liegen. Der Rest des Stapels wird trotzdem lesbar, so wie eine kaputte
    Datei ihn nicht anhält.
    """
    heic = [p for p in pfade if p.suffix.lower() in HEIC_ENDUNGEN]
    if not heic or pillow_heif_da():
        return []
    print("\nFür HEIC fehlt pillow-heif. Diese Dateien bleiben liegen:")
    for pfad in heic:
        print(f"  {pfad.relative_to(ordner).as_posix()}")
    print("Installieren mit:")
    print(f"  {interpreter()} -m pip install pillow-heif")
    return heic


def _vergleichbar(text: str) -> str:
    """Ein Pfad so, dass ein Ü aus macOS und eins aus Windows gleich sind."""
    return unicodedata.normalize("NFC", text.replace("\\", "/")).casefold()


def halte_mit_karte_zurueck(wurzel: Path, ordner: Path, pfade: list[Path]) -> list[Path]:
    """Die Dateien, die einen neuen Namen bekämen und auf die eine Karte zeigt.

    Sie werden mit den IDs der Karten genannt. Als `.jpg` bräche der
    Verweis in `quelldatei:`. Ein JPEG oder PNG behält seinen Namen und wird
    deshalb gar nicht erst nachgesehen. Ein HEIC mit Karte bliebe auch mit
    pillow-heif liegen. Gefragt wird deshalb vor dem Paket, und die Meldung
    nennt die Karte.

    `quelldatei:` steht relativ zu quellen/ und ist freier Text, mal mit
    Komma, mal mit „und", oft mit Seitenzahl dahinter (siehe suche.py).
    Gesucht wird deshalb der Pfad irgendwo im Text, ohne auf Groß- und
    Kleinschreibung zu achten, wie Windows und macOS beim Öffnen auch. Trifft
    das einmal zu viel, bleibt eine Datei liegen, die hätte umgewandelt werden
    dürfen. Die Meldung nennt die Karte, das ist der harmlose Fehler.
    """
    quellen = (wurzel / "quellen").resolve()
    namen = {}
    for pfad in pfade:
        echt = pfad.resolve()
        if wird_jpeg(pfad) and echt.is_relative_to(quellen):
            namen[pfad] = _vergleichbar(echt.relative_to(quellen).as_posix())
    if not namen:
        return []

    karten: dict[Path, list[str]] = {}
    for karte in lies_uebungen(wurzel):
        wert = karte.get("quelldatei")
        if not wert:
            continue
        # Zwei Seiten in eckigen Klammern liefert der Parser als Liste.
        text = _vergleichbar(", ".join(map(str, wert)) if isinstance(wert, list) else str(wert))
        for pfad, name in namen.items():
            if name in text:
                karten.setdefault(pfad, []).append(str(karte["id"]))
    if not karten:
        return []
    print("\nAuf diese Dateien zeigt eine Karte. Als .jpg bräche der Verweis,")
    print("sie bleiben liegen:")
    for pfad, ids in karten.items():
        print(f"  {pfad.relative_to(ordner).as_posix()}  {', '.join(ids)}")
    return list(karten)


def halte_namensgleiche_zurueck(ordner: Path, pfade: list[Path]) -> list[Path]:
    """Die Dateien, deren JPEG eine andere Datei überschriebe. Sie werden genannt.

    Neben `scan.tif` kann schon ein `scan.jpg` liegen, oder `scan.heic` will
    denselben Namen. Welche Datei die richtige ist, weiß nur der Trainer.
    Liegen bleiben deshalb alle, die denselben Namen wollen. Verglichen wird
    ohne Groß- und Kleinschreibung, denn unter Windows ist `scan.JPG`
    dieselbe Datei wie `scan.jpg`.
    """
    je_name: dict[str, list[Path]] = {}
    for pfad in pfade:
        if wird_jpeg(pfad):
            je_name.setdefault(str(ziel(pfad)).casefold(), []).append(pfad)
    namensgleich = [pfad for gruppe in je_name.values()
                    if len(gruppe) > 1 or ziel(gruppe[0]).exists() for pfad in gruppe]
    if not namensgleich:
        return []
    print("\nAls .jpg träfen diese Dateien auf einen Namen, den es schon gibt oder")
    print("den eine zweite bekäme. Sie bleiben liegen, bis eine umbenannt ist:")
    for pfad in namensgleich:
        print(f"  {pfad.relative_to(ordner).as_posix()}  -> {ziel(pfad).name}")
    return namensgleich


def melde_quer_liegende(ordner: Path, pfade: list[Path]) -> None:
    """Nennt Bilder, die quer liegen und trotzdem unter der Schwelle bleiben.

    Die Schwelle entscheidet, ob eine Datei angefasst wird, und ein kleines
    Bild bleibt deshalb byte-identisch, auch wenn sein EXIF es quer legt. Ohne
    diesen Hinweis fiele das erst dem auf, der die Seite lesen will. Gedreht
    wird trotzdem nicht: byte-identisch heisst byte-identisch.
    """
    from PIL import Image  # erst hier, damit der Hinweis aus pillow_da() greift

    schief = []
    for pfad in pfade:
        try:
            with Image.open(pfad) as bild:
                # getexif() liest den Kopf, es wird kein Pixel dekodiert.
                if bild.getexif().get(ORIENTIERUNG, 1) not in (0, 1):
                    schief.append(pfad)
        except Exception:  # noqa: BLE001
            continue  # Was sich nicht öffnen lässt, ist hier nicht das Thema.
    if not schief:
        return
    print("\nQuer, aber unter der Schwelle, deshalb unverändert:")
    for pfad in schief:
        print(f"  {pfad.relative_to(ordner).as_posix()}")


def bilder(anzahl: int) -> str:
    """"1 Bild" oder "15 Bilder". Die Bilanz soll sich vorlesen lassen."""
    return "1 Bild" if anzahl == 1 else f"{anzahl} Bilder"


def menschenmass(zahl: float) -> str:
    """Bytes so, wie man sie vorliest: 7,4 MB statt 7759872."""
    einheit = "B"
    for naechste in ("KB", "MB", "GB"):
        if abs(zahl) < 1024:
            break
        zahl /= 1024
        einheit = naechste
    if einheit == "B":
        return f"{int(zahl)} B"
    return f"{zahl:.1f}".replace(".", ",") + f" {einheit}"


# --------------------------------------------------------------------------
# Aufbereiten
# --------------------------------------------------------------------------

def verkleinert(bild):
    """Skaliert auf ZIELKANTE, falls nötig, und trifft die lange Kante genau.

    Die lange Kante wird gesetzt statt gerechnet. Über den Faktor käme bei
    krummen Seitenverhältnissen 1999 heraus, und dann stimmt das Zielmaß nur
    fast.
    """
    from PIL import Image  # erst hier, damit der Hinweis aus pillow_da() greift

    breite, hoehe = bild.size
    if max(breite, hoehe) <= ZIELKANTE:
        return bild
    if breite >= hoehe:
        neu = (ZIELKANTE, max(1, round(hoehe * ZIELKANTE / breite)))
    else:
        neu = (max(1, round(breite * ZIELKANTE / hoehe)), ZIELKANTE)
    return bild.resize(neu, Image.LANCZOS)


def kodiere(bild, endung: str, exif: bytes | None) -> bytes:
    """Schreibt das Bild in den Speicher, noch nicht auf die Platte.

    Erst der fertige Bytestrom sagt, ob sich das Ersetzen lohnt. Ein schon gut
    gepacktes PNG kann beim Neuschreiben wachsen, und ein kleineres Original
    durch ein größeres Erzeugnis zu ersetzen wäre das Gegenteil des Zwecks.
    """
    puffer = io.BytesIO()
    if endung in JPEG_ENDUNGEN:
        if bild.mode not in ("RGB", "L", "CMYK"):
            bild = bild.convert("RGB")
        if exif:
            bild.save(puffer, "JPEG", quality=QUALITAET, optimize=True, exif=exif)
        else:
            bild.save(puffer, "JPEG", quality=QUALITAET, optimize=True)
    else:
        bild.save(puffer, "PNG", optimize=True)
    return puffer.getvalue()


def fuer_jpeg(bild):
    """Bringt ein TIFF oder HEIC in RGB oder Graustufen, die jeder Betrachter zeigt.

    16 Bit Graustufen, wie ein Scanner sie schreiben kann, werden auf 8 Bit
    heruntergerechnet. convert() allein schnitte alles über 255 ab, und der
    Scan käme fast weiß heraus. Ein JPEG in CMYK zeigt mancher Betrachter
    falsch oder gar nicht.
    """
    if bild.mode.startswith("I;16"):
        return bild.convert("I").point(lambda wert: wert / 256).convert("L")
    if bild.mode not in ("RGB", "L"):
        return bild.convert("RGB")
    return bild


def bereite_auf(pfad: Path) -> tuple[Path, int, bool] | None:
    """Bereitet eine Datei auf und ersetzt sie. Gibt (zielpfad, gespart, gedreht) zurück.

    Der Zielpfad ist dieselbe Datei, bei TIFF und HEIC ein JPEG mit `.jpg`
    daneben. Das Original verschwindet dann.

    None heisst: die Datei bleibt, wie sie ist, weil das Erzeugnis nicht
    kleiner wäre. Lag sie quer, wird trotzdem geschrieben. Eine quer liegende
    Seite ist auch dann unlesbar, wenn sie nichts einspart. Ein TIFF oder
    HEIC wird immer ersetzt, lesen kann es der Agent so nie.
    """
    from PIL import Image, ImageOps  # erst hier, damit der Hinweis aus pillow_da() greift

    vorher = pfad.stat().st_size
    zielpfad = ziel(pfad)
    umwandeln = wird_jpeg(pfad)

    # Gelesen wird aus dem Speicher. Ein TIFF ohne Kompression bildet Pillow
    # sonst in den Speicher ab, und solange das Bild lebt, lässt Windows die
    # Datei nicht löschen.
    with Image.open(io.BytesIO(pfad.read_bytes())) as bild:
        # Ein JPEG fasst eine Seite. Aus einem mehrseitigen TIFF bliebe nur
        # die erste, und das Original fiele weg.
        seiten = getattr(bild, "n_frames", 1)
        if umwandeln and seiten > 1:
            raise ValueError(f"{seiten} Seiten, ein JPEG fasst nur eine")
        lag_quer = bild.getexif().get(ORIENTIERUNG, 1) not in (0, 1)
        gerade = ImageOps.exif_transpose(bild)
        klein = verkleinert(fuer_jpeg(gerade) if umwandeln else gerade)

        # Die Drehung ist jetzt in die Pixel eingerechnet. Bliebe der
        # EXIF-Eintrag stehen, drehte der nächste Betrachter ein zweites Mal.
        exif = klein.getexif()
        exif.pop(ORIENTIERUNG, None)
        roh_exif = exif.tobytes() if len(exif) else None

        neu = kodiere(klein, zielpfad.suffix.lower(), roh_exif)

    if not umwandeln and len(neu) >= vorher and not lag_quer:
        return None

    # Erst danebenschreiben, dann umbenennen: ein Abbruch mittendrin lässt das
    # Original heil liegen, statt es halb überschrieben zu hinterlassen. Nach
    # einem geglückten replace gibt es die Zwischendatei nicht mehr, das
    # Aufräumen im finally ist dann folgenlos. Sonst nimmt es die Reste mit,
    # statt sie in quellen/ liegen zu lassen.
    zwischen = zielpfad.with_name(zielpfad.name + ".neu")
    try:
        zwischen.write_bytes(neu)
        os.replace(zwischen, zielpfad)
    finally:
        zwischen.unlink(missing_ok=True)
    if umwandeln:
        # Erst jetzt, wo das JPEG steht. Ein Abbruch davor lässt das Original.
        pfad.unlink()
    return zielpfad, vorher - len(neu), lag_quer


# --------------------------------------------------------------------------
# Rückfrage
# --------------------------------------------------------------------------

def frage(anzahl: int, gesamt: int, als_jpeg: int) -> bool:
    """Fragt einmal für den ganzen Stapel, nicht je Datei.

    `als_jpeg` zählt die TIFF- und HEIC-Dateien darunter. Wer zustimmt, soll
    wissen, dass aus `scan.tif` ein `scan.jpg` wird.
    """
    ersetzt = "wird" if anzahl == 1 else "werden"
    if not als_jpeg:
        wie = "unter demselben Namen ersetzt"
    elif als_jpeg == anzahl:
        wie = "ersetzt, als JPEG mit .jpg"
    else:
        wie = f"ersetzt, {als_jpeg} davon als JPEG mit .jpg"
    print(f"\n{bilder(anzahl)} ({menschenmass(gesamt)}) {ersetzt} {wie}. "
          f"Weiter? [j/N] ", end="", flush=True)
    try:
        antwort = input().strip().lower()
    except EOFError:
        # Kein Mensch an der Tastatur. Ein stilles "ja" zu unterstellen wäre
        # bei einem unumkehrbaren Schritt die falsche Richtung.
        print("\nKeine Antwort möglich. Mit --ja bestätigen, wenn es so sein soll.")
        return False
    print()
    return antwort in ("j", "ja", "y", "yes")


# --------------------------------------------------------------------------

def main() -> int:
    konsole_vorbereiten()
    ap = argparse.ArgumentParser(
        description="Quellbilder verkleinern, nach EXIF geradedrehen und aus "
                    "TIFF und HEIC ein JPEG machen")
    ap.add_argument("ordner", nargs="?", default=None,
                    help="Ordner mit den Bildern, relativ zur Wurzel "
                         "(Standard: quellen/)")
    ap.add_argument("--wurzel", type=Path, default=None)
    ap.add_argument("--ja", action="store_true",
                    help="Rückfrage überspringen, die Originale werden ersetzt")
    a = ap.parse_args()

    if not pillow_da():
        return 1

    wurzel = a.wurzel.resolve() if a.wurzel else finde_wurzel()
    ordner = Path(a.ordner) if a.ordner else Path("quellen")
    if not ordner.is_absolute():
        ordner = wurzel / ordner
    if not ordner.is_dir():
        print(f"Kein Ordner: {ordner}")
        return 1

    aufbereiten, leicht = kandidaten(ordner)
    print(f"Ordner: {ordner}")

    # Was liegen bleibt, steht vor der Liste und vor der Rückfrage. Gefragt
    # wird nur nach dem, was wirklich ersetzt wird. Ein HEIC ohne pillow-heif
    # und eine Datei, deren JPEG eine andere überschriebe, bleiben unlesbar,
    # bis jemand etwas tut. Das färbt den Lauf rot, wie eine kaputte Datei.
    # Eine Datei mit Karte ist schon importiert, sie färbt ihn nicht.
    mit_karte = halte_mit_karte_zurueck(wurzel, ordner, aufbereiten)
    aufbereiten = [p for p in aufbereiten if p not in mit_karte]
    ohne_heif = halte_heic_zurueck(ordner, aufbereiten)
    aufbereiten = [p for p in aufbereiten if p not in ohne_heif]
    namensgleich = halte_namensgleiche_zurueck(ordner, aufbereiten)
    aufbereiten = [p for p in aufbereiten if p not in namensgleich]
    liegen = len(mit_karte) + len(ohne_heif) + len(namensgleich)
    rot = bool(ohne_heif or namensgleich)

    if not aufbereiten:
        if liegen:
            print("\nSonst ist nichts zu tun.")
        else:
            print(f"Nichts zu tun: kein Bild liegt über {menschenmass(SCHWELLE)}, "
                  f"keins ist TIFF oder HEIC.")
        melde_quer_liegende(ordner, leicht)
        return 1 if rot else 0

    gesamt = sum(p.stat().st_size for p in aufbereiten)
    print(f"\n{bilder(len(aufbereiten))} aufzubereiten, zusammen {menschenmass(gesamt)}:")
    for pfad in aufbereiten:
        neuer_name = f"  -> {ziel(pfad).name}" if wird_jpeg(pfad) else ""
        print(f"  {pfad.relative_to(ordner).as_posix()}  "
              f"{menschenmass(pfad.stat().st_size)}{neuer_name}")

    als_jpeg = sum(wird_jpeg(p) for p in aufbereiten)
    if not a.ja and not frage(len(aufbereiten), gesamt, als_jpeg):
        print("Abgebrochen. Es wurde nichts geschrieben.")
        return 1

    print()
    gespart = 0
    fertig = 0
    fehler = 0
    for pfad in aufbereiten:
        name = pfad.relative_to(ordner).as_posix()
        try:
            ergebnis = bereite_auf(pfad)
        except Exception as exc:  # noqa: BLE001
            # Eine kaputte Datei soll den Stapel nicht anhalten. Die anderen
            # vierzehn Seiten sollen trotzdem lesbar werden. Gezählt wird sie,
            # damit der Lauf am Ende rot ist.
            print(f"  FEHLER bei {name}: {exc}")
            fehler += 1
            continue
        if ergebnis is None:
            print(f"  unverändert  {name} (kleiner wird es nicht)")
            continue
        zielpfad, weniger, gedreht = ergebnis
        fertig += 1
        gespart += weniger
        neuer_name = f"{zielpfad.name}, " if wird_jpeg(pfad) else ""
        hinweis = ", gedreht" if gedreht else ""
        print(f"  ok  {name}  -> {neuer_name}{menschenmass(zielpfad.stat().st_size)}{hinweis}")

    # Ein quer liegendes Bild wird auch dann geschrieben, wenn es dabei wächst,
    # ein TIFF oder HEIC ebenso. Dann ist die Bilanz negativ, und das soll sie
    # auch sagen.
    bilanz = (f"{menschenmass(gespart)} gespart" if gespart >= 0
              else f"{menschenmass(-gespart)} mehr belegt")
    print(f"\nFertig: {fertig} von {len(aufbereiten)} aufbereitet, {bilanz}.")
    if liegen:
        print(f"Liegen geblieben, siehe oben: {bilder(liegen)}.")
    if leicht:
        print(f"Unter der Schwelle geblieben und unangetastet: {bilder(len(leicht))}.")
    melde_quer_liegende(ordner, leicht)
    return 1 if fehler or rot else 0


if __name__ == "__main__":
    raise SystemExit(main())
