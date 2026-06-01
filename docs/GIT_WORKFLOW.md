# Quy trình Git cho nhóm (tránh conflict)

Repo: `Day-3-Lab-Chatbot-vs-react-agent-a4`  
Nhánh gốc: **`main`** (ổn định, demo được)

---

## 1. Chiến lược nhánh

```
main
 ├── feature/backend-api      ← Backend (API, tools, RAG, DB)
 ├── feature/llm-agent        ← LLM (prompt, ReAct tinh chỉnh)
 ├── feature/guardrails       ← Guardrails (input/tool/output)
 └── feature/frontend-ui      ← 2 Frontend (chỉ folder frontend/)
```

| Vai trò | Nhánh gợi ý | Chỉ sửa trong |
|---------|--------------|----------------|
| Backend (Nam) | `feature/backend-api` hoặc `namle24-backendapi` | `src/api/`, `src/tools/`, `src/rag/`, `src/db/`, `src/services/`, `src/core/factory.py`, `run_api.py`, `requirements-api.txt`, `docs/` |
| LLM | `feature/llm-agent` | **`src/agent/agent.py`** (ưu tiên), có thể `src/core/*_provider.py` nếu cần |
| Guardrails | `feature/guardrails` | `src/guardrails/` (tạo mới), hook trong `src/api/` (thống nhất trước) |
| Frontend A+B | `feature/frontend-ui` | **`frontend/`** (tạo folder mới, không đụng `src/`) |

### File “nhạy cảm” — chỉ 1 người chính

| File | Owner chính | Ghi chú |
|------|-------------|---------|
| `src/agent/agent.py` | LLM | Backend đã có bản ReAct cơ bản; LLM merge `main` rồi sửa prompt |
| `src/services/chat_service.py` | Backend | LLM không sửa trừ khi thống nhất |
| `.env` | Mỗi người local | **Không commit** |
| `data/` | Local | Chạy `python -m src.rag.ingest` sau pull |

---

## 2. Backend — push lần đầu (Nam)

Đang ở nhánh `namle24-backendapi` — có thể **đổi tên** cho đồng bộ team:

```bash
cd ~/VINAI/Day-3-Lab-Chatbot-vs-react-agent-a4
# macOS/Linux: source .venv/bin/activate
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# Windows (CMD): .venv\Scripts\activate.bat
# Windows (Git Bash): source .venv/Scripts/activate

# Đảm bảo không add nhầm secret / artifact
git status
# Không được thấy .env trong staged

git add \
  .env.example .gitignore \
  requirements.txt requirements-api.txt \
  run_api.py \
  docs/ \
  src/api/ src/tools/ src/rag/ src/db/ src/services/ \
  src/core/factory.py \
  src/__init__.py \
  src/agent/agent.py \
  tests/test_backend.py \
  vinfast_rag_data.json

# prompt.md: add nếu cả nhóm dùng làm spec chung
git add prompt.md

git commit -m "$(cat <<'EOF'
feat(backend): VinFast API, RAG tools, chat sessions, and ReAct wiring

Add FastAPI endpoints for chat, confirm, history, and direct tool access.
Include TF-IDF RAG ingest, SQLite persistence, and frontend/git docs.
EOF
)"

# Đổi tên nhánh (tùy chọn)
git branch -M feature/backend-api

git push -u origin feature/backend-api
```

Sau đó mở **Pull Request** trên GitHub: `feature/backend-api` → `main`.

---

## 3. Các thành viên khác — bắt đầu từ đâu

### Sau khi PR Backend được merge vào `main`

Mỗi người:

```bash
git checkout main
git pull origin main
```

### LLM

```bash
git checkout -b feature/llm-agent
# Chỉ sửa src/agent/agent.py (prompt, parse, max_steps)
git add src/agent/agent.py
git commit -m "feat(llm): improve ReAct prompt for VF5 vs VF6 use case"
git push -u origin feature/llm-agent
# PR → main
```

### Frontend (2 người — 1 nhánh hoặc 2 nhánh con)

**Cách A — 1 nhánh chung (đơn giản):**

```bash
git checkout main
git pull
git checkout -b feature/frontend-ui
mkdir -p frontend
cd frontend && npm create vite@latest . -- --template react-ts
# ... code UI ...
git add frontend/
git commit -m "feat(frontend): chat shell and API integration"
git push -u origin feature/frontend-ui
```

**Cách B — 2 nhánh, merge tuần tự:**

- `feature/frontend-chat` (A: layout + chat)
- `feature/frontend-confirm-table` (B: confirm + bảng so sánh)  
  B merge `main` thường xuyên, PR nhỏ.

### Guardrails

```bash
git checkout -b feature/guardrails
mkdir -p src/guardrails
# Không sửa src/tools/ logic — gọi qua middleware
git push -u origin feature/guardrails
```

---

## 4. Quy tắc hàng ngày (giảm conflict)

1. **`main` luôn chạy được** — chỉ merge qua PR, đã test cơ bản.
2. **Pull `main` mỗi sáng** trước khi code:
   ```bash
   git checkout feature/your-branch
   git fetch origin
   git merge origin/main
   ```
3. **PR nhỏ** (< 500 dòng nếu có thể), 1 mục tiêu.
4. **Không force push** lên `main`.
5. **Communicate** trên PR nếu đụng `agent.py` hoặc `chat_service.py`.

---

## 5. Ai merge trước?

Thứ tự đề xuất:

1. **Backend** → `main` (API contract + docs)
2. **LLM** → `main` (prompt, dựa trên API ổn định)
3. **Frontend** → `main` (song song với LLM nếu chỉ `frontend/`)
4. **Guardrails** → `main` (cuối: bọc API, ít đụng logic tools)

Frontend và LLM **song song** được vì khác folder.

---

## 6. Xử lý conflict thường gặp

| Conflict tại | Cách xử lý |
|--------------|------------|
| `src/agent/agent.py` | Giữ logic loop Backend; LLM giữ phần prompt — trao đổi 5 phút trên call |
| `requirements.txt` | Gộp cả hai dependency, chạy lại `pip install` |
| `src/services/chat_service.py` | Ưu tiên Backend; Guardrails thêm hook qua PR riêng |
| `frontend/*` | Tự merge trong nhóm Frontend |

```bash
# Sau khi merge main bị conflict
git merge origin/main
# Sửa file conflict trong editor
git add <file đã sửa>
git commit
```

---

## 7. Checklist trước khi push

- [ ] Không có `.env` trong `git status`
- [ ] `data/` không bị add (đã trong `.gitignore`)
- [ ] `python -m src.rag.ingest` chạy được trên máy sạch (ghi trong PR)
- [ ] `pytest tests/test_backend.py` pass
- [ ] Đã cập nhật `docs/FRONTEND_GUIDE.md` nếu đổi API

---

## 8. Tóm tắt cho Nam (bạn) ngay bây giờ

| Việc | Lệnh / hành động |
|------|------------------|
| Nhánh hiện tại | `namle24-backendapi` → đổi `feature/backend-api` |
| Push | `git push -u origin feature/backend-api` |
| Không push | `.env`, `data/`, `.venv/` |
| Báo team | Link PR + `docs/FRONTEND_GUIDE.md` + chạy `python run_api.py` |
| LLM / FE | Bắt đầu nhánh **sau khi** PR backend merge (hoặc branch từ `feature/backend-api` nếu cần API sớm) |

**Branch từ backend chưa merge (API sớm cho FE):**

```bash
git fetch origin
git checkout -b feature/frontend-ui origin/feature/backend-api
```
