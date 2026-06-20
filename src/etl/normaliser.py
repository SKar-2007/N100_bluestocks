import re


def normalize_year(year_val, context=None):
    if year_val is None:
        return None
    if isinstance(year_val, (int, float)):
        year_val = str(int(year_val))

    year_val = str(year_val).strip()

    if not year_val:
        return None

    year_val = year_val.replace('\u2011', '-').replace('\u2012', '-').replace('\u2013', '-').replace('\u2014', '-')

    patterns = [
        (r'^FY(\d{4})$', lambda m: int(m.group(1))),
        (r'^FY(\d{2})$', lambda m: int(m.group(1)) + 2000 if int(m.group(1)) <= 50 else int(m.group(1)) + 1900),
        (r'^(\d{4})\s*[-–]\s*(\d{2})$', lambda m: int(m.group(1))),
        (r'^(\d{4})\s*[-–]\s*(\d{4})$', lambda m: int(m.group(1))),
        (r'^(\d{4})$', lambda m: int(m.group(1))),
        (r'^(?:(?:Mar|March|Dec|December|Jan|January|Jun|June|Sep|September)[\s-])?(\d{4})$', lambda m: int(m.group(1))),
        (r'^\d{2}[-–]\w{3}[-–](\d{4})$', lambda m: int(m.group(1))),
        (r'^\w{3}[-–]\d{2}[-–](\d{4})$', lambda m: int(m.group(1))),
        (r'^(\d{2})[-–]\d{2}[-–](\d{4})$', lambda m: int(m.group(2))),
        (r'^CY(\d{4})$', lambda m: int(m.group(1))),
        (r'^(\d{4})[-–](\d{2})[-–](\d{2})$', lambda m: int(m.group(1))),
    ]

    for pattern, handler in patterns:
        m = re.match(pattern, year_val, re.IGNORECASE)
        if m:
            result = handler(m)
            if context == 'fiscal' and result:
                return result
            return result

    try:
        return int(float(year_val))
    except (ValueError, TypeError):
        return None


def normalize_ticker(ticker):
    if ticker is None:
        return None

    ticker = str(ticker).strip().upper()

    if not ticker:
        return None

    ticker = re.sub(r'\s+', '', ticker)

    while re.search(r'\.(NS|BSE|NSE|BO)$', ticker, flags=re.IGNORECASE):
        ticker = re.sub(r'\.(NS|BSE|NSE|BO)$', '', ticker, flags=re.IGNORECASE)
    ticker = re.sub(r'^(NSE|BSE|NS|BO)[:\s]*', '', ticker, flags=re.IGNORECASE)

    ticker = re.sub(r'&', 'AND', ticker)
    ticker = re.sub(r'[^A-Z0-9\s-]', '', ticker)

    ticker = ticker.strip()

    special_mappings = {
        'TCS': 'TCS',
        'INFY': 'INFY',
        'WIPRO': 'WIPRO',
        'HCLTECH': 'HCLTECH',
        'TECHM': 'TECHM',
        'RELIANCE': 'RELIANCE',
        'HINDUNILVR': 'HINDUNILVR',
        'ITC': 'ITC',
        'SBIN': 'SBIN',
        'HDFCBANK': 'HDFCBANK',
        'ICICIBANK': 'ICICIBANK',
        'AXISBANK': 'AXISBANK',
        'KOTAKBANK': 'KOTAKBANK',
        'INDUSINDBK': 'INDUSINDBK',
        'BHARTIARTL': 'BHARTIARTL',
        'LT': 'LT',
        'MARUTI': 'MARUTI',
        'M&M': 'MANDM',
        'TATAMOTORS': 'TATAMOTORS',
        'TATASTEEL': 'TATASTEEL',
        'JSWSTEEL': 'JSWSTEEL',
        'SUNPHARMA': 'SUNPHARMA',
        'DRREDDY': 'DRREDDY',
        'HINDALCO': 'HINDALCO',
        'ONGC': 'ONGC',
        'COALINDIA': 'COALINDIA',
        'NTPC': 'NTPC',
        'POWERGRID': 'POWERGRID',
        'ADANIENT': 'ADANIENT',
        'ADANIPORTS': 'ADANIPORTS',
        'ASIANPAINT': 'ASIANPAINT',
        'NESTLEIND': 'NESTLEIND',
        'BAJFINANCE': 'BAJFINANCE',
        'BAJAJFINSV': 'BAJAJFINSV',
        'HDFC': 'HDFCLIFE',
        'ULTRACEMCO': 'ULTRACEMCO',
        'GRASIM': 'GRASIM',
        'BRITANNIA': 'BRITANNIA',
        'TITAN': 'TITAN',
        'DIVISLAB': 'DIVISLAB',
        'CIPLA': 'CIPLA',
        'SBILIFE': 'SBILIFE',
        'EICHERMOT': 'EICHERMOT',
        'HEROMOTOCO': 'HEROMOTOCO',
        'BAJAJ-AUTO': 'BAJAJ-AUTO',
        'NMDC': 'NMDC',
        'VEDL': 'VEDL',
        'IOC': 'IOC',
        'BPCL': 'BPCL',
        'HINDZINC': 'HINDZINC',
        'GAIL': 'GAIL',
        'TRENT': 'TRENT',
        'ZOMATO': 'ZOMATO',
        'DMART': 'DMART',
        'AVENUE': 'AVENUE',
        'BERGEPAINT': 'BERGEPAINT',
        'SHREECEM': 'SHREECEM',
        'AMBUJACEM': 'AMBUJACEM',
        'PIDILITIND': 'PIDILITIND',
        'COLPAL': 'COLPAL',
        'HAVELLS': 'HAVELLS',
        'BOSCHLTD': 'BOSCHLTD',
        'SIEMENS': 'SIEMENS',
        'ABB': 'ABB',
    }

    if ticker in special_mappings:
        return special_mappings[ticker]

    if not ticker:
        return None

    return ticker
