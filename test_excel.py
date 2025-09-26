from service.excel_loader import ExcelLoader

# Test Excel loading
url = "https://www.edmonton.ca/sites/default/files/public-files/assets/ProvincialFCSSMeasuresBank.xlsx?cb=1687494504"
print(f"Testing Excel URL: {url}")

docs = ExcelLoader(url).load()
print(f"Loaded {len(docs)} Excel sheets")

if docs:
    for i, doc in enumerate(docs):
        print(f"\nSheet {i+1}:")
        print(f"  Sheet name: {doc.metadata.get('sheet_name')}")
        print(f"  Rows: {doc.metadata.get('rows')}")
        print(f"  Columns: {doc.metadata.get('columns')}")
        print(f"  Content preview: {doc.page_content[:200]}...")
else:
    print("No documents loaded")