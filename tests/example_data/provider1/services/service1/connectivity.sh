#!/bin/bash
# Connectivity test for service1
curl -sf "${SERVICE_BASE_URL}/health" -o /dev/null
