import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.fixture
async def client():
    """Creates a virtual client to send requests to our application."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_index_page(client):
    """Test 1: Verify that the index page opens successfully."""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Task List" in response.text

@pytest.mark.asyncio
async def test_add_task_redirect(client):
    """Test 2: Successful task creation via form submission."""
    response = await client.post("/add", data={"title": "TestAdding", "description": "Understand the logic"}, follow_redirects=True)
    assert response.status_code == 200
    assert "TestAdding" in response.text

@pytest.mark.asyncio
async def test_toggle_task_status(client):
    """Test 3: Changing task status (completed / uncompleted)."""
    await client.post("/add", data={"title": "StatusTask"}, follow_redirects=True)
    
    index = await client.get("/")
    import re
    match = re.search(r"/toggle/([a-f0-9\-]{36})", index.text)
    assert match is not None
    task_id = match.group(1)

    response = await client.get(f"/toggle/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert "↩" in response.text or "✓" not in response.text

@pytest.mark.asyncio
async def test_toggle_task_not_found(client):
    """Test 4: Toggling status of a non-existent task (404 error)."""
    import uuid
    response = await client.get(f"/toggle/{uuid.uuid4()}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_task(client):
    """Test 5: Successful task deletion."""
    await client.post("/add", data={"title": "DeleteMe"}, follow_redirects=True)
    
    index = await client.get("/")
    import re
    match = re.search(r"/delete/([a-f0-9\-]{36})", index.text)
    assert match is not None
    task_id = match.group(1)

    response = await client.get(f"/delete/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert "DeleteMe" not in response.text

@pytest.mark.asyncio
async def test_delete_task_not_found(client):
    """Test 6: Attempting to delete a non-existent task (404 error)."""
    import uuid
    response = await client.get(f"/delete/{uuid.uuid4()}")
    assert response.status_code == 404