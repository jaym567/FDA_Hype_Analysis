
import os
import logging
from pathlib import Path

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Subdirectories
RAW_PMA_DIR = RAW_DIR / "pma"
RAW_RECALLS_DIR = RAW_RECALLS_DIR = RAW_DIR / "recalls"
RAW_OPENALEX_DIR = RAW_DIR / "openalex"

# Ensure directories exist
for d in [RAW_PMA_DIR, RAW_RECALLS_DIR, RAW_OPENALEX_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- APIs ---
OPENFDA_PMA_URL = "https://api.fda.gov/device/pma.json"
OPENFDA_RECALL_URL = "https://api.fda.gov/device/recall.json"
OPENALEX_WORKS_URL = "https://api.openalex.org/works"

# --- Parameters ---
START_YEAR = 1985
END_YEAR = 2025

# Advisory Committees relevant to "Surgical Devices" (Class III)
# Codes from FDA: 
# GI: Gastroenterology/Urology (GU)
# SU: General and Plastic Surgery
# OR: Orthopedic
# CV: Cardiovascular
# NE: Neurology
# OP: Ophthalmic
# DE: Dental
# AN: Anesthesiology (maybe less relevant, but includes tubes/monitors)
# EN: Ear, Nose, Throat
ADVISORY_COMMITTEES = [
    "General, Plastic Surgery",
    "Orthopedic",
    "Cardiovascular",
    "Neurology",
    "Ophthalmic",
    "Gastroenterology, Urology",
    "Dental",
    "Ear, Nose, Throat",
    "Obstetrics/Gynecology"
]

# Mapping committees to simpler specialty names
SPECIALTY_MAP = {
    "General, Plastic Surgery": "General/Plastic",
    "Orthopedic": "Orthopedic",
    "Cardiovascular": "Cardiovascular",
    "Neurology": "Neuro",
    "Ophthalmic": "Ophthalmic",
    "Gastroenterology, Urology": "GI/Urology",
    "Dental": "Dental",
    "Ear, Nose, Throat": "ENT",
    "Obstetrics/Gynecology": "OBGYN"
}

# OpenAlex settings
# Use environment variable or update here to bypass daily caps
OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "jmodi7@jh.edu") 

# Safety Limits to preserve credits
MAX_RESULTS_PER_DEVICE = 100  # Cap results per technology
SLEEP_BETWEEN_REQUESTS = 1.2  # Increase delay for burst protection
DEVICES_PER_SESSION = 500      # Set high to complete all remaining 143 devices in this final session

# --- Logging ---
def setup_logger(name, log_file=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    # File handler
    if log_file:
        fh = logging.FileHandler(log_file)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
    return logger
