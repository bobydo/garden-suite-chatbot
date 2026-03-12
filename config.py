import os

# === Base paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "data", "pdf")
WEBSITES_DIR = os.path.join(BASE_DIR, "data", "websites")
TEXTS_DIR = os.path.join(BASE_DIR, "data", "txt")
EXCEL_DIR = os.path.join(BASE_DIR, "data", "excel")
INDEX_DIR = os.path.join(BASE_DIR, "index", "qdrant")

# === Qdrant settings ===
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
PDF_COLLECTION = "pdf_index"
WEBSITE_COLLECTION = "website_index"
EXCEL_COLLECTION = "excel_index"
TEXT_COLLECTION = "text_index"

# === Ollama models ===
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# === Prompt file ===
SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "system_prompt.txt")

# === Excel files (URLs only) ===
EXCELS = [
    "https://www.edmonton.ca/sites/default/files/public-files/assets/ProvincialFCSSMeasuresBank.xlsx?cb=1687494504",
]

# === Websites (URLs only) ===
WEBSITES = [
    "https://www.edmonton.ca/",
    "https://www.edmonton.ca/business_economy/permits-development-construction",
    "https://www.edmonton.ca/city_government/bylaws",
    "https://www.edmonton.ca/city_government/bylaws/zoning-bylaw",
    "https://www.edmonton.ca/programs_services/for_schools_students_teachers/post-secondary-student-resources",
    "https://www.edmonton.ca/programs_services/housing/affordable-housing-developments",
    "https://www.edmonton.ca/programs_services/housing/welcome-homes",
    "https://www.edmonton.ca/projects_plans/transit/capital-line-south",
    "https://www.edmonton.ca/residential-neighbourhoods",
    "https://www.edmonton.ca/residential_neighbourhoods/application-requirements-house-permits",
    "https://www.edmonton.ca/residential_neighbourhoods/backyard-housing",
    "https://www.edmonton.ca/residential_neighbourhoods/develop-your-property",
    "https://www.edmonton.ca/residential_neighbourhoods/lot_grading/surface-drainage-problems-faq",
    "https://www.edmonton.ca/residential_neighbourhoods/residential-construction",
    "https://www.edmonton.ca/residential_neighbourhoods/secondary-suites",
    "https://www.edmonton.ca/residential_neighbourhoods/uncovered-deck",
    "https://zoningbylaw.edmonton.ca/backyard-housing",
    "https://zoningbylaw.edmonton.ca/bylaw-pdf-print",
    "https://zoningbylaw.edmonton.ca/dc-20974",
    "https://zoningbylaw.edmonton.ca/dc-21145",
    "https://zoningbylaw.edmonton.ca/dc-21276",
    "https://zoningbylaw.edmonton.ca/dc1-15946",
    "https://zoningbylaw.edmonton.ca/dc1-20476",
    "https://zoningbylaw.edmonton.ca/driveway",
    "https://zoningbylaw.edmonton.ca/flanking-side-yard",
    "https://zoningbylaw.edmonton.ca/home",
    "https://zoningbylaw.edmonton.ca/part-2-standard-zones-and-overlays",
    "https://zoningbylaw.edmonton.ca/part-2-standard-zones-and-overlays/commercial-zones/2100-cg-general-commercial-zone",
    "https://zoningbylaw.edmonton.ca/part-2-standard-zones-and-overlays/residential-zones/210-rs-small-scale-residential-zone",
    "https://zoningbylaw.edmonton.ca/part-2-standard-zones-and-overlays/residential-zones/220-rsf-small-scale-flex-residential-zone",
    "https://zoningbylaw.edmonton.ca/part-2-standard-zones-and-overlays/residential-zones/230-rsm-small-medium-scale-transition-residential-zone",
    "https://zoningbylaw.edmonton.ca/part-3-special-area-zones",
    "https://zoningbylaw.edmonton.ca/part-3-special-area-zones/paisley-special-area/3151-pld-paisley-low-density-zone",
    "https://zoningbylaw.edmonton.ca/part-5-general-development-regulations",
    "https://zoningbylaw.edmonton.ca/part-5-general-development-regulations/550-inclusive-design",
    "https://zoningbylaw.edmonton.ca/part-5-general-development-regulations/560-landscaping",
    "https://zoningbylaw.edmonton.ca/part-5-general-development-regulations/580-parking-access-site-circulation-and-bike-parking",
    "https://zoningbylaw.edmonton.ca/part-5-general-development-regulations/590-projection-setbacks",
    "https://zoningbylaw.edmonton.ca/part-6-specific-development-regulations",
    "https://zoningbylaw.edmonton.ca/part-6-specific-development-regulations/610-backyard-housing",
    "https://zoningbylaw.edmonton.ca/part-6-specific-development-regulations/660-home-based-businesses",
    "https://zoningbylaw.edmonton.ca/part-6-specific-development-regulations/690-signs",
    "https://zoningbylaw.edmonton.ca/part-8-definitions",
    "https://zoningbylaw.edmonton.ca/part-8-definitions/820-general-definitions",
    "https://zoningbylaw.edmonton.ca/setback",
    "https://zoningbylaw.edmonton.ca/street",
    "https://timberhaus.ca/blog/average-cost-to-build-a-house-in-edmonton",
    "https://www.coohom.com/article/cost-per-square-foot-to-build-a-house-in-edmonton",
    "https://newhomesalberta.ca/new-home-construction-costs-alberta-build-your-dream-home",
    "https://christina-reid.c21.ca/2025/01/20/building-cost-vs-buying-resale-in-edmonton-which-is-right-for-you",
]

# Minimum total characters from the cheap HTML loader before skipping Playwright
# If the initial WebBaseLoader result has at least this many characters across documents,
# we consider it "good enough" and avoid the heavier Playwright render.
# Tune higher to be stricter (render more often), lower to render less. Try 1200-2000 if render more
HTML_MIN_TEXT_CHARS = 600

# === Excel processing limits ===
# Maximum number of rows to process per Excel sheet to prevent huge documents
# Large Excel files can create documents that exceed token limits and slow processing
EXCEL_MAX_ROWS_PER_SHEET = int(os.getenv("EXCEL_MAX_ROWS_PER_SHEET", "1000"))

# === Retrieval quality settings ===
# Cosine distance threshold — candidates with distance > threshold are discarded (0=identical, 1=orthogonal)
RETRIEVAL_SCORE_THRESHOLD = float(os.getenv("RETRIEVAL_SCORE_THRESHOLD", "0.65"))
# Weight for vector similarity vs BM25 in hybrid scoring (1.0 = pure vector, 0.0 = pure BM25)
HYBRID_ALPHA = float(os.getenv("HYBRID_ALPHA", "0.7"))
# How many extra candidates to fetch per collection before filtering (gives BM25 a wider pool)
HYBRID_FETCH_MULTIPLIER = int(os.getenv("HYBRID_FETCH_MULTIPLIER", "3"))


