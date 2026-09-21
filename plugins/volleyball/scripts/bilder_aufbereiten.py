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

Pillow ist die einzige Abhängigkeit und nur hier eine (ADR-0005). Fehlt es,
bricht dieses Skript mit einem Installationshinweis ab und schreibt nichts.
Die übrigen Skripte des Plugins laufen davon unberührt weiter mit der
Standardbibliothek.

Bewusst nicht zugesagt wird "alles, was Pillow öffnet": HEIC und TIFF öffnet es
ohne Zusatzpaket nicht, und die Zusage bräche still bei dem Nutzer, der ein
iPhone benutzt.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tpdaten import finde_wurzel, interpreter, konsole_vorbereiten  # noqa: E402

# Ab hier gilt eine Datei als zu schwer. Die Schwelle steht auf der Dateigröße
# und nicht auf der Pixelzahl, weil sie sich ohne Bildbibliothek ablesen lässt:
# was gar nicht angefasst wird, muss auch nicht geöffnet werden.
SCHWELLE = 2 * 1024 * 1024
ZIELKANTE = 2000
QUALITAET = 85

ENDUNGEN = {".jpg", ".jpeg", ".png"}
JPEG_ENDUNGEN = {".jpg", ".jpeg"}

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
        print("Nur dieses Skript braucht Pillow. Die übrigen Skripte des")
        print("Plugins laufen ohne es weiter.")
        return False
    return True


# --------------------------------------------------------------------------
# Auswählen
# --------------------------------------------------------------------------

def kandidaten(ordner: Path) -> tuple[list[Path], list[Path]]:
    """Die Bilder über der Schwelle und die, die darunter liegen bleiben.

    Gesucht wird auch in Unterordnern: `quellen/` sammelt Quelle für Quelle in
    eigenen Ordnern, und ein Aufruf auf `quellen/` soll den ganzen Bestand
    lesbar machen, nicht nur dessen oberste Ebene.
    """
    schwer: list[Path] = []
    leicht: list[Path] = []
    for pfad in sorted(ordner.rglob("*")):
        if not pfad.is_file() or pfad.suffix.lower() not in ENDUNGEN:
            continue
        (schwer if pfad.stat().st_size > SCHWELLE else leicht).append(pfad)
    return schwer, leicht


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


def bereite_auf(pfad: Path) -> tuple[int, bool] | None:
    """Bereitet eine Datei auf und ersetzt sie. Gibt (gespart, gedreht) zurück.

    None heisst: die Datei bleibt, wie sie ist, weil das Erzeugnis nicht
    kleiner wäre. Lag sie quer, wird trotzdem geschrieben. Eine quer liegende
    Seite ist auch dann unlesbar, wenn sie nichts einspart.
    """
    from PIL import Image, ImageOps  # erst hier, damit der Hinweis aus pillow_da() greift

    vorher = pfad.stat().st_size
    endung = pfad.suffix.lower()

    with Image.open(pfad) as bild:
        lag_quer = bild.getexif().get(ORIENTIERUNG, 1) not in (0, 1)
        gerade = ImageOps.exif_transpose(bild)
        klein = verkleinert(gerade)

        # Die Drehung ist jetzt in die Pixel eingerechnet. Bliebe der
        # EXIF-Eintrag stehen, drehte der nächste Betrachter ein zweites Mal.
        exif = klein.getexif()
        exif.pop(ORIENTIERUNG, None)
        roh_exif = exif.tobytes() if len(exif) else None

        neu = kodiere(klein, endung, roh_exif)

    if len(neu) >= vorher and not lag_quer:
        return None

    # Erst danebenschreiben, dann umbenennen: ein Abbruch mittendrin lässt das
    # Original heil liegen, statt es halb überschrieben zu hinterlassen. Nach
    # einem geglückten replace gibt es die Zwischendatei nicht mehr, das
    # Aufräumen im finally ist dann folgenlos. Sonst nimmt es die Reste mit,
    # statt sie in quellen/ liegen zu lassen.
    zwischen = pfad.with_name(pfad.name + ".neu")
    try:
        zwischen.write_bytes(neu)
        os.replace(zwischen, pfad)
    finally:
        zwischen.unlink(missing_ok=True)
    return vorher - len(neu), lag_quer


# --------------------------------------------------------------------------
# Rückfrage
# --------------------------------------------------------------------------

def frage(anzahl: int, gesamt: int) -> bool:
    """Fragt einmal für den ganzen Stapel, nicht je Datei."""
    ersetzt = "wird" if anzahl == 1 else "werden"
    print(f"\n{bilder(anzahl)} {ersetzt} unter demselben Namen ersetzt "
          f"({menschenmass(gesamt)}). Weiter? [j/N] ", end="", flush=True)
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
        description="Quellbilder verkleinern und nach EXIF geradedrehen")
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

    schwer, leicht = kandidaten(ordner)
    print(f"Ordner: {ordner}")
    if not schwer:
        print(f"Nichts zu tun: kein Bild liegt über {menschenmass(SCHWELLE)}.")
        melde_quer_liegende(ordner, leicht)
        return 0

    gesamt = sum(p.stat().st_size for p in schwer)
    print(f"{bilder(len(schwer))} über {menschenmass(SCHWELLE)}, "
          f"zusammen {menschenmass(gesamt)}:")
    for pfad in schwer:
        print(f"  {pfad.relative_to(ordner).as_posix()}  "
              f"{menschenmass(pfad.stat().st_size)}")

    if not a.ja and not frage(len(schwer), gesamt):
        print("Abgebrochen. Es wurde nichts geschrieben.")
        return 1

    print()
    gespart = 0
    fertig = 0
    fehler = 0
    for pfad in schwer:
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
        weniger, gedreht = ergebnis
        fertig += 1
        gespart += weniger
        hinweis = ", gedreht" if gedreht else ""
        print(f"  ok  {name}  -> {menschenmass(pfad.stat().st_size)}{hinweis}")

    # Ein quer liegendes Bild wird auch dann geschrieben, wenn es dabei wächst.
    # Dann ist die Bilanz negativ, und das soll sie auch sagen.
    bilanz = (f"{menschenmass(gespart)} gespart" if gespart >= 0
              else f"{menschenmass(-gespart)} mehr belegt")
    print(f"\nFertig: {fertig} von {len(schwer)} aufbereitet, {bilanz}.")
    if leicht:
        print(f"Unter der Schwelle geblieben und unangetastet: {bilder(len(leicht))}.")
    melde_quer_liegende(ordner, leicht)
    return 1 if fehler else 0


if __name__ == "__main__":
    raise SystemExit(main())
