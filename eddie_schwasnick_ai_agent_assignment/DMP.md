# Mini Data Management Plan – Polygon.io Equity Reference Data

## Objective
The objective of this project is to collect and manage U.S.-listed equity reference data from the Polygon.io API for educational and analytical purposes. The dataset will demonstrate structured API collection, documentation, and quality assessment according to best practices.

## Data Sources
- **Primary Source:** Polygon.io API (free tier)  
- **Endpoint:** `/v3/reference/tickers`  
- **Authentication:** Free API key  

## Data Types
Variables collected:
- `ticker` – Unique symbol identifying the stock or fund  
- `name` – Full company or fund name  
- `market` – Type of market (e.g., stocks, crypto, fx)  
- `locale` – Geographic locale of listing (e.g., “us”)  
- `primary_exchange` – Primary exchange code (e.g., XNYS, XNAS)  
## Geographic Scope
- **Coverage:** United States equity markets  
- **Exchanges:** NYSE, Nasdaq, BATS, ARCA  

## Time Range
- **Data Type:** Real-time reference data (snapshot at time of collection)  
- **Historical Data:** Not included for this project, but Polygon provides endpoints for historical options and price series with user-specified time intervals.  

## Storage and Organization
- **Raw data:** Saved as JSON in `data/raw/`  
- **Processed data:** Reserved for future cleaning, in `data/processed/`  
- **Metadata:** Auto-generated and stored in `data/metadata/`  
- **Logs:** Execution logs in `logs/collection.log`  
- **Reports:** Human-readable reports in `reports/`  

## Documentation
- Metadata includes collection info, sources, processing history, and variable dictionary.  
- Quality reports assess completeness, accuracy, consistency, and timeliness.  
- Summaries provide collection statistics, issues, and recommendations.  

## Ethics and Respectful Collection
- All collection follows API provider’s usage terms.  
- No personal or sensitive data is accessed.  
- The agent includes randomized delays and adaptive strategies to respect rate limits.  

**Collector:** Edward Schwasnick  
**Date:** September 30, 2025
