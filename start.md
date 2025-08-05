# 服务启动的顺序


## 1、启动后端

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 2、启动AI服务

```bash
 python -m ai_engine.main
```

## 3、启动前端
```bash
cd frontend
npm start
```

