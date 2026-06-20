-- Q1: Total companies loaded
SELECT COUNT(*) AS total_companies FROM companies;

-- Q2: Sector distribution
SELECT s.sector_name, COUNT(c.company_id) AS company_count
FROM sectors s JOIN companies c ON s.sector_id = c.sector_id
GROUP BY s.sector_name ORDER BY company_count DESC;

-- Q3: Companies with most years of P&L data
SELECT c.ticker, c.company_name, COUNT(DISTINCT pl.year) AS years_of_data
FROM companies c JOIN profitandloss pl ON c.company_id = pl.company_id
GROUP BY c.company_id ORDER BY years_of_data DESC LIMIT 10;

-- Q4: Revenue trend for top 5 companies
SELECT c.ticker, pl.year, pl.revenue
FROM companies c JOIN profitandloss pl ON c.company_id = pl.company_id
WHERE c.ticker IN ('RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK')
ORDER BY c.ticker, pl.year;

-- Q5: Balance sheet total assets vs total liabilities per company
SELECT c.ticker, bs.year, bs.total_assets, bs.total_liabilities,
       (bs.total_assets - bs.total_liabilities) AS equity
FROM companies c JOIN balancesheet bs ON c.company_id = bs.company_id
ORDER BY bs.total_assets DESC LIMIT 15;

-- Q6: Cash flow from operations across companies (latest year)
SELECT c.ticker, cf.year, cf.cash_from_operations
FROM companies c JOIN cashflow cf ON c.company_id = cf.company_id
WHERE cf.year = (SELECT MAX(year) FROM cashflow WHERE company_id = c.company_id)
ORDER BY cf.cash_from_operations DESC LIMIT 10;

-- Q7: Stock price record count per company
SELECT c.ticker, c.company_name, COUNT(sp.price_id) AS price_records
FROM companies c JOIN stock_prices sp ON c.company_id = sp.company_id
GROUP BY c.company_id ORDER BY price_records DESC;

-- Q8: Data coverage check – companies with < 5 years of P&L data
SELECT c.ticker, c.company_name, COUNT(DISTINCT pl.year) AS years_covered
FROM companies c LEFT JOIN profitandloss pl ON c.company_id = pl.company_id
GROUP BY c.company_id HAVING years_covered < 5 ORDER BY years_covered;

-- Q9: Foreign key integrity check
PRAGMA foreign_key_check;

-- Q10: Row counts for all tables
SELECT 'companies' AS table_name, COUNT(*) AS row_count FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'financial_ratios', COUNT(*) FROM financial_ratios
UNION ALL SELECT 'peer_groups', COUNT(*) FROM peer_groups
ORDER BY table_name;
