#!/bin/bash
# Script to verify ACL rules are installed in Floodlight
# Run this from your host terminal (not Mininet CLI)

echo "=========================================="
echo "Checking ACL Rules in Floodlight"
echo "=========================================="
echo ""

FLOODLIGHT_URL="http://localhost:8080"

echo "Fetching ACL rules from Floodlight..."
echo "URL: ${FLOODLIGHT_URL}/wm/acl/rules/json"
echo ""

# Try to get ACL rules
response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${FLOODLIGHT_URL}/wm/acl/rules/json")
http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
body=$(echo "$response" | sed '/HTTP_CODE/d')

if [ "$http_code" != "200" ]; then
    echo "❌ ERROR: Failed to connect to Floodlight"
    echo "   HTTP Code: $http_code"
    echo "   Response: $body"
    echo ""
    echo "Make sure:"
    echo "  1. Floodlight is running"
    echo "  2. Floodlight is accessible at $FLOODLIGHT_URL"
    exit 1
fi

# Check if response is empty or contains rules
if [ -z "$body" ] || [ "$body" = "[]" ] || [ "$body" = "null" ]; then
    echo "⚠️  WARNING: No ACL rules found!"
    echo ""
    echo "This means:"
    echo "  - ACL rules are NOT installed"
    echo "  - Guest/Employee hosts can access blocked protocols"
    echo ""
    echo "To fix this:"
    echo "  1. Make sure dac_app.py is running"
    echo "  2. Check dac_app.py output for rule installation messages"
    echo "  3. Restart dac_app.py if needed"
    exit 1
fi

# Count SSH blocking rules (Floodlight uses nw_src and tp_dst with underscores, tp_dst is a number)
ssh_rules=$(echo "$body" | grep -o '"tp_dst"[^,]*22' | wc -l | tr -d ' ')
guest_ssh_rules=$(echo "$body" | grep -A10 -B10 '"tp_dst"[^,]*22' | grep -c '"nw_src"[^,]*"10\.0\.0\.\(3\|6\|9\)/32"' || echo "0")

echo "✅ ACL rules found!"
echo ""
echo "Summary:"
echo "  - Total ACL rules: $(echo "$body" | grep -o '"action"' | wc -l | tr -d ' ')"
echo "  - SSH (port 22) blocking rules: $ssh_rules"
echo "  - Guest SSH blocking rules: $guest_ssh_rules"
echo ""

# Check for specific guest IP rules (Floodlight uses nw_src with underscores)
echo "Checking for guest role blocking rules..."
for guest_ip in "10.0.0.3" "10.0.0.6" "10.0.0.9"; do
    if echo "$body" | grep -q "\"nw_src\"[^,]*\"${guest_ip}/32\""; then
        echo "  ✅ Found blocking rules for $guest_ip (guest)"
    else
        echo "  ❌ NO blocking rules found for $guest_ip (guest)"
    fi
done

echo ""
echo "Full ACL rules (formatted):"
echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
echo ""

