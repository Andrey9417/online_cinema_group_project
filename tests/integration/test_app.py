async def test_app_starts_and_serves_openapi(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    assert "openapi" in response.json()