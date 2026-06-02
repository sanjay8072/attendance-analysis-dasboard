Attendance Analysis Dashboard

Quick start

1. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the app:

```powershell
python app.py
```

3. Open http://127.0.0.1:5000 in your browser.

Notes

- The app generates a sample `data/attendance.csv` file if none exists.
- Upload a CSV with columns `date, student_id, student_name, present` via the dashboard.
- If `data/attendance.csv` is missing, the app will auto-load `sample_attendance.csv` from the project root.
- Use the date range controls to filter charts.
- Login is required to access the dashboard.
- Default account:
  - `sanjay r` / `sanjay123`
- API endpoints: `/api/daily_rates`, `/api/absences`, `/api/students`, `/api/update_names`, `/api/upload`, `/api/summary`.
- The app now saves backups of `data/attendance.csv` to the `backups/` folder before overwriting it.
- Use the dashboard button to generate a public share link for read-only access.

Deployment

To run this app as a shared website, deploy it to a hosting service that supports Python and WSGI.

Recommended setup:
- `Procfile` with `web: gunicorn app:app`
- `requirements.txt` includes `gunicorn`
- `runtime.txt` can specify `python-3.11.16` or later

Example deploy steps:
1. Push your project to a GitHub repo.
2. Use PythonAnywhere, Railway, or another hosting provider.
3. Configure the host to run `gunicorn app:app`.

The app will then be accessible as a shared website for your team.

Docker (recommended for sharing the whole app)

Build and run locally with Docker:

```bash
docker build -t attendance-dashboard .
docker run -p 8000:8000 attendance-dashboard
```

Then open http://127.0.0.1:8000 (the container uses port 8000).

Share the project (GitHub)

1. Create a GitHub repository:
   - Go to https://github.com/new
   - Enter a repository name like `attendance-dashboard`
   - Leave it Public or Private depending on your preference
   - Do not initialize with README, .gitignore, or license (we already have files)
   - Click **Create repository**

2. In your project folder, run these commands in PowerShell or terminal:

```bash
git init
git add .
git commit -m "Attendance dashboard"
git branch -M main
```

3. Copy the remote URL from GitHub and paste it here:

```bash
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

4. Confirm the code is now on GitHub by visiting:

```text
https://github.com/<your-username>/<your-repo>
```

5. If you want a live website, deploy using one of these hosts:
   - Render: https://render.com
   - Railway: https://railway.app
   - Heroku: https://heroku.com
   - PythonAnywhere: https://pythonanywhere.com

6. On the host, choose your GitHub repo and set the start command to:

```text
gunicorn app:app
```

7. Once deployed, you will get a public website URL you can submit for your placement project.

Tip: If the host asks for the repo URL, paste the GitHub link from step 4.

CI/CD (optional)

You can add a GitHub Actions workflow to build/test and push a Docker image to a registry or deploy automatically to a service.
