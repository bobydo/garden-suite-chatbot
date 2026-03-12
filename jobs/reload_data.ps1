Start-Job -ScriptBlock { cd D:\garden-suite-chatbot; .\myenv\Scripts\activate; python manage.py ingest_pdfs }
Start-Job -ScriptBlock { cd D:\garden-suite-chatbot; .\myenv\Scripts\activate; python manage.py ingest_websites }
Start-Job -ScriptBlock { cd D:\garden-suite-chatbot; .\myenv\Scripts\activate; python manage.py ingest_texts }
Start-Job -ScriptBlock { cd D:\garden-suite-chatbot; .\myenv\Scripts\activate; python manage.py ingest_excel }