import os

BERRYPATCH_ROOT = os.getenv("BERRYPATCH_ROOT", "/usr/local/Berrypatch")
SOURCES_DIR = os.path.join(BERRYPATCH_ROOT, "sources")
INSTANCES_DIR = os.path.join(BERRYPATCH_ROOT, "instances")

FARM_BASE_ADDRESS = "github.com/berrypatch/berryfarm"
FARM_GIT_CLONE_URL = f"https://{FARM_BASE_ADDRESS}.git"
FARM_ROOT = os.path.join(SOURCES_DIR, FARM_BASE_ADDRESS)
FARM_APPS_DIR = os.path.join(FARM_ROOT, "apps")
