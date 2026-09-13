"""
Módulo de gestión de frases diarias y Easter Egg (80s/90s Pop Culture).
Selecciona de manera determinística una frase por día para mostrar en el sidebar.
"""
import json
import os
from datetime import date
from typing import Dict, Any, List, Optional

QUOTES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frases.json")

def load_all_quotes() -> List[Dict[str, Any]]:
    """Carga todas las frases del archivo frases.json."""
    if not os.path.exists(QUOTES_FILE):
        return [
            {
                "id": 1,
                "frase": "¡Hermosa mañana, verdad?",
                "autor": "Guillermo Francella",
                "obra": "Extermineitors IV",
                "año": "1992",
                "categoria": "Cultura Pop Argentina"
            }
        ]
    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return [
            {
                "id": 1,
                "frase": "Hasta la vista, baby.",
                "autor": "Arnold Schwarzenegger",
                "obra": "Terminator 2",
                "año": "1991",
                "categoria": "Acción Clásica"
            }
        ]

def get_daily_quote(target_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Obtiene la frase del día de forma determinística basada en el día del año.
    Garantiza que todos los usuarios vean la misma frase el mismo día y rote diariamente.
    """
    quotes = load_all_quotes()
    if not quotes:
        return {
            "frase": "¡A comerlaaaaa!",
            "autor": "Guillermo Francella",
            "obra": "Poné a Francella",
            "año": "1998",
            "categoria": "Cultura Pop Argentina"
        }
    
    if target_date is None:
        target_date = date.today()
    
    # Cálculo determinístico: ordinal del día modulo cantidad de frases
    day_number = target_date.toordinal()
    index = day_number % len(quotes)
    return quotes[index]

def get_random_quote() -> Dict[str, Any]:
    """Obtiene una frase aleatoria para interacción de usuario."""
    import random
    quotes = load_all_quotes()
    return random.choice(quotes) if quotes else get_daily_quote()
