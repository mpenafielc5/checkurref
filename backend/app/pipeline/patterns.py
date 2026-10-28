"""Patrones de texto de las referencias, compartidos por todo el análisis.

Se escriben una sola vez y cada módulo los combina en sus expresiones: si se
corrige uno (por ejemplo, para aceptar otro tipo de inicial), el cambio llega a
la detección de la norma, a la separación y a la extracción de campos.
"""

# Mayúsculas y minúsculas con tilde, ñ y diéresis (Peñafiel, Quirós, Müller).
UPPER = "A-ZÀ-ÖØ-Þ"
LOWER = "a-zß-öø-ÿ"

# Número de una referencia IEEE al inicio: [1], [12]. El grupo guarda el número.
IEEE_NUMBER = r"\[(\d{1,3})\]"

# Iniciales de un nombre: "J.", "M. A.", "J.-M.".
INITIALS = rf"(?:[{UPPER}]\.\s?-?)+"

# Autor en APA, apellido antes de las iniciales: "Pérez, M." o "Delgado Quirós, M. A.".
SURNAME_FIRST = rf"[{UPPER}][\w'’-]+(?:\s[\w'’-]+){{0,2}},\s{INITIALS}"

# Sin fecha: "s. f.", "s.f." o "n.d.", a veces sin el último punto.
UNDATED = r"s\.\s?f\.?|n\.\s?d\.?"

# Año entre paréntesis de APA: (2020), (2020a), (2020, 3 de mayo) o sin fecha.
YEAR_IN_PARENS = rf"\((?:\d{{4}}[a-z]?|{UNDATED})(?:,[^)]{{0,30}})?\)"
