import os

# === Base paths ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PDF_DIR = os.path.join(BASE_DIR, "data", "pdf")
WEBSITES_DIR = os.path.join(BASE_DIR, "data", "websites")
TEXTS_DIR = os.path.join(BASE_DIR, "data", "processed")
INDEX_DIR = os.path.join(BASE_DIR, "index", "qdrant")

# === Qdrant settings ===
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
BYLAW_COLLECTION = "bylaw_index"
GUIDES_COLLECTION = "guides_index"

# === Ollama models ===
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# === Prompt file ===
SYSTEM_PROMPT_PATH = os.path.join(BASE_DIR, "prompts", "system_prompt.txt")

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
    "https://www.edmonton.ca/public-files/assets/document?path=PDF/Approved_2012-14_Capital_Budget.pdf",
    "https://www.edmonton.ca/public-files/assets/document?path=PDF/Discussion_Paper_4_North_Saskatchewan_River_Water_Quality.pdf",
    "https://www.edmonton.ca/public-files/assets/document?path=PDF/Secondary_Suite_Design_Guide.pdf",
    "https://www.edmonton.ca/public-files/assets/document?path=PDF/current_Zoning_Bylaw.pdf",
    "https://www.edmonton.ca/public-files/assets/document?path=Residential_Landscaping_and_Hardsurfacing_Requirements.pdf",
    "https://www.edmonton.ca/residential-neighbourhoods",
    "https://www.edmonton.ca/residential_neighbourhoods/application-requirements-house-permits",
    "https://www.edmonton.ca/residential_neighbourhoods/backyard-housing",
    "https://www.edmonton.ca/residential_neighbourhoods/develop-your-property",
    "https://www.edmonton.ca/residential_neighbourhoods/lot_grading/surface-drainage-problems-faq",
    "https://www.edmonton.ca/residential_neighbourhoods/residential-construction",
    "https://www.edmonton.ca/residential_neighbourhoods/secondary-suites",
    "https://www.edmonton.ca/residential_neighbourhoods/uncovered-deck",
    "https://www.edmonton.ca/sites/default/files/public-files/assets/ProvincialFCSSMeasuresBank.xlsx?cb=1687494504",
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
    "https://timberhaus.ca/blog/average-cost-to-build-a-house-in-edmonton/?utm_source=chatgpt.com",
    "https://www.coohom.com/article/cost-per-square-foot-to-build-a-house-in-edmonton?utm_source=chatgpt.com",
    "https://newhomesalberta.ca/new-home-construction-costs-alberta-build-your-dream-home/?utm_source=chatgpt.com",
    "https://christina-reid.c21.ca/2025/01/20/building-cost-vs-buying-resale-in-edmonton-which-is-right-for-you?utm_source=chatgpt.com",
]


