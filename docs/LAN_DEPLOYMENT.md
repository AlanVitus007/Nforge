# NForge: Two-Computer LAN Deployment Guide (Phase 9.2)

This guide details how to host **NForge** on a primary Windows computer (**Computer A: Server/Host**) and allow another computer on the same local network (**Computer B: Client**) to access the application and collaborate on research projects in real-time.

---

## 1. Architecture Overview

```
 ┌──────────────────────────────────────────────────────────────┐
 │                      COMPUTER A (Host/Server)                │
 │                     IP: e.g. 192.168.1.10                    │
 │                                                              │
 │  ┌────────────────────────┐       ┌───────────────────────┐  │
 │  │       PostgreSQL       │       │    Django REST API    │  │
 │  │  Port 5432 (Localhost) │◄──────┤    Port 8000 (LAN)    │  │
 │  └────────────────────────┘       └───────────▲───────────┘  │
 │                                               │              │
 │                                   ┌───────────┴───────────┐  │
 │                                   │  Vite React Frontend  │  │
 │                                   │    Port 5173 (LAN)    │  │
 │                                   └───────────▲───────────┘  │
 └───────────────────────────────────────────────┼──────────────┘
                                                 │ Wi-Fi / LAN
                                                 │
 ┌───────────────────────────────────────────────┴──────────────┐
 │                      COMPUTER B (Client)                     │
 │                     IP: e.g. 192.168.1.25                    │
 │                                                              │
 │                  Web Browser (Chrome / Edge / Firefox)      │
 │                  Navigates to: http://192.168.1.10:5173      │
 └──────────────────────────────────────────────────────────────┘
```

### Critical Collaboration Concept
> [!IMPORTANT]
> Both Computer A and Computer B must connect to the **same running backend and database instance** on Computer A. 
> Two independent localhost instances cannot collaborate because each would read and write to its own separate SQLite/PostgreSQL database. Running Computer A as the centralized host allows multiple users to share projects, papers, members, and AI research sessions seamlessly.

---

## 2. Prerequisites on Computer A

1. **Python 3.10+** with project virtual environment (`backend/venv`).
2. **Node.js 18+** with dependencies installed in `frontend/`.
3. **PostgreSQL** running locally on Computer A (database `nforge`).
4. Both computers connected to the **same Wi-Fi or local wired subnet**.

---

## 3. Step-by-Step Setup Instructions

### Step 1: Find Computer A's LAN IP Address
On Computer A, open PowerShell or Command Prompt and run:
```cmd
ipconfig
```
Locate your active network adapter (e.g., `Wireless LAN adapter Wi-Fi` or `Ethernet adapter Ethernet`) and find the **IPv4 Address**:
```
IPv4 Address. . . . . . . . . . . : 192.168.1.10
```
*(Note: Replace `192.168.1.10` with your actual host IP throughout this guide).*

---

### Step 2: Configure Environment Files on Computer A

#### Backend Configuration (`backend/.env`)
Edit `backend/.env` on Computer A to include your host IP in `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`:
```env
# Append your Computer A LAN IP to ALLOWED_HOSTS
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.10

# Allow both localhost and your LAN frontend URL in CORS
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.10:5173

# Database remains strictly local to Computer A
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=nforge
DB_USER=postgres
DB_PASSWORD=postgres
```

#### Frontend Configuration (`frontend/.env`)
Edit `frontend/.env` on Computer A to point to Computer A's LAN backend:
```env
# Point to Computer A's backend (the /api prefix is automatically handled if omitted)
VITE_API_URL=http://192.168.1.10:8000/api
```

---

### Step 3: Start PostgreSQL on Computer A
Ensure the PostgreSQL Windows service is running:
```powershell
Get-Service -Name postgresql*
```
*(PostgreSQL remains bound to `127.0.0.1:5432` on Computer A. It is NOT exposed to the network).*

---

### Step 4: Start Django Backend on Computer A
Open a PowerShell terminal on Computer A:
```powershell
cd c:\Clg\projects\Nforge\NForge\backend
.\venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000
```
> [!NOTE]
> Binding to `0.0.0.0:8000` tells Django to accept incoming connections from all network interfaces on Computer A.

---

### Step 5: Start Vite Frontend on Computer A
Open a second PowerShell terminal on Computer A:
```powershell
cd c:\Clg\projects\Nforge\NForge\frontend
npm run dev -- --host 0.0.0.0
```
*(Or use the convenience script: `npm run dev:lan`)*

Vite will display:
```
  VITE ready in 350 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: http://192.168.1.10:5173/
```

---

### Step 6: Verify and Connect

| Machine | Purpose | Target URL |
| :--- | :--- | :--- |
| **Computer A (Host)** | Local browser access | `http://localhost:5173/` |
| **Computer A (Host)** | API Health check | `http://localhost:8000/api/health/` |
| **Computer B (Client)** | Remote browser access | `http://192.168.1.10:5173/` |
| **Computer B (Client)** | API Health check | `http://192.168.1.10:8000/api/health/` |

---

## 4. Windows Firewall Configuration on Computer A

For Computer B to connect, Windows Defender Firewall on Computer A must allow inbound TCP traffic on ports **8000** (Django) and **5173** (Vite).

> [!WARNING]
> Do NOT expose PostgreSQL port `5432` to the LAN. PostgreSQL is only accessed locally by Django.

### Method 1: PowerShell (Run as Administrator)
Open an elevated PowerShell prompt on Computer A:
```powershell
# Allow Django Backend (Port 8000)
New-NetFirewallRule -DisplayName "NForge Django Backend (TCP 8000)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow

# Allow Vite Frontend (Port 5173)
New-NetFirewallRule -DisplayName "NForge Vite Frontend (TCP 5173)" -Direction Inbound -LocalPort 5173 -Protocol TCP -Action Allow
```

To remove these rules after testing:
```powershell
Remove-NetFirewallRule -DisplayName "NForge Django Backend (TCP 8000)"
Remove-NetFirewallRule -DisplayName "NForge Vite Frontend (TCP 5173)"
```

### Method 2: Windows Defender Firewall GUI
1. Press `Win + R`, type `wf.msc`, and press **Enter**.
2. In the left sidebar, click **Inbound Rules**.
3. In the right sidebar, click **New Rule...**.
4. Select **Port**, then click **Next**.
5. Select **TCP**, and in **Specific local ports**, enter: `8000, 5173`.
6. Select **Allow the connection**, then click **Next**.
7. Check **Private** (and optionally Domain; avoid Public if on untrusted Wi-Fi).
8. Name the rule: `NForge LAN Access (8000, 5173)` and click **Finish**.

---

## 5. Media & PDF Storage Behavior

- Uploaded research papers are stored in `backend/media/papers/` on Computer A's local drive.
- While `DEBUG=True`, Django serves media files directly through `backend/config/urls.py` via `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)`.
- The Vite development server on Computer A proxies `/media/` requests to Django.
- When Computer B opens a paper, the PDF is loaded in the viewer cleanly without cross-origin iframe restrictions.

---

## 6. Real-Time Collaboration Test Plan

### Test Part 1: Project Owner (Computer A) & Editor (Computer B)
1. **Computer A (Owner)**:
   - Open `http://localhost:5173/` (or `http://192.168.1.10:5173/`).
   - Register or log in as User A (`owner_user`).
   - Create a project: *"LAN Multi-Agent Research"*.
   - Upload one or more PDF research papers.
   - Go to Collaborators / Friends page: send a friend request or project invite to User B as **EDITOR**.
2. **Computer B (Editor)**:
   - Open `http://192.168.1.10:5173/` in a web browser.
   - Register or log in as User B (`editor_user`).
   - Accept the friend request and/or project invitation.
   - Open *"LAN Multi-Agent Research"* from the Projects list.
   - Confirm all uploaded papers from Computer A appear.
   - Open a paper in the Paper Viewer and verify the PDF loads and renders correctly.
   - Open the **Research Workspace**, create a new session, and submit an AI query.
   - Verify that the AI response, synthesis summary, and evidence cards generate properly.
3. **Computer A (Owner)**:
   - Refresh or navigate to the project's Research Workspace.
   - Confirm that User B's new session, queries, and AI synthesis are visible.

### Test Part 2: Role-Based Access Control (VIEWER Role)
1. **Computer A (Owner)**:
   - Invite a third user (`viewer_user`) with role **VIEWER**.
2. **Computer B (Viewer)**:
   - Log in as `viewer_user` and open the project.
   - **Allowed**: Can view project metadata, view papers, browse research sessions, and read historical AI analyses.
   - **Restricted**:
     - Cannot upload, edit, or delete papers.
     - Cannot trigger new AI synthesis / questions.
     - Cannot invite or remove project members.

---

## 7. Security and Production Boundaries

- **Development Only**: This configuration is designed specifically for local LAN collaboration during development and testing.
- **Do Not Expose to Public Internet**: Do not configure router port forwarding (NAT) or expose ports 8000/5173 to public IPs.
- **Strict CORS**: Do not set `CORS_ALLOW_ALL_ORIGINS = True` or use wildcard `*` origins. Only explicitly trusted origins (`localhost` and the host LAN IP) are permitted.
- **Authentication & RBAC**: Token authentication, session isolation, and owner/editor/viewer permissions remain fully enforced across all LAN requests.
