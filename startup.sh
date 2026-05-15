#!/bin/bash
set -e
source /antenv/bin/activate
cd /home/site/wwwroot
exec uvicorn api_main:app --host 0.0.0.0 --port 8000 --workers 1 --timeout-keep-alive 300
