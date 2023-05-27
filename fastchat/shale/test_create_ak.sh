
curl http://api.shaleprotocol.com:30085/v1/shale_create_api_key \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "'$1'"
  }'

curl http://api.shaleprotocol.com:30085/v1/shale_create_api_key \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "'$1'", "user_id": "test_user"
  }'

curl http://api.shaleprotocol.com:30085/v1/shale_create_api_key \
  -H "Content-Type: application/json" \
  -d '{
    "secret": "'$1'", "user_id": "test_user", "user_email": "test@shaleprotocol.com"
  }'
