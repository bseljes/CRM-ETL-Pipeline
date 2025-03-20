# CRM-ETL-Pipeline

## Overview  
This project aims to overhaul the existing ETL pipeline used by our company for extracting, transforming, and loading (ETL) data from our CRM system, Podio. The current infrastructure stores data in a **MySQL 5.7 production server**, which is subsequently transferred to a **SQL 8.0 AdHoc server** via Azure.

### Issues with the Current Pipeline  
- **Data Integrity**: Approximately **85% of the data** is successfully extracted and transferred, leaving significant gaps.  
- **High Operational Costs**: The reliance on Azure infrastructure results in elevated ongoing expenses.  
- **Unreliable Automation**: Podio’s current automation, which is still in the "Beta" stage, lacks support and guarantees for accurate performance.

### Proposed Solution  
I propose leveraging **Python** and **REST APIs** to develop a **pub/sub queue system** to retrieve data from Podio and store it in **MongoDB**, replacing the current SQL-based setup. This solution will:  
- Enhance **data accuracy**  
- Significantly reduce **operational costs**  
- Eliminate reliance on **Podio’s unreliable automation**

### Challenges  
- Transitioning from SQL to **MongoDB** requires the development of a new workflow to handle data structure changes within Podio. Additionally, an automated system will be needed to update metadata for field label and datatype changes in the AdHoc server.  
- Due to **Podio’s outdated API wrapper** (last updated 15 years ago), a **custom API wrapper** will need to be created to ensure smoother and more efficient integration.
