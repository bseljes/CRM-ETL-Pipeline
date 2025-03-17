# CRM-ETL-Pipeline  

## Overview  
This project aims to replace my company’s existing ETL pipeline for extracting, transforming, and loading (ETL) data from our CRM (Podio). The current setup saves data from Podio into a **MySQL 5.7 production server**, which is then transferred to a **SQL 8.0 AdHoc server** via Azure.  

### Issues with the Current Pipeline  
- **Data Accuracy**: Only about **85% of the data** is successfully saved and transferred.  
- **High Costs**: The reliance on Azure significantly increases operational expenses.  
- **Unreliable Automation**: The current pipeline depends on Podio’s built-in automation, which is still **in beta** and not guaranteed to be **100% reliable**.  

### Solution  
Using **Python** and **REST APIs**, I will build a **pub/sub queue system** to retrieve data from Podio and store it in **MongoDB** as a new production database. This approach will:  
    Improve **data accuracy**  
    Reduce **operational costs**  
    Eliminate dependency on **Podio’s unreliable automation**  

### Future Improvements  
- Develop an **ETL pipeline** to transfer data from the **new MongoDB production database** to the **AdHoc database**—**without** relying on Azure, further reducing costs.  
- Since Podio has **not updated its API wrapper in 15 years**, I will need to **build a custom wrapper** for better integration.  
