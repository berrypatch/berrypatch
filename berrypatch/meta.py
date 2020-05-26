import datetime
import json

META_FILENAME = "berry-meta.json"


def create_metadata(app, variables):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    result = {
        "name": app.name,
        "variables": variables,
        "data_files": app.data_files,
        "compose_template": app.compose_template,
        "berry_json": app.to_berry_json(),
        "date_installed": now,
    }
    return result


def load_metadata(filename):
    with open(filename, "r") as fp:
        berry_meta = json.loads(fp.read())
    # TODO: validate structure
    return berry_meta
