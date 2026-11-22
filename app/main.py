"""task manager: FastAPI REST API + embedded HTML/JS UI."""
import time
from contextlib import asynccontextmanager
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func, text
from sqlalchemy.orm import Session

from database import Base, engine, get_db


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    done = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    done: bool | None = None


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    done: bool


def init_db(retries: int = 10, delay: float = 3.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except Exception as exc:  # DB may still be starting
            print(f"DB not ready ({attempt}/{retries}): {exc}", flush=True)
            time.sleep(delay)
    print("Starting without DB; /health stays up, API returns errors.", flush=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Task Manager", lifespan=lifespan)


@app.get("/health")
def health():
    """Liveness probe for the ALB: does not touch the DB so a DB blip
    does not cause all tasks to be killed."""
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "up"}


@app.get("/api/tasks", response_model=List[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.id).all()


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    task = Task(title=payload.title)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.put("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if payload.title is not None:
        task.title = payload.title
    if payload.done is not None:
        task.done = payload.done
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    db.delete(task)
    db.commit()
    return Response(status_code=204)


@app.get("/api/cpu")
def burn_cpu(ms: int = 200):
    """CPU-bound endpoint used by the load test to trigger Auto Scaling."""
    end = time.perf_counter() + min(max(ms, 1), 2000) / 1000
    n = 0
    while time.perf_counter() < end:
        n += sum(i * i for i in range(1000))
    return {"burned_ms": ms}


INDEX_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Student Task Manager</title>
<style>
body{font-family:system-ui,sans-serif;max-width:640px;margin:2rem auto;padding:0 1rem}
form{display:flex;gap:.5rem}input[type=text]{flex:1;padding:.5rem}
li{display:flex;align-items:center;gap:.5rem;padding:.4rem 0;border-bottom:1px solid #ddd}
li span{flex:1}.done span{text-decoration:line-through;color:#888}
ul{list-style:none;padding:0}
</style></head><body>
<h1>Student Task Manager</h1>
<form id="f"><input id="t" type="text" placeholder="New task" maxlength="200" required>
<button>Add</button></form>
<ul id="l"></ul>
<p><a href="/docs">API docs</a> · <a href="/health">health</a></p>
<script>
const l=document.getElementById('l');
async function api(m,u,b){const r=await fetch(u,{method:m,headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined});if(!r.ok)throw new Error(await r.text());return r.status===204?null:r.json()}
async function load(){const ts=await api('GET','/api/tasks');l.replaceChildren();
for(const t of ts){const li=document.createElement('li');if(t.done)li.className='done';
const c=document.createElement('input');c.type='checkbox';c.checked=t.done;
c.onchange=async()=>{await api('PUT','/api/tasks/'+t.id,{done:c.checked});load()};
const s=document.createElement('span');s.textContent=t.title;
const d=document.createElement('button');d.textContent='Delete';
d.onclick=async()=>{await api('DELETE','/api/tasks/'+t.id);load()};
li.append(c,s,d);l.append(li)}}
document.getElementById('f').onsubmit=async e=>{e.preventDefault();const i=document.getElementById('t');
await api('POST','/api/tasks',{title:i.value});i.value='';load()};
load().catch(e=>alert('Failed to load tasks: '+e.message));
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML
