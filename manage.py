import argparse
from service.retriever_service import RetrieverService

def main():
    parser = argparse.ArgumentParser(description="Garden Suite Chatbot Manager")
    parser.add_argument("cmd", choices=["ingest_pdfs", "ingest_websites", "ingest_texts", "ingest_excel"], help="Command to run")
    args = parser.parse_args()

    r = RetrieverService()
    if args.cmd == "ingest_pdfs":
        r.ingest_pdfs()
    elif args.cmd == "ingest_websites":
        r.ingest_websites()
    elif args.cmd == "ingest_texts":
        r.ingest_texts_folder()
    elif args.cmd == "ingest_excel":
        r.ingest_excel_files()
    else:
        print("Unknown command.")

if __name__ == "__main__":
    main()
