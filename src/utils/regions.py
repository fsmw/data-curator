"""Region and language definitions for filtering and analysis."""

# Latinoamérica y Caribe
LATAM_ISO_CODES = [
    "ARG", "BOL", "BRA", "CHL", "COL", "CRI", "CUB", "DOM", "ECU", 
    "SLV", "GTM", "HTI", "HND", "MEX", "NIC", "PAN", "PRY", "PER", 
    "URY", "VEN", "PRI"
]

# Norteamérica
NORTH_AMERICA_ISO_CODES = [
    "USA", "CAN", "MEX"
]

# Sudamérica
SOUTH_AMERICA_ISO_CODES = [
    "ARG", "BOL", "BRA", "CHL", "COL", "ECU", "GUY", "PRY", "PER",
    "SUR", "URY", "VEN"
]

# Centroamérica y Caribe
CENTRAL_AMERICA_CARIBBEAN_ISO_CODES = [
    "BLZ", "CRI", "SLV", "GTM", "HND", "NIC", "PAN",
    "CUB", "DOM", "HTI", "JAM", "PRI", "TTO", "BRB", "GRD", 
    "LCA", "VCT", "ATG", "DMA", "BHS"
]

# Toda América (Norte, Centro, Sur y Caribe)
AMERICAS_ISO_CODES = list(set(
    NORTH_AMERICA_ISO_CODES + 
    SOUTH_AMERICA_ISO_CODES + 
    CENTRAL_AMERICA_CARIBBEAN_ISO_CODES
))

# Europa
EUROPE_ISO_CODES = [
    "ALB", "AND", "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK",
    "EST", "FIN", "FRA", "DEU", "GIB", "GRC", "HUN", "ISL", "IRL",
    "ITA", "LVA", "LIE", "LTU", "LUX", "MLT", "MCO", "NLD", "NOR",
    "POL", "PRT", "ROU", "SMR", "SRB", "SVK", "SVN", "ESP", "SWE",
    "CHE", "GBR", "UKR", "BLR", "MDA", "RUS", "MKD", "BIH", "MNE",
    "KOS", "VAT"
]

# Unión Europea
EU_ISO_CODES = [
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN",
    "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX",
    "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE"
]

# Asia
ASIA_ISO_CODES = [
    "AFG", "ARM", "AZE", "BHR", "BGD", "BTN", "BRN", "KHM", "CHN",
    "CYP", "GEO", "IND", "IDN", "IRN", "IRQ", "ISR", "JPN", "JOR",
    "KAZ", "KWT", "KGZ", "LAO", "LBN", "MYS", "MDV", "MNG", "MMR",
    "NPL", "PRK", "OMN", "PAK", "PHL", "QAT", "SAU", "SGP", "KOR",
    "LKA", "SYR", "TWN", "TJK", "THA", "TLS", "TUR", "TKM", "ARE",
    "UZB", "VNM", "YEM"
]

# África
AFRICA_ISO_CODES = [
    "DZA", "AGO", "BEN", "BWA", "BFA", "BDI", "CPV", "CMR", "CAF",
    "TCD", "COM", "COG", "COD", "CIV", "DJI", "EGY", "GNQ", "ERI",
    "SWZ", "ETH", "GAB", "GMB", "GHA", "GIN", "GNB", "KEN", "LSO",
    "LBR", "LBY", "MDG", "MWI", "MLI", "MRT", "MUS", "MAR", "MOZ",
    "NAM", "NER", "NGA", "RWA", "STP", "SEN", "SYC", "SLE", "SOM",
    "ZAF", "SSD", "SDN", "TZA", "TGO", "TUN", "UGA", "ZMB", "ZWE"
]

# Oceanía
OCEANIA_ISO_CODES = [
    "AUS", "NZL", "FJI", "PNG", "SLB", "VUT", "NCL", "PYF", "WSM",
    "KIR", "TUV", "TON", "NRU", "PLW", "MHL", "FSM", "GUM", "ASM"
]

# Países de habla hispana
SPANISH_SPEAKING_ISO_CODES = [
    "ARG", "BOL", "CHL", "COL", "CRI", "CUB", "DOM", "ECU", "SLV",
    "GTM", "HND", "MEX", "NIC", "PAN", "PRY", "PER", "ESP", "URY",
    "VEN", "PRI", "GIB", "PHL", "GNQ"  # España, Gibraltar, Filipinas, Guinea Ecuatorial
]

