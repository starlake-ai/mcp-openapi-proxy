#!/bin/bash
# This script iterates over all listening TCP ports on localhost
# and checks the /openapi.json endpoint on each port.
# It uses 'ss' to list listening ports, 'awk' to extract port numbers,
# and 'curl' to verify if /openapi.json returns HTTP 200.
#
# Usage:
#   chmod +x scripts/check_openapi.sh
#   ./scripts/check_openapi.sh
#
# Extract all unique listening TCP ports using ss and awk.
ports=$(ss -tuln | awk '/LISTEN/ {
  split($5, a, ":");
  port = a[length(a)];
  if(port ~ /^[0-9]+$/) print port
}' | sort -nu)
 
echo "Found listening ports:"
echo "$ports"
echo ""
 
# Iterate over each port and test the /openapi.json endpoint.
for port in $ports; do
    echo "Checking port $port for /openapi.json endpoint..."
    http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/openapi.json)
    if [[ $http_code == "200" ]]; then
        echo "Port $port: Valid /openapi.json endpoint detected (HTTP $http_code)"
    else
        echo "Port $port: /openapi.json not valid (HTTP $http_code)"
    fi
    echo ""
done
