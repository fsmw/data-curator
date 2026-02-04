
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.append('/home/fsmw/dev/mises/data-curator')

from src.cleaning import DataCleaner
from src.config import Config

def test_filtering():
    print("Testing Latam Filtering...")
    
    # Create mock dataframe with mixed countries
    data = {
        'country': ['Argentina', 'Brazil', 'United States', 'China', 'Chile', 'France', 'Bolivia'],
        'value': [1, 2, 3, 4, 5, 6, 7]
    }
    df = pd.DataFrame(data)
    
    cleaner = DataCleaner(Config())
    
    # 1. Standardize (relies on src.const.COUNTRY_CODES)
    # Argentina -> ARG, Brazil -> BRA, U.S. -> USA, China -> CHN, Chile -> CHL, France -> FRA, Bolivia -> BOL
    df_std = cleaner._standardize_countries(df)
    
    print("Standardized codes:")
    print(df_std['country'].tolist())
    
    # 2. Filter Latam
    df_latam = cleaner.filter_by_region(df_std, 'latam')
    
    print("\nFiltered (Latam):")
    print(df_latam['country'].tolist())
    
    expected = ['ARG', 'BRA', 'CHL', 'BOL']
    result = df_latam['country'].tolist()
    
    if sorted(result) == sorted(expected):
        print("\nSUCCESS: Filtered correctly.")
        return True
    else:
        print(f"\nFAILURE: Expected {expected}, got {result}")
        return False

if __name__ == "__main__":
    if test_filtering():
        sys.exit(0)
    else:
        sys.exit(1)
