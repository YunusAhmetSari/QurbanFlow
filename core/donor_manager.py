"""
QurbanFlow – Spenderverwaltung

Verwaltet die Ordnerstruktur für Spender:
- Prüft ob ein Spender schon existiert
- Berechnet den korrekten Zähler (Max_Mustermann_1, Max_Mustermann_2, ...)
- Legt neue Ordner an
"""

import re
from pathlib import Path
from typing import Tuple, List, Dict

from config import DONORS_DIR, OUTPUT_DIR


def normalize_name(name: str) -> str:
    """
    Normalisiert einen Spendernamen für die Ordnerbenennung.

    - Entfernt führende/nachfolgende Leerzeichen
    - Behält Leerzeichen zwischen Worten bei (Title Case)
    - Entfernt Sonderzeichen (außer Buchstaben, Zahlen, Leerzeichen, Bindestriche)

    Args:
        name: Roher Spendername (z.B. "max mustermann")

    Returns:
        Normalisierter Name (z.B. "Max Mustermann")
    """
    name = name.strip()
    # Title Case anwenden
    name = name.title()
    # Nur Buchstaben, Zahlen, Leerzeichen und Bindestriche behalten
    name = re.sub(r"[^\w\-\s]", "", name, flags=re.UNICODE)
    # Doppelte Leerzeichen entfernen
    name = re.sub(r"\s+", " ", name)
    return name


def _parse_folder_name(folder_name: str) -> Tuple[str, int]:
    """
    Extrahiert Name und Zähler aus einem Ordnernamen.
    
    Formate:
    - "Name" -> ("Name", 1)
    - "Name 1" -> ("Name", 1)
    - "Name 2" -> ("Name", 2)
    """
    # Prüfen auf "Name Zahl" am Ende
    match = re.match(r"^(.*?) (\d+)$", folder_name)
    if match:
        return match.group(1), int(match.group(2))
    
    # Kein Zähler -> Zähler ist 1
    return folder_name, 1


def get_existing_donations(name: str) -> List[Path]:
    """
    Findet alle existierenden Spenden-Ordner für einen normalisierten Namen.

    Args:
        name: Normalisierter Spendername (z.B. "Max Mustermann")

    Returns:
        Sortierte Liste von Ordner-Pfaden für diesen Spender
    """
    if not DONORS_DIR.exists():
        return []

    matches = []
    
    # Wir suchen nach exaktem Namen oder "Name N"
    for folder in DONORS_DIR.iterdir():
        if not folder.is_dir():
            continue
            
        folder_name = folder.name
        base_name, counter = _parse_folder_name(folder_name)
        
        if base_name == name:
            matches.append((counter, folder))

    # Nach Zähler sortieren
    matches.sort(key=lambda x: x[0])
    return [m[1] for m in matches]


def get_next_counter(name: str) -> int:
    """
    Berechnet den nächsten Zähler für einen Spender.

    Args:
        name: Normalisierter Spendername

    Returns:
        Nächste Zählernummer
    """
    existing = get_existing_donations(name)
    if not existing:
        return 1

    counters = []
    for folder in existing:
        _, counter = _parse_folder_name(folder.name)
        counters.append(counter)
        
    return max(counters) + 1


def create_donor_folder(raw_name: str) -> Tuple[Path, Path, str, int]:
    """
    Erstellt einen neuen Spender-Ordner mit korrektem Zähler.

    Erstellt sowohl den Eingangs-Ordner (Spender/) als auch den Ausgabe-Ordner (Output/).

    Args:
        raw_name: Roher Spendername (wird normalisiert)

    Returns:
        Tuple von (donor_input_path, donor_output_path, normalized_name, counter)

    Example:
        >>> path_in, path_out, name, count = create_donor_folder("Max Mustermann")
        >>> print(path_in)  # Spender/Max Mustermann 2 (falls 1 existiert)
    """
    normalized = normalize_name(raw_name)
    counter = get_next_counter(normalized)
    
    # Formatierung:
    # 1 -> "Name 1" (um konsistent zu bleiben mit "Mila Gönen 1")
    # Oder wollen wir "Name" für 1 erlauben?
    # Basierend auf "Mila Gönen" UND "Mila Gönen 1" ist es gemischt.
    # Wir nutzen ab sofort immer "Name Counter" für neue Ordner, um Eindeutigkeit zu haben.
    
    folder_name = f"{normalized} {counter}"

    donor_path = DONORS_DIR / folder_name
    output_path = OUTPUT_DIR / folder_name

    donor_path.mkdir(parents=True, exist_ok=True)
    output_path.mkdir(parents=True, exist_ok=True)

    return donor_path, output_path, normalized, counter


def list_all_donors() -> Dict[str, List[Path]]:
    """
    Listet alle Spender und ihre Spenden-Ordner auf.

    Returns:
        Dict mit Spendername → Liste von Ordner-Pfaden
    """
    if not DONORS_DIR.exists():
        return {}

    donors: Dict[str, List[Path]] = {}

    for folder in sorted(DONORS_DIR.iterdir()):
        if folder.is_dir():
            name, _ = _parse_folder_name(folder.name)
            donors.setdefault(name, []).append(folder)

    return donors


def get_donation_count(raw_name: str) -> int:
    """
    Gibt die Anzahl bisheriger Spenden eines Spenders zurück.

    Args:
        raw_name: Spendername (wird normalisiert)

    Returns:
        Anzahl bisheriger Spenden (0 wenn neu)
    """
    normalized = normalize_name(raw_name)
    return len(get_existing_donations(normalized))
