import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crypto_openssl import build_task_payload, sign_payload, verify_payload
from app.models import Task
from app.schemas import TaskCreate, UpdateTask


def verify_task_integrity(task: Task) -> bool:
    payload = build_task_payload(task.title, task.description, task.completed)
    return verify_payload(payload, task.signature)


async def create_task(session: AsyncSession, data: TaskCreate) -> Task:
    payload = build_task_payload(data.title, data.description, False)
    signature = sign_payload(payload)

    task = Task(
        title=data.title,
        description=data.description,
        signature=signature,
    )
    session.add(task)
    await session.flush()
    await session.commit()
    await session.refresh(task)
    return task


async def get_task(session: AsyncSession, task_id: uuid.UUID) -> Task | None:
    return await session.get(Task, task_id)


async def list_tasks(session: AsyncSession, *, only_pending: bool = False) -> Sequence[Task]:
    stmt = select(Task)
    if only_pending:
        stmt = stmt.where(Task.completed.is_(False))

    stmt = stmt.order_by(Task.completed.asc(), Task.created_at.desc())
    res = await session.execute(stmt)
    return res.scalars().all()


async def updated_task(session: AsyncSession, task_id: uuid.UUID, data: UpdateTask) -> Task | None:
    task = await session.get(Task, task_id)
    if task is None:
        return None

    changes = data.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(task, field, value)

    payload = build_task_payload(task.title, task.description, task.completed)
    task.signature = sign_payload(payload)

    await session.flush()
    await session.commit()
    await session.refresh(task)
    return task


async def delete_task(session: AsyncSession, task_id: uuid.UUID) -> bool:
    task = await session.get(Task, task_id)
    if task is None:
        return False
    await session.delete(task)
    await session.flush()
    await session.commit()
    return True