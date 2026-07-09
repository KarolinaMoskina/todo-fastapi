import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.fixture
async def client():
    """Создает виртуального клиента для отправки запросов к нашему приложению."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_index_page(client):
    """Тест 1: Проверяем, что главная страница успешно открывается"""
    response = await client.get("/")
    assert response.status_code == 200
    assert "Список задач" in response.text

@pytest.mark.asyncio
async def test_add_task_redirect(client):
    """Тест 2: Успешное добавление задачи через форму"""
    response = await client.post("/add", data={"title": "ТестДобавления", "description": "Понять логику"}, follow_redirects=True)
    assert response.status_code == 200
    assert "ТестДобавления" in response.text

@pytest.mark.asyncio
async def test_toggle_task_status(client):
    """Тест 3: Изменение статуса задачи (выполнено / не выполнено)"""
    await client.post("/add", data={"title": "СтатусЗадача"}, follow_redirects=True)
    
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
    """Тест 4: Переключение статуса у несуществующей задачи (ошибка 404)"""
    import uuid
    response = await client.get(f"/toggle/{uuid.uuid4()}")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_delete_task(client):
    """Тест 5: Успешное удаление задачи"""
    await client.post("/add", data={"title": "УдалиМеняНафиг"}, follow_redirects=True)
    
    index = await client.get("/")
    import re
    match = re.search(r"/delete/([a-f0-9\-]{36})", index.text)
    assert match is not None
    task_id = match.group(1)

    response = await client.get(f"/delete/{task_id}", follow_redirects=True)
    assert response.status_code == 200
    assert "УдалиМеняНафиг" not in response.text

@pytest.mark.asyncio
async def test_delete_task_not_found(client):
    """Тест 6: Попытка удалить несуществующую задачу (ошибка 404)"""
    import uuid
    response = await client.get(f"/delete/{uuid.uuid4()}")
    assert response.status_code == 404