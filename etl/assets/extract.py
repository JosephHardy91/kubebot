import subprocess
from subprocess import CompletedProcess
import dagster as dg

@dg.asset
def k8s_resources()->list[str]:
    result = subprocess.run(
        ["kubectl", "api-resources", "--verbs=list", "-o", "name"],
        capture_output=True, text=True
    )
    return result.stdout.strip().split("\n")

def explain_resource(resource: str) -> CompletedProcess[str]:
    result = subprocess.run(
        ["kubectl", "explain", resource, "--recursive"],
        capture_output=True, text=True
    )
    return result

@dg.asset
def k8s_explain_docs(k8s_resources: list[str])->dict[str,str]:
    docs = {}
    for resource in k8s_resources:
         result = explain_resource(resource)
         if result.returncode == 0:
            docs[resource] = result.stdout
    return docs