# Países de habla inglesa (principales)
ENGLISH_SPEAKING_ISO_CODES = [
    "USA", "GBR", "CAN", "AUS", "NZL", "IRL", "ZAF", "IND", "NGA",
    "KEN", "GHA", "TZA", "UGA", "ZMB", "ZWE", "JAM", "TTO", "BRB",
    "GUY", "BHS", "BLZ", "FJI", "SGP", "PHL", "PAK", "BGD", "MYS"
]

# Países de habla portuguesa
PORTUGUESE_SPEAKING_ISO_CODES = [
    "BRA", "PRT", "AGO", "MOZ", "CPV", "GNB", "STP", "TLS", "MAC"
]

# Países de habla francesa (principales)
FRENCH_SPEAKING_ISO_CODES = [
    "FRA", "CAN", "BEL", "CHE", "LUX", "MCO", "DZA", "MAR", "TUN",
    "SEN", "CIV", "MLI", "BFA", "NER", "TCD", "COG", "GAB", "CMR",
    "TGO", "BEN", "MDG", "HTI", "RWA", "BDI", "COD", "CAF", "GIN",
    "TCD", "COM", "DJI", "VUT", "PYF", "NCL"
]

# Mapeo de nombres de filtros a listas de códigos
FILTER_PRESETS = {
    # Regiones geográficas
    "latam": LATAM_ISO_CODES,
    "latinamerica": LATAM_ISO_CODES,
    "latinoamerica": LATAM_ISO_CODES,
    "north_america": NORTH_AMERICA_ISO_CODES,
    "norteamerica": NORTH_AMERICA_ISO_CODES,
    "south_america": SOUTH_AMERICA_ISO_CODES,
    "sudamerica": SOUTH_AMERICA_ISO_CODES,
    "central_america_caribbean": CENTRAL_AMERICA_CARIBBEAN_ISO_CODES,
    "centroamerica_caribe": CENTRAL_AMERICA_CARIBBEAN_ISO_CODES,
    "americas": AMERICAS_ISO_CODES,
    "america": AMERICAS_ISO_CODES,
    "europe": EUROPE_ISO_CODES,
    "europa": EUROPE_ISO_CODES,
    "eu": EU_ISO_CODES,
    "union_europea": EU_ISO_CODES,
    "asia": ASIA_ISO_CODES,
    "africa": AFRICA_ISO_CODES,
    "oceania": OCEANIA_ISO_CODES,
    
    # Idiomas
    "spanish": SPANISH_SPEAKING_ISO_CODES,
    "español": SPANISH_SPEAKING_ISO_CODES,
    "hispanohablante": SPANISH_SPEAKING_ISO_CODES,
    "hispanico": SPANISH_SPEAKING_ISO_CODES,
    "english": ENGLISH_SPEAKING_ISO_CODES,
    "ingles": ENGLISH_SPEAKING_ISO_CODES,
    "portuguese": PORTUGUESE_SPEAKING_ISO_CODES,
    "portugues": PORTUGUESE_SPEAKING_ISO_CODES,
    "french": FRENCH_SPEAKING_ISO_CODES,
    "frances": FRENCH_SPEAKING_ISO_CODES,
}


def get_filter_countries(filter_name: str) -> list:
    """
    Obtener lista de códigos ISO para un filtro predefinido.
    
    Args:
        filter_name: Nombre del filtro (ej: 'latam', 'spanish', 'americas')
        
    Returns:
        Lista de códigos ISO3 o lista vacía si no existe
    """
    return FILTER_PRESETS.get(filter_name.lower(), [])


def list_available_filters() -> dict:
    """
    Retorna un diccionario con los filtros disponibles organizados por categoría.
    """
    return {
        "regiones_geograficas": {
            "latam / latinamerica / latinoamerica": "Latinoamérica y Caribe",
            "north_america / norteamerica": "Norteamérica",
            "south_america / sudamerica": "Sudamérica",
            "central_america_caribbean / centroamerica_caribe": "Centroamérica y Caribe",
            "americas / america": "Toda América",
            "europe / europa": "Europa",
            "eu / union_europea": "Unión Europea",
            "asia": "Asia",
            "africa": "África",
            "oceania": "Oceanía",
        },
        "idiomas": {
            "spanish / español / hispanohablante / hispanico": "Países de habla hispana",
            "english / ingles": "Países de habla inglesa",
            "portuguese / portugues": "Países de habla portuguesa",
            "french / frances": "Países de habla francesa",
        }
    }
