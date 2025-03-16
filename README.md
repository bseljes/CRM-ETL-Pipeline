# CRM-ETL-Pipeline
The purpose of this pipeline is to replace the ETL pipeline currently in use by my company.  The current pipeline was to save all data from the CRM (Podio) inside a MySQL 5.7 production server.  Then using Azure  the production server would load into a SQL 8.0 AdHoc server.
The issue with the current pipeline is only about 85% of the information was successfully saved and moved.  The cost associated with it was astronomical for the accuracy.  The current pipeline relies on Podio automation that is "In Beta" per Podio and was tagged as/
shouldn't be relied on to be 100% accurate.  Using Python to create a gateway using rest APIs I will be able to create a pub/sub queue of information that will be queried from Podio and sent to a MongoDB to be saved as a new production database.  This will fix the accuracy issue.
Later on I will want to create an ETL to move the data from the production to the AdHoc database without using Azure this will fix the associated cost issue.
