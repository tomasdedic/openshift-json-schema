from shutil import which
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import argparse
import os
import urllib
import sys
import urllib
import ssl
import yaml
import json
import subprocess

existing_definitions_file = None

OPENSHIFT_API_SPEC_FILE = "openshift-api-spec.json"

script_dir = os.path.dirname(os.path.realpath(__file__))

openapi2jsonschema_location = which("openapi2jsonschema")


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


# Check if prerequisite executables are available
if openapi2jsonschema_location is None:
    print("Error: openapi2jsonschema is not available")
    sys.exit(1)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

parser = argparse.ArgumentParser()

parser.add_argument("-u", "--url", action="store", dest="url",
                    required=True, help="OpenShift API URL")
parser.add_argument("-t", "--token", action="store",
                    dest="token", required=True, help="OpenShift API Token")
parser.add_argument("-ov", "--openshift-version", action="store",
                    dest="openshift_version", default="master", help="OpenShift Version")
parser.add_argument("-d", "--destination", action="store",
                    dest="destination", help="Output file")
parser.add_argument("-s", "--strict", action="store",
                    dest="strict", help="Strict schema")
parser.add_argument("--dry-run", action="store", type=str2bool, nargs='?',
                    const=True, default=False, dest="dryrun", help="Strict schema")

args = parser.parse_args()


def loadYAML(location):
    if os.path.isfile(location):
        req = urllib.request.Request(
            "file://" + os.path.realpath(location))
        res = urllib.request.urlopen(req)
        return yaml.load(
            res.read(), Loader=yaml.SafeLoader)
    else:
        headers = {"Authorization": "Bearer {}".format(args.token)}

        req = urllib.request.Request(url=openapi_endpoint, headers=headers)

        try:
            res = urllib.request.urlopen(req, context=ctx)
            return yaml.load(res.read(), Loader=yaml.SafeLoader)
        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            sys.exit(1)
        except URLError as e:
            print('Failed to reach a server.')
            print('Reason: ', e.reason)
            sys.exit(1)


openapi_endpoint = "{}/openapi/v2".format(args.url)

print("Downloading and parsing API schema from: {}\n".format(openapi_endpoint))

openapi_data = loadYAML(openapi_endpoint)

definitions = openapi_data["definitions"]
#delete_list = []
delete_list = ['io.netapp.trident.v1.TridentActionMirrorUpdate', 'io.netapp.trident.v1.TridentActionSnapshotRestore', 'io.netapp.trident.v1.TridentBackendConfig', 'io.netapp.trident.v1.TridentBackend', 'io.netapp.trident.v1.TridentConfigurator', 'io.netapp.trident.v1.TridentMirrorRelationship', 'io.netapp.trident.v1.TridentNode', 'io.netapp.trident.v1.TridentOrchestrator', 'io.netapp.trident.v1.TridentSnapshotInfo', 'io.netapp.trident.v1.TridentSnapshot', 'io.netapp.trident.v1.TridentStorageClass', 'io.netapp.trident.v1.TridentTransaction', 'io.netapp.trident.v1.TridentVersion', 'io.netapp.trident.v1.TridentVolumePublication', 'io.netapp.trident.v1.TridentVolumeReference', 'io.netapp.trident.v1.TridentVolume', 'io.netapp.trident.v1.TridentActionMirrorUpdateList', 'io.netapp.trident.v1.TridentActionSnapshotRestoreList', 'io.netapp.trident.v1.TridentBackendConfigList', 'io.netapp.trident.v1.TridentBackendList', 'io.netapp.trident.v1.TridentConfiguratorList', 'io.netapp.trident.v1.TridentMirrorRelationshipList', 'io.netapp.trident.v1.TridentNodeList', 'io.netapp.trident.v1.TridentOrchestratorList', 'io.netapp.trident.v1.TridentSnapshotInfoList', 'io.netapp.trident.v1.TridentSnapshotList', 'io.netapp.trident.v1.TridentStorageClassList', 'io.netapp.trident.v1.TridentTransactionList', 'io.netapp.trident.v1.TridentVersionList', 'io.netapp.trident.v1.TridentVolumeList', 'io.netapp.trident.v1.TridentVolumePublicationList', 'io.netapp.trident.v1.TridentVolumeReferenceList']

spec_file = os.path.join(script_dir, OPENSHIFT_API_SPEC_FILE)


with open(spec_file, "w") as openapi_spec_file:
    for type_name in definitions:
        type_def = definitions[type_name]
        if "x-kubernetes-group-version-kind" in type_def:
            for kube_ext in type_def["x-kubernetes-group-version-kind"]:
                if "properties" not in type_def and type_name not in delete_list:
                    delete_list.append(type_name)

    if len(delete_list) > 0:
        print("The following API resources do not have valid OpenAPI specifications:\n")
        print(delete_list)

    for del_item in delete_list:
        print(del_item)
        try:
            del definitions[del_item]
        except:
            pass
    openapi_spec_file.write(json.dumps(openapi_data, indent=2))

if args.dryrun:
    print("\nDry run activated: Not building schema\n")
    sys.exit(0)

destination = args.destination

if destination is None:
    destination = "{}/openshift-json-schema".format(script_dir)

output_destination = os.path.join(
    destination, "{}-standalone".format(args.openshift_version))

if args.strict is not None:
    output_destination += "-strict"


# Check if existing _definitions.json file exists
definitions_file = os.path.join(output_destination, "_definitions.json")
if os.path.isfile(definitions_file):
    print("\nParsing existing _definitions.json file\n")
    existing_definitions_file = loadYAML(definitions_file)


command = [openapi2jsonschema_location, "-o",
           output_destination, "--expanded", "--kubernetes","--strict", spec_file]

if args.strict is not None:
    command.append("--strict")


print("\nProcessing schemas into {}\n".format(output_destination))

job = subprocess.Popen(
    command,
    shell=False,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    close_fds=True,
)

try:
    (stdout, stderr) = job.communicate(timeout=10000)
except subprocess.TimeoutExpired:
    job.kill()
    (stdout, stderr) = job.communicate()
stdout = stdout.decode("utf-8")
stderr = stderr.decode("utf-8")
print("[STDERR]: %s" % stderr)
print("[STDOUT]: %s" % stdout)

# Attempt to Merge _definitions file
if existing_definitions_file is not None:
    print("Merging Contents from Existing Definition File")
    new_definitions_file = loadYAML(definitions_file)

    with open(definitions_file, "w") as updated_definitions_file:
        existing_definitions_file.update(new_definitions_file)
        updated_definitions_file.write(
            json.dumps(existing_definitions_file, indent=2))


if os.path.exists(spec_file):
    os.remove(spec_file)
