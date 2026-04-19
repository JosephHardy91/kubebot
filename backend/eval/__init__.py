# Retrieval evaluation set for Kubebot
#
# Each entry has:
#   question  – the user query
#   expected  – list of resource names (or field_path prefixes) that
#               *should* appear in the top-k results for a correct answer
#
# Expand this list as new failure modes surface.

EVAL_SET: list[dict] = [
    {
        "question": "How do I create a deployment?",
        "expected": ["deployments.apps"],
    },
    {
        "question": "What is a pod?",
        "expected": ["pods"],
    },
    {
        "question": "How do I expose a service externally?",
        "expected": ["services"],
    },
    {
        "question": "How do I set resource limits on a container?",
        "expected": ["pods", "limitranges"],
    },
    {
        "question": "What is a ConfigMap and how do I use it?",
        "expected": ["configmaps"],
    },
    {
        "question": "How do I manage secrets in Kubernetes?",
        "expected": ["secrets"],
    },
    {
        "question": "What is a StatefulSet?",
        "expected": ["statefulsets.apps"],
    },
    {
        "question": "How do I set up a CronJob?",
        "expected": ["cronjobs.batch"],
    },
    {
        "question": "What are namespaces used for?",
        "expected": ["namespaces"],
    },
    {
        "question": "How do I configure horizontal pod autoscaling?",
        "expected": ["horizontalpodautoscalers.autoscaling"],
    },
    {
        "question": "How do I persist data with volumes?",
        "expected": ["persistentvolumeclaims", "persistentvolumes"],
    },
    {
        "question": "What is an Ingress?",
        "expected": ["ingresses.networking.k8s.io"],
    },
    {
        "question": "How do I do a rolling update?",
        "expected": ["deployments.apps"],
    },
    {
        "question": "What is a DaemonSet?",
        "expected": ["daemonsets.apps"],
    },
    {
        "question": "How do I check container logs?",
        "expected": ["pods"],
    },
]
