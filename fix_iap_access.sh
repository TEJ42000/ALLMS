#!/bin/bash
# Emergency script to restore IAP access for matej@mgms.eu

echo "=========================================="
echo "Fixing IAP Access for matej@mgms.eu"
echo "=========================================="
echo ""

# Add user to IAP
echo "Adding matej@mgms.eu to IAP access list..."
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=lls-study-portal \
  --project=vigilant-axis-483119-r8 \
  --region=europe-west4 \
  --member='user:matej@mgms.eu' \
  --role='roles/iap.httpsResourceAccessor'

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SUCCESS! Your email has been added to IAP."
    echo ""
    echo "Please wait 1-2 minutes, then try accessing:"
    echo "https://lls-study-portal-sarfwmfd3q-ez.a.run.app/admin/courses"
    echo ""
else
    echo ""
    echo "❌ ERROR: Failed to add email to IAP."
    echo "You may need to authenticate first:"
    echo "  gcloud auth login"
    echo ""
fi

