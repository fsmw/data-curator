
import sys
from pathlib import Path
sys.path.append('/home/fsmw/dev/mises/data-curator')

from src.dataset_catalog import DatasetCatalog
from src.config import Config

# Mock config
class MockConfig:
    data_root = Path('/tmp')
    def get_directory(self, name):
        return Path('/tmp')

def test_naming():
    catalog = DatasetCatalog(MockConfig())
    
    test_cases = [
        ("pib_owid_latam_2020_2024.csv", "Pib - Latam", "pib", "owid"), 
        ("gasto_militar_owid_latam_2010_2024.csv", "Gasto Militar - Latam", "gasto_militar", "owid"),
        ("inflation_owid_latam_2015_2024.csv", "Inflation - Latam", "inflation", "owid"),
        ("general_sample_complex-id_2000_2020.csv", "Complex Id", "general", "sample"),
        ("tax_oecd_global_2020.csv", "Tax - Global", "tax", "oecd"),
        # Edge case: generic name produced by some cleaners
        ("general_owid_price-changes-consumer-goods-services-united-states_global_1997_2024.csv", 
         "Price Changes Consumer Goods Services United States", "general", "owid")
    ]
    
    print("Running Naming Tests...")
    all_passed = True
    for filename, expected_name, expected_topic, expected_source in test_cases:
        path = Path(filename)
        res = catalog._parse_filename(path)
        
        print(f"\nFile: {filename}")
        print(f"  -> Name: '{res['indicator_name']}'")
        print(f"  -> Topic: '{res['topic']}'")
        print(f"  -> Source: '{res['source']}'")
        
        if res['indicator_name'] != expected_name:
            print(f"  FAILED: Expected '{expected_name}', got '{res['indicator_name']}'")
            all_passed = False
        else:
            print("  PASSED")
            
    return all_passed

if __name__ == "__main__":
    success = test_naming()
    sys.exit(0 if success else 1)
