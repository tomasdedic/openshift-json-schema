# OPENSHIFT JSON schema generation

## TOOLING
```bash
# tooling instalace
python3 -m venv ~/venv/openapi
source ~/venv/openapi/bin/activate                                │

pip install "cython<3.0.0" && pip install --no-build-isolation pyyaml==5.4.1
pip install --upgrade setuptools wheel
pip install openapi2jsonschema

```
## GET SCHEMAS
```bash
oc proxy --port=8080 &
python build_schema.py -u http://127.0.0.1:8080 -t "" -d output_directory
```

