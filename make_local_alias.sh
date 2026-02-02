#!/bin/bash
# make_local_alias.sh
echo 'alias kubebot='\''f(){ curl -s -X POST localhost:8000/ask --data "{\"question\":\"$1\"}" -H "Content-Type: application/json" | jq -r ".answer" | glow; }; f'\''' >> ~/.bashrc && echo "Added to ~/.bashrc"