"""Quick test for search logic."""

MOCK_INDICATORS = [
    {"id": "9", "indicator": "tax_revenues_gdp", "source": "owid", "topic": "presion_fiscal", "keywords": "impuestos recaudación fiscal tax revenue tributaria"},
    {"id": "10", "indicator": "government_spending", "source": "owid", "topic": "presion_fiscal", "keywords": "gasto público government spending fiscal"},
    {"id": "31", "indicator": "tax_revenue", "source": "oecd", "topic": "presion_fiscal", "keywords": "impuestos recaudación fiscal presión tributaria tax"},
    {"id": "61", "indicator": "tax_pressure", "source": "eclac", "topic": "presion_fiscal", "keywords": "presión fiscal impuestos carga tributaria tax"},
]

query = "tax"
results = []

for ind in MOCK_INDICATORS:
    if query:
        query_match = (
            query in ind["indicator"].lower() or 
            query in ind["topic"].lower() or
            query in ind.get("keywords", "").lower()
        )
        if not query_match:
            continue
    results.append(ind)

print(f"Found {len(results)} results for '{query}':")
for r in results:
    print(f"  - {r['indicator']} ({r['source'].upper()})")
