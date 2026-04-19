import subprocess
from subprocess import CompletedProcess
import dagster as dg
import re

@dg.asset
def k8s_resources()->list[str]:
    result = subprocess.run(
        ["kubectl", "api-resources", "--verbs=list", "-o", "name"],
        capture_output=True, text=True
    )
    return result.stdout.strip().split("\n")

def parse_explain_text(text: str) -> str:
    lines = text.splitlines()
    out = []
    in_fields = False

    for line in lines:
        stripped = line.strip()

        # detect headers like FIELDS:, DESCRIPTION:, etc.
        if stripped.endswith(":") and stripped.isupper():
            in_fields = stripped.startswith("FIELDS")
            out.append(stripped)
            continue

        if in_fields:
            # normalize indentation to 2 spaces per level
            indent = len(line) - len(line.lstrip())
            level = indent // 2

            normalized = "  " * level + stripped
            out.append(normalized)
        else:
            # leave other sections mostly untouched
            out.append(stripped)

    return "\n".join(out)


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
            docs[resource] = parse_explain_text(result.stdout)
    return docs
