#!/bin/bash
# make_local_alias.sh
# Cookie file stores the session between calls
echo 'alias kubebot='\''f(){ curl -s -X POST localhost:8000/ask --data "{\"question\":\"$1\"}" -H "Content-Type: application/json" -b ~/.kubebot_cookies -c ~/.kubebot_cookies | jq -r ".answer" | glow; }; f'\''' >> ~/.bashrc && echo "Added to ~/.bashrc"
echo 'alias kubebot_clear='\''rm -f ~/.kubebot_cookies && echo "Session cleared"'\''' >> ~/.bashrc && echo "Added kubebot_clear to ~/.bashrc"