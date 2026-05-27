#What to test:

#Sending rapid-fire requests to the API endpoints to verify that your rate-limiting decorators or middleware block traffic after exceeding thresholds (429 Too Many Requests).

#Verifying that authenticated users or specific trusted IPs bypass or have higher rate limits than unauthenticated clients.

import sys 
