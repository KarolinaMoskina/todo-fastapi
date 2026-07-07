from fastapi import FastAPI, Depends, Form, Request, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.database import get_session, init_db, kill_engine
from app import crud
from app.schemas import TaskCreate, UpdateTask
from contextlib import asynccontextmanager

app = FastAPI(title="TODO_list")

templates = Jinja2Templates(directory=".")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>TODO_list</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .todo-container { max-width: 650px; margin: 50px auto; background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .completed-task { text-decoration: line-through; color: #6c757d; }
    </style>
</head>
<body>
    <div class="container">
        <div class="todo-container">
            <h2 class="text-center mb-4 text-primary">Tasks</h2>
            
            {% if not edit_task %}
            <form action="/add" method="post" class="mb-4">
                <div class="input-group mb-2">
                    <input type="text" name="title" class="form-control" placeholder="Task name..." required>
                    <button class="btn btn-primary" type="submit">Add</button>
                </div>
                <input type="text" name="description" class="form-control form-control-sm" placeholder="Description (optional)">
            </form>
            {% else %}
            
            <form action="/edit/{{ edit_task.id }}" method="post" class="mb-4 p-3 bg-light border rounded">
                <h5 class="text-secondary mb-3">Edit tasks</h5>
                <div class="mb-2">
                    <input type="text" name="title" class="form-control" value="{{ edit_task.title }}" required>
                </div>
                <div class="mb-3">
                    <input type="text" name="description" class="form-control form-control-sm" value="{{ edit_task.description or '' }}">
                </div>
                <div class="d-flex gap-2">
                    <button class="btn btn-success btn-sm" type="submit">Save</button>
                    <a href="/" class="btn btn-secondary btn-sm">Cancel</a>
                </div>
            </form>
            {% endif %}

            <ul class="list-group">
                {% for task in tasks %}
                <li class="list-group-item d-flex justify-content-between align-items-center {% if task.completed %}list-group-item-light{% endif %}">
                    <div>
                        <span class="fw-bold {% if task.completed %}completed-task{% endif %}">{{ task.title }}</span>
                        {% if task.description %}
                            <br><small class="text-muted">{{ task.description }}</small>
                        {% endif %}
                    </div>
                    <div class="btn-group btn-group-sm">
                        {% if not task.completed %}
                            <a href="/toggle/{{ task.id }}" class="btn btn-success">✓</a>
                            <a href="/?edit_id={{ task.id }}" class="btn btn-warning">✏️</a>
                        {% else %}
                            <a href="/toggle/{{ task.id }}" class="btn btn-secondary">↩</a>
                        {% endif %}
                        <a href="/delete/{{ task.id }}" class="btn btn-danger">Delete</a>
                    </div>
                </li>
                {% else %}
                <li class="list-group-item text-center text-muted py-3">No tasks. Chill Bro!</li>
                {% endfor %}
            </ul>
        </div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request, edit_id: uuid.UUID = None, db: AsyncSession = Depends(get_session)):
    tasks = await crud.list_tasks(db)
    
    edit_task = None
    if edit_id:
        edit_task = await crud.get_task(db, edit_id)
        if not edit_task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
    return templates.env.from_string(HTML_TEMPLATE).render(
        request=request, 
        tasks=tasks, 
        edit_task=edit_task
    )

@app.post("/add")
async def add_task(title: str = Form(...), description: str = Form(None), db: AsyncSession = Depends(get_session)):
    task_data = TaskCreate(title=title, description=description if description else None)
    await crud.create_task(db, task_data)
    return RedirectResponse(url="/", status_code=303)

@app.post("/edit/{task_id}")
async def edit_task_submit(task_id: uuid.UUID, title: str = Form(...), description: str = Form(None), db: AsyncSession = Depends(get_session)):
    update_data = UpdateTask(title=title, description=description if description else None)
    updated = await crud.updated_task(db, task_id, update_data)
    
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task to modify not found")
        
    return RedirectResponse(url="/", status_code=303)

@app.get("/toggle/{task_id}")
async def toggle_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    task = await crud.get_task(db, task_id)
    
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
    update_data = UpdateTask(completed=not task.completed)
    await crud.updated_task(db, task_id, update_data)
    return RedirectResponse(url="/", status_code=303)

@app.get("/delete/{task_id}")
async def delete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    deleted = await crud.delete_task(db, task_id)
    
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task to delete not found")
        
    return RedirectResponse(url="/", status_code=303)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await kill_engine()

app.router.lifespan_context = lifespan