#!/bin/bash
# Connectivity test for service2
curl -sf "${SERVICE_BASE_URL}/health" -o /dev/null
