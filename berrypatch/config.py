import os

BERRYPATCH_ROOT = os.getenv("BERRYPATCH_ROOT", "/usr/local/Berrypatch")
APPS_DIR = os.getenv("BERRYPATCH_APPS_DIR", os.path.join(BERRYPATCH_ROOT, "apps"))
INSTANCES_DIR = os.path.join(BERRYPATCH_ROOT, "instances")
